import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import ROOT_DIR, get_settings

RUNTIME_CONFIG_PATH = ROOT_DIR / "runtime" / "config" / "runtime-config.json"


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    label: str
    base_url: str
    api_key: str
    model: str
    enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SpeechConfig:
    api_key: str
    asr_model: str
    tts_model: str
    voice_name: str
    language: str
    provider: str = "aliyun"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeConfig:
    database_url: str
    providers: list[ProviderConfig]
    active_provider_id: str
    speech: SpeechConfig

    def to_dict(self) -> dict[str, object]:
        return {
            "database_url": self.database_url,
            "providers": [provider.to_dict() for provider in self.providers],
            "active_provider_id": self.active_provider_id,
            "speech": self.speech.to_dict(),
        }


def get_runtime_config() -> RuntimeConfig:
    if RUNTIME_CONFIG_PATH.exists():
        payload = json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
        return _runtime_config_from_payload(payload)
    return _default_runtime_config()


def save_runtime_config(payload: dict[str, object]) -> RuntimeConfig:
    runtime_config = _runtime_config_from_payload(payload)
    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_CONFIG_PATH.write_text(
        json.dumps(runtime_config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return runtime_config


def get_database_url() -> str:
    return get_runtime_config().database_url


def get_active_provider() -> ProviderConfig:
    runtime_config = get_runtime_config()
    for provider in runtime_config.providers:
        if provider.id == runtime_config.active_provider_id:
            return provider
    return runtime_config.providers[0]


def get_speech_config() -> SpeechConfig:
    return get_runtime_config().speech


def check_database_connection(database_url: str) -> str:
    try:
        engine = create_engine(database_url, future=True)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        engine.dispose()
        return "ready"
    except Exception:
        return "offline"


def check_llm_connection(provider: ProviderConfig) -> str:
    if provider.base_url.strip() and provider.api_key.strip() and provider.model.strip():
        return "configured"
    return "missing"


def check_speech_configuration(speech: SpeechConfig) -> str:
    required = [
        speech.api_key.strip(),
        speech.asr_model.strip(),
        speech.tts_model.strip(),
        speech.voice_name.strip(),
    ]
    return "configured" if all(required) else "missing"


def _default_runtime_config() -> RuntimeConfig:
    settings = get_settings()
    default_provider = ProviderConfig(
        id="default-provider",
        label="默认 Provider",
        base_url=settings.kimi_base_url,
        api_key=settings.kimi_api_key,
        model=settings.kimi_model,
        enabled=True,
    )
    return RuntimeConfig(
        database_url=settings.database_url,
        providers=[default_provider],
        active_provider_id=default_provider.id,
        speech=SpeechConfig(
            api_key=settings.aliyun_dashscope_api_key,
            asr_model=settings.aliyun_asr_model,
            tts_model=settings.aliyun_tts_model,
            voice_name=settings.aliyun_tts_voice,
            language=settings.aliyun_speech_language,
            provider="aliyun",
        ),
    )


def _runtime_config_from_payload(payload: dict[str, object]) -> RuntimeConfig:
    fallback = _default_runtime_config()
    provider_payloads = payload.get("providers")
    providers = [
        ProviderConfig(
            id=str(item.get("id", f"provider-{index}")).strip() or f"provider-{index}",
            label=str(item.get("label", f"Provider {index + 1}")).strip() or f"Provider {index + 1}",
            base_url=str(item.get("base_url", "")).strip(),
            api_key=str(item.get("api_key", "")).strip(),
            model=str(item.get("model", "")).strip(),
            enabled=bool(item.get("enabled", True)),
        )
        for index, item in enumerate(provider_payloads if isinstance(provider_payloads, list) else [])
        if isinstance(item, dict)
    ]
    if not providers:
        providers = fallback.providers

    active_provider_id = str(payload.get("active_provider_id", providers[0].id)).strip() or providers[0].id
    speech_payload = payload.get("speech", {})
    if not isinstance(speech_payload, dict):
        speech_payload = {}

    return RuntimeConfig(
        database_url=str(payload.get("database_url", fallback.database_url)).strip() or fallback.database_url,
        providers=providers,
        active_provider_id=active_provider_id,
        speech=SpeechConfig(
            api_key=str(speech_payload.get("api_key", fallback.speech.api_key)).strip(),
            asr_model=str(speech_payload.get("asr_model", fallback.speech.asr_model)).strip()
            or fallback.speech.asr_model,
            tts_model=str(speech_payload.get("tts_model", fallback.speech.tts_model)).strip()
            or fallback.speech.tts_model,
            voice_name=str(speech_payload.get("voice_name", fallback.speech.voice_name)).strip()
            or fallback.speech.voice_name,
            language=str(speech_payload.get("language", fallback.speech.language)).strip()
            or fallback.speech.language,
            provider=str(speech_payload.get("provider", fallback.speech.provider)).strip()
            or fallback.speech.provider,
        ),
    )
