from types import SimpleNamespace

from app.services.asr_service import AliyunAsrService
from app.services.tts_service import AliyunTtsService


def test_aliyun_asr_service_calls_dashscope_recognize(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAudioASR:
        @staticmethod
        def recognize(*, file: str, model: str):
            captured["file"] = file
            captured["model"] = model
            return {"output": {"text": "打开今天的课程"}}

    monkeypatch.setattr("app.services.asr_service.AudioASR", FakeAudioASR)
    monkeypatch.setattr(
        "app.services.asr_service.get_settings",
        lambda: SimpleNamespace(
            aliyun_dashscope_api_key="dashscope-key",
            aliyun_asr_model="paraformer-realtime-v2",
            aliyun_speech_language="zh-CN",
        ),
    )

    result = AliyunAsrService().transcribe_audio(b"\x00\x00" * 16, 16000)

    assert result == "打开今天的课程"
    assert captured["model"] == "paraformer-realtime-v2"
    assert str(captured["file"]).endswith(".wav")


def test_aliyun_asr_service_raises_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.asr_service.get_settings",
        lambda: SimpleNamespace(
            aliyun_dashscope_api_key="",
            aliyun_asr_model="paraformer-realtime-v2",
            aliyun_speech_language="zh-CN",
        ),
    )

    service = AliyunAsrService()

    try:
        service.transcribe_audio(b"\x00", 16000)
    except RuntimeError as exc:
        assert "API Key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")


def test_aliyun_tts_service_returns_mp3_bytes(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeTextToSpeech:
        @staticmethod
        def tts(*, text: str, model: str, voice: str):
            captured["text"] = text
            captured["model"] = model
            captured["voice"] = voice
            return {"audio": b"fake-mp3"}

    monkeypatch.setattr("app.services.tts_service.TextToSpeech", FakeTextToSpeech)
    monkeypatch.setattr(
        "app.services.tts_service.get_settings",
        lambda: SimpleNamespace(
            aliyun_dashscope_api_key="dashscope-key",
            aliyun_tts_model="cosyvoice-v1",
            aliyun_tts_voice="longxiaochun",
        ),
    )

    audio, mime_type = AliyunTtsService().synthesize_text("你好")

    assert audio == b"fake-mp3"
    assert mime_type == "audio/mpeg"
    assert captured == {"text": "你好", "model": "cosyvoice-v1", "voice": "longxiaochun"}


def test_aliyun_tts_service_raises_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.tts_service.get_settings",
        lambda: SimpleNamespace(
            aliyun_dashscope_api_key="",
            aliyun_tts_model="cosyvoice-v1",
            aliyun_tts_voice="longxiaochun",
        ),
    )

    try:
        AliyunTtsService().synthesize_text("你好")
    except RuntimeError as exc:
        assert "API Key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")
