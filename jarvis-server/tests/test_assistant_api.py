import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import assistant as assistant_router
from app.services.search_service import SearchResult


def test_interpret_normalizes_wakeword_and_opens_workspace() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/assistant/interpret",
        json={"text": "Jarviss open search README", "hotkey_armed": False},
    )

    assert response.status_code == 200
    assert response.json()["heard_wakeword"] is True
    assert response.json()["workspace"] == "search"


def test_interpret_requires_confirmation_for_dangerous_delete() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/assistant/interpret",
        json={"text": r"Jarvis delete D:\danger.txt"},
    )

    assert response.status_code == 200
    assert response.json()["action_proposal"] == {
        "action_type": "delete_file",
        "target": r"D:\danger.txt",
        "risk_level": "dangerous",
        "requires_confirmation": True,
    }


def test_interpret_handles_teacher_style_and_high_risk_ambiguity() -> None:
    client = TestClient(create_app())

    style_response = client.post(
        "/api/assistant/interpret",
        json={"text": "Jarvis 切换到面试高压陪练型"},
    )
    ambiguity_response = client.post(
        "/api/assistant/interpret",
        json={"text": "Jarvis maybe delete something"},
    )

    assert style_response.status_code == 200
    assert style_response.json()["teacher_style"] == "面试高压陪练型"
    assert "已切换到面试高压陪练型" in style_response.json()["clarification"]
    assert ambiguity_response.status_code == 200
    assert "高风险模糊请求" in ambiguity_response.json()["clarification"]
    assert ambiguity_response.json()["action_proposal"] is None


def test_search_summary_and_home_snapshot_work_together(monkeypatch) -> None:
    # Patch the module-level summary_service singleton so the test never hits the real LLM.
    monkeypatch.setattr(
        assistant_router.summary_service,
        "summarize",
        lambda source_type, content: {
            "summary": content,
            "bullets": ["会话要点一", "会话要点二"],
        },
    )
    client = TestClient(create_app())

    search_response = client.get("/api/search", params={"query": "Jarvis", "scope": "local"})
    summary_response = client.post(
        "/api/summary",
        json={"source_type": "session", "content": "Jarvis can summarize this session."},
    )
    task_response = client.post(
        "/api/tasks",
        json={"title": "Review M6 timeline", "detail": "Check reminders and memory."},
    )
    action_response = client.post(
        "/api/actions/execute",
        json={
            "action_type": "write_file",
            "target": "runtime/temp/m6-note.txt",
            "content": "Jarvis action log",
        },
    )
    home_response = client.get("/api/home")

    assert search_response.status_code == 200
    assert search_response.json()["results"]
    assert summary_response.status_code == 200
    assert "Jarvis can summarize this session." in summary_response.json()["summary"]
    assert task_response.status_code == 200
    assert task_response.json()["title"] == "Review M6 timeline"
    assert action_response.status_code == 200
    assert action_response.json()["status"] == "completed"
    from app.config import ROOT_DIR
    assert (ROOT_DIR / "runtime" / "temp" / "m6-note.txt").exists()
    assert home_response.status_code == 200
    assert home_response.json()["tasks"]
    assert home_response.json()["memories"]
    assert home_response.json()["recent_actions"]
    assert home_response.json()["reminders"]


def test_search_preferences_upload_and_resume_state() -> None:
    client = TestClient(create_app())

    preference_response = client.post(
        "/api/preferences",
        json={"teacher_style": "幽默风趣型", "voice_name": "zh-CN-YunxiNeural"},
    )
    upload_response = client.post(
        "/api/context/upload",
        json={
            "title": "阶段复盘截图",
            "source_type": "image",
            "content": "data:image/png;base64,ZmFrZQ==",
        },
    )
    workspace_response = client.post(
        "/api/workspace/state",
        json={"workspace": "tasks", "session_id": "session-42"},
    )
    home_response = client.get("/api/home")

    assert preference_response.status_code == 200
    assert preference_response.json()["voice_name"] == "zh-CN-YunxiNeural"
    assert upload_response.status_code == 200
    assert upload_response.json()["source_type"] == "image"
    assert workspace_response.status_code == 200
    assert home_response.status_code == 200
    assert home_response.json()["preferences"] == {
        "teacher_style": "幽默风趣型",
        "voice_name": "zh-CN-YunxiNeural",
    }
    assert home_response.json()["resume"] == {
        "workspace": "tasks",
        "session_id": "session-42",
    }
    assert home_response.json()["stage_progress"]["current_stage"] == "M6"
    assert home_response.json()["uploaded_contexts"][0]["title"] == "阶段复盘截图"


