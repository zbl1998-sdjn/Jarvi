from pathlib import Path

from sqlalchemy import inspect

from app import db as db_module
import app.config as config_module
from fastapi.testclient import TestClient

from app.config import Settings, get_server_runtime_config
from app.main import create_app


def test_health_reports_service_name() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "jarvis-server",
        "mode": "m6",
        "degraded": False,
        "dependencies": {
            "database": "ready",
            "llm": "missing",
            "speech": "missing",
            "config": "missing",
        },
    }


def test_health_checks_database_connection(monkeypatch) -> None:
    executed_statements: list[str] = []
    actions: list[str] = []

    class FakeSession:
        def __enter__(self) -> "FakeSession":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, statement) -> None:
            executed_statements.append(str(statement))

        def rollback(self) -> None:
            actions.append("rollback")

    monkeypatch.setattr("app.routers.health.SessionLocal", lambda: FakeSession())

    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    assert executed_statements == ["select 1"]
    assert actions == ["rollback"]


def test_settings_define_postgresql_database_url_by_default() -> None:
    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jarvis"


def test_settings_define_portable_knowledge_root_by_default() -> None:
    settings = Settings()

    assert settings.knowledge_root == str(config_module.ROOT_DIR / "knowledge")


def test_settings_read_server_host_and_port_from_configured_env_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/jarvis\n"
        "JARVIS_SERVER_HOST=0.0.0.0\n"
        "JARVIS_SERVER_PORT=9009\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("JARVIS_SERVER_HOST", raising=False)
    monkeypatch.delenv("JARVIS_SERVER_PORT", raising=False)
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)

    settings = Settings(_env_file=env_path)

    assert settings.database_url == "postgresql+psycopg://postgres:postgres@localhost:5432/jarvis"
    assert settings.server_host == "0.0.0.0"
    assert settings.server_port == 9009


def test_settings_read_kimi_runtime_config_from_env_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "KIMI_API_KEY=test-kimi-key\n"
        "KIMI_BASE_URL=https://api.moonshot.ai/v1\n"
        "KIMI_MODEL=kimi-k2.5\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_BASE_URL", raising=False)
    monkeypatch.delenv("KIMI_MODEL", raising=False)

    settings = Settings(_env_file=env_path)

    assert settings.kimi_api_key == "test-kimi-key"
    assert settings.kimi_base_url == "https://api.moonshot.ai/v1"
    assert settings.kimi_model == "kimi-k2.5"


def test_settings_read_aliyun_speech_runtime_config_from_env_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "ALIYUN_DASHSCOPE_API_KEY=test-dashscope-key\n"
        "ALIYUN_ASR_MODEL=paraformer-realtime-v2\n"
        "ALIYUN_TTS_MODEL=cosyvoice-v1\n"
        "ALIYUN_TTS_VOICE=longxiaochun\n"
        "ALIYUN_SPEECH_LANGUAGE=zh-CN\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("ALIYUN_DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ALIYUN_ASR_MODEL", raising=False)
    monkeypatch.delenv("ALIYUN_TTS_MODEL", raising=False)
    monkeypatch.delenv("ALIYUN_TTS_VOICE", raising=False)
    monkeypatch.delenv("ALIYUN_SPEECH_LANGUAGE", raising=False)

    settings = Settings(_env_file=env_path)

    assert settings.aliyun_dashscope_api_key == "test-dashscope-key"
    assert settings.aliyun_asr_model == "paraformer-realtime-v2"
    assert settings.aliyun_tts_model == "cosyvoice-v1"
    assert settings.aliyun_tts_voice == "longxiaochun"
    assert settings.aliyun_speech_language == "zh-CN"


def test_server_runtime_config_reads_host_and_port_from_configured_env_file(
    tmp_path, monkeypatch
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "JARVIS_SERVER_HOST=0.0.0.0\nJARVIS_SERVER_PORT=9009\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("JARVIS_SERVER_HOST", raising=False)
    monkeypatch.delenv("JARVIS_SERVER_PORT", raising=False)
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: Settings(_env_file=env_path),
    )

    runtime_config = get_server_runtime_config()

    assert runtime_config == {"host": "0.0.0.0", "port": 9009}


def test_create_app_can_use_isolated_database_before_app_setup(tmp_path) -> None:
    database_path = tmp_path / "isolated.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    db_module.reset_database()
    db_module.configure_database(database_url)
    try:
        create_app()
        tables = inspect(db_module.get_engine()).get_table_names()
    finally:
        db_module.reset_database()

    assert database_path.exists()
    assert sorted(tables) == [
        "action_audits",
        "chat_messages",
        "chat_sessions",
        "memory_entries",
        "memory_facts",
        "preference_states",
        "realtime_events",
        "reminder_events",
        "session_artifacts",
        "task_items",
        "uploaded_contexts",
        "user_profile_facts",
        "workspace_states",
    ]
    assert str(db_module.get_engine().url) == "postgresql+psycopg://postgres:***@127.0.0.1:5432/jarvis"


def test_create_app_starts_in_degraded_mode_when_database_bootstrap_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.Base.metadata.create_all",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("database offline")),
    )

    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "service": "jarvis-server",
        "mode": "m6",
        "degraded": True,
        "dependencies": {
            "database": "offline",
            "llm": "missing",
            "speech": "missing",
            "config": "missing",
        },
    }


def test_preference_state_voice_name_defaults_to_longxiaochun() -> None:
    from app.models import PreferenceState

    col = PreferenceState.__table__.c.voice_name

    assert col.default is not None
    assert col.default.arg == "longxiaochun"


def test_contract_scaffold_exists_for_cross_layer_schema() -> None:
    from app.config import ROOT_DIR

    project_root = ROOT_DIR
    required_contracts = [
        project_root / "contracts" / "sessions" / "session-events.json",
        project_root / "contracts" / "websocket" / "realtime-events.json",
        project_root / "contracts" / "actions" / "action-proposal.json",
        project_root / "contracts" / "actions" / "action-result.json",
        project_root / "contracts" / "workspace" / "workspace-command.json",
    ]

    assert all(path.exists() for path in required_contracts)
