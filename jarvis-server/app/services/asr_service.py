from __future__ import annotations

import os
import tempfile
import wave

from app.config import get_settings

try:  # pragma: no cover - import guarded for test envs
    import dashscope
    from dashscope.audio.asr import Recognition
except Exception:  # pragma: no cover
    dashscope = None  # type: ignore[assignment]
    Recognition = None  # type: ignore[assignment]


# Kept importable name for tests/patches.
AudioASR = Recognition


class AliyunAsrService:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.aliyun_dashscope_api_key
        self.model = settings.aliyun_asr_model
        self.language = settings.aliyun_speech_language

    def transcribe_audio(self, audio_bytes: bytes, sample_rate_hz: int) -> str:
        if not self.api_key:
            raise RuntimeError("Aliyun DashScope ASR 未配置 API Key。")

        if dashscope is not None:
            dashscope.api_key = self.api_key

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(sample_rate_hz)
                    wav.writeframes(audio_bytes)

            recognizer = AudioASR
            result = recognizer.recognize(file=tmp_path, model=self.model)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        text = _extract_text(result)
        if not text:
            raise RuntimeError("DashScope ASR 未识别出文本。")
        return text


def _extract_text(result: object) -> str:
    if isinstance(result, dict):
        output = result.get("output") if hasattr(result, "get") else None
        if isinstance(output, dict):
            text = output.get("text")
            if isinstance(text, str):
                return text.strip()
            sentence = output.get("sentence")
            if isinstance(sentence, list) and sentence:
                candidate = sentence[0]
                if isinstance(candidate, dict):
                    inner = candidate.get("text")
                    if isinstance(inner, str):
                        return inner.strip()
    output_attr = getattr(result, "output", None)
    if output_attr is not None:
        text = getattr(output_attr, "text", None)
        if isinstance(text, str):
            return text.strip()
    return ""
