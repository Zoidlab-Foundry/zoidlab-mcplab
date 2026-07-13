"""Postgres data layer for MCPLab with per-tenant Row-Level Security (§3.2).

Tenant isolation is DB-enforced (FORCE RLS keyed on app.current_owner). App connections use
the RLS-enforced role; DDL + cross-tenant admin use the superuser. Secrets are never stored —
connectors keep an auth *reference* label only. Public API mirrors the former sqlite database.py.
"""
import os
import uuid
import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app_rls@127.0.0.1:5433/mcplab")
DATABASE_URL_ADMIN = os.environ.get("DATABASE_URL_ADMIN", "postgresql://foundry@127.0.0.1:5433/mcplab")
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": False})


def admin_conn():
    return psycopg.connect(DATABASE_URL_ADMIN, row_factory=dict_row)


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


class _tx:
    def __init__(self, owner):
        self.owner = owner or ""

    def __enter__(self):
        self.conn = _pool.getconn()
        self.cur = self.conn.cursor(row_factory=dict_row)
        self.cur.execute("SELECT set_config('app.current_owner', %s, true)", (self.owner,))
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        try:
            self.conn.rollback() if exc_type else self.conn.commit()
        finally:
            self.cur.close()
            _pool.putconn(self.conn)


_TENANT_TABLES = ["connectors", "connector_versions", "test_runs", "jobs"]