def test_web_search_and_controlled_web_actions_are_supported(monkeypatch) -> None:
    client = TestClient(create_app())
    monkeypatch.setattr(
        assistant_router.search_service,
        "search_web",
        lambda query: [
            SearchResult(
                scope="web",
                path="https://example.com/jarvis",
                title="Jarvis web result",
                snippet=f"Web result for {query}",
            )
        ],
    )
    monkeypatch.setattr(
        assistant_router.action_service,
        "_fetch_web_preview",
        lambda target: f"Fetched {target}",
    )

    search_response = client.get("/api/search", params={"query": "Jarvis", "scope": "web"})
    proposal_response = client.post(
        "/api/actions/propose",
        json={"action_type": "open_web_page", "target": "https://example.com"},
    )
    action_response = client.post(
        "/api/actions/execute",
        json={"action_type": "fetch_web", "target": "https://example.com"},
    )
    home_response = client.get("/api/home")

    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["scope"] == "web"
    assert proposal_response.status_code == 200
    assert proposal_response.json()["requires_confirmation"] is True
    assert action_response.status_code == 200
    assert action_response.json()["detail"] == "Fetched https://example.com"
    assert any(
        action["action_type"] == "fetch_web" for action in home_response.json()["recent_actions"]
    )


def test_runtime_config_supports_multiple_providers_and_dependency_checks(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "app.routers.assistant.check_database_connection",
        lambda _database_url: "ready",
    )
    monkeypatch.setattr(
        "app.routers.assistant.check_llm_connection",
        lambda _provider: "configured",
    )
    monkeypatch.setattr(
        "app.routers.assistant.check_speech_configuration",
        lambda _speech: "configured",
    )
    # Prevent configure_database from mutating global DB state or creating real .db files
    monkeypatch.setattr("app.routers.assistant.configure_database", lambda _url: None)

    client = TestClient(create_app())
    payload = {
        "database_url": "sqlite+pysqlite:///runtime-config.db",
        "providers": [
            {
                "id": "kimi-default",
                "label": "Kimi 默认",
                "base_url": "https://api.moonshot.ai/v1",
                "api_key": "kimi-key",
                "model": "kimi-k2.5",
                "enabled": True,
            },
            {
                "id": "custom-openai",
                "label": "自定义 OpenAI",
                "base_url": "https://example.com/v1",
                "api_key": "custom-key",
                "model": "gpt-4.1",
                "enabled": True,
            },
        ],
        "active_provider_id": "custom-openai",
        "speech": {
            "api_key": "dashscope-key",
            "asr_model": "paraformer-realtime-v2",
            "tts_model": "cosyvoice-v1",
            "voice_name": "longxiaochun",
            "language": "zh-CN",
        },
    }

    save_response = client.post("/api/runtime-config", json=payload)
    get_response = client.get("/api/runtime-config")
    check_response = client.post("/api/runtime-config/check")

    assert save_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["active_provider_id"] == "custom-openai"
    assert len(get_response.json()["providers"]) == 2
    assert check_response.status_code == 200
    assert check_response.json()["dependencies"] == {
        "database": "ready",
        "llm": "configured",
        "speech": "configured",
        "config": "ready",
    }
    assert json.loads(config_path.read_text(encoding="utf-8"))["active_provider_id"] == "custom-openai"


