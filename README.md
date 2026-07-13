# ZoidLab MCPLab — Foundry Package 12

MCP Connector Lab. A control plane for Model Context Protocol connectors: register a
connector, **discover its tools with a real MCP handshake** (JSON-RPC `initialize` +
`tools/list` over Streamable HTTP), govern which tools are callable (per-connector
allow-list, risk level, human-approval gate, TrustGate decisions), **test-call tools for
real** (`tools/call`), and freeze immutable, integrity-hashed connector versions.

Discovery and test are genuinely real for reachable HTTP/SSE MCP endpoints and SSRF-guarded
(private/loopback hosts refused). stdio and auth-gated servers are governed and versioned
here but honestly reported as not-callable-from-the-control-plane. Secrets are never stored:
a connector carries an auth *reference* label only; credentials are supplied at call time and
never persisted. Every data endpoint requires Nyquest Pro (fail-closed on the Next middleware
AND the FastAPI backend).

## Layout
- `backend/` — FastAPI + SQLite. `mcp_client.py` real JSON-RPC MCP client (SSRF-guarded);
  `database.py` owner-scoped connectors/versions/test-runs; `main.py` the `/api` surface.
- `frontend/` — Next 15 + React 19 (indigo theme). Dashboard, Connectors (+ detail:
  discover/govern/test/version), Tests.

## Run locally
Backend: `cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn main:app --port 8706`
Frontend: `cd frontend && npm install && MCPLAB_API_URL=http://127.0.0.1:8706 npm run dev` (port 3706)

Live: https://mcplab.zoidlab.ai
