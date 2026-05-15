def test_mcp_create_server():
    from mcp.server.fastmcp import FastMCP
    from app.mcp.server import create_mcp_server
    import tempfile, os
    tmp = tempfile.mkdtemp()
    server = create_mcp_server(db_path=os.path.join(tmp, "test.db"))
    assert isinstance(server, FastMCP)