def test_home_snapshot_exposes_runtime_summary(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "runtime-config.json"
    # Write an explicit config so the test never falls back to env-var-based defaults.
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-runtime.db",
            "providers": [{
                "id": "kimi-default",
                "label": "Kimi",
                "base_url": "https://api.moonshot.ai/v1",
                "api_key": "test-key",
                "model": "kimi-k2.5",
                "enabled": True,
            }],
            "active_provider_id": "kimi-default",
            "speech": {
                "api_key": "test-speech-key",
                "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1",
                "voice_name": "longxiaochun",
                "language": "zh-CN",
                "provider": "aliyun",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    response = client.get("/api/home")

    assert response.status_code == 200
    runtime = response.json().get("runtime")
    assert runtime is not None
    required_keys = {"llm_provider", "llm_model", "speech_provider", "voice_name", "knowledge_root", "knowledge_root_exists"}
    assert required_keys <= set(runtime.keys())
    # Values reflect the public release (Aliyun/Kimi) stack locked in the fixture config above.
    # runtime.voice_name mirrors the DB-backed preference (default "longxiaochun"),
    # not the runtime config JSON, so it always matches what /api/tts will use.
    assert runtime["voice_name"] == "longxiaochun"
    assert runtime["speech_provider"] == "aliyun"
    assert runtime["llm_provider"] == "kimi-default"
    assert isinstance(runtime["knowledge_root_exists"], bool)


def test_home_runtime_voice_name_mirrors_db_preference_not_config_json(monkeypatch, tmp_path) -> None:
    """runtime.voice_name must equal preferences.voice_name (DB) — never drift from it.

    Even when the runtime config JSON carries a different voice_name, the effective
    voice that /api/tts uses is the DB-backed preference. /api/home must reflect that
    same value in runtime.voice_name so clients can rely on a single source of truth.
    """
    config_path = tmp_path / "runtime-config.json"
    # Runtime config JSON has a *different* voice from the DB preference.
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-mirror.db",
            "providers": [{
                "id": "kimi-default",
                "label": "Kimi",
                "base_url": "https://api.moonshot.ai/v1",
                "api_key": "test-key",
                "model": "kimi-k2.5",
                "enabled": True,
            }],
            "active_provider_id": "kimi-default",
            "speech": {
                "api_key": "",
                "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1",
                "voice_name": "config-json-voice",  # intentionally differs from DB preference
                "language": "zh-CN",
                "provider": "aliyun",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    # Set DB preference to a voice that differs from the config JSON value.
    pref_response = client.post(
        "/api/preferences",
        json={"teacher_style": "默认", "voice_name": "db-pref-voice"},
    )
    assert pref_response.status_code == 200

    home_response = client.get("/api/home")
    assert home_response.status_code == 200
    body = home_response.json()

    # DB preference reflects the saved voice.
    assert body["preferences"]["voice_name"] == "db-pref-voice"
    # runtime.voice_name must mirror the DB preference, not the config JSON.
    assert body["runtime"]["voice_name"] == "db-pref-voice"
    # The two fields must agree — no drift.
    assert body["runtime"]["voice_name"] == body["preferences"]["voice_name"]


def test_action_proposal_marks_command_execution_as_dangerous() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/actions/propose",
        json={"action_type": "run_command", "target": "Get-Location"},
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "dangerous"
    assert response.json()["requires_confirmation"] is True


def test_runtime_config_persists_knowledge_root_and_speech_provider(tmp_path, monkeypatch) -> None:
    """knowledge_root and speech.provider must round-trip through save → load."""
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "app.routers.assistant.check_database_connection",
        lambda _database_url: "ready",
    )
    # Prevent configure_database from mutating global DB state or creating real .db files
    monkeypatch.setattr("app.routers.assistant.configure_database", lambda _url: None)

    client = TestClient(create_app())
    payload = {
        "database_url": "sqlite+pysqlite:///test.db",
        "providers": [
            {
                "id": "p1",
                "label": "Test LLM",
                "base_url": "https://api.test.ai/v1",
                "api_key": "test-key",
                "model": "test-model-v1",
                "enabled": True,
            }
        ],
        "active_provider_id": "p1",
        "speech": {
            "api_key": "speech-key",
            "asr_model": "paraformer-realtime-v2",
            "tts_model": "cosyvoice-v1",
            "voice_name": "longxiaochun",
            "language": "zh-CN",
            "provider": "aliyun",
        },
        "knowledge_root": str(tmp_path / "my-knowledge"),
    }

    save_response = client.post("/api/runtime-config", json=payload)
    get_response = client.get("/api/runtime-config")

    assert save_response.status_code == 200
    assert save_response.json()["knowledge_root"] == str(tmp_path / "my-knowledge")
    assert save_response.json()["speech"]["provider"] == "aliyun"

    assert get_response.status_code == 200
    assert get_response.json()["knowledge_root"] == str(tmp_path / "my-knowledge")
    assert get_response.json()["speech"]["provider"] == "aliyun"

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["knowledge_root"] == str(tmp_path / "my-knowledge")


def test_home_reflects_runtime_config_knowledge_root(tmp_path, monkeypatch) -> None:
    """/api/home runtime summary must use runtime config knowledge_root, not env-var default."""
    custom_root = tmp_path / "custom-knowledge-dir"
    config_path = tmp_path / "runtime-config.json"
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-home.db",
            "providers": [{
                "id": "p1",
                "label": "Test",
                "base_url": "https://api.test.ai/v1",
                "api_key": "key",
                "model": "model-x",
                "enabled": True,
            }],
            "active_provider_id": "p1",
            "speech": {
                "api_key": "",
                "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1",
                "voice_name": "longxiaochun",
                "language": "zh-CN",
                "provider": "aliyun",
            },
            "knowledge_root": str(custom_root),
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    response = client.get("/api/home")

    assert response.status_code == 200
    runtime = response.json()["runtime"]
    assert runtime["knowledge_root"] == str(custom_root)
    assert runtime["knowledge_root_exists"] is False  # dir wasn't created


def test_saving_runtime_config_voice_name_syncs_db_preference_and_home(tmp_path, monkeypatch) -> None:
    """Saving runtime config with a new speech.voice_name must sync the DB preference
    so /api/home runtime.voice_name and preferences.voice_name stay consistent (no drift).

    Task 6 spec: /api/runtime-config save and /api/home must echo voice_name consistently.
    Fix: saving runtime config syncs the DB-backed preference voice_name to the saved value.
    """
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)
    # Prevent DB switch so the test-app's in-memory schema stays active.
    monkeypatch.setattr("app.routers.assistant.configure_database", lambda _url: None)

    client = TestClient(create_app())
    payload = {
        "database_url": "sqlite+pysqlite:///test-sync.db",
        "providers": [
            {
                "id": "p1",
                "label": "Test",
                "base_url": "https://api.test.ai/v1",
                "api_key": "key",
                "model": "model-x",
                "enabled": True,
            }
        ],
        "active_provider_id": "p1",
        "speech": {
            "api_key": "",
            "asr_model": "paraformer-realtime-v2",
            "tts_model": "cosyvoice-v1",
            "voice_name": "synced-runtime-voice",
            "language": "zh-CN",
            "provider": "aliyun",
        },
    }

    save_response = client.post("/api/runtime-config", json=payload)
    assert save_response.status_code == 200

    home_response = client.get("/api/home")
    assert home_response.status_code == 200
    body = home_response.json()

    # After saving runtime config, preferences.voice_name must be synced to the runtime speech voice.
    assert body["preferences"]["voice_name"] == "synced-runtime-voice"
    # runtime.voice_name mirrors the DB preference, which was just synced — no drift.
    assert body["runtime"]["voice_name"] == "synced-runtime-voice"
    assert body["runtime"]["voice_name"] == body["preferences"]["voice_name"]


def test_saving_preferences_voice_name_syncs_runtime_config_json(tmp_path, monkeypatch) -> None:
    """POST /api/preferences must mirror the new voice_name into the runtime config JSON
    so GET /api/runtime-config never drifts from GET /api/home / preferences (Task 6 bidirectional fix).
    """
    config_path = tmp_path / "runtime-config.json"
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-bidir.db",
            "providers": [{
                "id": "p1",
                "label": "Test",
                "base_url": "https://api.test.ai/v1",
                "api_key": "key",
                "model": "model-x",
                "enabled": True,
            }],
            "active_provider_id": "p1",
            "speech": {
                "api_key": "",
                "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1",
                "voice_name": "old-config-voice",
                "language": "zh-CN",
                "provider": "aliyun",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    # Change voice via preferences endpoint.
    pref_response = client.post(
        "/api/preferences",
        json={"teacher_style": "默认", "voice_name": "new-pref-voice"},
    )
    assert pref_response.status_code == 200
    assert pref_response.json()["voice_name"] == "new-pref-voice"

    # The runtime config JSON must also reflect the new voice.
    rc_response = client.get("/api/runtime-config")
    assert rc_response.status_code == 200
    assert rc_response.json()["speech"]["voice_name"] == "new-pref-voice"


def test_search_uses_runtime_config_knowledge_root_dynamically(tmp_path, monkeypatch) -> None:
    """SearchService must pick up the runtime-config knowledge_root without restart."""
    knowledge_dir = tmp_path / "dynamic-knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "topic.md").write_text("dynamic knowledge content about jarvis-dynamic-query")

    config_path = tmp_path / "runtime-config.json"
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-search.db",
            "providers": [{
                "id": "p1",
                "label": "Test",
                "base_url": "https://api.test.ai/v1",
                "api_key": "key",
                "model": "model-x",
                "enabled": True,
            }],
            "active_provider_id": "p1",
            "speech": {
                "api_key": "",
                "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1",
                "voice_name": "longxiaochun",
                "language": "zh-CN",
                "provider": "aliyun",
            },
            "knowledge_root": str(knowledge_dir),
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    client = TestClient(create_app())
    response = client.get(
        "/api/search",
        params={"query": "jarvis-dynamic-query", "scope": "knowledge"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) > 0
    assert any("jarvis-dynamic-query" in r["snippet"] for r in results)


# ── Task 6 Issue 2: configure_database ordering ──────────────────────────────

_MINIMAL_PAYLOAD = {
    "database_url": "sqlite+pysqlite:///test-ordering.db",
    "providers": [
        {
            "id": "p1",
            "label": "T",
            "base_url": "https://t.ai/v1",
            "api_key": "k",
            "model": "m",
            "enabled": True,
        }
    ],
    "active_provider_id": "p1",
    "speech": {
        "api_key": "",
        "asr_model": "paraformer-realtime-v2",
        "tts_model": "cosyvoice-v1",
        "voice_name": "new-order-voice",
        "language": "zh-CN",
        "provider": "aliyun",
    },
}


def test_store_runtime_config_configure_db_called_before_voice_sync(tmp_path, monkeypatch) -> None:
    """configure_database must be called BEFORE voice sync so the new DB receives the update.

    Task 6 spec: voice sync must target the newly configured DB, not the old one.
    This test proves the call order: configure_database → voice_sync.
    """
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    call_order: list[str] = []
    monkeypatch.setattr(
        "app.routers.assistant.configure_database",
        lambda _url: call_order.append("configure_database"),
    )
    original_update = assistant_router.memory_service.update_preferences

    def tracked_update(db, *, teacher_style: str, voice_name: str):
        call_order.append("voice_sync")
        return original_update(db, teacher_style=teacher_style, voice_name=voice_name)

    monkeypatch.setattr(assistant_router.memory_service, "update_preferences", tracked_update)

    client = TestClient(create_app())
    response = client.post("/api/runtime-config", json=_MINIMAL_PAYLOAD)

    assert response.status_code == 200
    assert call_order == ["configure_database", "voice_sync"], (
        f"configure_database must precede voice_sync; got: {call_order}"
    )


def test_store_runtime_config_configure_db_not_skipped_if_voice_sync_fails(tmp_path, monkeypatch) -> None:
    """configure_database must still be called even when voice sync throws.

    Task 6 spec: a voice-sync error must never prevent the DB from being reconfigured.
    """
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    configure_db_calls: list[str] = []
    monkeypatch.setattr(
        "app.routers.assistant.configure_database",
        lambda url: configure_db_calls.append(url),
    )

    def failing_update(*_args, **_kwargs) -> None:
        raise RuntimeError("db write intentionally failed")

    monkeypatch.setattr(assistant_router.memory_service, "update_preferences", failing_update)

    client = TestClient(create_app())
    payload = {**_MINIMAL_PAYLOAD, "database_url": "sqlite+pysqlite:///test-failsync.db"}
    response = client.post("/api/runtime-config", json=payload)

    # configure_database must have been called despite voice sync failure
    assert len(configure_db_calls) == 1
    assert configure_db_calls[0] == "sqlite+pysqlite:///test-failsync.db"
    # The API must still return 200 — voice sync failure is non-fatal
    assert response.status_code == 200


def test_knowledge_root_can_be_cleared_to_empty_string(tmp_path, monkeypatch) -> None:
    """Setting knowledge_root='' must persist as empty string, not revert to settings default.

    Bug: _runtime_config_from_payload used `or fallback.knowledge_root`, so an explicit
    empty string silently fell back and the user could never actually clear the override.
    """
    config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)
    monkeypatch.setattr("app.routers.assistant.configure_database", lambda _url: None)

    client = TestClient(create_app())
    payload = {
        "database_url": "sqlite+pysqlite:///test-clear.db",
        "providers": [{
            "id": "p1", "label": "Test",
            "base_url": "https://api.test.ai/v1", "api_key": "key",
            "model": "model-x", "enabled": True,
        }],
        "active_provider_id": "p1",
        "speech": {
            "api_key": "", "asr_model": "paraformer-realtime-v2",
            "tts_model": "cosyvoice-v1", "voice_name": "longxiaochun",
            "language": "zh-CN", "provider": "aliyun",
        },
        "knowledge_root": "",  # explicit empty → must clear the override
    }

    save_response = client.post("/api/runtime-config", json=payload)
    assert save_response.status_code == 200
    # The returned config must carry empty string, not the settings default path
    assert save_response.json()["knowledge_root"] == ""

    # The persisted JSON file must also store ""
    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["knowledge_root"] == ""

    # Re-reading via GET must also return ""
    get_response = client.get("/api/runtime-config")
    assert get_response.status_code == 200
    assert get_response.json()["knowledge_root"] == ""


def test_get_runtime_config_returns_empty_knowledge_root_when_config_stores_empty(tmp_path, monkeypatch) -> None:
    """get_runtime_config() must return knowledge_root='' when the JSON stores '' — not fall back."""
    config_path = tmp_path / "runtime-config.json"
    config_path.write_text(
        json.dumps({
            "database_url": "sqlite+pysqlite:///test-read-empty.db",
            "providers": [{
                "id": "p1", "label": "Test",
                "base_url": "https://api.test.ai/v1", "api_key": "key",
                "model": "model-x", "enabled": True,
            }],
            "active_provider_id": "p1",
            "speech": {
                "api_key": "", "asr_model": "paraformer-realtime-v2",
                "tts_model": "cosyvoice-v1", "voice_name": "longxiaochun",
                "language": "zh-CN", "provider": "aliyun",
            },
            "knowledge_root": "",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.runtime_config_service.RUNTIME_CONFIG_PATH", config_path)

    from app.services.runtime_config_service import get_runtime_config
    config = get_runtime_config()
    assert config.knowledge_root == ""
