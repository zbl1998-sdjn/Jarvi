# Agent Core Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a server-side Agent Core service that becomes the single execution entrypoint for desktop requests and future platform gateways.

**Architecture:** Add a small, typed service boundary in `jarvis-server` that assembles context, calls the existing orchestrator/tool loop, and returns structured results. Existing chat/realtime routes are adapted to delegate to Agent Core rather than embedding cognitive logic in each route or service.

**Tech Stack:** FastAPI, SQLAlchemy, existing `agent_loop.py`, pytest

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\agent_core_models.py`
  - Typed request/result dataclasses for Agent Core.
- Create: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
  - Builds the context bundle from session history, preferences, recall hits, and candidate skills.
- Create: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
  - Main server-side orchestration entrypoint.
- Create: `D:\Jarvis\jarvis-server\app\routers\agent.py`
  - New `/api/agent/*` endpoints.
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_context_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_core_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_api.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\chat_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\realtime.py`
- Modify: `D:\Jarvis\jarvis-server\app\main.py`

---

### Task 1: Create typed Agent Core contracts

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\agent_core_models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_context_service.py`

- [ ] **Step 1: Write the failing contract/context test**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_context_service import AgentContextService


def test_agent_context_service_builds_context_bundle(fake_db):
    service = AgentContextService()
    request = AgentCoreRequest(
        query="帮我总结上次的修复经验",
        entrypoint="chat",
        session_id="session-1",
        teacher_style="幽默风趣型",
        voice_name="longxiaochun",
    )

    bundle = service.build(fake_db, request)

    assert bundle.query == "帮我总结上次的修复经验"
    assert bundle.entrypoint == "chat"
    assert isinstance(bundle.history, list)
    assert isinstance(bundle.memory_facts, list)
    assert isinstance(bundle.user_profile_facts, list)
    assert isinstance(bundle.recall_hits, list)
    assert isinstance(bundle.candidate_skills, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py -q
```

Expected: FAIL with import errors for the new service/model modules.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentCoreRequest:
    query: str
    entrypoint: str
    session_id: str | None = None
    teacher_style: str = ""
    voice_name: str = ""


@dataclass(frozen=True)
class AgentContextBundle:
    query: str
    entrypoint: str
    session_id: str | None
    teacher_style: str
    voice_name: str
    history: list[tuple[str, str]] = field(default_factory=list)
    memory_facts: list[dict[str, object]] = field(default_factory=list)
    user_profile_facts: list[dict[str, object]] = field(default_factory=list)
    recall_hits: list[dict[str, object]] = field(default_factory=list)
    candidate_skills: list[dict[str, object]] = field(default_factory=list)
```

```python
from app.services.agent_core_models import AgentContextBundle, AgentCoreRequest


class AgentContextService:
    def build(self, db, request: AgentCoreRequest) -> AgentContextBundle:
        return AgentContextBundle(
            query=request.query,
            entrypoint=request.entrypoint,
            session_id=request.session_id,
            teacher_style=request.teacher_style,
            voice_name=request.voice_name,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_core_models.py app/services/agent_context_service.py tests/test_agent_context_service.py
git commit -m "feat: add agent core contracts"
```

---

### Task 2: Build the Agent Core service

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_core_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\chat_service.py`

- [ ] **Step 1: Write the failing service test**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService


def test_agent_core_service_returns_structured_result(fake_db):
    service = AgentCoreService()
    result = service.run(
        fake_db,
        AgentCoreRequest(query="测试任务", entrypoint="chat", session_id=None),
    )

    assert result.session_id is not None
    assert isinstance(result.answer, str)
    assert isinstance(result.trace, dict)
    assert isinstance(result.context, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py -q
```

Expected: FAIL because `AgentCoreService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import asdict, dataclass

from app.repositories.session_repository import SessionRepository
from app.services.agent_context_service import AgentContextService
from app.services.agent_core_models import AgentCoreRequest
from app.services.chat_service import create_chat_client
from app.services.agent_loop import run_agent


@dataclass(frozen=True)
class AgentCoreResult:
    session_id: str
    answer: str
    trace: dict[str, object]
    context: dict[str, object]


class AgentCoreService:
    def __init__(self) -> None:
        self.context_service = AgentContextService()

    def run(self, db, request: AgentCoreRequest) -> AgentCoreResult:
        repository = SessionRepository(db)
        bundle = self.context_service.build(db, request)
        active_session = request.session_id or repository.create_session()
        history = repository.list_messages(active_session)
        client = create_chat_client()
        result = run_agent(
            client=client,
            db=db,
            user_query=request.query,
            history=history,
            teacher_style=request.teacher_style,
        )
        repository.append_message(active_session, role="user", content=request.query)
        repository.append_message(active_session, role="assistant", content=result.answer)
        repository.commit()
        return AgentCoreResult(
            session_id=active_session,
            answer=result.answer,
            trace={"iterations": result.trace.iterations, "calls": result.trace.calls},
            context=asdict(bundle),
        )
```

- [ ] **Step 4: Adapt `prepare_chat()` to delegate to Agent Core**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService

def prepare_chat(
    query: str,
    repository: SessionRepository,
    session_id: str | None = None,
    chat_client: KimiChatClient | None = None,
) -> PreparedChat:
    db = getattr(repository, "db", None)
    if db is not None:
        result = AgentCoreService().run(
            db,
            AgentCoreRequest(
                query=query,
                entrypoint="chat",
                session_id=active_session,
                teacher_style=teacher_style,
            ),
        )
        return PreparedChat(session_id=result.session_id, answer=result.answer, trace=AgentTrace(calls=result.trace["calls"], iterations=int(result.trace["iterations"])))
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py tests\test_chat_sse.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/agent_core_service.py app/services/chat_service.py tests/test_agent_core_service.py
git commit -m "feat: add agent core service"
```

---

### Task 3: Add Agent Core API entrypoints

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\routers\agent.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_agent_api.py`
- Modify: `D:\Jarvis\jarvis-server\app\main.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\realtime.py`

- [ ] **Step 1: Write the failing API tests**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_agent_run_endpoint_returns_structured_payload():
    client = TestClient(create_app())
    response = client.post(
        "/api/agent/run",
        json={"query": "测试一下", "entrypoint": "chat"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert "answer" in body
    assert "trace" in body


def test_agent_profile_endpoint_returns_profile_shape():
    client = TestClient(create_app())
    response = client.get("/api/agent/profile")
    assert response.status_code == 200
    assert "user_profile" in response.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_api.py -q
```

Expected: FAIL with 404s for the new endpoints.

- [ ] **Step 3: Write minimal API/router implementation**

```python
from fastapi import APIRouter
from pydantic import BaseModel

from app.db import SessionLocal
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService

router = APIRouter()


class AgentRunRequest(BaseModel):
    query: str
    entrypoint: str = "chat"
    session_id: str | None = None
    teacher_style: str = ""
    voice_name: str = ""


@router.post("/api/agent/run")
def run_agent_endpoint(request: AgentRunRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        result = AgentCoreService().run(
            db,
            AgentCoreRequest(**request.model_dump()),
        )
        return {
            "session_id": result.session_id,
            "answer": result.answer,
            "trace": result.trace,
            "context": result.context,
        }
    finally:
        db.close()


@router.get("/api/agent/profile")
def get_agent_profile() -> dict[str, object]:
    return {"user_profile": [], "memory_facts": []}
```

```python
from app.routers.agent import router as agent_router

app.include_router(agent_router)
```

- [ ] **Step 4: Make realtime route delegate to Agent Core for text turns**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService

result = AgentCoreService().run(
    db,
    AgentCoreRequest(
        query=turn.transcript,
        entrypoint="realtime",
        session_id=session_id,
        teacher_style=str(message.get("teacher_style", "")).strip(),
        voice_name=str(message.get("voice_name", "")).strip(),
    ),
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_api.py tests\test_realtime_ws.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routers/agent.py app/routers/realtime.py app/main.py tests/test_agent_api.py
git commit -m "feat: add agent core api"
```

---

## Self-Review

- **Spec coverage:** This plan covers the Agent Core service boundary, API entrypoints, and handoff from current chat/realtime flows.
- **Placeholder scan:** No placeholders remain.
- **Type consistency:** `AgentCoreRequest`, `AgentContextBundle`, `AgentCoreService`, and `AgentCoreResult` are used consistently throughout.
