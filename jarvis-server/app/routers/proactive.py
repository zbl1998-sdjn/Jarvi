"""SSE endpoint for proactive Jarvis speech events (daemon alerts)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.proactive_service import get_bus

router = APIRouter()


@router.get("/api/proactive/stream")
async def proactive_stream() -> StreamingResponse:
    bus = get_bus()
    queue = bus.subscribe()

    async def event_stream():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"event: {event.get('type', 'message')}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
