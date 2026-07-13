"""Seed MCPLab with a catalog of well-known MCP connectors as governed templates.

These are marked catalog=true and status='draft' — they are starting points, NOT claims that
a given endpoint is live and reachable. Discovery is what proves an endpoint real: point a
connector at a reachable HTTP MCP endpoint and MCPLab does a genuine handshake. No tools are
fabricated here; the tools list stays empty until a real discovery populates it.
"""
import database as db

_CATALOG = [
    {"name": "GitHub MCP", "description": "Issues, PRs, repos, and code search over the GitHub MCP server.",
     "transport": "http", "endpoint_url": "", "auth_type": "bearer", "auth_ref": "github_pat",
     "tags": ["dev", "vcs"], "risk_level": "high", "human_approval": True},
    {"name": "Slack MCP", "description": "Post messages and read channels via a Slack MCP server.",
     "transport": "http", "endpoint_url": "", "auth_type": "bearer", "auth_ref": "slack_bot_token",
     "tags": ["chat", "notify"], "risk_level": "high", "human_approval": True},
    {"name": "Filesystem MCP", "description": "Local file read/write — stdio transport, runs beside the host.",
     "transport": "stdio", "endpoint_url": "", "auth_type": "none", "auth_ref": "",
     "tags": ["files", "local"], "risk_level": "high", "human_approval": True},
    {"name": "Fetch MCP", "description": "Fetch and convert web pages to text for grounding.",
     "transport": "http", "endpoint_url": "", "auth_type": "none", "auth_ref": "",
     "tags": ["web", "read"], "risk_level": "medium", "human_approval": False},
    {"name": "Postgres MCP", "description": "Read-only SQL queries against a Postgres database.",
     "transport": "http", "endpoint_url": "", "auth_type": "header", "auth_ref": "pg_conn_ref",
     "tags": ["data", "sql"], "risk_level": "high", "human_approval": True},
]


def run():
    if db.list_connectors(None):
        return 0
    for c in _CATALOG:
        db.create_connector(c, owner=None, catalog=True)
    return len(_CATALOG)
