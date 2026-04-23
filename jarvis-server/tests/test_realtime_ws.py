import base64

from fastapi.testclient import TestClient

from app.main import create_app


def test_realtime_socket_sends_error_and_voice_state_on_runtime_error(monkeypatch) -> None:
    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            raise RuntimeError("speech engine unavailable")

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "trigger error"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Connection must still be alive — send interrupt and get a response
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "speech engine unavailable",
        "recoverable": True,
    }
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_realtime_socket_rejects_oversized_audio_buffer_without_disconnecting(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: object())

    client = TestClient(create_app())

    large_audio = b"\x00" * (512 * 1024 + 1)

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json(
            {
                "type": "audio_chunk",
                "audio_base64": base64.b64encode(large_audio).decode("ascii"),
            }
        )

        error_event = websocket.receive_json()

        # Connection must still be alive
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "audio buffer exceeded limit",
        "recoverable": True,
    }
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_realtime_socket_emits_state_transcript_audio_and_done(monkeypatch) -> None:
    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            from app.services.speech_service import SpeechTurnResult

            return SpeechTurnResult(
                transcript=text,
                reply_text="基于学习资料整理后的语音回复",
                audio_text="基于学习资料整理后的语音回复",
            )

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "open lesson"})

        listening = websocket.receive_json()
        transcript = websocket.receive_json()
        thinking = websocket.receive_json()
        speaking = websocket.receive_json()
        audio = websocket.receive_json()
        done = websocket.receive_json()

    assert listening == {"type": "voice_state", "state": "listening"}
    assert transcript == {
        "type": "transcript",
        "role": "user",
        "text": "open lesson",
        "final": True,
    }
    assert thinking == {"type": "voice_state", "state": "thinking"}
    assert speaking == {"type": "voice_state", "state": "speaking"}
    assert audio == {
        "type": "audio_chunk",
        "text": "基于学习资料整理后的语音回复",
        "final": True,
    }
    assert done == {"type": "voice_state", "state": "idle"}


def test_realtime_socket_emits_interrupted_state() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "interrupt"})

        interrupted = websocket.receive_json()

    assert interrupted == {"type": "voice_state", "state": "interrupted"}


def test_input_text_runtime_error_clears_audio_buffer(monkeypatch) -> None:
    """Regression: RuntimeError in input_text must clear the audio_buffer so a
    subsequent audio_commit does not process stale buffered audio."""
    audio_turn_called = []

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            raise RuntimeError("speech engine unavailable")

        def handle_audio_turn(self, audio_bytes: bytes, sample_rate_hz: int):
            audio_turn_called.append(audio_bytes)
            from app.services.speech_service import SpeechTurnResult
            return SpeechTurnResult(
                transcript="should not happen",
                reply_text="should not happen",
                audio_text="should not happen",
            )

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        # Buffer some audio first
        websocket.send_json(
            {
                "type": "audio_chunk",
                "audio_base64": base64.b64encode(b"\x01\x02\x03\x04").decode("ascii"),
            }
        )
        # input_text triggers RuntimeError — must also clear audio_buffer
        websocket.send_json({"type": "input_text", "text": "trigger error"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Commit audio: if buffer was NOT cleared, handle_audio_turn gets called
        websocket.send_json({"type": "audio_commit", "sample_rate_hz": 16000})

        # Connection must still be alive
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "speech engine unavailable",
        "recoverable": True,
    }
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}
    # Core assertion: stale audio must NOT have been processed
    assert audio_turn_called == [], "audio_buffer was not cleared on input_text RuntimeError"


# ---------------------------------------------------------------------------
# Regression: non-RuntimeError provider / network exceptions must NOT silently
# disconnect the socket — they must emit structured error events and continue.
# ---------------------------------------------------------------------------

