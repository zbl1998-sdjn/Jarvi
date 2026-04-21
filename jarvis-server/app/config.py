import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jarvis",
        validation_alias="DATABASE_URL",
    )
    server_host: str = Field(default="127.0.0.1", validation_alias="JARVIS_SERVER_HOST")
    server_port: int = Field(default=8001, validation_alias="JARVIS_SERVER_PORT")
    knowledge_root: str = Field(
        default=r"C:\Users\YourName\Documents\JarvisKnowledge",
        validation_alias="JARVIS_KNOWLEDGE_ROOT",
    )
    kimi_api_key: str = Field(default="", validation_alias="KIMI_API_KEY")
    kimi_base_url: str = Field(
        default="https://api.moonshot.ai/v1",
        validation_alias="KIMI_BASE_URL",
    )
    kimi_model: str = Field(default="kimi-k2.5", validation_alias="KIMI_MODEL")
    kimi_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="KIMI_TIMEOUT_SECONDS",
    )
    kimi_system_prompt: str = Field(
        default="你是 Jarvis，负责用中文提供准确、直接、可执行的桌面助手回复。",
        validation_alias="KIMI_SYSTEM_PROMPT",
    )
    aliyun_dashscope_api_key: str = Field(
        default="", validation_alias="ALIYUN_DASHSCOPE_API_KEY"
    )
    aliyun_asr_model: str = Field(
        default="paraformer-realtime-v2",
        validation_alias="ALIYUN_ASR_MODEL",
    )
    aliyun_tts_model: str = Field(
        default="cosyvoice-v1",
        validation_alias="ALIYUN_TTS_MODEL",
    )
    aliyun_tts_voice: str = Field(
        default="longxiaochun",
        validation_alias="ALIYUN_TTS_VOICE",
    )
    aliyun_speech_language: str = Field(
        default="zh-CN",
        validation_alias="ALIYUN_SPEECH_LANGUAGE",
    )


def get_settings() -> Settings:
    return Settings()


def get_server_runtime_config() -> dict[str, str | int]:
    settings = get_settings()
    return {
        "host": settings.server_host,
        "port": settings.server_port,
    }


def get_server_runtime_config_json() -> str:
    return json.dumps(get_server_runtime_config())
