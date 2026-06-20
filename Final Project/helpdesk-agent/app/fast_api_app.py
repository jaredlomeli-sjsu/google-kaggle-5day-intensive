"""
FastAPI wrapper — runs the helpdesk agent locally and accepts Pub/Sub push messages.

HOW TO RUN LOCALLY:
  1. Fill in .env with GOOGLE_API_KEY (or Vertex AI credentials)
  2. Install: uv sync
  3. Start:   uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
  4. Test:    curl -X POST http://localhost:8080/apps/helpdesk_agent/trigger/pubsub \\
                -H "Content-Type: application/json" \\
                -d '{"message": {"data": ""}, "description": "Password reset for john@nexus.com"}'
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

fast_api_app = FastAPI(title="Nexus Technologies Helpdesk Agent")
session_service = InMemorySessionService()
runner = Runner(app=adk_app, session_service=session_service)

APP_NAME = "helpdesk_agent"


def _normalize_subscription(sub: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", sub)[-64:]


@fast_api_app.post("/apps/helpdesk_agent/trigger/pubsub")
async def pubsub_trigger(request: Request):
    """Receive a Pub/Sub push message and run it through the helpdesk agent."""
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

    ticket_text = payload.get("description", json.dumps(payload))

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=ticket_text)],
    )

    result_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                result_text = event.content.parts[-1].text or result_text
    except Exception as e:
        err = str(e)
        if any(k in err for k in ("RESOURCE_EXHAUSTED", "429", "API_KEY_INVALID", "UNAUTHENTICATED")):
            # API key not set or quota hit — fall back gracefully so dashboard still works
            result_text = (
                "HUMAN REVIEW REQUIRED: AI analysis unavailable "
                "(Gemini API key not set or quota exceeded). "
                "Please review this ticket manually in the supervisor dashboard."
            )
        else:
            raise

    return JSONResponse({"status": "processed", "result": result_text})


@fast_api_app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(fast_api_app, host="0.0.0.0", port=8080)
