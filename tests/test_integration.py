class TestCommentCRUD:
    def test_create_and_list(self, client, auth_headers):
        resp = client.post("/api/comments", json={
            "page_url": "http://example.com",
            "comment_text": "fix the button",
            "element_selector": "#btn",
        }, headers=auth_headers)
        assert resp.status_code == 201
        created = resp.json()
        assert created["comment_text"] == "fix the button"

        resp = client.get("/api/comments", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_too_long(self, client, auth_headers):
        resp = client.post("/api/comments", json={
            "page_url": "http://a.com",
            "comment_text": "x" * 10001,
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_resolve_comment(self, client, auth_headers):
        resp = client.post("/api/comments", json={
            "page_url": "http://a.com", "comment_text": "resolve me",
        }, headers=auth_headers)
        cid = resp.json()["id"]
        resp = client.patch(f"/api/comments/{cid}", json={"status": "resolved"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_delete_comment(self, client, auth_headers):
        resp = client.post("/api/comments", json={
            "page_url": "http://a.com", "comment_text": "delete me",
        }, headers=auth_headers)
        cid = resp.json()["id"]
        resp = client.delete(f"/api/comments/{cid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_unauthenticated(self, client):
        resp = client.get("/api/comments")
        assert resp.status_code == 401


class TestAdminKeys:
    def test_create_and_list(self, client, admin_token):
        resp = client.post(
            "/admin/keys", json={"name": "alice"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        key = resp.json()["api_key"]
        assert len(key) >= 32

        resp = client.get("/admin/keys", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_revoke_key(self, client, admin_token):
        resp = client.post(
            "/admin/keys", json={"name": "bob"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        uid = resp.json()["id"]
        resp = client.delete(f"/admin/keys/{uid}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    def test_admin_wrong_token(self, client):
        resp = client.get("/admin/keys", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401


class TestProjectMappings:
    def test_create_and_list(self, client, auth_headers):
        resp = client.post("/api/projects", json={
            "page_url": "http://example.com", "project_path": "/home/user/proj",
        }, headers=auth_headers)
        assert resp.status_code == 201

        resp = client.get("/api/projects", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestDataIsolation:
    def test_users_cant_see_others_comments(self, client, admin_token):
        u1 = client.post("/admin/keys", json={"name": "alice"}, headers={"Authorization": f"Bearer {admin_token}"}).json()
        u2 = client.post("/admin/keys", json={"name": "bob"}, headers={"Authorization": f"Bearer {admin_token}"}).json()

        h1 = {"Authorization": f"Bearer {u1['api_key']}"}
        h2 = {"Authorization": f"Bearer {u2['api_key']}"}

        client.post("/api/comments", json={"page_url": "http://a.com", "comment_text": "alice only"}, headers=h1)

        resp = client.get("/api/comments", headers=h2)
        assert resp.status_code == 200
        texts = [c["comment_text"] for c in resp.json()]
        assert "alice only" not in texts


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
