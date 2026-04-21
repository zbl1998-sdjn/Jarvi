from dataclasses import dataclass
import inspect

from app.services.asr_service import AliyunAsrService
from app.config import get_settings
from app.services.knowledge_context_service import KnowledgeContextService
from app.services.kimi_client import KimiChatClient
from app.services.tts_service import AliyunTtsService
from app.services.runtime_config_service import get_active_provider, get_speech_config


@dataclass(frozen=True)
class SpeechTurnResult:
    transcript: str
    reply_text: str
    audio_text: str
    audio_bytes: bytes | None = None
    audio_mime_type: str | None = None


class SpeechService:
    def __init__(self) -> None:
        settings = get_settings()
        provider = get_active_provider()
        speech = get_speech_config()
        self.chat_client = KimiChatClient(
            api_key=provider.api_key or settings.kimi_api_key,
            base_url=provider.base_url or settings.kimi_base_url,
            model=provider.model or settings.kimi_model,
            timeout_seconds=settings.kimi_timeout_seconds,
            system_prompt=(
                "你是 Jarvis 的语音副驾，回答要简洁、口语化、自然，适合直接播报。"
            ),
        )
        self.knowledge_context = KnowledgeContextService()
        self.asr_service = AliyunAsrService()
        self.tts_service = AliyunTtsService()
        self.default_voice_name = speech.voice_name or settings.aliyun_tts_voice

    def handle_text_turn(self, text: str, teacher_style: str = "") -> SpeechTurnResult:
        reply = self._complete_with_style(
            query=text,
            knowledge_context=self.knowledge_context.build_context(text),
            teacher_style=teacher_style,
        )
        return SpeechTurnResult(
            transcript=text,
            reply_text=reply,
            audio_text=reply,
        )

    def handle_audio_turn(
        self,
        audio_bytes: bytes,
        sample_rate_hz: int,
        teacher_style: str = "",
        voice_name: str = "",
    ) -> SpeechTurnResult:
        transcript = self.asr_service.transcribe_audio(audio_bytes, sample_rate_hz)
        reply = self._complete_with_style(
            query=transcript,
            knowledge_context=self.knowledge_context.build_context(transcript),
            teacher_style=teacher_style,
        )
        synthesized_audio, mime_type = self.tts_service.synthesize_text(
            reply,
            voice_name=voice_name or self.default_voice_name,
        )
        return SpeechTurnResult(
            transcript=transcript,
            reply_text=reply,
            audio_text=reply,
            audio_bytes=synthesized_audio,
            audio_mime_type=mime_type,
        )

    def _complete_with_style(
        self,
        query: str,
        knowledge_context: str,
        teacher_style: str,
    ) -> str:
        complete_signature = inspect.signature(self.chat_client.complete)
        if "teacher_style" in complete_signature.parameters:
            return self.chat_client.complete(
                query=query,
                history=[],
                knowledge_context=knowledge_context,
                teacher_style=teacher_style,
            )
        return self.chat_client.complete(
            query=query,
            history=[],
            knowledge_context=knowledge_context,
        )
