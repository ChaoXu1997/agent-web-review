"""Unit tests for Project Mapping API — TDD Cycle 1: GET /api/projects."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from server import ReviewHandler, ThreadedHTTPServer, sse_manager
from storage import CommentStorage
from project_storage import ProjectMappingStorage

BASE = "http://127.0.0.1:{port}"


class TestProjectsAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        comment_storage = CommentStorage(data_dir=cls.tmp)
        cls.project_storage = ProjectMappingStorage(data_dir=cls.tmp)

        import server as srv
        srv.storage = comment_storage
        srv.project_storage = cls.project_storage

        cls.httpd = ThreadedHTTPServer(("127.0.0.1", 0), ReviewHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        sse_manager._clients.clear()
        sse_manager._queues.clear()
        cls.httpd.shutdown()

    def setUp(self):
        self.project_storage.delete_all()

    def _url(self, path):
        return BASE.format(port=self.port) + path

    def _req(self, path, method="GET", data=None, origin=None):
        url = self._url(path)
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        if origin:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 204:
                    return resp.status, None
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw

    # ---- Cycle 1: GET /api/projects ----

    def test_get_projects_empty(self):
        code, body = self._req("/api/projects")
        self.assertEqual(code, 200)
        self.assertEqual(body, [])

    def test_get_projects_with_data(self):
        # Seed storage directly
        self.project_storage.create(
            {"page_url": "http://localhost:3000", "project_path": "/home/user/my-app"}
        )
        code, body = self._req("/api/projects")
        self.assertEqual(code, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["page_url"], "http://localhost:3000")
        self.assertEqual(body[0]["project_path"], "/home/user/my-app")


    # ---- Cycle 2: POST /api/projects ----

    def test_create_project_mapping(self):
        code, body = self._req("/api/projects", "POST", {
            "page_url": "http://localhost:3000",
            "project_path": "/home/user/my-app",
        })
        self.assertEqual(code, 201)
        self.assertEqual(body["page_url"], "http://localhost:3000")
        self.assertEqual(body["project_path"], "/home/user/my-app")

        # Verify it persists via GET
        code, body = self._req("/api/projects")
        self.assertEqual(code, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["page_url"], "http://localhost:3000")


    # ---- Cycle 3: POST duplicate page_url returns 409 ----

    def test_create_duplicate_page_url_returns_409(self):
        self._req("/api/projects", "POST", {
            "page_url": "http://localhost:3000",
            "project_path": "/home/user/app-a",
        })
        code, body = self._req("/api/projects", "POST", {
            "page_url": "http://localhost:3000",
            "project_path": "/home/user/app-b",
        })
        self.assertEqual(code, 409)
        self.assertIn("already exists", body["error"])


    # ---- Cycle 4: DELETE /api/projects ----

    def test_delete_project_mapping(self):
        self._req("/api/projects", "POST", {
            "page_url": "http://localhost:3000",
            "project_path": "/home/user/my-app",
        })
        code, body = self._req(
            "/api/projects?page_url=" + urllib.parse.quote("http://localhost:3000"),
            "DELETE",
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["deleted"], True)

        # Verify it's gone
        code, body = self._req("/api/projects")
        self.assertEqual(code, 200)
        self.assertEqual(body, [])

    def test_delete_nonexistent_project_mapping(self):
        code, body = self._req(
            "/api/projects?page_url=" + urllib.parse.quote("http://nonexistent.com"),
            "DELETE",
        )
        self.assertEqual(code, 404)
        self.assertIn("not found", body["error"])


    # ---- Cycle 5: Input validation — page_url required ----

    def test_create_missing_page_url(self):
        code, body = self._req("/api/projects", "POST", {
            "project_path": "/home/user/my-app",
        })
        self.assertEqual(code, 400)
        self.assertIn("page_url", body["error"])

    def test_create_missing_project_path(self):
        code, body = self._req("/api/projects", "POST", {
            "page_url": "http://localhost:3000",
        })
        self.assertEqual(code, 400)
        self.assertIn("project_path", body["error"])

    def test_create_empty_body(self):
        url = self._url("/api/projects")
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req):
                self.fail("expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)


if __name__ == "__main__":
    unittest.main()
