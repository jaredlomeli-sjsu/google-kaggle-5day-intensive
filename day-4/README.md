# Day 4 — Domain-Specific Agents & Multi-Agent Evaluation

## Projects

### 1. `ambient-expense-agent`

An event-driven AI agent built with **ADK 2.0** that processes employee expense reports automatically. The agent uses a graph-based workflow to route expenses based on business rules — auto-approving low-value submissions and escalating high-value ones for human review.

**Workflow:**
```
Pub/Sub Message
    └─> parse_expense         (extract amount + description)
            └─> check_amount
                    ├─> auto_approve      (under $100 — no LLM needed)
                    └─> security_screen   (over $100)
                                ├─> flag_security   (PII or injection detected)
                                └─> risk_analyzer   (Gemini LLM risk assessment)
                                            └─> human_review  (APPROVE / REJECT)
```

**Code Structure:**
```
ambient-expense-agent/
├── app/
│   ├── agent.py                  # ADK 2.0 workflow graph
│   ├── agent_runtime_app.py      # Google Cloud Agent Runtime wrapper
│   ├── fast_api_app.py           # Local FastAPI server + Pub/Sub endpoint
│   └── app_utils/
│       ├── telemetry.py          # OpenTelemetry + GCS log upload
│       └── typing.py             # Pydantic feedback model
├── tests/
│   ├── eval/                     # ADK evaluation datasets + config
│   ├── integration/              # Integration tests
│   └── unit/                     # Unit tests
├── deployment/                   # Terraform configs for Google Cloud
├── agents-cli-manifest.yaml      # Cloud deployment descriptor
├── deployment_metadata.json      # Tracks deployed Agent Runtime ID
└── pyproject.toml                # Dependencies (uv)
```

**Setup:**
```bash
cd ambient-expense-agent
cp .env.example .env        # fill in GOOGLE_API_KEY
uv sync
uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
```

---

### 2. `shopping-assistant`

A conversational shopping agent that helps users find products, compare options, and make purchasing decisions through natural language.

**Code Structure:**
```
shopping-assistant/
├── app/
│   ├── agent.py                  # ADK 2.0 shopping workflow
│   ├── agent_runtime_app.py      # Cloud deployment wrapper
│   └── app_utils/
│       ├── telemetry.py
│       └── typing.py
├── tests/
│   ├── eval/                     # Evaluation datasets
│   ├── integration/
│   └── unit/
├── deployment/                   # Terraform configs
├── agents-cli-manifest.yaml
└── pyproject.toml
```

**Setup:**
```bash
cd shopping-assistant
cp .env.example .env        # fill in GOOGLE_API_KEY
uv sync
uv run adk web             # launch ADK web UI
```

---

## Key Concepts Covered
- ADK 2.0 graph-based workflow design (`Workflow`, `Edge`, `node`, `LlmAgent`)
- Event-driven agent architecture with Pub/Sub triggers
- Security screening for PII and prompt injection before LLM calls
- Multi-agent evaluation with the ADK eval framework
- Human-in-the-loop patterns using `RequestInput` nodes
