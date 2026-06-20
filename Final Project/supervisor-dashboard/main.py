"""
Supervisor Dashboard — FastAPI app for the IT helpdesk human-in-the-loop workflow.

HOW TO RUN LOCALLY:
  Terminal 1: cd helpdesk-agent && uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
  Terminal 2: cd supervisor-dashboard && uv run uvicorn main:app --reload --port 8081
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

app = FastAPI(title="Nexus Technologies IT Helpdesk Supervisor")
templates = Jinja2Templates(directory="templates")

AGENT_URL = "http://localhost:8080/apps/helpdesk_agent/trigger/pubsub"
AGENT_RUNTIME_ID = os.getenv("AGENT_RUNTIME_ID", "")

# In-memory store for pending tickets (local mode)
pending_tickets: List[dict] = []
ticket_counter = 0


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TicketSubmission(BaseModel):
    reporter: str
    category: str
    affected_system: str
    description: str


class ActionRequest(BaseModel):
    session_id: str
    action: str  # "escalate" or "close"
    reviewer: str = "supervisor"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/submit")
async def submit_ticket(ticket: TicketSubmission):
    """Receive a form submission, send it to the helpdesk agent, handle the result."""
    global ticket_counter

    ticket_text = (
        f"{ticket.description} "
        f"Reported by {ticket.reporter} "
        f"category: {ticket.category} "
        f"affected system: {ticket.affected_system}"
    )

    payload = {
        "description": ticket_text,
        "reporter": ticket.reporter,
        "category": ticket.category,
        "affected_system": ticket.affected_system,
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AGENT_URL,
                json={"message": {"data": encoded}, "subscription": "local-helpdesk-sub"},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Helpdesk agent is not running. Start it on port 8080 first.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    agent_response = result.get("result", "")

    # If human review required, store it as a pending ticket card
    if "HUMAN REVIEW" in agent_response.upper():
        ticket_counter += 1
        session_id = f"ticket-{ticket_counter:04d}"

        risk_level = "MEDIUM"
        if "HIGH" in agent_response:
            risk_level = "HIGH"
        elif "LOW" in agent_response:
            risk_level = "LOW"

        pending_tickets.append({
            "session_id": session_id,
            "reporter": ticket.reporter,
            "category": ticket.category,
            "affected_system": ticket.affected_system,
            "description": ticket.description,
            "status": "pending_review",
            "risk_level": risk_level,
            "ai_recommendation": agent_response,
        })

        return JSONResponse({
            "status": "pending_review",
            "session_id": session_id,
            "message": f"Ticket {session_id} requires supervisor review. Card added to dashboard.",
        })

    # Auto-resolved or security-flagged — no dashboard card needed
    return JSONResponse({
        "status": "auto_resolved",
        "message": agent_response or "Ticket processed automatically.",
    })


@app.get("/api/pending")
async def get_pending():
    """Return pending tickets waiting for supervisor decision."""
    return JSONResponse(pending_tickets)


@app.post("/api/action")
async def submit_action(body: ActionRequest):
    """Escalate or close a pending ticket."""
    global pending_tickets

    if body.action not in ("escalate", "close"):
        raise HTTPException(status_code=400, detail="action must be 'escalate' or 'close'")

    match = next((t for t in pending_tickets if t["session_id"] == body.session_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    pending_tickets = [t for t in pending_tickets if t["session_id"] != body.session_id]

    return JSONResponse({
        "status": "success",
        "session_id": body.session_id,
        "decision": body.action.upper(),
        "reviewer": body.reviewer,
        "message": f"Ticket {body.action}d by {body.reviewer}.",
    })


@app.get("/health")
async def health():
    return {"status": "ok", "pending_count": len(pending_tickets)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
