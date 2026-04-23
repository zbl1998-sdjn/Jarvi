import asyncio
import json
import base64
import inspect

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db import SessionLocal
from app.repositories.realtime_repository import RealtimeRepository
from app.repositories.session_repository import SessionRepository
from app.services.memory_service import MemoryService
from app.services.speech_service import SpeechService

router = APIRouter()


def _is_recoverable(exc: BaseException) -> bool:
    """Classify whether an exception represents a transient/recoverable failure.

    - Network and timeout errors are transient (recoverable).
    - HTTP 4xx errors (except 429 rate-limit) indicate auth/config issues (not recoverable).
    - HTTP 429 and 5xx are transient (recoverable).
    - Everything else (including RuntimeError) defaults to recoverable.
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return True


MAX_AUDIO_BUFFER_BYTES = 512 * 1024


@router.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    db = SessionLocal()
    sessions = SessionRepository(db)
    realtime = RealtimeRepository(db)
    speech = SpeechService()
    memory = MemoryService()
    session_id: str | None = None
    audio_buffer = bytearray()

    def persist_event(event: dict[str, object]) -> None:
        if session_id is None:
            return
        realtime.append_voice_event(
            session_id,
            event_type=str(event["type"]),
            payload=json.dumps(event, ensure_ascii=False),
        )

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "start":
                if session_id is None:
                    session_id = sessions.create_session()
                    sessions.commit()
                continue

            if message_type == "interrupt":
                event = {"type": "voice_state", "state": "interrupted"}
                persist_event(event)
                if session_id is not None:
                    realtime.commit()
                audio_buffer.clear()
                await websocket.send_json(event)
                continue

            if message_type == "audio_chunk":
                audio_base64 = str(message.get("audio_base64", "")).strip()
                if audio_base64:
                    decoded = base64.b64decode(audio_base64)
                    if len(audio_buffer) + len(decoded) > MAX_AUDIO_BUFFER_BYTES:
                        audio_buffer.clear()
                        await websocket.send_json(
                            {"type": "error", "message": "audio buffer exceeded limit", "recoverable": True}
                        )
                        continue
                    audio_buffer.extend(decoded)
                continue

            if message_type == "audio_commit":
                if session_id is None:
                    session_id = sessions.create_session()
                    sessions.commit()

                if not audio_buffer:
                    continue

                sample_rate_hz = int(message.get("sample_rate_hz", 16000))
                handle_audio_signature = inspect.signature(speech.handle_audio_turn)
                try:
                    if "teacher_style" in handle_audio_signature.parameters or "voice_name" in handle_audio_signature.parameters:
                        turn = await asyncio.to_thread(
                            speech.handle_audio_turn,
                            bytes(audio_buffer),
                            sample_rate_hz,
                            teacher_style=str(message.get("teacher_style", "")).strip(),
                            voice_name=str(message.get("voice_name", "")).strip(),
                        )
                    else:
                        turn = await asyncio.to_thread(speech.handle_audio_turn, bytes(audio_buffer), sample_rate_hz)
                except Exception as exc:
                    audio_buffer.clear()
                    await websocket.send_json({"type": "error", "message": str(exc), "recoverable": _is_recoverable(exc)})
                    await websocket.send_json({"type": "voice_state", "state": "error"})
                    continue
                audio_buffer.clear()
            elif message_type == "input_text":
                text = str(message.get("text", "")).strip()
                if not text:
                    continue

                if session_id is None:
                    session_id = sessions.create_session()
                    sessions.commit()

                handle_text_signature = inspect.signature(speech.handle_text_turn)
                try:
                    if "teacher_style" in handle_text_signature.parameters:
                        turn = await asyncio.to_thread(
                            speech.handle_text_turn,
                            text,
                            teacher_style=str(message.get("teacher_style", "")).strip(),
                        )
                    else:
                        turn = await asyncio.to_thread(speech.handle_text_turn, text)
                except Exception as exc:
                    audio_buffer.clear()
                    await websocket.send_json({"type": "error", "message": str(exc), "recoverable": _is_recoverable(exc)})
                    await websocket.send_json({"type": "voice_state", "state": "error"})
                    continue
            else:
                continue

            try:
                sessions.append_message(session_id, role="user", content=turn.transcript)
                sessions.append_message(session_id, role="assistant", content=turn.reply_text)
                memory.update_workspace_state(db, active_workspace="console", session_id=session_id)

                events = [
                    {"type": "voice_state", "state": "listening"},
                    {
                        "type": "transcript",
                        "role": "user",
                        "text": turn.transcript,
                        "final": True,
                    },
                    {"type": "voice_state", "state": "thinking"},
                    {"type": "voice_state", "state": "speaking"},
                    {
                        "type": "audio_chunk",
                        "text": turn.audio_text,
                        **(
                            {
                                "audio_base64": base64.b64encode(turn.audio_bytes).decode("ascii"),
                                "mime_type": turn.audio_mime_type,
                            }
                            if turn.audio_bytes and turn.audio_mime_type
                            else {}
                        ),
                        "final": True,
                    },
                    {"type": "voice_state", "state": "idle"},
                ]

                for event in events:
                    persist_event(event)

                sessions.commit()
                realtime.commit()
                for event in events:
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                db.rollback()
                await websocket.send_json({"type": "error", "message": str(exc), "recoverable": _is_recoverable(exc)})
                await websocket.send_json({"type": "voice_state", "state": "error"})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
