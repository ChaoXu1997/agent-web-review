"""Local HTTP server for Agent Web Review — Python 3.10+, stdlib only."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import socket
import socketserver
import threading
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from models import Comment
from storage import CommentStorage
from project_storage import ProjectMappingStorage

logger = logging.getLogger("awr")

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
MAX_COMMENT_LENGTH = 10_000

# ---------------------------------------------------------------------------
# SSE Manager
# ---------------------------------------------------------------------------


class SSEManager:
    def __init__(self) -> None:
        self._clients: dict[str, threading.Event] = {}
        self._queues: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def add_client(self, client_id: str) -> threading.Event:
        stop = threading.Event()
        with self._lock:
            self._clients[client_id] = stop
            self._queues[client_id] = []
        return stop

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._clients.pop(client_id, None)
            self._queues.pop(client_id, None)

    def broadcast(self, event_type: str, data: dict) -> None:
        msg = json.dumps({"type": event_type, "data": data})
        with self._lock:
            for cid in list(self._clients):
                self._queues[cid].append(msg)
                self._clients[cid].set()

    def get_events(self, client_id: str) -> list[str]:
        with self._lock:
            events = self._queues.get(client_id, [])
            self._queues[client_id] = []
            return events

    def is_connected(self, client_id: str) -> bool:
        with self._lock:
            return client_id in self._clients

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)


# ---------------------------------------------------------------------------
# CORS — restrict to localhost and chrome-extension origins
# ---------------------------------------------------------------------------


def _cors_headers(origin: Optional[str] = None) -> dict:
    headers = {
        "Access-Control-Allow-Methods": "GET, POST, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if origin and (origin.startswith("chrome-extension://") or
                   origin.startswith("http://localhost") or
                   origin.startswith("http://127.0.0.1")):
        headers["Access-Control-Allow-Origin"] = origin
    else:
        headers["Access-Control-Allow-Origin"] = "http://localhost:9876"
    return headers


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

sse_manager = SSEManager()
storage: Optional[CommentStorage] = None
project_storage: Optional[ProjectMappingStorage] = None


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = "AWR/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info("%s — %s", self.address_string(), fmt % args)

    # ---- helpers ----

    def _cors(self) -> dict:
        origin = self.headers.get("Origin")
        return _cors_headers(origin)

    def _send(self, code: int, body: object = None, headers: dict | None = None) -> None:
        if body is not None and not isinstance(body, (str, bytes)):
            body = json.dumps(body, ensure_ascii=False)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in self._cors().items():
            self.send_header(k, v)
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        payload = body or ""
        encoded = payload.encode("utf-8") if isinstance(payload, str) else payload
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if code >= 200 and code != 204:
            self.wfile.write(encoded)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_SIZE:
            raise ValueError("request body too large")
        if length == 0:
            raise ValueError("empty body")
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _route(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = urllib.parse.parse_qs(parsed.query)

        if method == "OPTIONS":
            self._send(204)
            return

        if path == "/api/health" and method == "GET":
            self._send(200, {"status": "ok", "version": "1.0.0", "sse_clients": sse_manager.client_count})
            return

        if path == "/api/comments/stream" and method == "GET":
            self._handle_sse()
            return

        if path == "/api/projects":
            if method == "GET":
                mappings = project_storage.get_all()
                self._send(200, mappings)
                return
            if method == "POST":
                self._handle_create_project()
                return
            if method == "DELETE":
                page_url = (qs.get("page_url") or [None])[0]
                if page_url:
                    self._handle_delete_project(page_url)
                else:
                    self._send(400, {"error": "page_url query parameter required for DELETE"})
                return

        if path == "/api/comments":
            if method == "GET":
                self._handle_list(qs)
                return
            if method == "POST":
                self._handle_create()
                return
            if method == "DELETE":
                page_url = (qs.get("page_url") or [None])[0]
                status = (qs.get("status") or [None])[0]
                if page_url or status:
                    self._handle_delete_all(page_url, status=status)
                else:
                    self._send(400, {"error": "page_url or status query parameter required for DELETE"})
                return

        if path.startswith("/api/comments/") and method == "DELETE":
            comment_id = path[len("/api/comments/"):]
            self._handle_delete(comment_id)
            return

        if path.startswith("/api/comments/") and method == "PATCH":
            comment_id = path[len("/api/comments/"):]
            self._handle_patch(comment_id)
            return

        self._send(404, {"error": "not found"})

    # ---- endpoint handlers ----

    def _handle_create_project(self) -> None:
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return
        if not body.get("page_url"):
            self._send(400, {"error": "page_url is required"})
            return
        if not body.get("project_path"):
            self._send(400, {"error": "project_path is required"})
            return
        try:
            mapping = project_storage.create(body)
        except ValueError as e:
            self._send(409, {"error": str(e)})
            return
        self._send(201, mapping)

    def _handle_delete_project(self, page_url: str) -> None:
        if project_storage.delete(page_url):
            self._send(200, {"deleted": True})
        else:
            self._send(404, {"error": f"mapping for {page_url} not found"})

    def _handle_list(self, qs: dict) -> None:
        page_url = (qs.get("page_url") or [None])[0]
        status = (qs.get("status") or [None])[0]
        comments = storage.get_all(page_url, status=status)
        self._send(200, [c.to_dict() for c in comments])

    def _handle_create(self) -> None:
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        if not body.get("page_url"):
            self._send(400, {"error": "page_url is required"})
            return
        if not body.get("comment_text"):
            self._send(400, {"error": "comment_text is required"})
            return
        if len(body.get("comment_text", "")) > MAX_COMMENT_LENGTH:
            self._send(400, {"error": f"comment_text too long (max {MAX_COMMENT_LENGTH} chars)"})
            return

        comment = Comment.from_dict(body)
        created = storage.create(comment)
        sse_manager.broadcast("comment_added", created.to_dict())
        self._send(201, created.to_dict())

    def _handle_delete(self, comment_id: str) -> None:
        if not re.match(r'^[a-f0-9]+$', comment_id):
            self._send(400, {"error": "invalid comment id"})
            return
        if storage.delete(comment_id):
            sse_manager.broadcast("comment_deleted", {"id": comment_id})
            self._send(204)
        else:
            self._send(404, {"error": f"comment {comment_id} not found"})

    def _handle_delete_all(self, page_url: Optional[str], status: Optional[str] = None) -> None:
        removed = storage.delete_all(page_url, status=status)
        if removed:
            filter_desc = f"page_url={page_url}" if page_url else f"status={status}"
            if page_url and status:
                filter_desc = f"page_url={page_url}&status={status}"
            sse_manager.broadcast("comments_cleared", {"filter": filter_desc})
        self._send(200, {"deleted": removed})

    def _handle_patch(self, comment_id: str) -> None:
        # Validate id format
        if not re.match(r'^[a-f0-9]+$', comment_id):
            self._send(400, {"error": "invalid comment id"})
            return

        # Parse body
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        # Validate status value
        new_status = body.get("status")
        if new_status != "resolved":
            self._send(400, {"error": "invalid status value, only \"resolved\" is accepted"})
            return

        # Update storage
        updated = storage.update_status(comment_id, new_status)
        if updated is None:
            self._send(404, {"error": f"comment {comment_id} not found"})
            return

        # Broadcast SSE event
        sse_manager.broadcast("comment_resolved", updated.to_dict())
        self._send(200, updated.to_dict())

    # ---- SSE ----

    def _handle_sse(self) -> None:
        origin = self.headers.get("Origin")
        cors = _cors_headers(origin)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()

        client_id = f"c-{threading.get_ident()}-{int(time.time()*1000)}"
        stop = sse_manager.add_client(client_id)
        last_heartbeat = time.time()

        try:
            while True:
                if not sse_manager.is_connected(client_id):
                    break
                events = sse_manager.get_events(client_id)
                for ev in events:
                    self.wfile.write(f"data: {ev}\n\n".encode())
                    self.wfile.flush()
                stop.clear()

                now = time.time()
                if now - last_heartbeat >= 30:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    last_heartbeat = now

                stop.wait(timeout=1.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            sse_manager.remove_client(client_id)

    # ---- HTTP verb dispatch ----

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def do_DELETE(self) -> None:
        self._route("DELETE")

    def do_PATCH(self) -> None:
        self._route("PATCH")

    def do_OPTIONS(self) -> None:
        self._route("OPTIONS")


# ---------------------------------------------------------------------------
# Threaded server
# ---------------------------------------------------------------------------


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(port: int = 9876) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return port
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def main() -> None:
    global storage

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    storage = CommentStorage()
    port = find_free_port(9876)
    server = ThreadedHTTPServer(("127.0.0.1", port), ReviewHandler)

    def _shutdown(sig, frame) -> None:
        logger.info("shutting down…")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Agent Web Review server listening on http://127.0.0.1:%d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logger.info("stopped")


if __name__ == "__main__":
    main()
