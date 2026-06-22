# Nexus Technologies IT Helpdesk Triage Agent

**Google / Kaggle 5-Day AI Agents Intensive — Capstone Project**
**Track:** Agents for Business | **Author:** Jared Lomeli | jared.lomeli@sjsu.edu

---

## The Problem

IT helpdesk teams spend a significant portion of their day reading and sorting support tickets before anyone actually starts working on them. A password reset request gets treated the same as an ERP outage because everything lands in the same queue. On top of that, there is no built-in protection against malicious ticket submissions. An employee account that has been compromised, or someone deliberately trying to manipulate an AI-powered helpdesk, can submit a ticket containing phishing indicators or prompt injection phrases that reach the LLM without any filtering.

This project tackles both of those problems. The goal was to build a system that resolves routine tickets instantly with no AI cost, intercepts security threats before they reach the model, and applies real AI reasoning only to the complex incidents where it actually adds value.

---

## The Solution

The Nexus Technologies IT Helpdesk Triage Agent is built on Google ADK 2.0 and processes incoming IT support tickets into one of three outcomes:

**Auto-Resolve** handles the routine requests. Password resets, printer problems, WiFi issues, VPN connectivity, and new employee onboarding tickets are matched against a keyword list and resolved immediately with the appropriate knowledge base article. No LLM call is made and no time is wasted.

**Security Escalation** handles the dangerous ones. Before any ticket reaches the AI, a screening node checks for threat keywords like phishing, malware, ransomware, and data breach, as well as prompt injection phrases like "ignore previous instructions" and "auto-approve." If either check fires, the ticket gets escalated to the Security Operations Center and the LLM is bypassed entirely.

**Human Review** handles everything else. Complex and ambiguous incidents are analyzed by two specialized Gemini agents that assess severity, look up the right resources using MCP tools, and draft a professional response email. The result lands on a supervisor dashboard where an IT manager makes the final call to escalate or close the ticket.

---

## Architecture

The system runs as two separate services. The helpdesk agent runs on port 8080 and contains the full ADK 2.0 triage workflow. The supervisor dashboard runs on port 8082 and gives IT managers a web interface to review and act on tickets that need human judgment.

```
START
  └── parse_ticket
        └── classify_priority
              ├── [routine]   → auto_resolve               (KB article, no LLM)
              └── [elevated]  → security_screen
                                    ├── [threat]  → flag_security         (SOC alert, no LLM)
                                    └── [clean]   → risk_analyzer         (LlmAgent, Gemini 2.5 Flash)
                                                        └── prepare_draft_input
                                                              └── response_drafter   (LlmAgent, Gemini 2.5 Flash)
                                                                    └── human_review → Supervisor Dashboard
```

The workflow is defined using ADK 2.0's `Workflow`, `Edge`, and `node` primitives. Routing decisions happen inside each node by setting `ctx.route`. The two LlmAgents are connected to three MCP agent skills that give them access to the Nexus knowledge base, escalation matrix, and SLA targets during analysis.

### MCP Agent Skills

The `kb_mcp_server.py` file is a standalone MCP server built with FastMCP that exposes three agent skills over stdio transport. These skills are what the `risk_analyzer` agent calls during its analysis:

- `lookup_kb_article(query)` searches 21 KB articles covering common IT issues and returns matching article IDs, titles, and internal URLs
- `get_escalation_matrix()` returns the full IT escalation matrix mapping severity levels to responsible teams and SLA targets
- `get_sla_target(severity)` returns the specific SLA response window for LOW, MEDIUM, HIGH, or CRITICAL incidents

The same functions are imported directly into `agent.py` so the agent can call them without spawning a subprocess during local development. The MCP server can also be connected to external clients like Claude Desktop by running `uv run python -m app.kb_mcp_server`.

### Security Design

The `security_screen` node runs before any model call. It checks for 17 threat keyword phrases and 7 prompt injection patterns using plain string matching. If either check triggers, the ticket is routed to `flag_security` which generates a SOC escalation message and returns immediately. The model never sees the content of flagged tickets.

### Supervisor Dashboard

The supervisor dashboard is a FastAPI application with a glassmorphic dark-teal UI. Tickets that complete the full AI analysis path appear as cards showing the reporter, category, affected system, risk level, full AI incident analysis, and the drafted response email. The IT supervisor clicks Escalate or Close to resolve each ticket.

---

## File Structure

```
Final Project/
├── README.md                          
├── HOW_TO_ACTIVATE.txt                
├── .env.example                       
├── capstone_helpdesk_agent.ipynb      
├── helpdesk-agent/
│   ├── GEMINI.md                      
│   ├── agents-cli-manifest.yaml       
│   ├── pyproject.toml                 
│   ├── app/
│   │   ├── agent.py                   (ADK 2.0 workflow: 2 LlmAgents + 5 nodes)
│   │   ├── kb_mcp_server.py           (MCP server: 3 agent skills)
│   │   ├── fast_api_app.py            (local Pub/Sub receiver on port 8080)
│   │   └── agent_runtime_app.py       (Cloud Agent Runtime entry point)
│   └── tests/
│       └── test_agent.py              (17 unit tests, no API key needed)
└── supervisor-dashboard/
    ├── main.py                        (FastAPI supervisor app on port 8082)
    └── templates/
        └── index.html                 (glassmorphic teal supervisor UI)
```

---

## Setup Instructions

**Prerequisites:** Python 3.11+, `uv` installed (`pip install uv`), and a Gemini API key from https://aistudio.google.com/apikey

### Step 1: Set up credentials

Copy the credentials template and fill in your API key:

```bash
cp helpdesk-agent/.env.example helpdesk-agent/.env
```

Open `helpdesk-agent/.env` and set:

```
GOOGLE_API_KEY=your-key-here
GOOGLE_GENAI_USE_VERTEXAI=False
```

### Step 2: Install dependencies

```bash
cd helpdesk-agent
uv sync

cd ../supervisor-dashboard
uv sync
```

### Step 3: Run locally

Open two terminal windows:

**Terminal 1 — Helpdesk agent:**
```bash
cd helpdesk-agent
uv run uvicorn app.fast_api_app:fast_api_app --reload --port 8080
```

**Terminal 2 — Supervisor dashboard:**
```bash
cd supervisor-dashboard
uv run uvicorn main:app --reload --port 8082
```

Open your browser to `http://localhost:8082` to see the IT Supervisor Dashboard.

### Step 4: Test the three paths

Submit these tickets from the dashboard form to verify all three routing paths:

| Ticket Description | Expected Result |
|--------------------|----------------|
| `I forgot my password and cannot log in` | AUTO-RESOLVED with KB-001 |
| `I received a suspicious phishing email with a malware attachment` | SECURITY ESCALATION, no AI |
| `The ERP system has been down for 2 hours, 50 employees cannot work` | HUMAN REVIEW card with AI analysis and drafted email |

### Step 5: Run the tests

The full test suite runs without an API key:

```bash
cd helpdesk-agent
uv run pytest tests/ -v
```

All 17 tests should pass.

---

## Cloud Deployment

The helpdesk agent deploys to Google Agent Runtime using `agents-cli` and the supervisor dashboard deploys to Cloud Run. Full step-by-step deployment instructions including Pub/Sub topic and subscription setup are in `HOW_TO_ACTIVATE.txt`.

```bash
# Deploy helpdesk agent
cd helpdesk-agent
agents-cli deploy --project YOUR_PROJECT_ID --region us-central1

# Deploy supervisor dashboard
cd ../supervisor-dashboard
gcloud run deploy supervisor-dashboard \
  --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars AGENT_RUNTIME_ID=YOUR_ID,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
```