def test_realtime_socket_stays_alive_on_httpx_timeout(monkeypatch) -> None:
    """httpx.TimeoutException from a speech provider must surface as a structured
    error (recoverable=True) without killing the websocket."""
    import httpx

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            raise httpx.TimeoutException("upstream timed out")

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "trigger timeout"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Connection must still be alive — send interrupt and get a response
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "upstream timed out",
        "recoverable": True,
    }
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_realtime_socket_stays_alive_on_httpx_http_status_error_401(monkeypatch) -> None:
    """httpx.HTTPStatusError(401) must surface as a non-recoverable structured error
    without killing the websocket."""
    import httpx

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            response = httpx.Response(401)
            raise httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("POST", "http://x"),
                response=response,
            )

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "trigger 401"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Connection must still be alive
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event["type"] == "error"
    assert error_event["recoverable"] is False  # auth failure is not transient
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_realtime_socket_stays_alive_on_httpx_http_status_error_429(monkeypatch) -> None:
    """httpx.HTTPStatusError(429) must surface as a recoverable structured error."""
    import httpx

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            response = httpx.Response(429)
            raise httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=httpx.Request("POST", "http://x"),
                response=response,
            )

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "trigger 429"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event["type"] == "error"
    assert error_event["recoverable"] is True  # rate-limit is transient
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_is_recoverable_classifies_exceptions() -> None:
    """Unit-test for the _is_recoverable helper."""
    import httpx

    from app.routers.realtime import _is_recoverable

    assert _is_recoverable(httpx.TimeoutException("t")) is True
    assert _is_recoverable(httpx.ConnectError("c")) is True

    exc_401 = httpx.HTTPStatusError(
        "401", request=httpx.Request("POST", "http://x"), response=httpx.Response(401)
    )
    assert _is_recoverable(exc_401) is False

    exc_403 = httpx.HTTPStatusError(
        "403", request=httpx.Request("POST", "http://x"), response=httpx.Response(403)
    )
    assert _is_recoverable(exc_403) is False

    exc_429 = httpx.HTTPStatusError(
        "429", request=httpx.Request("POST", "http://x"), response=httpx.Response(429)
    )
    assert _is_recoverable(exc_429) is True

    exc_503 = httpx.HTTPStatusError(
        "503", request=httpx.Request("POST", "http://x"), response=httpx.Response(503)
    )
    assert _is_recoverable(exc_503) is True

    assert _is_recoverable(RuntimeError("runtime")) is True
    assert _is_recoverable(ValueError("value")) is True


def test_realtime_post_turn_failure_emits_error_and_keeps_socket_alive(monkeypatch) -> None:
    """Regression: if post-turn persistence/update work raises after speech succeeds,
    the websocket must emit structured error events and remain usable — not silently close."""

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            from app.services.speech_service import SpeechTurnResult

            return SpeechTurnResult(transcript=text, reply_text="ok", audio_text="ok")

    class FakeSessionRepo:
        def __init__(self, db):
            pass

        def create_session(self):
            return "s-1"

        def commit(self):
            pass

        def append_message(self, session_id, role, content):
            raise RuntimeError("db write failed")

    class FakeRealtimeRepo:
        def __init__(self, db):
            pass

        def append_voice_event(self, session_id, event_type, payload):
            pass

        def commit(self):
            pass

    class FakeMemoryService:
        def update_workspace_state(self, db, **kwargs):
            pass

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())
    monkeypatch.setattr("app.routers.realtime.SessionRepository", FakeSessionRepo)
    monkeypatch.setattr("app.routers.realtime.RealtimeRepository", FakeRealtimeRepo)
    monkeypatch.setattr("app.routers.realtime.MemoryService", lambda: FakeMemoryService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "hello"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Connection must still be alive after the post-turn failure
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "db write failed",
        "recoverable": True,
    }
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}


