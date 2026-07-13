"""ZoidLab MCPLab API — Foundry Package 12, MCP Connector Lab.

Register MCP connectors, discover their tools with a REAL MCP handshake, govern which tools
are callable (per-connector allow-list + human-approval + TrustGate decisions), test-call
tools for real over HTTP, and freeze immutable connector versions with an integrity hash.
Every data endpoint requires Nyquest Pro (backend fail-closed). Secrets are never stored —
connectors carry an auth *reference* label only. NOTE: uses /api (platform-consistent).
"""
import hashlib
import json
import uuid as _uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

import db_pg as db
import mcp_client
import exporter
import foundry
import jobs
import seed_mcp
from tasks import run_test as run_test_task
from auth import session, require_pro, entitlement


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    jobs.init()
    interrupted = jobs.reconcile()
    if interrupted:
        print(f"[mcplab] reconciled {interrupted} interrupted job(s)")
    n = seed_mcp.run()
    if n:
        print(f"[mcplab] seeded {n} catalog connectors")
    yield


app = FastAPI(title="ZoidLab MCPLab API", lifespan=lifespan)


def require_owner(request: Request):
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email") if s else None, s.get("name") if s else None)
    return o


@app.get("/api/health")
def health():
    return {"ok": True, "service": "mcplab"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": s.get("sub"), "email": s.get("email"),
            "name": s.get("name"), "tier": s.get("tier")}


@app.get("/api/auth/entitlements")
def auth_entitlements(request: Request):
    return entitlement(request)


@app.get("/api/meta")
def meta():
    return {"transports": ["http", "sse", "stdio"], "auth_types": ["none", "bearer", "header"],
            "note": "Discovery + test are real for reachable HTTP/SSE MCP endpoints; stdio and "
                    "auth-gated servers are governed and versioned but not callable from the control plane."}


@app.get("/api/stats")
def stats(request: Request, owner: str = Depends(require_owner)):
    return db.stats(owner)


# --- connectors ---
class ConnectorBody(BaseModel):
    name: str
    description: Optional[str] = ""
    transport: Optional[str] = "http"
    endpoint_url: Optional[str] = ""
    auth_type: Optional[str] = "none"
    auth_ref: Optional[str] = ""
    tags: Optional[list] = []
    status: Optional[str] = "draft"
    risk_level: Optional[str] = "medium"
    human_approval: Optional[bool] = False


class ConnectorPatch(BaseModel):
    description: Optional[str] = None
    transport: Optional[str] = None
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_ref: Optional[str] = None
    tags: Optional[list] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    human_approval: Optional[bool] = None


@app.get("/api/connectors")
def connectors(request: Request, owner: str = Depends(require_owner)):
    return {"connectors": db.list_connectors(owner)}


@app.get("/api/connectors/{cid}")
def get_connector(cid: str, request: Request, owner: str = Depends(require_owner)):
    c = db.get_connector(cid, owner)
    if not c:
        raise HTTPException(404, "not_found")
    return c


@app.post("/api/connectors")
def create_connector(body: ConnectorBody, owner: str = Depends(require_owner)):
    return {"ok": True, "connector": db.create_connector(body.model_dump(), owner)}


@app.patch("/api/connectors/{cid}")
def patch_connector(cid: str, body: ConnectorPatch, owner: str = Depends(require_owner)):
    c = db.update_connector(cid, owner, {k: v for k, v in body.model_dump().items() if v is not None})
    if not c:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "connector": c}


