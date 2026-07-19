"""Celery app for VisionLab — the durable distributed job runner (§3.2).

Redis is the broker + result backend. Tasks ack late (a crashed worker re-delivers the job),
run one-at-a-time per worker slot, carry soft/hard time limits, retry transient failures with
backoff, and are rate-limited per worker. Registered task module: tasks.
"""
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0")

app = Celery("mcplab", broker=REDIS_URL, backend=REDIS_URL, include=["tasks"])
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=150,          # hard kill
    task_soft_time_limit=120,     # raises SoftTimeLimitExceeded first
    task_default_rate_limit="60/m",
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)


# Each prefork child must own its own Postgres pool: connections opened in the parent at
# import break on fork, and the inherited pool times out on first use (PoolTimeout).
from celery.signals import worker_process_init


@worker_process_init.connect
def _fresh_db_pool_per_child(**_):
    import db_pg
    from psycopg_pool import ConnectionPool
    try:
        db_pg._pool.close()
    except Exception:
        pass
    db_pg._pool = ConnectionPool(db_pg.DATABASE_URL, min_size=1, max_size=10,
                                 open=True, kwargs={"autocommit": False})
