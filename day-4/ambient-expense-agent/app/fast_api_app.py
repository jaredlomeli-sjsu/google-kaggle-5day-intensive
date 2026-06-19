# ruff: noqa
"""
FastAPI wrapper that exposes the expense agent as an ambient (event-driven) service.
Accepts Pub/Sub push messages and runs them through the ADK workflow.
"""

import base64
import json
import re

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import app as adk_app

fast_api_app = FastAPI(title="Ambient Expense Agent")
session_service = InMemorySessionService()
runner = Runner(app=adk_app, session_service=session_service)

APP_NAME = "expense_agent"


def _normalize_subscription(sub: str) -> str:
    """Shorten a fully-qualified Pub/Sub subscription path to a readable ID."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", sub)[-64:]


@fast_api_app.post("/apps/expense_agent/trigger/pubsub")
async def pubsub_trigger(request: Request):
    """Receive a Pub/Sub push message and process it as an expense submission."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    message = body.get("message", {})
    subscription = body.get("subscription", "default-sub")
    encoded_data = message.get("data", "")

    try:
        decoded = base64.b64decode(encoded_data).decode("utf-8")
        payload = json.loads(decoded)
    except Exception:
        decoded = encoded_data
        payload = {"description": decoded}

    user_id = _normalize_subscription(subscription)
    session = await session_service.create_session(app_name=APP_NAME, user_id=user_id)

    expense_text = payload.get("description", json.dumps(payload))

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=expense_text)],
    )

    result_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            result_text = event.content.parts[-1].text or result_text

    return JSONResponse({"status": "processed", "result": result_text})


@fast_api_app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(fast_api_app, host="0.0.0.0", port=8080)
