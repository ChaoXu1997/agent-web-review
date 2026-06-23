from __future__ import annotations

import asyncio
import json
import threading

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["sse"])


class SSEManager:
    def __init__(self) -> None:
        # client_id -> (queue, owning event loop). Each asyncio.Queue is bound to
        # the loop it was created on; broadcasting must schedule the put on the
        # owner loop via call_soon_threadsafe to stay safe across loops/threads.
        self._clients: dict[str, tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = {}
        self._lock = threading.Lock()

    def add_client(self, client_id: str, queue: asyncio.Queue) -> None:
        loop = asyncio.get_running_loop()
        with self._lock:
            self._clients[client_id] = (queue, loop)

    def remove_client(self, client_id: str) -> None:
        with self._lock:
            self._clients.pop(client_id, None)

    def broadcast(self, event_type: str, data: dict) -> None:
        msg = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        with self._lock:
            clients = list(self._clients.values())
        for queue, loop in clients:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, msg)
            except RuntimeError:
                # loop closed; client will be reaped by its handler's finally
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
