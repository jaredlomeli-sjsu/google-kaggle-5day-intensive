# Day 5 — Spec-Driven Production-Grade Development & Cloud Deployment

A full-stack, production-ready expense approval system built without Antigravity IDE — using Claude Code instead. Two connected services run together locally and are designed for Google Cloud deployment.

**System Architecture:**
```
Submission Form (browser)
    └─> manager-dashboard :8081  (FastAPI)
            └─> expense-agent :8080  (FastAPI + ADK 2.0)
                    ├─> AUTO-APPROVED   (under $100)
                    └─> HUMAN REVIEW    (over $100)
                            └─> pending card on dashboard
                                    └─> manager clicks Approve / Reject
```

---

## Projects

### 1. `expense-agent-system/expense-agent`

The AI backend that receives expense submissions, runs them through the ADK 2.0 workflow, and returns a decision.

**Workflow:**
```
Pub/Sub message (or form submission)
    └─> parse_expense         (extract amount from text)
            └─> check_amount
                    ├─> auto_approve      (under $100)
                    └─> security_screen   (over $100)
                                ├─> flag_security   (PII / injection blocked)
                                └─> risk_analyzer   (Gemini risk assessment)
                                            └─> human_review
```

**Code Structure:**
```
expense-agent/
├── app/
│   ├── agent.py                  # ADK 2.0 workflow graph
│   ├── agent_runtime_app.py      # Google Cloud Agent Runtime wrapper
│   ├── fast_api_app.py           # Local server + Pub/Sub endpoint (:8080)
│   └── app_utils/
│       ├── telemetry.py          # OpenTelemetry setup
│       └── typing.py             # Pydantic feedback model
├── tests/
│   └── test_agent.py             # Unit tests (no API key needed)
├── agents-cli-manifest.yaml      # Cloud deployment config
├── deployment_metadata.json      # Tracks deployed Agent Runtime ID
├── .env.example                  # Credentials template
└── pyproject.toml                # Dependencies (uv)
```

**Setup:**
```bash
cd expense-agent-system/expense-agent
cp .env.example .env        # fill in GOOGLE_API_KEY
uv sync
uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
```

---

### 2. `expense-agent-system/manager-dashboard`

A glassmorphic web dashboard where managers submit expenses and review pending approvals.

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the approval dashboard UI |
| `GET` | `/api/pending` | Returns list of sessions awaiting decision |
| `POST` | `/api/submit` | Submits an expense to the agent |
| `POST` | `/api/action` | Approves or rejects a pending session |

**Code Structure:**
```
manager-dashboard/
├── templates/
│   └── index.html                # Glassmorphic approval UI
├── main.py                       # FastAPI app (4 endpoints)
├── .env.example                  # Credentials template
└── pyproject.toml                # Dependencies (uv)
```

**Setup:**
```bash
cd expense-agent-system/manager-dashboard
cp .env.example .env        # fill in GOOGLE_API_KEY
uv sync
uv run uvicorn main:app --reload --port 8081
```

Open **http://localhost:8081** in your browser.

---

## Running Both Together

```bash
# Terminal 1 — Expense Agent
cd expense-agent-system/expense-agent
uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080

# Terminal 2 — Manager Dashboard
cd expense-agent-system/manager-dashboard
uv run uvicorn main:app --reload --port 8081
```

- Submit an expense **under $100** → auto-approved instantly
- Submit an expense **over $100** → review card appears on the dashboard
- Click **Approve** or **Reject** → card fades out

---

## Key Concepts Covered
- Spec-driven development vs. vibe coding
- ADK 2.0 production deployment with Agent Runtime and `agents-cli`
- Event-driven architecture with Google Cloud Pub/Sub
- Human-in-the-loop approval workflows with session persistence
- FastAPI + Cloud Run for frontend deployment
- OIDC authentication for secure service-to-service communication
