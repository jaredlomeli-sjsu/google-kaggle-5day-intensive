# ruff: noqa
"""
Ambient Expense Agent — ADK 2.0 event-driven workflow.

HOW TO ACTIVATE:
  1. Copy ../.env.example to ../.env
  2. Fill in GOOGLE_API_KEY and GOOGLE_CLOUD_PROJECT
  3. Run locally:  uv run python -m app.agent
  4. Deploy:       agents-cli deploy --project YOUR_PROJECT_ID --region us-central1

Architecture:
  START → parse_expense → check_amount
    ├─ 'low'  (<$100)  → auto_approve
    └─ 'high' (≥$100)  → security_screen
                           ├─ 'blocked' → flag_security
                           └─ 'clean'  → risk_analyzer → human_review
"""

import os
import re

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Auth — swap between Gemini API key and Vertex AI based on .env
# ---------------------------------------------------------------------------

_use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() == "true"

if _use_vertex:
    import google.auth
    _, _project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GOOGLE_CLOUD_PROJECT", _project_id)
    os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
else:
    # Gemini API key path — no Google Cloud project required
    _api_key = os.getenv("GOOGLE_API_KEY", "")
    if not _api_key or _api_key == "YOUR_GEMINI_API_KEY_HERE":
        print(
            "\n[WARNING] GOOGLE_API_KEY is not set.\n"
            "Copy .env.example to .env and fill in your key before running.\n"
            "Get a free key at: https://aistudio.google.com/apikey\n"
        )

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.workflow import START, Edge, Workflow, node

APPROVAL_THRESHOLD = 100.0

# ---------------------------------------------------------------------------
# Security patterns — PII detection and prompt injection guards
# ---------------------------------------------------------------------------

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_RE = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
_INJECTION_PHRASES = [
    "ignore previous",
    "bypass",
    "auto-approve",
    "auto approve",
    "override",
    "forget instructions",
    "disregard",
]

# ---------------------------------------------------------------------------
# Workflow nodes
# ---------------------------------------------------------------------------


@node
def parse_expense(ctx: Context, node_input) -> dict:
    """Extract expense fields from raw input text."""
    text = ""
    if hasattr(node_input, "parts") and node_input.parts:
        text = node_input.parts[0].text
    elif isinstance(node_input, str):
        text = node_input

    amount = 0.0
    amount_match = re.search(r"\$?([\d,]+\.?\d*)", text)
    if amount_match:
        amount = float(amount_match.group(1).replace(",", ""))

    ctx.state["expense"] = {"amount": amount, "description": text, "raw": text}
    return ctx.state["expense"]


@node
def check_amount(ctx: Context, node_input) -> None:
    """Route based on dollar threshold."""
    expense = ctx.state.get("expense", node_input)
    amount = expense.get("amount", 0) if isinstance(expense, dict) else 0
    ctx.route = "low" if amount < APPROVAL_THRESHOLD else "high"
    ctx.output = expense


@node
def auto_approve(ctx: Context, node_input) -> str:
    """Instantly approve expenses under the threshold — no LLM needed."""
    expense = ctx.state.get("expense", {})
    amount = expense.get("amount", 0)
    return (
        f"AUTO-APPROVED: ${amount:.2f} is under the "
        f"${APPROVAL_THRESHOLD:.0f} threshold. No further review required."
    )


@node
def security_screen(ctx: Context, node_input) -> None:
    """Redact PII and detect prompt injection before the LLM sees anything."""
    expense = ctx.state.get("expense", {})
    description = expense.get("description", "")
    flags = []

    if _SSN_RE.search(description):
        description = _SSN_RE.sub("[SSN REDACTED]", description)
        flags.append("ssn")

    if _CARD_RE.search(description):
        description = _CARD_RE.sub("[CARD REDACTED]", description)
        flags.append("credit_card")

    lower = description.lower()
    if any(phrase in lower for phrase in _INJECTION_PHRASES):
        flags.append("injection")

    expense["description"] = description
    expense["security_flags"] = flags
    ctx.state["expense"] = expense

    ctx.route = "blocked" if flags else "clean"
    ctx.output = expense


@node
def flag_security(ctx: Context, node_input) -> str:
    """Escalate to human review due to security concerns — LLM bypassed."""
    expense = ctx.state.get("expense", {})
    flags = expense.get("security_flags", [])
    amount = expense.get("amount", 0)
    return (
        f"SECURITY ESCALATION: ${amount:.2f} expense flagged for human review.\n"
        f"Issues detected: {', '.join(flags)}.\n"
        "LLM analysis was bypassed. A human reviewer must inspect this submission."
    )


# ---------------------------------------------------------------------------
# LLM-powered risk analysis
# Requires GOOGLE_API_KEY or Vertex AI credentials to be set in .env
# ---------------------------------------------------------------------------

risk_analyzer = LlmAgent(
    name="risk_analyzer",
    model="gemini-2.0-flash-lite",
    instruction=(
        "You are a corporate expense compliance analyst. "
        "Review the expense submission and assess the risk level. "
        "Consider: Is the amount reasonable for the stated purpose? "
        "Are there any red flags (unusual vendors, vague descriptions, round numbers)? "
        "Provide a concise risk summary (LOW / MEDIUM / HIGH) with 2-3 bullet points of reasoning. "
        "End with: 'RECOMMENDATION: Approve' or 'RECOMMENDATION: Reject'."
    ),
    output_key="risk_analysis",
)


@node
def human_review(ctx: Context, node_input) -> str:
    """Present risk analysis and request human approval decision."""
    expense = ctx.state.get("expense", {})
    amount = expense.get("amount", 0)
    risk = ctx.state.get("risk_analysis", "Risk analysis unavailable.")
    return (
        f"HUMAN REVIEW REQUIRED: ${amount:.2f} expense submission.\n\n"
        f"AI Risk Analysis:\n{risk}\n\n"
        "Please review and reply with APPROVE or REJECT."
    )


# ---------------------------------------------------------------------------
# Workflow graph definition
# ---------------------------------------------------------------------------

root_agent = Workflow(
    name="expense_triage_workflow",
    edges=[
        Edge(from_node=START, to_node=parse_expense),
        Edge(from_node=parse_expense, to_node=check_amount),
        Edge(from_node=check_amount, to_node=auto_approve, route="low"),
        Edge(from_node=check_amount, to_node=security_screen, route="high"),
        Edge(from_node=security_screen, to_node=risk_analyzer, route="clean"),
        Edge(from_node=security_screen, to_node=flag_security, route="blocked"),
        Edge(from_node=risk_analyzer, to_node=human_review),
    ],
)

app = App(name="expense_agent", root_agent=root_agent)
