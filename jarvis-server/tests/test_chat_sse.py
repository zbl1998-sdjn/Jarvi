import json
from asyncio import run

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.chat_service import prepare_chat, stream_chat


def parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []

    for chunk in body.strip().split("\n\n"):
        lines = chunk.splitlines()
        event_name = lines[0].removeprefix("event: ").strip()
        payload = json.loads(lines[1].removeprefix("data: ").strip())
        events.append({"event": event_name, "data": payload})

    return events


def test_chat_stream_emits_session_text_and_done_events(monkeypatch) -> None:
    class FakeChatClient:
        def complete(
            self,
            query: str,
            history: list[tuple[str, str]],
            knowledge_context: str = "",
        ) -> str:
            assert query == "hello jarvis"
            assert history == []
            assert knowledge_context == ""
            return "这是首轮 Kimi 回复。"

    monkeypatch.setattr(
        "app.services.chat_service.create_chat_client",
        lambda: FakeChatClient(),
    )
    monkeypatch.setattr(
        "app.services.chat_service.KnowledgeContextService",
        lambda: type("FakeKnowledgeContext", (), {"build_context": lambda self, query: ""})(),
    )

    client = TestClient(create_app())

    response = client.get(
        "/api/chat",
        params={"query": "hello jarvis"},
        headers={"accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)
    session_id = events[0]["data"]["session_id"]

    assert events == [
        {
            "event": "session",
            "data": {"session_id": session_id},
        },
        {
            "event": "text",
            "data": {"text": "这是首轮 Kimi 回复。"},
        },
        {
            "event": "done",
            "data": {"session_id": session_id},
        },
    ]


async def collect_events(generator) -> list[str]:
    return [chunk async for chunk in generator]


def test_stream_chat_persists_user_and_assistant_messages(monkeypatch) -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, ...]] = []

        def session_exists(self, session_id: str) -> bool:
            self.calls.append(("session_exists", session_id))
            return False

        def create_session(self) -> str:
            self.calls.append(("create_session",))
            return "session-123"

        def list_messages(self, session_id: str) -> list[tuple[str, str]]:
            self.calls.append(("list_messages", session_id))
            return []

        def append_message(self, session_id: str, role: str, content: str) -> None:
            self.calls.append(("append_message", session_id, role, content))

        def commit(self) -> None:
            self.calls.append(("commit",))

    class FakeChatClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def complete(
            self,
            query: str,
            history: list[tuple[str, str]],
            knowledge_context: str = "",
        ) -> str:
            self.calls.append(("complete", query, history, knowledge_context))
            return "这是来自 Kimi 的回复"

    repository = FakeRepository()
    chat_client = FakeChatClient()
    monkeypatch.setattr(
        "app.services.chat_service.KnowledgeContextService",
        lambda: type("FakeKnowledgeContext", (), {"build_context": lambda self, query: ""})(),
    )

    prepared = prepare_chat(
        query="hello jarvis",
        repository=repository,
        chat_client=chat_client,
    )

    assert repository.calls == [
        ("create_session",),
        ("list_messages", "session-123"),
        ("append_message", "session-123", "user", "hello jarvis"),
        ("append_message", "session-123", "assistant", "这是来自 Kimi 的回复"),
        ("commit",),
    ]
    assert chat_client.calls == [("complete", "hello jarvis", [], "")]
    assert prepared.session_id == "session-123"
    assert prepared.answer == "这是来自 Kimi 的回复"


def test_stream_chat_emits_events_from_prepared_chat() -> None:
    chunks = run(collect_events(stream_chat(session_id="session-123", answer="Jarvis M1 已收到：hello jarvis")))

    assert parse_sse_events("".join(chunks)) == [
        {
            "event": "session",
            "data": {"session_id": "session-123"},
        },
        {
            "event": "text",
            "data": {"text": "Jarvis M1 已收到：hello jarvis"},
        },
        {
            "event": "done",
            "data": {"session_id": "session-123"},
        },
    ]


def test_stream_chat_creates_new_session_when_requested_one_is_missing(monkeypatch) -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, ...]] = []

        def session_exists(self, session_id: str) -> bool:
            self.calls.append(("session_exists", session_id))
            return False

        def create_session(self) -> str:
            self.calls.append(("create_session",))
            return "session-456"

        def list_messages(self, session_id: str) -> list[tuple[str, str]]:
            self.calls.append(("list_messages", session_id))
            return []

        def append_message(self, session_id: str, role: str, content: str) -> None:
            self.calls.append(("append_message", session_id, role, content))

        def commit(self) -> None:
            self.calls.append(("commit",))

    class FakeChatClient:
        def complete(
            self,
            query: str,
            history: list[tuple[str, str]],
            knowledge_context: str = "",
        ) -> str:
            assert query == "hello again"
            assert history == []
            assert knowledge_context == ""
            return "第二次也由 Kimi 回复"

    repository = FakeRepository()
    chat_client = FakeChatClient()
    monkeypatch.setattr(
        "app.services.chat_service.KnowledgeContextService",
        lambda: type("FakeKnowledgeContext", (), {"build_context": lambda self, query: ""})(),
    )

    prepared = prepare_chat(
        query="hello again",
        session_id="missing-session",
        repository=repository,
        chat_client=chat_client,
    )

    assert repository.calls == [
        ("session_exists", "missing-session"),
        ("create_session",),
        ("list_messages", "session-456"),
        ("append_message", "session-456", "user", "hello again"),
        ("append_message", "session-456", "assistant", "第二次也由 Kimi 回复"),
        ("commit",),
    ]
    assert prepared.session_id == "session-456"
    assert prepared.answer == "第二次也由 Kimi 回复"


def test_chat_stream_uses_model_response(monkeypatch) -> None:
    class FakeChatClient:
        def complete(
            self,
            query: str,
            history: list[tuple[str, str]],
            knowledge_context: str = "",
        ) -> str:
            assert query == "hello jarvis"
            assert history == []
            assert knowledge_context == ""
            return "Kimi 已接管当前对话。"

    monkeypatch.setattr(
        "app.services.chat_service.create_chat_client",
        lambda: FakeChatClient(),
    )
    monkeypatch.setattr(
        "app.services.chat_service.KnowledgeContextService",
        lambda: type("FakeKnowledgeContext", (), {"build_context": lambda self, query: ""})(),
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/chat",
        params={"query": "hello jarvis"},
        headers={"accept": "text/event-stream"},
    )

    assert response.status_code == 200

    events = parse_sse_events(response.text)

    assert events[1] == {
        "event": "text",
        "data": {"text": "Kimi 已接管当前对话。"},
    }


def test_chat_returns_error_response_when_persistence_fails_before_first_event(monkeypatch) -> None:
    class FakeDb:
        def close(self) -> None:
            return None

    class FailingRepository:
        def __init__(self, _db) -> None:
            pass

        def session_exists(self, session_id: str) -> bool:
            return False

        def create_session(self) -> str:
            return "session-789"

        def append_message(self, session_id: str, role: str, content: str) -> None:
            raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.routers.chat.SessionLocal", lambda: FakeDb())
    monkeypatch.setattr("app.routers.chat.SessionRepository", FailingRepository)

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get(
        "/api/chat",
        params={"query": "trigger failure"},
        headers={"accept": "text/event-stream"},
    )

    assert response.status_code == 500
    assert not response.headers["content-type"].startswith("text/event-stream")
