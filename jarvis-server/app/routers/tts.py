from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.memory_service import MemoryService
from app.services.tts_service import AliyunTtsService
from app.db import SessionLocal


router = APIRouter()


class TtsRequest(BaseModel):
    text: str
    voice_name: str | None = None


@router.post("/api/tts")
async def synthesize(body: TtsRequest) -> Response:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice = body.voice_name
    if not voice:
        db = SessionLocal()
        try:
            voice = MemoryService().get_preferences(db).voice_name
        finally:
            db.close()

    service = AliyunTtsService()
    try:
        audio, mime = service.synthesize_text(text, voice_name=voice)
    except RuntimeError as err:
        raise HTTPException(status_code=503, detail=str(err))

    return Response(content=audio, media_type=mime)
