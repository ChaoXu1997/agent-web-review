from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["sse"])


class SSEManager:
    def __init__(self) -> None:
        self._clients: dict[str, asyncio.Queue] = {}
        self._lock = threading.Lock()

    def add_client(self, client_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            self._clients[client_id] = queue

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._clients.pop(client_id, None)

    def broadcast(self, event_type: str, data: dict, user_id: Optional[str] = None) -> None:
        msg = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        with self._lock:
            for cid, queue in self._clients.items():
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)


sse_manager = SSEManager()


@router.get("/api/comments/stream")
async def comments_stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    client_id = f"c-{id(queue)}"
    sse_manager.add_client(client_id, queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            sse_manager.remove_client(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
