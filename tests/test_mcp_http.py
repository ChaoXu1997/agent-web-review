"""Regression tests for the real MCP streamable-http endpoint.

These hit /mcp over the actual ASGI mount path (NOT a FakeCtx), guarding the
two bugs that broke the MCP wiring until project-level install was attempted:

1. Endpoint path: the old mcp SDK's streamable_http_app() hardcodes the endpoint
   at /mcp internally, so mounting it at /mcp made the real path /mcp/mcp.
   Mount at "/" so FastAPI /api/* wins first and /mcp falls through to the MCP
   app.  Symptom was: POST /mcp -> 307, POST /mcp/ -> 404.

2. Session manager: a mounted sub-app's own lifespan is NOT triggered by
   Starlette, so the MCP session manager never started. The parent FastAPI
   lifespan must run it via an AsyncExitStack.  Symptom was: 500
   "Task group is not initialized. Make sure to use run()."

Both are exercised by driving the parent lifespan ourselves (runs the session
manager) and POSTing the real streamable-http initialize over ASGITransport —
same event loop, no extra deps.
"""

from __future__ import annotations

import asyncio

import httpx


def _init_request() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "awr-test", "version": "1.0"},
        },
    }


async def _post_mcp_initialize(app) -> tuple[int, str, str]:
    """Run the parent lifespan (starts the MCP session manager) and POST /mcp.

    We drive the lifespan manually (not via TestClient) so the session manager
    and the httpx request share one event loop. The initialize response is an
    SSE stream that stays open; we read only until the serverInfo line and let
    the context managers tear the connection down.
    """
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        # Host must satisfy MCP's DNS-rebinding protection, which matches
        # allowed_hosts like "localhost:*" — so include a port. ASGITransport
        # does not open a socket; only the Host header is validated.
        async with httpx.AsyncClient(
            transport=transport, base_url="http://localhost:9876"
        ) as client:
            async with client.stream(
                "POST",
                "/mcp",
                json=_init_request(),
                headers={"Accept": "application/json, text/event-stream"},
            ) as resp:
                status = resp.status_code
                content_type = resp.headers.get("content-type", "")
                collected: list[str] = []
                async for line in resp.aiter_lines():
                    collected.append(line)
                    if "serverInfo" in line:
                        break
                return status, content_type, "\n".join(collected)


def test_mcp_initialize_reaches_endpoint(app):
    """Regression (bug 1): POST /mcp must hit the MCP endpoint — 200 + SSE stream,
    not 404/307 (wrong mount path)."""
    status, content_type, _ = asyncio.run(_post_mcp_initialize(app))
    assert status == 200
    assert content_type.startswith("text/event-stream")


def test_mcp_initialize_session_manager_running(app):
    """Regression (bug 2): the session manager must be running via the parent
    lifespan and return a valid initialize result — was 500 'Task group is not
    initialized'."""
    _, _, body = asyncio.run(_post_mcp_initialize(app))
    assert "serverInfo" in body
    assert "agent-web-review" in body
