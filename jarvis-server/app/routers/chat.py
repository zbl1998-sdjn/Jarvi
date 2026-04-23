import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db import SessionLocal
from app.repositories.session_repository import SessionRepository
from app.services.chat_service import prepare_chat, stream_chat

router = APIRouter()


@router.get("/api/chat")
async def chat(query: str, session_id: str | None = None) -> StreamingResponse:
    db = SessionLocal()
    repository = SessionRepository(db)
    try:
        prepared_chat = await asyncio.to_thread(
            prepare_chat, query=query, session_id=session_id, repository=repository
        )
    except Exception:
        db.close()
        raise

    async def event_stream():
        try:
            async for event in stream_chat(
                session_id=prepared_chat.session_id,
                answer=prepared_chat.answer,
            ):
                yield event
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
