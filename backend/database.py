"""SQLite persistence for ZoidLab MCPLab (Foundry Package 12 — MCP Connector Lab).

Register MCP connectors, discover their tools via a REAL MCP handshake, govern which tools
are allowed (per-connector policy + TrustGate decisions), test-call tools for real over HTTP,
and freeze immutable connector versions. Owner = Nyquest user id; seed (owner NULL) is shared.
Secrets are NEVER stored in plaintext — a connector holds an auth *reference* label only.
"""
import os
import json
import uuid
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "mcplab.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, d=None):
    try:
        return json.loads(v) if v is not None else d
    except Exception:
        return d


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS connectors (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
                transport TEXT DEFAULT 'http', endpoint_url TEXT, auth_type TEXT DEFAULT 'none', auth_ref TEXT,
                tags TEXT, status TEXT DEFAULT 'draft', risk_level TEXT DEFAULT 'medium',
                allowed_tools TEXT, human_approval INTEGER DEFAULT 0, catalog INTEGER DEFAULT 0,
                tools TEXT, discovery TEXT, version TEXT DEFAULT '1.0.0',
                created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_conn_owner ON connectors(owner_user_id);
            CREATE TABLE IF NOT EXISTS connector_versions (
                id TEXT PRIMARY KEY, connector_id TEXT, owner_user_id TEXT, version TEXT, snapshot TEXT,
                integrity TEXT, created_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_cv_conn ON connector_versions(connector_id);
            CREATE TABLE IF NOT EXISTS test_runs (
                id TEXT PRIMARY KEY, owner_user_id TEXT, connector_id TEXT, connector_name TEXT, tool_name TEXT,
                arguments TEXT, status TEXT, decision TEXT, result TEXT, is_error INTEGER, error TEXT,
                latency_ms INTEGER, correlation_id TEXT, created_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_tr_owner ON test_runs(owner_user_id, created_at);
            """
        )


def _vis(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


# --- connectors ---
def _conn_out(r):
    if not r:
        return None
    d = dict(r)
    d["tags"] = _pj(d.get("tags"), []); d["allowed_tools"] = _pj(d.get("allowed_tools"), [])
    d["tools"] = _pj(d.get("tools"), []); d["discovery"] = _pj(d.get("discovery"), None)
    d["human_approval"] = bool(d.get("human_approval")); d["catalog"] = bool(d.get("catalog"))
    return d


def list_connectors(v=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM connectors WHERE {_vis()} ORDER BY updated_at DESC", (v,)).fetchall()
    return [_conn_out(r) for r in rows]


def get_connector(cid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM connectors WHERE id=? AND {_vis()}", (cid, v)).fetchone()
    return _conn_out(r)


def create_connector(d, owner, catalog=False):
    cid = new_id("conn"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO connectors (id,owner_user_id,name,slug,description,transport,endpoint_url,
                     auth_type,auth_ref,tags,status,risk_level,allowed_tools,human_approval,catalog,tools,discovery,version,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'1.0.0',?,?)""",
                  (cid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("transport", "http"),
                   d.get("endpoint_url", ""), d.get("auth_type", "none"), d.get("auth_ref", ""),
                   _j(d.get("tags", [])), d.get("status", "draft"), d.get("risk_level", "medium"),
                   _j(d.get("allowed_tools", [])), 1 if d.get("human_approval") else 0, 1 if catalog else 0,
                   _j([]), None, now, now))
    return get_connector(cid, owner)


def update_connector(cid, owner, fields):
    cur = get_connector(cid, owner)
    if not cur or (cur.get("owner_user_id") and cur["owner_user_id"] != owner):
        return None
    cols = []
    args = []
    for k in ("description", "transport", "endpoint_url", "auth_type", "auth_ref", "status", "risk_level"):
        if k in fields and fields[k] is not None:
            cols.append(f"{k}=?"); args.append(fields[k])
    for k in ("tags", "allowed_tools"):
        if k in fields and fields[k] is not None:
            cols.append(f"{k}=?"); args.append(_j(fields[k]))
    if "human_approval" in fields and fields["human_approval"] is not None:
        cols.append("human_approval=?"); args.append(1 if fields["human_approval"] else 0)
    if not cols:
        return cur
    cols.append("updated_at=?"); args.append(now_iso())
    args.append(cid)
    with _conn() as c:
        c.execute(f"UPDATE connectors SET {','.join(cols)} WHERE id=?", args)
    return get_connector(cid, owner)


def save_discovery(cid, owner, tools, discovery):
    with _conn() as c:
        c.execute("UPDATE connectors SET tools=?, discovery=?, updated_at=? WHERE id=? AND (owner_user_id IS NULL OR owner_user_id=?)",
                  (_j(tools), _j(discovery), now_iso(), cid, owner))
    return get_connector(cid, owner)


def delete_connector(cid, owner):
    cur = get_connector(cid, owner)
    if not cur or (cur.get("owner_user_id") and cur["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM connectors WHERE id=?", (cid,))
        c.execute("DELETE FROM connector_versions WHERE connector_id=?", (cid,))
    return True


# --- versions ---
def create_version(cid, owner, snapshot, integrity):
    cur = get_connector(cid, owner)
    if not cur:
        return None
    parts = (cur.get("version") or "1.0.0").split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except Exception:
        parts = ["1", "0", "1"]
    ver = ".".join(parts)
    vid = new_id("cver")
    with _conn() as c:
        c.execute("""INSERT INTO connector_versions (id,connector_id,owner_user_id,version,snapshot,integrity,created_at)
                     VALUES (?,?,?,?,?,?,?)""", (vid, cid, owner, ver, _j(snapshot), integrity, now_iso()))
        c.execute("UPDATE connectors SET version=?, updated_at=? WHERE id=?", (ver, now_iso(), cid))
    return {"id": vid, "version": ver, "integrity": integrity}


def list_versions(cid, owner):
    with _conn() as c:
        rows = c.execute(f"SELECT id,version,integrity,created_at FROM connector_versions WHERE connector_id=? AND {_vis()} ORDER BY created_at DESC",
                         (cid, owner)).fetchall()
    return [dict(r) for r in rows]


# --- test runs ---
def create_test_run(connector, tool_name, arguments, owner, correlation_id):
    rid = new_id("mtest")
    with _conn() as c:
        c.execute("""INSERT INTO test_runs (id,owner_user_id,connector_id,connector_name,tool_name,arguments,status,correlation_id,created_at)
                     VALUES (?,?,?,?,?,?,'running',?,?)""",
                  (rid, owner, connector["id"], connector["name"], tool_name, _j(arguments), correlation_id, now_iso()))
    return rid


def finish_test_run(rid, res):
    with _conn() as c:
        c.execute("""UPDATE test_runs SET status=?, decision=?, result=?, is_error=?, error=?, latency_ms=? WHERE id=?""",
                  (res.get("status", "failed"), res.get("decision"), _j(res.get("result")),
                   1 if res.get("is_error") else 0, res.get("error"), res.get("latency_ms"), rid))


def _test_out(r):
    if not r:
        return None
    d = dict(r); d["arguments"] = _pj(d.get("arguments"), {}); d["result"] = _pj(d.get("result"), None)
    d["is_error"] = bool(d.get("is_error")); return d


def list_test_runs(v=None, limit=100):
    with _conn() as c:
        rows = c.execute(f"""SELECT id,owner_user_id,connector_id,connector_name,tool_name,status,decision,is_error,
                             latency_ms,created_at FROM test_runs WHERE {_vis()} ORDER BY created_at DESC LIMIT ?""",
                         (v, limit)).fetchall()
    return [dict(r) for r in rows]


def get_test_run(rid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM test_runs WHERE id=? AND {_vis()}", (rid, v)).fetchone()
    return _test_out(r)


def stats(v=None):
    with _conn() as c:
        conns = c.execute(f"SELECT COUNT(*) n FROM connectors WHERE {_vis()}", (v,)).fetchone()["n"]
        active = c.execute(f"SELECT COUNT(*) n FROM connectors WHERE status='active' AND {_vis()}", (v,)).fetchone()["n"]
        tools = c.execute(f"SELECT COALESCE(SUM(json_array_length(COALESCE(tools,'[]'))),0) n FROM connectors WHERE {_vis()}", (v,)).fetchone()["n"]
        tests = c.execute(f"SELECT COUNT(*) n FROM test_runs WHERE {_vis()}", (v,)).fetchone()["n"]
    return {"connectors": conns, "active": active, "tools": tools or 0, "tests": tests}
