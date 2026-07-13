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
