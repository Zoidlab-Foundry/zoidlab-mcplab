"""Durable tracked jobs backed by Postgres + Celery (§1.3 / §3.2).

The API records a job row (queued) and enqueues a Celery task; a separate worker process
executes it and drives the row through queued → running → succeeded | partial | failed |
blocked | timed_out | cancelled. Because the worker is its own service with a Redis-backed
queue, jobs survive an API restart; `reconcile()` on API startup sweeps rows a dead worker
left behind (older than a grace window) into `interrupted`, and terminal failures after all
retries are copied to `dead_letters`. Job rows are tenant-scoped by RLS like everything else.
"""
import datetime
import db_pg as db

TERMINAL = {"succeeded", "partial", "failed", "blocked", "timed_out", "cancelled", "interrupted"}
_GRACE_SECONDS = 1800  # a 'running' row older than this with no worker is treated as interrupted


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def init():
    pass  # jobs table is created in db_pg.init()


def create(owner, kind, resource_id, timeout_s=120):
    jid = db.new_id("job")
    with db._tx(owner) as cur:
        cur.execute("""INSERT INTO jobs (id,owner_user_id,kind,resource_id,status,timeout_s,created_at)
                       VALUES (%s,%s,%s,%s,'queued',%s,%s)""",
                    (jid, owner, kind, resource_id, timeout_s, _now()))
    return jid


def set_celery(jid, owner, celery_id):
    with db._tx(owner) as cur:
        cur.execute("UPDATE jobs SET celery_id=%s WHERE id=%s", (celery_id, jid))


def mark_running(jid, owner, attempts=1):
    with db._tx(owner) as cur:
        cur.execute("UPDATE jobs SET status='running', attempts=%s, started_at=COALESCE(started_at,%s) WHERE id=%s",
                    (attempts, _now(), jid))


def mark(jid, owner, status, error=None, dead=False):
    with db._tx(owner) as cur:
        cur.execute("UPDATE jobs SET status=%s, error=%s, finished_at=%s WHERE id=%s", (status, error, _now(), jid))
        if dead:
            cur.execute("""INSERT INTO dead_letters (id,owner_user_id,kind,resource_id,error,created_at)
                           SELECT %s, owner_user_id, kind, resource_id, %s, %s FROM jobs WHERE id=%s""",
                        (db.new_id("dl"), error, _now(), jid))


def status_from_result(res):
    s = (res or {}).get("status")
    if s == "completed":
        outcome = (res or {}).get("outcome")
        if outcome in ("partial", "goal_missed", "halted_no_handoff", "halted_ambiguous", "max_steps_reached"):
            return "partial"
        return "succeeded"
    if s in ("blocked", "failed"):
        return s
    return "succeeded" if s else "failed"


def mark_terminal(jid, owner, res):
    mark(jid, owner, status_from_result(res), error=(res or {}).get("error"))


def get(jid, owner=None):
    with db._tx(owner) as cur:
        cur.execute("SELECT * FROM jobs WHERE id=%s", (jid,))
        return cur.fetchone()


def list_jobs(owner, limit=50):
    with db._tx(owner) as cur:
        cur.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()


def cancel(jid, owner):
    j = get(jid, owner)
    if not j or j["status"] in TERMINAL:
        return False
    # best-effort: revoke the Celery task if we have its id
    if j.get("celery_id"):
        try:
            from celery_app import app as capp
            capp.control.revoke(j["celery_id"], terminate=True, signal="SIGTERM")
        except Exception:
            pass
    mark(jid, owner, "cancelled", "cancelled by user")
    return True


def reconcile():
    """Cross-tenant sweep (admin/superuser, bypasses RLS): interrupt stale in-flight jobs."""
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(seconds=_GRACE_SECONDS)).isoformat() + "Z"
    with db.admin_conn() as c:
        cur = c.execute("""UPDATE jobs SET status='interrupted', error='reconciled after restart', finished_at=%s
                           WHERE status IN ('queued','running') AND created_at < %s""", (_now(), cutoff))
        return cur.rowcount
