import base64

from fastapi.testclient import TestClient

from app.main import create_app


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