def init():
    with admin_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS connectors (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
            transport TEXT DEFAULT 'http', endpoint_url TEXT, auth_type TEXT DEFAULT 'none', auth_ref TEXT,
            tags JSONB, status TEXT DEFAULT 'draft', risk_level TEXT DEFAULT 'medium',
            allowed_tools JSONB, human_approval BOOLEAN DEFAULT false, catalog BOOLEAN DEFAULT false,
            tools JSONB, discovery JSONB, version TEXT DEFAULT '1.0.0', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS connector_versions (
            id TEXT PRIMARY KEY, connector_id TEXT, owner_user_id TEXT, version TEXT, snapshot JSONB,
            integrity TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS test_runs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, connector_id TEXT, connector_name TEXT, tool_name TEXT,
            arguments JSONB, status TEXT, decision TEXT, result JSONB, is_error BOOLEAN, error TEXT,
            latency_ms INTEGER, correlation_id TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, status TEXT, error TEXT,
            attempts INTEGER DEFAULT 0, celery_id TEXT, timeout_s INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS dead_letters (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, error TEXT, created_at TEXT)""")
        for t in _TENANT_TABLES:
            c.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            c.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
            c.execute(f"DROP POLICY IF EXISTS {t}_isolation ON {t}")
            c.execute(f"""CREATE POLICY {t}_isolation ON {t}
                USING (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))
                WITH CHECK (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_conn_owner ON connectors(owner_user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tr_owner ON test_runs(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id, created_at)")
        c.execute("GRANT USAGE ON SCHEMA public TO app_rls")
        c.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO app_rls")


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _pool.connection() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)
                     ON CONFLICT (id) DO UPDATE SET email=COALESCE(EXCLUDED.email,users.email),
                       name=COALESCE(EXCLUDED.name,users.name), updated_at=EXCLUDED.updated_at""",
                  (uid, email, name, now, now))


# --- connectors ---
def list_connectors(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM connectors ORDER BY updated_at DESC")
        return cur.fetchall()


def get_connector(cid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM connectors WHERE id=%s", (cid,))
        return cur.fetchone()


def create_connector(d, owner, catalog=False):
    cid = new_id("conn"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO connectors (id,owner_user_id,name,slug,description,transport,endpoint_url,
                       auth_type,auth_ref,tags,status,risk_level,allowed_tools,human_approval,catalog,tools,discovery,version,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'1.0.0',%s,%s)""",
                    (cid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("transport", "http"),
                     d.get("endpoint_url", ""), d.get("auth_type", "none"), d.get("auth_ref", ""),
                     Json(d.get("tags", [])), d.get("status", "draft"), d.get("risk_level", "medium"),
                     Json(d.get("allowed_tools", [])), bool(d.get("human_approval")), bool(catalog),
                     Json([]), None, now, now))
    return get_connector(cid, owner)


def update_connector(cid, owner, fields):
    cur_c = get_connector(cid, owner)
    if not cur_c or (cur_c.get("owner_user_id") and cur_c["owner_user_id"] != owner):
        return None
    cols, args = [], []
    for k in ("description", "transport", "endpoint_url", "auth_type", "auth_ref", "status", "risk_level"):
        if k in fields and fields[k] is not None:
            cols.append(f"{k}=%s"); args.append(fields[k])
    for k in ("tags", "allowed_tools"):
        if k in fields and fields[k] is not None:
            cols.append(f"{k}=%s"); args.append(Json(fields[k]))
    if "human_approval" in fields and fields["human_approval"] is not None:
        cols.append("human_approval=%s"); args.append(bool(fields["human_approval"]))
    if not cols:
        return cur_c
    cols.append("updated_at=%s"); args.append(now_iso())
    args.append(cid)
    with _tx(owner) as cur:
        cur.execute(f"UPDATE connectors SET {','.join(cols)} WHERE id=%s", args)
    return get_connector(cid, owner)


def save_discovery(cid, owner, tools, discovery):
    with _tx(owner) as cur:
        cur.execute("UPDATE connectors SET tools=%s, discovery=%s, updated_at=%s WHERE id=%s",
                    (Json(tools), Json(discovery), now_iso(), cid))
    return get_connector(cid, owner)


def delete_connector(cid, owner):
    cur_c = get_connector(cid, owner)
    if not cur_c or (cur_c.get("owner_user_id") and cur_c["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM connector_versions WHERE connector_id=%s", (cid,))
        cur.execute("DELETE FROM connectors WHERE id=%s", (cid,))
    return True


# --- versions ---
def create_version(cid, owner, snapshot, integrity):
    cur_c = get_connector(cid, owner)
    if not cur_c:
        return None
    parts = (cur_c.get("version") or "1.0.0").split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except Exception:
        parts = ["1", "0", "1"]
    ver = ".".join(parts)
    vid = new_id("cver")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO connector_versions (id,connector_id,owner_user_id,version,snapshot,integrity,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""", (vid, cid, owner, ver, Json(snapshot), integrity, now_iso()))
        cur.execute("UPDATE connectors SET version=%s, updated_at=%s WHERE id=%s", (ver, now_iso(), cid))
    return {"id": vid, "version": ver, "integrity": integrity}


def list_versions(cid, owner):
    with _tx(owner) as cur:
        cur.execute("SELECT id,version,integrity,created_at FROM connector_versions WHERE connector_id=%s ORDER BY created_at DESC", (cid,))
        return cur.fetchall()


# --- test runs ---
def create_test_run(connector, tool_name, arguments, owner, correlation_id):
    rid = new_id("mtest")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO test_runs (id,owner_user_id,connector_id,connector_name,tool_name,arguments,status,correlation_id,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,'running',%s,%s)""",
                    (rid, owner, connector["id"], connector["name"], tool_name, Json(arguments), correlation_id, now_iso()))
    return rid


def finish_test_run(rid, res, owner=None):
    with _tx(owner) as cur:
        cur.execute("""UPDATE test_runs SET status=%s, decision=%s, result=%s, is_error=%s, error=%s, latency_ms=%s WHERE id=%s""",
                    (res.get("status", "failed"), res.get("decision"), Json(res.get("result")),
                     bool(res.get("is_error")), res.get("error"), res.get("latency_ms"), rid))


def set_test_status(rid, status, owner=None):
    with _tx(owner) as cur:
        cur.execute("UPDATE test_runs SET status=%s WHERE id=%s", (status, rid))


def list_test_runs(v=None, limit=100):
    with _tx(v) as cur:
        cur.execute("""SELECT id,owner_user_id,connector_id,connector_name,tool_name,status,decision,is_error,
                       latency_ms,created_at FROM test_runs ORDER BY created_at DESC LIMIT %s""", (limit,))
        return cur.fetchall()


def get_test_run(rid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM test_runs WHERE id=%s", (rid,))
        return cur.fetchone()


def stats(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT COUNT(*) n FROM connectors"); conns = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM connectors WHERE status='active'"); active = cur.fetchone()["n"]
        cur.execute("SELECT COALESCE(SUM(jsonb_array_length(COALESCE(tools,'[]'::jsonb))),0) n FROM connectors"); tools = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM test_runs"); tests = cur.fetchone()["n"]
    return {"connectors": conns, "active": active, "tools": tools or 0, "tests": tests}