def test_realtime_post_turn_failure_calls_db_rollback(monkeypatch) -> None:
    """Regression: when a post-turn persistence step raises, db.rollback() must be
    called so the SQLAlchemy session is not left in a tainted state."""
    rollback_calls: list[int] = []

    class FakeDb:
        def close(self) -> None:
            pass

        def rollback(self) -> None:
            rollback_calls.append(1)

    class FakeSpeechService:
        def handle_text_turn(self, text: str):
            from app.services.speech_service import SpeechTurnResult

            return SpeechTurnResult(transcript=text, reply_text="ok", audio_text="ok")

    class FakeSessionRepo:
        def __init__(self, db):
            pass

        def create_session(self):
            return "s-rollback"

        def commit(self):
            pass

        def append_message(self, session_id, role, content):
            raise RuntimeError("db write failed")

    class FakeRealtimeRepo:
        def __init__(self, db):
            pass

        def append_voice_event(self, session_id, event_type, payload):
            pass

        def commit(self):
            pass

    class FakeMemoryService:
        def update_workspace_state(self, db, **kwargs):
            pass

    monkeypatch.setattr("app.routers.realtime.SessionLocal", lambda: FakeDb())
    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())
    monkeypatch.setattr("app.routers.realtime.SessionRepository", FakeSessionRepo)
    monkeypatch.setattr("app.routers.realtime.RealtimeRepository", FakeRealtimeRepo)
    monkeypatch.setattr("app.routers.realtime.MemoryService", lambda: FakeMemoryService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json({"type": "input_text", "text": "hello"})

        error_event = websocket.receive_json()
        voice_state_event = websocket.receive_json()

        # Connection must still be alive after rollback
        websocket.send_json({"type": "interrupt"})
        interrupted_event = websocket.receive_json()

    assert error_event == {
        "type": "error",
        "message": "db write failed",
        "recoverable": True,
    }
    assert voice_state_event == {"type": "voice_state", "state": "error"}
    assert interrupted_event == {"type": "voice_state", "state": "interrupted"}
    assert len(rollback_calls) >= 1, "db.rollback() was not called after post-turn persistence failure"


def test_realtime_socket_processes_uploaded_audio_chunks(monkeypatch) -> None:
    class FakeSpeechService:
        def handle_audio_turn(self, audio_bytes: bytes, sample_rate_hz: int):
            from app.services.speech_service import SpeechTurnResult

            assert audio_bytes == b"\x01\x02\x03\x04"
            assert sample_rate_hz == 16000
            return SpeechTurnResult(
                transcript="open lesson from audio",
                reply_text="音频回路已走通",
                audio_text="音频回路已走通",
                audio_bytes=b"fake-mp3",
                audio_mime_type="audio/mpeg",
            )

    monkeypatch.setattr("app.routers.realtime.SpeechService", lambda: FakeSpeechService())

    client = TestClient(create_app())

    with client.websocket_connect("/ws/realtime") as websocket:
        websocket.send_json({"type": "start"})
        websocket.send_json(
            {
                "type": "audio_chunk",
                "audio_base64": base64.b64encode(b"\x01\x02\x03\x04").decode("ascii"),
            }
        )
        websocket.send_json({"type": "audio_commit", "sample_rate_hz": 16000})

        listening = websocket.receive_json()
        transcript = websocket.receive_json()
        thinking = websocket.receive_json()
        speaking = websocket.receive_json()
        audio = websocket.receive_json()
        done = websocket.receive_json()

    assert listening == {"type": "voice_state", "state": "listening"}
    assert transcript == {
        "type": "transcript",
        "role": "user",
        "text": "open lesson from audio",
        "final": True,
    }
    assert thinking == {"type": "voice_state", "state": "thinking"}
    assert speaking == {"type": "voice_state", "state": "speaking"}
    assert audio == {
        "type": "audio_chunk",
        "text": "音频回路已走通",
        "audio_base64": base64.b64encode(b"fake-mp3").decode("ascii"),
        "mime_type": "audio/mpeg",
        "final": True,
    }
    assert done == {"type": "voice_state", "state": "idle"}
