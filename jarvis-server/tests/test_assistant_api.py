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


def test_search_summary_and_home_snapshot_work_together() -> None:
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
    assert Path("D:/Jarvis/.worktrees/jarvis-m1-shell-text-console/runtime/temp/m6-note.txt").exists()
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


def test_action_proposal_marks_command_execution_as_dangerous() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/actions/propose",
        json={"action_type": "run_command", "target": "Get-Location"},
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "dangerous"
    assert response.json()["requires_confirmation"] is True
