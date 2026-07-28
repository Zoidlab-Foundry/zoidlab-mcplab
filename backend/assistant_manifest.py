"""MCPLab assistant manifest — what the in-app assistant knows and may do.

This file is the assistant's security boundary: only the capabilities declared here exist
for it, and they execute through this app's own session-authed API (require_pro + RLS apply).
Delete-class operations are intentionally not declared, and the human-approval `approve`
flag is deliberately NOT exposed — approval-gated tool calls stay with the human UI.
"""
from foundry_common.assistant import cap, page

MANIFEST = {
    "app": "MCPLab",
    "description": (
        "MCPLab is a governed MCP connector lab: register Model Context Protocol "
        "connectors, discover their live tool manifests with a real MCP handshake, and "
        "run governed test calls over HTTP. Every call passes governance gates — "
        "per-connector tool allow-lists and human-approval gates apply, and TrustGate "
        "preflights each call. Test runs execute as DURABLE background jobs (poll the "
        "job/test until it completes). Secrets are never stored; connectors carry an "
        "auth reference label only."
    ),
    "base_url": "http://127.0.0.1:8706",
    "pages": [
        page("/", "Dashboard", "Overview: connector/test/version stats and recent activity."),
        page("/connectors", "Connectors", "Register MCP connectors and browse the catalog.",
             assists={"new-connector": "the New connector button"}),
        page("/connectors/{id}", "Connector detail",
             "Discover tools, set governance (allow-list, approval, status), run test "
             "calls, freeze versions, export.",
             assists={"discover-tools": "the Discover tools button",
                      "run-test": "the Run test call button"}),
        page("/tests", "Test calls", "Every tool invocation with its governance decision."),
    ],
    "capabilities": [
        cap("list_connectors", "GET", "/api/connectors", risk="read",
            desc="The user's MCP connectors with transport, auth type, risk, governance, and tools."),
        cap("get_connector", "GET", "/api/connectors/{cid}", risk="read",
            desc="One connector: endpoint, discovered tools, allow-list, approval flag, versions count.",
            params={"cid": "connector id"}),
        cap("list_tests", "GET", "/api/tests", risk="read",
            desc="The user's test calls, newest first, with status and governance decision."),
        cap("get_test", "GET", "/api/tests/{rid}", risk="read",
            desc="One test run: status, decision, latency, result or error.",
            params={"rid": "test run id"}),
        cap("list_jobs", "GET", "/api/jobs", risk="read",
            desc="The user's durable background jobs (test calls run as jobs)."),
        cap("get_job", "GET", "/api/jobs/{jid}", risk="read",
            desc="One background job: state, timings, linked test run.",
            params={"jid": "job id"}),
        cap("stats", "GET", "/api/stats", risk="read",
            desc="Counts of connectors, test calls, and frozen versions."),
        cap("register_connector", "POST", "/api/connectors", risk="write",
            desc="Register an MCP connector. Secrets are never stored — auth_ref is a "
                 "label only. Confirm name and endpoint with the user first.",
            params={"name": "connector name",
                    "description": "short description",
                    "transport": "'http', 'sse', or 'stdio' (default http)",
                    "endpoint_url": "MCP endpoint URL (http/sse only)",
                    "auth_type": "'none', 'bearer', or 'header' (default none)",
                    "auth_ref": "auth reference label (never a secret)",
                    "tags": "list of tag strings",
                    "risk_level": "'low', 'medium', or 'high' (default medium)",
                    "human_approval": "true to require human approval before any tool call"}),
        cap("discover_tools", "POST", "/api/connectors/{cid}/discover", risk="write",
            desc="Run a real MCP handshake against the connector's endpoint and save its "
                 "live tool manifest. Only http/sse transports are reachable.",
            params={"cid": "connector id"}),
        cap("run_test", "POST", "/api/test", risk="write",
            desc="Run a governed test call of one tool. Allow-lists, human-approval gates, "
                 "and TrustGate apply — the call may come back 'blocked' with a decision. "
                 "Executes as a durable background job: poll get_test/get_job for the result. "
                 "Approval-gated calls must be approved by the user in the app UI.",
            params={"connector_id": "connector id", "tool_name": "tool to call",
                    "arguments": "JSON object of tool arguments"}),
    ],
}