@app.delete("/api/connectors/{cid}")
def delete_connector(cid: str, owner: str = Depends(require_owner)):
    if not db.delete_connector(cid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- discover (real MCP handshake) ---
class DiscoverBody(BaseModel):
    endpoint_url: Optional[str] = None
    auth_value: Optional[str] = None   # supplied at call time, never stored


@app.post("/api/connectors/{cid}/discover")
async def discover(cid: str, body: DiscoverBody, owner: str = Depends(require_owner)):
    c = db.get_connector(cid, owner)
    if not c:
        raise HTTPException(404, "not_found")
    if c.get("transport") not in ("http", "sse"):
        return {"ok": False, "reachable": False, "error": "transport_not_discoverable",
                "detail": f"{c.get('transport')} transport can't be reached from the control plane."}
    url = body.endpoint_url or c.get("endpoint_url")
    if not url:
        raise HTTPException(400, "no_endpoint_url")
    res = await mcp_client.discover(url, auth_type=c.get("auth_type", "none"), auth_value=body.auth_value)
    if res.get("ok"):
        db.save_discovery(cid, owner, res.get("tools", []), {"server_info": res.get("server_info"),
                          "latency_ms": res.get("latency_ms"), "discovered_at": db.now_iso()})
    return res


# --- test (governed, real tool call) ---
class TestBody(BaseModel):
    connector_id: str
    tool_name: str
    arguments: Optional[dict] = {}
    auth_value: Optional[str] = None
    approve: Optional[bool] = False


@app.post("/api/test")
async def test_tool(body: TestBody, request: Request, owner: str = Depends(require_owner)):
    c = db.get_connector(body.connector_id, owner)
    if not c:
        raise HTTPException(404, "connector_not_found")
    corr = "corr_" + _uuid.uuid4().hex[:12]
    # 1. transport gate
    if c.get("transport") not in ("http", "sse") or not c.get("endpoint_url"):
        rid = db.create_test_run(c, body.tool_name, body.arguments, owner, corr)
        db.finish_test_run(rid, {"status": "blocked", "decision": "not_testable",
                                 "error": "This connector's transport is not callable from the control plane."})
        return db.get_test_run(rid, owner)
    # 2. allow-list gate
    allowed = c.get("allowed_tools") or []
    if allowed and body.tool_name not in allowed:
        rid = db.create_test_run(c, body.tool_name, body.arguments, owner, corr)
        db.finish_test_run(rid, {"status": "blocked", "decision": "denied_by_allowlist",
                                 "error": f"'{body.tool_name}' is not in this connector's allowed tools."})
        return db.get_test_run(rid, owner)
    # 3. human-approval gate
    if c.get("human_approval") and not body.approve:
        rid = db.create_test_run(c, body.tool_name, body.arguments, owner, corr)
        db.finish_test_run(rid, {"status": "blocked", "decision": "requires_approval",
                                 "error": "High-risk connector — approve to run this tool call."})
        return db.get_test_run(rid, owner)
    # 4. TrustGate preflight
    foundry.set_session(request.cookies.get("zb_session"))
    pf = await foundry.trustgate_preflight(
        {"prompt": f"MCP tool call: {c.get('name')} :: {body.tool_name}", "model": "mcp",
         "data_classification": "internal", "context_type": "mcp_tool_call",
         "risk_level": c.get("risk_level")}, correlation_id=corr)
    if pf.get("decision") == "blocked":
        rid = db.create_test_run(c, body.tool_name, body.arguments, owner, corr)
        db.finish_test_run(rid, {"status": "blocked", "decision": "trustgate_blocked",
                                 "error": "TrustGate blocked: " + "; ".join(pf.get("reasons") or [])})
        return db.get_test_run(rid, owner)
    # 5. real call — durable tracked Celery job (§1.3 / §3.2)
    rid = db.create_test_run(c, body.tool_name, body.arguments, owner, corr)
    decision = pf.get("decision") or "allow"
    job_id = jobs.create(owner, "mcp_test", rid, timeout_s=60)
    async_res = run_test_task.delay(job_id, rid, c["id"], body.tool_name, body.arguments or {},
                                    body.auth_value, decision, owner, corr)
    jobs.set_celery(job_id, owner, async_res.id)
    return {"job_id": job_id, "run_id": rid, "status": "queued", "test": db.get_test_run(rid, owner)}


# --- jobs ---
@app.get("/api/jobs/{jid}")
def get_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    j = jobs.get(jid, owner)
    if not j:
        raise HTTPException(404, "not_found")
    return j


@app.get("/api/jobs")
def list_jobs(request: Request, owner: str = Depends(require_owner)):
    return {"jobs": jobs.list_jobs(owner)}


@app.post("/api/jobs/{jid}/cancel")
def cancel_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    return {"ok": jobs.cancel(jid, owner)}


@app.get("/api/tests")
def tests(request: Request, owner: str = Depends(require_owner)):
    return {"tests": db.list_test_runs(owner)}


@app.get("/api/tests/{rid}")
def get_test(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_test_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return r


# --- versions (immutable, integrity-hashed) ---
@app.get("/api/connectors/{cid}/versions")
def versions(cid: str, request: Request, owner: str = Depends(require_owner)):
    return {"versions": db.list_versions(cid, owner)}


@app.post("/api/connectors/{cid}/versions")
def freeze_version(cid: str, request: Request, owner: str = Depends(require_owner)):
    c = db.get_connector(cid, owner)
    if not c:
        raise HTTPException(404, "not_found")
    snapshot = {"name": c["name"], "description": c["description"], "transport": c["transport"],
                "endpoint_url": c["endpoint_url"], "auth_type": c["auth_type"], "auth_ref": c["auth_ref"],
                "tags": c["tags"], "risk_level": c["risk_level"], "allowed_tools": c["allowed_tools"],
                "human_approval": c["human_approval"], "tools": c["tools"]}
    integrity = "sha256:" + hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    v = db.create_version(cid, owner, snapshot, integrity)
    return {"ok": True, "version": v}


# --- export ---
@app.get("/api/connectors/{cid}/export")
def export_connector(cid: str, request: Request, owner: str = Depends(require_owner)):
    c = db.get_connector(cid, owner)
    if not c:
        raise HTTPException(404, "not_found")
    return exporter.to_package(c, owner=owner)
