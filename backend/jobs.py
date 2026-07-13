"""Durable, tracked background jobs (blueprint §1.3).

Long-running work (a real relay run) is submitted as a durable job: it is persisted to SQLite
before it starts, executed in a background task with a timeout, and moves through an explicit
lifecycle — queued → running → (succeeded | partial | failed | blocked | timed_out | cancelled).
Jobs survive a process restart: on startup, any job left mid-flight is reconciled to
`interrupted` (and its underlying run marked failed) rather than silently lost. Clients poll
GET /api/jobs/{id} for status instead of holding a long HTTP request open.

This is a single-process durable tracker (SQLite + asyncio), not a distributed queue — the same
interface a Redis/Celery worker would sit behind, so callers don't change when that arrives.
"""
import asyncio
import datetime

import database as db

TERMINAL = {"succeeded", "partial", "failed", "blocked", "timed_out", "cancelled", "interrupted"}
_TASKS = {}  # job_id -> asyncio.Task (in-process handle for cancellation)


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def init():
    with db._conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, status TEXT,
            error TEXT, timeout_s INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id, created_at)")


def reconcile():
    """Mark jobs left running/queued by a crash or restart as interrupted."""
    with db._conn() as c:
        rows = c.execute("SELECT id FROM jobs WHERE status IN ('queued','running')").fetchall()
        for r in rows:
            c.execute("UPDATE jobs SET status='interrupted', error='process restarted', finished_at=? WHERE id=?",
                      (_now(), r["id"]))
    return len(rows)


def _set(job_id, **fields):
    cols = ", ".join(f"{k}=?" for k in fields)
    with db._conn() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), job_id))


def get(job_id, owner=None):
    with db._conn() as c:
        if owner is None:
            r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        else:
            r = c.execute("SELECT * FROM jobs WHERE id=? AND (owner_user_id IS NULL OR owner_user_id=?)",
                          (job_id, owner)).fetchone()
    return dict(r) if r else None


def list_jobs(owner, limit=50):
    with db._conn() as c:
        rows = c.execute("SELECT * FROM jobs WHERE (owner_user_id IS NULL OR owner_user_id=?) ORDER BY created_at DESC LIMIT ?",
                         (owner, limit)).fetchall()
    return [dict(r) for r in rows]


def submit(owner, kind, resource_id, runner, on_result=None, timeout_s=120, status_of=None):
    """Create a durable job and start it in the background.

    runner()      -> awaitable returning the engine result dict
    on_result(res)-> optional sync callback to persist the result (e.g. db.finish_run)
    status_of(res)-> optional map from result dict to a terminal job status
    """
    jid = db.new_id("job")
    with db._conn() as c:
        c.execute("INSERT INTO jobs (id,owner_user_id,kind,resource_id,status,timeout_s,created_at) VALUES (?,?,?,?,'queued',?,?)",
                  (jid, owner, kind, resource_id, timeout_s, _now()))
    task = asyncio.create_task(_run(jid, runner, on_result, timeout_s, status_of))
    _TASKS[jid] = task
    task.add_done_callback(lambda _t: _TASKS.pop(jid, None))
    return get(jid, owner)


def _default_status(res):
    s = (res or {}).get("status")
    if s == "completed":
        outcome = (res or {}).get("outcome")
        if outcome in ("partial", "goal_missed", "halted_no_handoff", "halted_ambiguous", "max_steps_reached"):
            return "partial"
        return "succeeded"
    if s in ("blocked", "failed"):
        return s
    return "succeeded" if s else "failed"


async def _run(jid, runner, on_result, timeout_s, status_of):
    _set(jid, status="running", started_at=_now())
    try:
        res = await asyncio.wait_for(runner(), timeout=timeout_s)
    except asyncio.CancelledError:
        _set(jid, status="cancelled", error="cancelled by user", finished_at=_now())
        raise
    except asyncio.TimeoutError:
        _set(jid, status="timed_out", error=f"exceeded {timeout_s}s", finished_at=_now())
        if on_result:
            try:
                on_result({"status": "failed", "error": f"timed out after {timeout_s}s"})
            except Exception:
                pass
        return
    except Exception as e:
        _set(jid, status="failed", error=str(e)[:400], finished_at=_now())
        return
    if on_result:
        try:
            on_result(res)
        except Exception:
            pass
    status = (status_of or _default_status)(res)
    _set(jid, status=status, error=(res or {}).get("error"), finished_at=_now())


def cancel(job_id, owner):
    j = get(job_id, owner)
    if not j or j["status"] in TERMINAL:
        return False
    task = _TASKS.get(job_id)
    if task:
        task.cancel()
        return True
    _set(job_id, status="cancelled", error="cancelled by user", finished_at=_now())
    return True
