# Coding Agent Guide — Nexus Technologies IT Helpdesk Agent

## Project Overview

This is a production-grade IT helpdesk ticket triage system for **Nexus Technologies**.
It uses Google ADK 2.0 to build an event-driven workflow that automatically handles
employee IT support tickets with three outcomes:

1. **Auto-resolve**: Routine tickets (password reset, printer, WiFi, VPN) are closed
   instantly with a relevant KB article — no LLM call required.
2. **Security escalation**: Tickets mentioning phishing, malware, data breach, or
   credential theft are flagged to the Security Operations team, bypassing the LLM.
3. **Human review**: All other elevated tickets are analyzed by Gemini for severity
   (LOW/MEDIUM/HIGH) and queued in the Supervisor Dashboard for an IT supervisor decision.

## Prerequisites

Install the CLI (one-time):
```bash
uv tool install google-agents-cli
```

## Architecture

```
START → parse_ticket → classify_priority
  ├─ 'routine'  → auto_resolve       (KB article, no LLM)
  └─ 'elevated' → security_screen
                   ├─ 'threat' → flag_security    (SOC alert, no LLM)
                   └─ 'clean'  → risk_analyzer    (Gemini 2.0 Flash Lite)
                                   ↓
                              human_review         (Supervisor Dashboard)
```

## Two-Service Setup (local development)

```
helpdesk-agent/       → FastAPI on port 8080 (the AI triage agent)
supervisor-dashboard/ → FastAPI on port 8081 (the human approval UI)
```

The dashboard submits tickets to the agent via its Pub/Sub endpoint and displays
pending tickets that need an IT supervisor decision (escalate or close).

## Agent Endpoint Contract

```
POST /apps/helpdesk_agent/trigger/pubsub
Content-Type: application/json

{
  "message": {
    "data": "<base64-encoded JSON payload>"
  },
  "subscription": "local-helpdesk-sub"
}

Payload (before base64):
{
  "description": "<full ticket text including reporter, category, system>",
  "reporter": "email@nexus.com",
  "category": "Software | Hardware | Network | Security | Account/Access | Other",
  "affected_system": "<system name>"
}

Response:
{
  "status": "processed",
  "result": "<agent decision text>"
}
```

Result text starts with:
- `AUTO-RESOLVED:` — routine ticket closed with KB article
- `SECURITY ESCALATION:` — threat detected, SOC alerted
- `HUMAN REVIEW REQUIRED:` — elevated ticket needing supervisor action

## Supervisor Dashboard Endpoints

```
GET  /              → HTML dashboard (glassmorphic dark-teal theme)
GET  /api/pending   → JSON list of tickets awaiting supervisor decision
POST /api/submit    → Submit a new ticket (from the dashboard form)
POST /api/action    → Escalate or close a pending ticket
GET  /health        → Health check

POST /api/submit body:
{
  "reporter": "john@nexus.com",
  "category": "Network",
  "affected_system": "Corporate ERP",
  "description": "ERP system down, 50 users affected"
}

POST /api/action body:
{
  "session_id": "ticket-0001",
  "action": "escalate" | "close",
  "reviewer": "supervisor"
}
```

## Authentication

Two modes — set in `helpdesk-agent/.env`:

```env
# Mode A: Gemini API Key (local dev, no GCP billing required)
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY_HERE
GOOGLE_GENAI_USE_VERTEXAI=False

# Mode B: Vertex AI (cloud deployment)
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

Note: auto_resolve and flag_security paths work WITHOUT an API key.
Only risk_analyzer (the Gemini LLM step) requires a valid key.

## Development Phases

### Phase 1: Understand Requirements
Read this GEMINI.md, the agent.py workflow, and the test suite before making changes.

### Phase 2: Build and Implement
Use `agents-cli playground` for interactive testing. Iterate on agent instructions.

### Phase 3: The Evaluation Loop
```bash
agents-cli eval generate   # run agent on test dataset
agents-cli eval grade      # grade results
agents-cli eval compare    # regression diff
```

### Phase 4: Pre-Deployment Tests
```bash
uv run pytest tests/ -v
```

### Phase 5: Deploy to Dev
Requires explicit approval. Run `agents-cli deploy` only after user confirms.

## Development Commands

| Command | Purpose |
|---------|---------|
| `agents-cli playground` | Interactive local testing |
| `uv run pytest tests/` | Run unit tests (no API key needed) |
| `agents-cli eval generate` | Run agent on eval dataset |
| `agents-cli eval grade` | Grade evaluation results |
| `agents-cli lint` | Check code quality |
| `agents-cli deploy` | Deploy to Agent Runtime |

## Key Files

| File | Purpose |
|------|---------|
| `app/agent.py` | Core ADK 2.0 workflow — routing logic, LLM agent, all nodes |
| `app/fast_api_app.py` | Local Pub/Sub receiver (port 8080) |
| `app/agent_runtime_app.py` | Cloud Agent Runtime entry point |
| `app/app_utils/typing.py` | Pydantic feedback model |
| `app/app_utils/telemetry.py` | OpenTelemetry + GCS log setup |
| `tests/test_agent.py` | Unit tests for routing logic (no API key) |
| `../supervisor-dashboard/main.py` | FastAPI dashboard (port 8081) |
| `../supervisor-dashboard/templates/index.html` | Glassmorphic UI |

## Operational Guidelines

- **NEVER change the model** unless explicitly asked (gemini-2.0-flash-lite).
- **Code preservation**: Only modify code directly targeted by the user's request.
- **Run Python with uv**: `uv run python script.py`
- **Stop on repeated errors**: If the same error appears 3+ times, fix the root cause.
