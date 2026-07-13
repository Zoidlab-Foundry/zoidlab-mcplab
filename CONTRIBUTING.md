# Contributing

This is a ZoidLab Foundry package. It runs on the shared Foundry enterprise stack: a FastAPI
backend, a Postgres database with per-tenant Row-Level Security, a Celery worker (Redis broker)
for durable jobs, and a Next.js frontend gated behind Nyquest Pro.

## Layout
- `backend/` — FastAPI (`main.py`), Postgres data layer with RLS (`db_pg.py`), durable jobs
  (`jobs.py`) + Celery worker (`celery_app.py`, `tasks.py`), Foundry integration (`foundry.py`),
  export envelope (`exporter.py`).
- `frontend/` — Next.js 15 + React 19 (App Router). The Foundry Pro gate and SSO handoff are
  reusable components shared across the suite.

## Local development
Bring up the shared infra (Postgres + Redis + MinIO) with the `foundry-infra` compose stack,
then:

```
cd backend
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, REDIS_URL, NYQUEST_API_KEY, BUILDER_SESSION_SECRET
./.venv/bin/uvicorn main:app --port <PORT>
./.venv/bin/celery -A celery_app worker --loglevel=info   # in a second shell
```

```
cd frontend
npm install
npm run dev
```

## Ground rules
- **Never fabricate results.** Runs must go through the real relay / real provider, or be
  clearly labelled as a mock. Seeds contain definitions only, never fake outputs.
- **Fail closed.** Every data endpoint requires Nyquest Pro on both the Next middleware and the
  FastAPI backend. Don't add an endpoint that reads or writes tenant data without `require_pro`.
- **Respect tenant isolation.** All tenant tables are RLS-scoped by `owner_user_id`; go through
  `db_pg` (which sets `app.current_owner`) — never bypass it with the admin connection for
  per-user reads/writes.
- **No secrets in the repo or in exports.** Credentials are referenced, never stored.

## Pull requests
CI runs a Python compile check and a production `next build` on every push and PR. Keep both
green. Describe what's real vs mocked in the PR body.
