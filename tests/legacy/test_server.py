"""Unit tests for the AWR HTTP server."""

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
from models import Comment

BASE = "http://127.0.0.1:{port}"
EXTENSION_ORIGIN = "chrome-extension://abcdefghijklmnop"


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        storage = CommentStorage(data_dir=cls.tmp)
        import server as srv
        srv.storage = storage

        cls.httpd = ThreadedHTTPServer(("127.0.0.1", 0), ReviewHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        # Clean up any lingering SSE clients
        sse_manager._clients.clear()
        sse_manager._queues.clear()
        cls.httpd.shutdown()

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
                cors_origin = resp.headers.get("Access-Control-Allow-Origin", "")
                if resp.status == 204:
                    return resp.status, None, cors_origin
                return resp.status, json.loads(resp.read()), cors_origin
        except urllib.error.HTTPError as e:
            cors_origin = e.headers.get("Access-Control-Allow-Origin", "")
            body = e.read().decode()
            try:
                return e.code, json.loads(body), cors_origin
            except json.JSONDecodeError:
                return e.code, body, cors_origin

    # ---- health ----

    def test_health(self):
        code, body, _ = self._req("/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("version", body)

    # ---- create ----

    def test_create_comment(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://example.com/page1",
            "comment_text": "Fix the alignment",
            "element_selector": "#header",
        })
        self.assertEqual(code, 201)
        self.assertIn("id", body)
        self.assertEqual(body["comment_text"], "Fix the alignment")
        self.assertEqual(body["element_selector"], "#header")
        self.assertEqual(body["status"], "open")

    def test_create_missing_page_url(self):
        code, body, _ = self._req("/api/comments", "POST", {"comment_text": "test"})
        self.assertEqual(code, 400)
        self.assertIn("page_url", body["error"])

    def test_create_missing_comment_text(self):
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://a.com"})
        self.assertEqual(code, 400)
        self.assertIn("comment_text", body["error"])

    def test_create_invalid_json(self):
        url = self._url("/api/comments")
        req = urllib.request.Request(url, data=b"not json", method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req):
                self.fail("expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_create_comment_too_long(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://a.com",
            "comment_text": "x" * 10001,
        })
        self.assertEqual(code, 400)
        self.assertIn("too long", body["error"])

    def test_create_body_too_large(self):
        # Send a request with Content-Length > MAX_BODY_SIZE but minimal actual data
        url = self._url("/api/comments")
        small_data = json.dumps({"page_url": "http://a.com", "comment_text": "x"}).encode()
        req = urllib.request.Request(url, data=small_data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Content-Length", str(11 * 1024 * 1024))  # lie about size
        try:
            with urllib.request.urlopen(req):
                self.fail("expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    # ---- list ----

    def test_list_all(self):
        self._req("/api/comments", "POST", {"page_url": "http://list.com", "comment_text": "first"})
        self._req("/api/comments", "POST", {"page_url": "http://other.com", "comment_text": "second"})
        code, body, _ = self._req("/api/comments")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(body), 2)

    def test_list_filtered(self):
        self._req("/api/comments", "POST", {"page_url": "http://filter.com", "comment_text": "f1"})
        self._req("/api/comments", "POST", {"page_url": "http://filter.com", "comment_text": "f2"})
        self._req("/api/comments", "POST", {"page_url": "http://other.com", "comment_text": "o1"})
        code, body, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://filter.com"))
        self.assertEqual(code, 200)
        texts = [c["comment_text"] for c in body]
        self.assertIn("f1", texts)
        self.assertIn("f2", texts)
        self.assertNotIn("o1", texts)

    # ---- delete ----

    def test_delete_comment(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://del.com", "comment_text": "delete me",
        })
        cid = body["id"]
        code, _, _ = self._req(f"/api/comments/{cid}", "DELETE")
        self.assertEqual(code, 204)
        code, _, _ = self._req(f"/api/comments/{cid}", "DELETE")
        self.assertEqual(code, 404)

    def test_delete_invalid_id(self):
        code, body, _ = self._req("/api/comments/../../etc/passwd", "DELETE")
        self.assertEqual(code, 400)

    def test_delete_all_for_page(self):
        self._req("/api/comments", "POST", {"page_url": "http://clear.com", "comment_text": "c1"})
        self._req("/api/comments", "POST", {"page_url": "http://clear.com", "comment_text": "c2"})
        self._req("/api/comments", "POST", {"page_url": "http://keep.com", "comment_text": "k1"})
        code, body, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://clear.com"), "DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(body["deleted"], 2)

    def test_delete_all_requires_page_url(self):
        code, body, _ = self._req("/api/comments", "DELETE")
        self.assertEqual(code, 400)

    # ---- 404 ----

    def test_not_found(self):
        code, body, _ = self._req("/api/nonexistent")
        self.assertEqual(code, 404)

    # ---- CORS ----

    def test_cors_allows_extension_origin(self):
        code, _, cors = self._req("/api/health", origin=EXTENSION_ORIGIN)
        self.assertEqual(cors, EXTENSION_ORIGIN)

    def test_cors_allows_localhost(self):
        code, _, cors = self._req("/api/health", origin="http://localhost:9876")
        self.assertEqual(cors, "http://localhost:9876")

    def test_cors_restricts_unknown_origin(self):
        code, _, cors = self._req("/api/health", origin="http://evil.com")
        self.assertNotEqual(cors, "http://evil.com")

    def test_cors_options_preflight(self):
        url = self._url("/api/health")
        req = urllib.request.Request(url, method="OPTIONS")
        req.add_header("Origin", EXTENSION_ORIGIN)
        try:
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), EXTENSION_ORIGIN)
                self.assertIn("DELETE", resp.headers.get("Access-Control-Allow-Methods", ""))
        except urllib.error.HTTPError as e:
            self.assertEqual(e.headers.get("Access-Control-Allow-Origin"), EXTENSION_ORIGIN)

    # ---- SSE ----

    def test_patch_comment_resolved(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://patch.com", "comment_text": "patch me",
        })
        self.assertEqual(code, 201)
        cid = body["id"]
        self.assertEqual(body["status"], "open")

        code, body, _ = self._req(f"/api/comments/{cid}", "PATCH", {
            "status": "resolved",
        })
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "resolved")
        self.assertEqual(body["id"], cid)
        self.assertEqual(body["comment_text"], "patch me")

    def test_patch_invalid_id_format(self):
        code, body, _ = self._req("/api/comments/../../etc/passwd", "PATCH", {
            "status": "resolved",
        })
        self.assertEqual(code, 400)

    def test_patch_nonexistent_id(self):
        code, body, _ = self._req("/api/comments/deadbeef1234", "PATCH", {
            "status": "resolved",
        })
        self.assertEqual(code, 404)

    def test_patch_invalid_status(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://bad-status.com", "comment_text": "test",
        })
        cid = code if code != 201 else body["id"]

        code, body, _ = self._req(f"/api/comments/{cid}", "PATCH", {
            "status": "open",
        })
        self.assertEqual(code, 400)
        self.assertIn("invalid", body.get("error", "").lower())

        code, body, _ = self._req(f"/api/comments/{cid}", "PATCH", {
            "status": "closed",
        })
        self.assertEqual(code, 400)

    def test_patch_missing_body(self):
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://empty-body.com", "comment_text": "test",
        })
        cid = body["id"]
        # Send PATCH with no body
        url = self._url(f"/api/comments/{cid}")
        req = urllib.request.Request(url, method="PATCH")
        try:
            with urllib.request.urlopen(req):
                self.fail("expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_patch_broadcasts_sse(self):
        import http.client

        # Open SSE connection
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        conn.request("GET", "/api/comments/stream", headers={"Origin": EXTENSION_ORIGIN})
        resp = conn.getresponse()

        got_event = threading.Event()
        buf = ""

        def read_sse():
            nonlocal buf
            while True:
                try:
                    chunk = resp.read(1)
                    if not chunk:
                        break
                    buf += chunk.decode(errors="replace")
                    if "comment_resolved" in buf:
                        got_event.set()
                        break
                except Exception:
                    break

        t = threading.Thread(target=read_sse, daemon=True)
        t.start()
        time.sleep(0.5)

        # Create a comment then resolve it via PATCH
        code, body, _ = self._req("/api/comments", "POST", {
            "page_url": "http://sse-patch.com", "comment_text": "resolve via SSE",
        })
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})

        found = got_event.wait(timeout=4)
        t.join(timeout=2)
        conn.close()
        self.assertTrue(found, f"SSE comment_resolved event not received. Data: {buf[:300]}")

    # ---- GET ?status filter ----

    def test_get_filter_status_open(self):
        self._req("/api/comments", "POST", {"page_url": "http://sf.com", "comment_text": "s-open1"})
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://sf.com", "comment_text": "s-open2"})
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})
        code, body, _ = self._req("/api/comments?status=open")
        self.assertEqual(code, 200)
        texts = [c["comment_text"] for c in body]
        self.assertIn("s-open1", texts)
        self.assertNotIn("s-open2", texts)

    def test_get_filter_status_resolved(self):
        self._req("/api/comments", "POST", {"page_url": "http://sf.com", "comment_text": "r-open"})
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://sf.com", "comment_text": "r-resolved"})
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})
        code, body, _ = self._req("/api/comments?status=resolved")
        self.assertEqual(code, 200)
        texts = [c["comment_text"] for c in body]
        self.assertIn("r-resolved", texts)
        self.assertNotIn("r-open", texts)

    def test_get_filter_status_no_match(self):
        # Use a unique page_url to avoid cross-test data contamination
        self._req("/api/comments", "POST", {"page_url": "http://sf-nomatch.com", "comment_text": "only-open"})
        code, body, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://sf-nomatch.com") + "&status=resolved")
        self.assertEqual(code, 200)
        self.assertEqual(body, [])

    def test_get_filter_combined_page_url_and_status(self):
        self._req("/api/comments", "POST", {"page_url": "http://combo.com", "comment_text": "combo-open"})
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://combo.com", "comment_text": "combo-resolved"})
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})
        self._req("/api/comments", "POST", {"page_url": "http://other.com", "comment_text": "other-resolved"})
        code, body, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://combo.com") + "&status=open")
        self.assertEqual(code, 200)
        texts = [c["comment_text"] for c in body]
        self.assertIn("combo-open", texts)
        self.assertNotIn("combo-resolved", texts)

    # ---- DELETE ?status filter ----

    def test_delete_all_by_status(self):
        self._req("/api/comments", "POST", {"page_url": "http://ds.com", "comment_text": "ds-open"})
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://ds.com", "comment_text": "ds-resolved"})
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})
        code, body, _ = self._req("/api/comments?status=resolved", "DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(body["deleted"], 1)
        code, remaining, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://ds.com"))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["status"], "open")

    def test_delete_all_by_status_no_match(self):
        self._req("/api/comments", "POST", {"page_url": "http://ds.com", "comment_text": "ds-open"})
        code, body, _ = self._req("/api/comments?status=resolved", "DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(body["deleted"], 0)

    def test_delete_all_combined_page_url_and_status(self):
        self._req("/api/comments", "POST", {"page_url": "http://dc.com", "comment_text": "dc-open"})
        code, body, _ = self._req("/api/comments", "POST", {"page_url": "http://dc.com", "comment_text": "dc-resolved"})
        cid = body["id"]
        self._req(f"/api/comments/{cid}", "PATCH", {"status": "resolved"})
        code, body, _ = self._req("/api/comments?page_url=" + urllib.parse.quote("http://dc.com") + "&status=resolved", "DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(body["deleted"], 1)

    def test_delete_all_requires_page_url_or_status(self):
        code, body, _ = self._req("/api/comments", "DELETE")
        self.assertEqual(code, 400)
        self.assertIn("required", body["error"])

    def test_sse_stream(self):
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        conn.request("GET", "/api/comments/stream", headers={"Origin": EXTENSION_ORIGIN})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Content-Type"), "text/event-stream")

        got_event = threading.Event()
        buf = ""

        def read_sse():
            nonlocal buf
            while True:
                try:
                    chunk = resp.read(1)
                    if not chunk:
                        break
                    buf += chunk.decode(errors="replace")
                    if "comment_added" in buf:
                        got_event.set()
                        break
                except Exception:
                    break

        t = threading.Thread(target=read_sse, daemon=True)
        t.start()

        time.sleep(0.5)
        self._req("/api/comments", "POST", {
            "page_url": "http://sse-test.com",
            "comment_text": "SSE test",
        })

        found = got_event.wait(timeout=4)
        t.join(timeout=2)
        conn.close()
        self.assertTrue(found, f"SSE event not received. Data: {buf[:200]}")


if __name__ == "__main__":
    unittest.main()
