"""
Manager Dashboard — FastAPI app for the human-in-the-loop approval workflow.

HOW TO RUN LOCALLY:
  Terminal 1: cd expense-agent && uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
  Terminal 2: cd manager-dashboard && uv run uvicorn main:app --reload --port 8081
  Browser:    http://localhost:8081
"""

import base64
import json
import os
from typing import List

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Expense Manager Dashboard")
templates = Jinja2Templates(directory="templates")

AGENT_URL = "http://localhost:8080/apps/expense_agent/trigger/pubsub"
AGENT_RUNTIME_ID = os.getenv("AGENT_RUNTIME_ID", "")

# In-memory store for pending sessions (local mode)
pending_sessions: List[dict] = []
session_counter = 0


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ExpenseSubmission(BaseModel):
    submitter: str
    amount: float
    category: str
    description: str
    date: str


class ActionRequest(BaseModel):
    session_id: str
    action: str  # "approve" or "reject"
    reviewer: str = "manager"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/submit")
async def submit_expense(expense: ExpenseSubmission):
    """Receive a form submission, send it to the expense agent, handle the result."""
    global session_counter

    # Build the expense text the agent parses
    expense_text = (
        f"${expense.amount:.2f} {expense.description} "
        f"submitted by {expense.submitter} "
        f"category: {expense.category} date: {expense.date}"
    )

    # Encode exactly like a real Pub/Sub message would
    payload = {
        "description": expense_text,
        "amount": expense.amount,
        "submitter": expense.submitter,
        "category": expense.category,
        "date": expense.date,
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AGENT_URL,
                json={"message": {"data": encoded}, "subscription": "local-form-sub"},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Expense agent is not running. Start it on port 8080 first.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    agent_response = result.get("result", "")

    # If human review required, store it as a pending session
    if "HUMAN REVIEW" in agent_response.upper():
        session_counter += 1
        session_id = f"local-session-{session_counter:03d}"

        risk_level = "MEDIUM"
        if "HIGH" in agent_response:
            risk_level = "HIGH"
        elif "LOW" in agent_response:
            risk_level = "LOW"

        pending_sessions.append({
            "session_id": session_id,
            "submitter": expense.submitter,
            "amount": expense.amount,
            "category": expense.category,
            "description": expense.description,
            "date": expense.date,
            "status": "pending_review",
            "risk_level": risk_level,
            "ai_recommendation": agent_response,
        })

        return JSONResponse({
            "status": "pending_review",
            "session_id": session_id,
            "message": f"${expense.amount:.2f} requires human review. Card added to dashboard.",
        })

    # Auto-approved
    return JSONResponse({
        "status": "auto_approved",
        "message": agent_response or f"${expense.amount:.2f} auto-approved.",
    })


@app.get("/api/pending")
async def get_pending():
    """Return pending sessions waiting for manager decision."""
    return JSONResponse(pending_sessions)


@app.post("/api/action")
async def submit_action(body: ActionRequest):
    """Approve or reject a pending session."""
    global pending_sessions

    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    # Remove from pending list
    match = next((s for s in pending_sessions if s["session_id"] == body.session_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Session not found.")

    pending_sessions = [s for s in pending_sessions if s["session_id"] != body.session_id]

    return JSONResponse({
        "status": "success",
        "session_id": body.session_id,
        "decision": body.action.upper(),
        "reviewer": body.reviewer,
        "message": f"Expense {body.action}d by {body.reviewer}.",
    })


@app.get("/health")
async def health():
    return {"status": "ok", "pending_count": len(pending_sessions)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
