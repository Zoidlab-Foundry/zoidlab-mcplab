"""Real MCP handshake over HTTP(S) — Streamable-HTTP / JSON-RPC 2.0.

Discovery does a genuine `initialize` + `tools/list`; test does a genuine `tools/call`.
This only works for HTTP-transport MCP servers reachable from the control plane; stdio and
auth-gated servers are reported honestly as not-testable-here rather than faked. SSRF-guarded:
private, loopback, and link-local hosts are refused.
"""
import ipaddress
import socket
import json
import time
from urllib.parse import urlparse
import httpx

PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "zoidlab-mcplab", "version": "1.0.0"}


def _ssrf_ok(url):
    try:
        u = urlparse(url)
    except Exception:
        return False, "unparseable_url"
    if u.scheme not in ("http", "https"):
        return False, "scheme_must_be_http_s"
    host = u.hostname
    if not host:
        return False, "no_host"
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f"dns_error: {str(e)[:80]}"
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
            return False, f"blocked_host_range: {ip}"
    return True, None


def _headers(auth_type, auth_value):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if auth_type == "bearer" and auth_value:
        h["Authorization"] = f"Bearer {auth_value}"
    elif auth_type == "header" and auth_value and ":" in auth_value:
        k, v = auth_value.split(":", 1)
        h[k.strip()] = v.strip()
    return h


def _parse_body(r):
    ct = r.headers.get("content-type", "")
    if "text/event-stream" in ct:
        for line in r.text.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except Exception:
                    continue
        return None
    try:
        return r.json()
    except Exception:
        return None


async def _rpc(client, url, headers, method, params, rid):
    payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
    r = await client.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return _parse_body(r)


async def discover(endpoint_url, auth_type="none", auth_value=None, timeout=15):
    """Real initialize + tools/list. Returns {ok, tools, server_info, error}."""
    ok, why = _ssrf_ok(endpoint_url)
    if not ok:
        return {"ok": False, "reachable": False, "error": why, "tools": []}
    headers = _headers(auth_type, auth_value)
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            init = await _rpc(c, endpoint_url, headers, "initialize",
                              {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                               "clientInfo": _CLIENT_INFO}, 1)
            server_info = ((init or {}).get("result") or {}).get("serverInfo") if init else None
            listing = await _rpc(c, endpoint_url, headers, "tools/list", {}, 2)
            tools = ((listing or {}).get("result") or {}).get("tools") if listing else []
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        hint = "auth_required" if code in (401, 403) else f"http_{code}"
        return {"ok": False, "reachable": True, "error": hint, "tools": []}
    except Exception as e:
        return {"ok": False, "reachable": False, "error": str(e)[:160], "tools": []}
    norm = [{"name": t.get("name"), "description": t.get("description", ""),
             "input_schema": t.get("inputSchema") or t.get("input_schema") or {}} for t in (tools or [])]
    return {"ok": True, "reachable": True, "server_info": server_info, "tools": norm,
            "latency_ms": int((time.perf_counter() - t0) * 1000)}


async def call_tool(endpoint_url, tool_name, arguments, auth_type="none", auth_value=None, timeout=25):
    """Real tools/call. Returns {ok, result, is_error, error}."""
    ok, why = _ssrf_ok(endpoint_url)
    if not ok:
        return {"ok": False, "error": why}
    headers = _headers(auth_type, auth_value)
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            await _rpc(c, endpoint_url, headers, "initialize",
                       {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": _CLIENT_INFO}, 1)
            res = await _rpc(c, endpoint_url, headers, "tools/call",
                             {"name": tool_name, "arguments": arguments or {}}, 3)
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"http_{e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    result = (res or {}).get("result") or {}
    return {"ok": True, "result": result, "is_error": bool(result.get("isError")),
            "latency_ms": int((time.perf_counter() - t0) * 1000)}
