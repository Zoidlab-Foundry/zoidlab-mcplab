"""MCPLab ⇄ Foundry integration — SpendGuard usage emission + TrustGate preflight.

Cross-app calls carry the caller's zb_session (forwarded on interactive requests) or a
minted owner session. Best-effort; never breaks a connector test. §6.3 usage events + §6.4
policy decisions.
"""
import os
import time
import uuid
import jwt
import httpx
from contextvars import ContextVar

ENABLED = os.environ.get("FOUNDRY_INTEGRATION", "on").lower() not in ("off", "false", "0")
SPENDGUARD_URL = os.environ.get("SPENDGUARD_URL", "http://127.0.0.1:8701").rstrip("/")
TRUSTGATE_URL = os.environ.get("TRUSTGATE_URL", "http://127.0.0.1:8700").rstrip("/")
SECRET = os.environ.get("BUILDER_SESSION_SECRET", "")

_session: ContextVar = ContextVar("foundry_session", default=None)


def set_session(token):
    _session.set(token or None)


def mint_session(owner, email=None):
    if not (SECRET and owner):
        return None
    now = int(time.time())
    return jwt.encode({"sub": owner, "email": email, "tier": "pro", "iat": now, "exp": now + 900},
                      SECRET, algorithm="HS256")


def _headers():
    tok = _session.get()
    return {"Cookie": f"zb_session={tok}", "Content-Type": "application/json"} if tok else None


def available():
    return ENABLED and bool(_headers())


async def emit_spend(usage, resource_id=None, feature="", correlation_id=None, environment="production"):
    """One SpendGuard usage event for an MCP connector test (real model + token split)."""
    if not available() or not usage or not usage.get("model"):
        return 0
    pt = int(usage.get("prompt_tokens") or 0); ct = int(usage.get("completion_tokens") or 0)
    if pt <= 0 and ct <= 0:
        return 0
    ev = {"model": usage["model"], "prompt_tokens": pt, "completion_tokens": ct,
          "app": "mcplab", "feature": feature or "mcp_test", "source": "mcplab",
          "environment": environment, "correlation_id": correlation_id,
          "resource_ref": {"package_id": "mcp", "resource_id": resource_id, "resource_type": "mcp_test"}}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(f"{SPENDGUARD_URL}/api/events", headers=_headers(), json=ev)
            return 1 if r.status_code < 400 else 0
    except Exception:
        return 0


async def trustgate_preflight(action, correlation_id=None):
    """Ask TrustGate whether a vision action is allowed (§6.4). Returns decision or skipped."""
    if not available():
        return {"decision": "skipped", "reasons": []}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{TRUSTGATE_URL}/api/test", headers=_headers(),
                             json={"request": action, "save": True, "correlation_id": correlation_id})
            return r.json() if r.status_code < 400 else {"decision": "skipped", "reasons": []}
    except Exception:
        return {"decision": "skipped", "reasons": []}
