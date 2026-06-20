# ruff: noqa
"""
Nexus Technologies IT Helpdesk Triage Agent — ADK 2.0 event-driven workflow.

HOW TO ACTIVATE:
  1. Copy ../.env.example to ../.env
  2. Fill in GOOGLE_API_KEY (get a free key at https://aistudio.google.com/apikey)
  3. Run locally:  uv run python -m app.agent
  4. Deploy:       agents-cli deploy --project YOUR_PROJECT_ID --region us-central1

Architecture:
  START → parse_ticket → classify_priority
    ├─ 'routine'  (<common issues>)  → auto_resolve
    └─ 'elevated' (complex/unknown) → security_screen
                                        ├─ 'threat' (phishing/malware/breach) → flag_security
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
    _api_key = os.getenv("GOOGLE_API_KEY", "")
    if not _api_key or _api_key == "YOUR_GEMINI_API_KEY_HERE":
        print(
            "\n[WARNING] GOOGLE_API_KEY is not set.\n"
            "Copy .env.example to .env and fill in your key before running.\n"
            "Get a free key at: https://aistudio.google.com/apikey\n"
            "NOTE: auto_resolve and flag_security paths work without a key.\n"
            "      Only risk_analyzer (AI analysis) requires a valid API key.\n"
        )

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.workflow import START, Edge, Workflow, node

# ---------------------------------------------------------------------------
# Routing keyword lists
# ---------------------------------------------------------------------------

ROUTINE_KEYWORDS = [
    "password", "reset", "unlock", "locked out", "account lock",
    "printer", "print", "printing",
    "wifi", "wi-fi", "wireless", "internet connection",
    "vpn", "remote access",
    "software install", "install software", "install app",
    "email setup", "email client", "outlook setup",
    "monitor", "display", "screen resolution",
    "keyboard", "mouse", "headset", "headphones",
    "new employee", "onboarding", "new hire",
]

THREAT_KEYWORDS = [
    "phishing", "phish",
    "malware", "ransomware", "virus", "trojan", "worm",
    "data breach", "breach",
    "hacked", "hack", "compromised",
    "credential theft", "credential stuffing",
    "suspicious email", "suspicious link", "suspicious attachment",
    "unauthorized access", "unauthorized login",
]

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
# KB article lookup for auto-resolved tickets
# ---------------------------------------------------------------------------

_KB_ARTICLES = {
    "password": "KB-001: Self-Service Password Reset — nexus.internal/kb/password-reset",
    "printer":  "KB-042: Printer Troubleshooting Guide — nexus.internal/kb/printer",
    "print":    "KB-042: Printer Troubleshooting Guide — nexus.internal/kb/printer",
    "wifi":     "KB-015: Wireless Connectivity Issues — nexus.internal/kb/wifi",
    "wi-fi":    "KB-015: Wireless Connectivity Issues — nexus.internal/kb/wifi",
    "vpn":      "KB-033: VPN Setup & Troubleshooting — nexus.internal/kb/vpn",
    "email":    "KB-027: Email Client Configuration — nexus.internal/kb/email",
    "outlook":  "KB-027: Email Client Configuration — nexus.internal/kb/email",
    "monitor":  "KB-056: Display & Monitor Setup — nexus.internal/kb/monitor",
    "keyboard": "KB-061: Peripheral Device Replacement — nexus.internal/kb/peripherals",
    "mouse":    "KB-061: Peripheral Device Replacement — nexus.internal/kb/peripherals",
    "onboard":  "KB-002: New Employee IT Onboarding Checklist — nexus.internal/kb/onboarding",
    "new hire": "KB-002: New Employee IT Onboarding Checklist — nexus.internal/kb/onboarding",
}

_KB_DEFAULT = "KB-000: IT Self-Service Portal — nexus.internal/kb"


def _find_kb(description: str) -> str:
    lower = description.lower()
    for keyword, article in _KB_ARTICLES.items():
        if keyword in lower:
            return article
    return _KB_DEFAULT


# ---------------------------------------------------------------------------
# Workflow nodes
# ---------------------------------------------------------------------------


@node
def parse_ticket(ctx: Context, node_input) -> dict:
    """Extract ticket fields from raw input text."""
    text = ""
    if hasattr(node_input, "parts") and node_input.parts:
        text = node_input.parts[0].text
    elif isinstance(node_input, str):
        text = node_input

    ctx.state["ticket"] = {"description": text, "raw": text}
    return ctx.state["ticket"]


@node
def classify_priority(ctx: Context, node_input) -> None:
    """Route to 'routine' for common issues, 'elevated' for everything else."""
    ticket = ctx.state.get("ticket", node_input)
    description = ticket.get("description", "") if isinstance(ticket, dict) else str(ticket)
    lower = description.lower()

    is_routine = any(kw in lower for kw in ROUTINE_KEYWORDS)
    ctx.route = "routine" if is_routine else "elevated"
    ctx.output = ticket


@node
def auto_resolve(ctx: Context, node_input) -> str:
    """Instantly resolve routine tickets with a relevant KB article — no LLM needed."""
    ticket = ctx.state.get("ticket", {})
    description = ticket.get("description", "")
    kb = _find_kb(description)
    return (
        f"AUTO-RESOLVED: This appears to be a routine IT request.\n"
        f"Recommended resource: {kb}\n"
        f"Ticket has been logged and closed automatically. "
        f"If the issue persists, reply to reopen and escalate to Tier 2."
    )


@node
def security_screen(ctx: Context, node_input) -> None:
    """Detect threat keywords and prompt injection before the LLM sees anything."""
    ticket = ctx.state.get("ticket", {})
    description = ticket.get("description", "")
    flags = []

    lower = description.lower()

    if any(kw in lower for kw in THREAT_KEYWORDS):
        flags.append("security_threat")

    if any(phrase in lower for phrase in _INJECTION_PHRASES):
        flags.append("injection")

    ticket["security_flags"] = flags
    ctx.state["ticket"] = ticket

    ctx.route = "threat" if flags else "clean"
    ctx.output = ticket


@node
def flag_security(ctx: Context, node_input) -> str:
    """Escalate to Security Operations team — LLM is bypassed entirely."""
    ticket = ctx.state.get("ticket", {})
    flags = ticket.get("security_flags", [])
    excerpt = ticket.get("description", "")[:120]
    return (
        f"SECURITY ESCALATION: This ticket has been flagged for the Security Operations team.\n"
        f"Flags detected: {', '.join(flags)}.\n"
        f"Ticket excerpt: \"{excerpt}...\"\n"
        "LLM analysis was bypassed. A security analyst must review this submission immediately.\n"
        "SOC contact: security@nexus.internal | On-call: +1 (555) 867-5309"
    )


# ---------------------------------------------------------------------------
# LLM-powered risk analysis
# Requires GOOGLE_API_KEY or Vertex AI credentials to be set in .env
# ---------------------------------------------------------------------------

risk_analyzer = LlmAgent(
    name="risk_analyzer",
    model="gemini-2.0-flash-lite",
    instruction=(
        "You are a Tier 2 IT incident analyst for Nexus Technologies. "
        "Review this support ticket and assess the severity. "
        "Consider: How many users are potentially affected? Is this a critical business system? "
        "Is there any risk of data loss or extended downtime? "
        "Provide a severity rating (LOW / MEDIUM / HIGH) with 2-3 bullet points of reasoning. "
        "End with exactly one of: "
        "'RECOMMENDATION: Assign to Tier 2' or "
        "'RECOMMENDATION: Assign to Tier 3' or "
        "'RECOMMENDATION: Close (invalid/duplicate)'."
    ),
    output_key="risk_analysis",
)


@node
def human_review(ctx: Context, node_input) -> str:
    """Present risk analysis and request IT supervisor decision."""
    ticket = ctx.state.get("ticket", {})
    description = ticket.get("description", "")
    risk = ctx.state.get("risk_analysis", "Risk analysis unavailable.")
    return (
        f"HUMAN REVIEW REQUIRED: IT support ticket needs supervisor decision.\n\n"
        f"Ticket: {description}\n\n"
        f"AI Incident Analysis:\n{risk}\n\n"
        "Please review in the Nexus Helpdesk Supervisor Dashboard and escalate or close."
    )


# ---------------------------------------------------------------------------
# Workflow graph definition
# ---------------------------------------------------------------------------

root_agent = Workflow(
    name="helpdesk_triage_workflow",
    edges=[
        Edge(from_node=START, to_node=parse_ticket),
        Edge(from_node=parse_ticket, to_node=classify_priority),
        Edge(from_node=classify_priority, to_node=auto_resolve, route="routine"),
        Edge(from_node=classify_priority, to_node=security_screen, route="elevated"),
        Edge(from_node=security_screen, to_node=risk_analyzer, route="clean"),
        Edge(from_node=security_screen, to_node=flag_security, route="threat"),
        Edge(from_node=risk_analyzer, to_node=human_review),
    ],
)

app = App(name="helpdesk_agent", root_agent=root_agent)
