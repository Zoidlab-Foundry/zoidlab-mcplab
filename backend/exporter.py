"""MCPLab package export — a portable, governed MCP connector definition wrapped in the
canonical Foundry base envelope (blueprint §6.2). Auth is an opaque *reference* only; no
secret material is ever included."""
import envelope


def to_package(conn, owner=None):
    payload = {
        "schema_version": "1.0",
        "package_type": "nyquest_mcp_connector_package",
        "foundry_package": "mcp",
        "resource_version": conn.get("version", "1.0.0"),
        "connector": {"name": conn.get("name"), "description": conn.get("description"),
                      "transport": conn.get("transport"), "endpoint_url": conn.get("endpoint_url"),
                      "auth_type": conn.get("auth_type"), "auth_ref": conn.get("auth_ref"),
                      "tags": conn.get("tags", [])},
        "governance": {"risk_level": conn.get("risk_level"), "human_approval": conn.get("human_approval"),
                       "allowed_tools": conn.get("allowed_tools", [])},
        "discovered_tools": [{"name": t.get("name"), "description": t.get("description")} for t in conn.get("tools", [])],
        "dependencies": [],
        "credential_refs": [{"ref": conn.get("auth_ref"), "type": conn.get("auth_type")}] if conn.get("auth_ref") else [],
    }
    return envelope.wrap("mcp", "mcp_connector", conn.get("id"), conn.get("version", "1.0.0"),
                         payload, nyquest_user_id=owner)
