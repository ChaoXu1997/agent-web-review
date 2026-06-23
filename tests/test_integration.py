class TestCommentCRUD:
    def test_create_and_list_no_auth(self, client):
        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://example.com",
                "comment_text": "fix the button",
                "element_selector": "#btn",
            },
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["comment_text"] == "fix the button"

        resp = client.get("/api/comments")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_too_long(self, client):
        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://a.com",
                "comment_text": "x" * 10001,
            },
        )
        assert resp.status_code == 400

    def test_create_oversized_screenshot_rejected(self, client):
        from app.models import MAX_SCREENSHOT_B64

        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://a.com",
                "comment_text": "ok",
                "screenshot_b64": "x" * (MAX_SCREENSHOT_B64 + 1),
            },
        )
        assert resp.status_code == 422

    def test_create_oversized_element_html_rejected(self, client):
        from app.models import MAX_ELEMENT_FIELD

        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://a.com",
                "comment_text": "ok",
                "element_html": "x" * (MAX_ELEMENT_FIELD + 1),
            },
        )
        assert resp.status_code == 422

    def test_resolve_comment(self, client):
        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://a.com",
                "comment_text": "resolve me",
            },
        )
        cid = resp.json()["id"]
        resp = client.patch(f"/api/comments/{cid}", json={"status": "resolved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_delete_comment(self, client):
        resp = client.post(
            "/api/comments",
            json={
                "page_url": "http://a.com",
                "comment_text": "delete me",
            },
        )
        cid = resp.json()["id"]
        resp = client.delete(f"/api/comments/{cid}")
        assert resp.status_code == 204


class TestProjectMappings:
    def test_create_and_list_no_auth(self, client):
        resp = client.post(
            "/api/projects",
            json={
                "page_url": "http://example.com",
                "project_path": "/home/user/proj",
            },
        )
        assert resp.status_code == 201

        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_duplicate_conflict(self, client):
        client.post(
            "/api/projects",
            json={
                "page_url": "http://example.com",
                "project_path": "/proj",
            },
        )
        resp = client.post(
            "/api/projects",
            json={
                "page_url": "http://example.com",
                "project_path": "/other",
            },
        )
        assert resp.status_code == 409


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestSSE:
    def test_sse_manager_broadcast(self):
        # add_client must run inside an event loop (it records the owning loop);
        # broadcast schedules the put via call_soon_threadsafe on that loop.
        import asyncio
        from app.routes.sse import SSEManager

        mgr = SSEManager()

        async def scenario():
            q: asyncio.Queue = asyncio.Queue()
            mgr.add_client("c1", q)
            assert mgr.client_count == 1
            mgr.broadcast("comment_resolved", {"id": "x"})
            # broadcast schedules async; let the loop run one tick to deliver
            await asyncio.sleep(0)
            return q

        q = asyncio.run(scenario())
        msg = q.get_nowait()
        assert "comment_resolved" in msg
