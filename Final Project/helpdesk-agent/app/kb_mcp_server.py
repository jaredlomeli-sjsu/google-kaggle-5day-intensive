"""
Nexus Technologies KB MCP Server.

Exposes knowledge-base article lookups, the IT escalation matrix, and SLA
targets as MCP tools via the Model Context Protocol (stdio transport).

Standalone usage (for external MCP clients such as Claude Desktop, Cursor, etc.):
  uv run python -m app.kb_mcp_server

The same functions are also imported directly by agent.py so the risk_analyzer
LlmAgent can call them as ADK function tools without a separate subprocess.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nexus-kb")

_KB: dict[str, tuple[str, str, str]] = {
    "password":   ("KB-001", "Self-Service Password Reset",           "nexus.internal/kb/001"),
    "printer":    ("KB-042", "Printer Troubleshooting Guide",         "nexus.internal/kb/042"),
    "print":      ("KB-042", "Printer Troubleshooting Guide",         "nexus.internal/kb/042"),
    "wifi":       ("KB-015", "Wireless Connectivity Issues",          "nexus.internal/kb/015"),
    "wi-fi":      ("KB-015", "Wireless Connectivity Issues",          "nexus.internal/kb/015"),
    "vpn":        ("KB-033", "VPN Setup & Troubleshooting",           "nexus.internal/kb/033"),
    "email":      ("KB-027", "Email Client Configuration",            "nexus.internal/kb/027"),
    "outlook":    ("KB-027", "Email Client Configuration",            "nexus.internal/kb/027"),
    "monitor":    ("KB-056", "Display & Monitor Setup",               "nexus.internal/kb/056"),
    "keyboard":   ("KB-061", "Peripheral Device Replacement",         "nexus.internal/kb/061"),
    "mouse":      ("KB-061", "Peripheral Device Replacement",         "nexus.internal/kb/061"),
    "onboard":    ("KB-002", "New Employee IT Onboarding Checklist",  "nexus.internal/kb/002"),
    "new hire":   ("KB-002", "New Employee IT Onboarding Checklist",  "nexus.internal/kb/002"),
    "erp":        ("KB-101", "ERP System Incident Response",          "nexus.internal/kb/101"),
    "database":   ("KB-102", "Database Outage Protocol",              "nexus.internal/kb/102"),
    "network":    ("KB-103", "Network Outage Response Plan",          "nexus.internal/kb/103"),
    "server":     ("KB-104", "Server Failure Runbook",                "nexus.internal/kb/104"),
    "backup":     ("KB-105", "Data Backup & Recovery Procedures",     "nexus.internal/kb/105"),
    "storage":    ("KB-105", "Data Backup & Recovery Procedures",     "nexus.internal/kb/105"),
    "software":   ("KB-200", "Software Deployment & Licensing",       "nexus.internal/kb/200"),
    "license":    ("KB-200", "Software Deployment & Licensing",       "nexus.internal/kb/200"),
    "hardware":   ("KB-201", "Hardware Replacement Request",          "nexus.internal/kb/201"),
    "laptop":     ("KB-201", "Hardware Replacement Request",          "nexus.internal/kb/201"),
    "desktop":    ("KB-201", "Hardware Replacement Request",          "nexus.internal/kb/201"),
}

_ESCALATION_MATRIX = """
Nexus Technologies IT Escalation Matrix
----------------------------------------
LOW severity    → Tier 2 (helpdesk@nexus.internal)        SLA: 8 hours
MEDIUM severity → Tier 2 or Tier 3 based on blast radius  SLA: 4 hours
HIGH severity   → Tier 3 (it-oncall@nexus.internal)       SLA: 1 hour  + PagerDuty alert
CRITICAL        → Incident Commander + VP Engineering      SLA: Immediate + war room
"""

_SLA_MAP = {
    "LOW":      "8-hour response — Tier 2 (helpdesk@nexus.internal)",
    "MEDIUM":   "4-hour response — Tier 2/3 depending on blast radius",
    "HIGH":     "1-hour response — Tier 3 (it-oncall@nexus.internal) + PagerDuty alert",
    "CRITICAL": "Immediate — Incident Commander + VP Engineering notification required",
}


@mcp.tool()
def lookup_kb_article(query: str) -> str:
    """
    Search the Nexus Technologies knowledge base for support articles.

    Args:
        query: Keywords describing the IT issue, e.g. 'ERP outage' or 'network down'.

    Returns:
        Matching KB article IDs, titles, and URLs, or a pointer to the self-service portal.
    """
    lower = query.lower()
    seen: dict[str, str] = {}
    for keyword, (kb_id, title, url) in _KB.items():
        if keyword in lower and kb_id not in seen:
            seen[kb_id] = f"{kb_id}: {title} — {url}"
    if seen:
        return "Relevant KB articles:\n" + "\n".join(seen.values())
    return "No specific article found. See KB-000: IT Self-Service Portal — nexus.internal/kb"


@mcp.tool()
def get_escalation_matrix() -> str:
    """
    Return the Nexus Technologies IT escalation matrix.

    Returns:
        Escalation paths, team contacts, and SLA targets for each severity level.
    """
    return _ESCALATION_MATRIX


@mcp.tool()
def get_sla_target(severity: str) -> str:
    """
    Return the SLA response target for a given incident severity level.

    Args:
        severity: One of LOW, MEDIUM, HIGH, or CRITICAL (case-insensitive).

    Returns:
        The SLA target and escalation contact for that severity.
    """
    key = severity.strip().upper()
    return _SLA_MAP.get(
        key,
        f"Unknown severity '{severity}'. Valid values: LOW, MEDIUM, HIGH, CRITICAL.",
    )


if __name__ == "__main__":
    mcp.run()
