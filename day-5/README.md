# Day 5 — Spec-Driven Production-Grade Development & Cloud Deployment

## Projects

### Expense Agent System
A full-stack, production-ready expense approval system built without Antigravity IDE — using Claude Code instead. The system consists of two connected services that run together locally and are designed for Google Cloud deployment.

---

### expense-agent
The AI backend that processes expense report submissions.

**How it works:**
- Receives expense data via a Pub/Sub-style HTTP endpoint
- Auto-approves expenses under $100 with no LLM call
- Screens expenses over $100 for PII and prompt injection
- Calls Gemini to generate a risk analysis (LOW / MEDIUM / HIGH)
- Returns a human review request with the AI recommendation

**Key files:**
- `app/agent.py` — ADK 2.0 workflow graph
- `app/fast_api_app.py` — Local FastAPI server (Pub/Sub simulation)
- `app/agent_runtime_app.py` — Google Cloud Agent Runtime wrapper
- `agents-cli-manifest.yaml` — Cloud deployment config

---

### manager-dashboard
A glassmorphic web dashboard where managers review and action pending expense approvals.

**How it works:**
- Submission form sends expenses to the agent in real Pub/Sub message format
- Under $100 expenses are auto-approved and confirmed instantly
- Over $100 expenses appear as review cards on the dashboard
- Manager clicks Approve or Reject — card fades out and is removed
- Designed to connect to Google Cloud Agent Runtime when deployed

**Key files:**
- `main.py` — FastAPI app with 3 endpoints (dashboard, pending list, approve/reject)
- `templates/index.html` — Glassmorphic approval UI

---

## Running Locally

**Terminal 1 — Expense Agent (port 8080):**
```bash
cd expense-agent-system/expense-agent
uv sync
uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
```

**Terminal 2 — Manager Dashboard (port 8081):**
```bash
cd expense-agent-system/manager-dashboard
uv sync
uv run uvicorn main:app --reload --port 8081
```

Open **http://localhost:8081** in your browser.

Add your Gemini API key to `expense-agent/.env` and `manager-dashboard/.env` to activate AI analysis.

---

## Key Concepts Covered
- Spec-driven development vs. vibe coding
- ADK 2.0 production deployment with Agent Runtime and `agents-cli`
- Event-driven architecture with Google Cloud Pub/Sub
- Human-in-the-loop approval workflows with session persistence
- FastAPI + Cloud Run for frontend deployment
- OIDC authentication for secure service-to-service communication
