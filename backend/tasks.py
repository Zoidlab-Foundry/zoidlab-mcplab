"""Celery tasks for MCPLab — the real MCP tool call runs here, in the worker process."""
import asyncio

from celery.exceptions import SoftTimeLimitExceeded

from celery_app import app
import db_pg as db
import mcp_client
import jobs


def _job_status(res):
    if res.get("status") == "completed":
        return "partial" if res.get("is_error") else "succeeded"
    return "failed"


@app.task(bind=True, name="mcplab.run_test", max_retries=1,
          autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True)
def run_test(self, job_id, run_id, connector_id, tool_name, arguments, auth_value, decision, owner, corr):
    jobs.mark_running(job_id, owner, attempts=self.request.retries + 1)
    db.set_test_status(run_id, "running", owner)
    try:
        c = db.get_connector(connector_id, owner)
        if not c:
            raise RuntimeError("connector not found")
        res = asyncio.run(mcp_client.call_tool(c.get("endpoint_url"), tool_name, arguments or {},
                                               auth_type=c.get("auth_type", "none"), auth_value=auth_value))
        if res.get("ok"):
            out = {"status": "completed", "decision": decision, "result": res.get("result"),
                   "is_error": res.get("is_error"), "latency_ms": res.get("latency_ms")}
        else:
            out = {"status": "failed", "decision": decision, "error": res.get("error"), "latency_ms": res.get("latency_ms")}
        db.finish_test_run(run_id, out, owner)
        jobs.mark(job_id, owner, _job_status(out), error=out.get("error"))
        return {"status": out["status"]}
    except SoftTimeLimitExceeded:
        db.finish_test_run(run_id, {"status": "failed", "decision": decision, "error": "timed out"}, owner)
        jobs.mark(job_id, owner, "timed_out", "soft time limit exceeded")
        return {"status": "timed_out"}
    except Exception as e:
        if self.request.retries >= self.max_retries:
            db.finish_test_run(run_id, {"status": "failed", "decision": decision, "error": str(e)[:400]}, owner)
            jobs.mark(job_id, owner, "failed", str(e)[:400], dead=True)
            return {"status": "failed"}
        raise
