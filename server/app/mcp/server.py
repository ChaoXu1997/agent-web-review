from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP


@dataclass
class MCPLifespanContext:
    app: FastAPI


AWR_INSTRUCTIONS = """\
Agent Web Review (AWR) — review web pages and fix issues.

Workflow:
1. Call awr_get_comments to fetch open review comments for a project
   (pass project_path=<CWD> to resolve CWD->URL mappings).
2. Read each comment's comment_text (what to fix) and
   element_html/element_selector (where to fix).
3. Make the code changes.
4. Call awr_resolve_comment to mark each comment as done.
"""


def create_mcp_server(app: FastAPI | None = None) -> FastMCP:
    @asynccontextmanager
    async def mcp_lifespan(server: FastMCP) -> AsyncIterator[MCPLifespanContext]:
        # Resolve at request time: production passes app=None and relies on the
        # process-global _app (assigned at the end of create_app); tests pass app
        # directly. Resolving here avoids reading _app before create_app finishes.
        resolved_app = app if app is not None else _fallback_app()
        yield MCPLifespanContext(app=resolved_app)

    server = FastMCP(
        "agent-web-review", instructions=AWR_INSTRUCTIONS, lifespan=mcp_lifespan
    )
    from app.mcp.tools import register_tools

    register_tools(server)
    return server


def _fallback_app() -> FastAPI:
    """Resolve the process-global app when create_mcp_server is called without one."""
    from app.main import _app

    return _app
