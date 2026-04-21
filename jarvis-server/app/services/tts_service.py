from __future__ import annotations

import base64

from app.config import get_settings

try:  # pragma: no cover
    import dashscope
    from dashscope.audio.tts import SpeechSynthesizer
except Exception:  # pragma: no cover
    dashscope = None  # type: ignore[assignment]
    SpeechSynthesizer = None  # type: ignore[assignment]


TextToSpeech = SpeechSynthesizer


class AliyunTtsService:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.aliyun_dashscope_api_key
        self.model = settings.aliyun_tts_model
        self.voice_name = settings.aliyun_tts_voice

    def synthesize_text(self, text: str, voice_name: str | None = None) -> tuple[bytes, str]:
        if not self.api_key:
            raise RuntimeError("Aliyun DashScope TTS 未配置 API Key。")

        if dashscope is not None:
            dashscope.api_key = self.api_key

        voice = voice_name or self.voice_name
        synth = TextToSpeech
        result = synth.tts(text=text, model=self.model, voice=voice)
        audio = _extract_audio(result)
        if not audio:
            raise RuntimeError("DashScope TTS 未返回音频数据。")
        return audio, "audio/mpeg"


def _extract_audio(result: object) -> bytes:
    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    if isinstance(result, dict):
        audio = result.get("audio")
        if isinstance(audio, (bytes, bytearray)):
            return bytes(audio)
        if isinstance(audio, str):
            try:
                return base64.b64decode(audio)
            except Exception:  # pragma: no cover
                return b""
    get_audio = getattr(result, "get_audio_data", None)
    if callable(get_audio):
        data = get_audio()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    audio_attr = getattr(result, "audio", None)
    if isinstance(audio_attr, (bytes, bytearray)):
        return bytes(audio_attr)
    return b""
