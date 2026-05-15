from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from app.db import init_db


@dataclass
class MCPLifespanContext:
    db_path: str


@asynccontextmanager
async def mcp_lifespan(server: FastMCP) -> AsyncIterator[MCPLifespanContext]:
    db_path = os.environ.get("AWR_DATA_DIR", "")
    if db_path:
        db_path = os.path.join(db_path, "awr.db")
    else:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "awr.db"
        )
    yield MCPLifespanContext(db_path=db_path)


AWR_INSTRUCTIONS = """\
Agent Web Review (AWR) — review web pages and fix issues.

Workflow:
1. Call awr_get_comments to fetch open review comments for a project.
2. Read each comment's comment_text (what to fix) and element_html/element_selector (where to fix).
3. Make the code changes.
4. Call awr_resolve_comment to mark each comment as done.
"""


def create_mcp_server(db_path: str | None = None) -> FastMCP:
    server = FastMCP("agent-web-review", instructions=AWR_INSTRUCTIONS, lifespan=mcp_lifespan)
    from app.mcp.tools import register_tools
    register_tools(server)
    return server
