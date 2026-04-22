# Platform Gateway and Event Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified multi-entry gateway API and event-stream protocol so desktop, future web clients, and future bot connectors all speak the same `action -> observation -> thought -> result` language.

**Architecture:** Reuse the server-side Agent Core from Stage 1 and place a thin gateway/session layer in front of it. Event envelopes are defined once, persisted once, and replayed to every client instead of each entrypoint inventing its own chat-specific response shape.

**Tech Stack:** FastAPI, Pydantic, WebSocket, SQLAlchemy, React, existing Jarvis trace/proposal UI

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\schemas\gateway.py`
  - Shared request/response/event envelope models.
- Create: `D:\Jarvis\jarvis-server\app\services\event_stream_service.py`
  - Persists and replays structured gateway events.
- Create: `D:\Jarvis\jarvis-server\app\routers\gateway.py`
  - `/api/gateway/sessions`, `/api/gateway/stream`, and replay endpoints.
- Modify: `D:\Jarvis\jarvis-server\app\main.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\chat.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\realtime.py`
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_gateway_api.py`
- Create: `D:\Jarvis\jarvis-ui\src\app\api\gateway-client.ts`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\trace-panel-model.ts`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\TracePanel.tsx`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\TracePanel.test.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`

---

### Task 1: Define the gateway event contracts and persistence model

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\schemas\gateway.py`
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_gateway_api.py`

- [ ] **Step 1: Write the failing contract test**

```python
from app.schemas.gateway import GatewayEvent, GatewayRequest


def test_gateway_event_contract_has_required_fields():
    request = GatewayRequest(
        entrypoint="desktop-chat",
        session_id="session-1",
        user_text="帮我继续昨天的修复",
        attachments=[],
    )
    event = GatewayEvent(
        event_id="evt-1",
        session_id="session-1",
        event_type="thought",
        phase="understanding",
        payload={"summary": "正在读取历史上下文"},
    )

    assert request.entrypoint == "desktop-chat"
    assert event.event_type == "thought"
    assert event.payload["summary"] == "正在读取历史上下文"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_gateway_api.py -q
```

Expected: FAIL with import errors for `app.schemas.gateway`.

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime
from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    entrypoint: str
    session_id: str | None = None
    user_text: str
    attachments: list[dict[str, object]] = Field(default_factory=list)


class GatewayEvent(BaseModel):
    event_id: str
    session_id: str
    event_type: str
    phase: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

```python
class EventStreamRecord(Base):
    __tablename__ = "event_stream_records"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    phase = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_gateway_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/gateway.py app/models.py tests/test_gateway_api.py
git commit -m "feat: add gateway event contracts"
```

---

### Task 2: Route chat/realtime through the gateway stream service

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\event_stream_service.py`
- Create: `D:\Jarvis\jarvis-server\app\routers\gateway.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\chat.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\realtime.py`
- Modify: `D:\Jarvis\jarvis-server\app\main.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_gateway_api.py`

- [ ] **Step 1: Write the failing integration test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_gateway_stream_replays_persisted_events():
    client = TestClient(app)
    create_response = client.post(
        "/api/gateway/sessions",
        json={"entrypoint": "desktop-chat", "user_text": "测试", "attachments": []},
    )
    session_id = create_response.json()["session_id"]

    replay_response = client.get(f"/api/gateway/sessions/{session_id}/events")

    assert replay_response.status_code == 200
    assert isinstance(replay_response.json()["events"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_gateway_api.py -q
```

Expected: FAIL because the gateway router does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
import json
import uuid

from app.models import EventStreamRecord
from app.schemas.gateway import GatewayEvent


class EventStreamService:
    def append(self, db, event: GatewayEvent) -> None:
        db.add(
            EventStreamRecord(
                id=event.event_id,
                session_id=event.session_id,
                event_type=event.event_type,
                phase=event.phase,
                payload_json=json.dumps(event.payload, ensure_ascii=False),
            )
        )
        db.commit()

    def list_for_session(self, db, session_id: str) -> list[GatewayEvent]:
        rows = (
            db.query(EventStreamRecord)
            .filter_by(session_id=session_id)
            .order_by(EventStreamRecord.created_at.asc())
            .all()
        )
        return [
            GatewayEvent(
                event_id=row.id,
                session_id=row.session_id,
                event_type=row.event_type,
                phase=row.phase,
                payload=json.loads(row.payload_json),
                created_at=row.created_at,
            )
            for row in rows
        ]
```

```python
@router.post("/api/gateway/sessions")
def create_gateway_session(request: GatewayRequest) -> dict[str, object]:
    session_id = request.session_id or str(uuid.uuid4())
    return {"session_id": session_id, "accepted": True}


@router.get("/api/gateway/sessions/{session_id}/events")
def list_gateway_events(session_id: str) -> dict[str, object]:
    db = SessionLocal()
    try:
        events = EventStreamService().list_for_session(db, session_id)
        return {"session_id": session_id, "events": [event.model_dump(mode="json") for event in events]}
    finally:
        db.close()
```

- [ ] **Step 4: Adapt chat/realtime to append gateway events**

```python
EventStreamService().append(
    db,
    GatewayEvent(
        event_id=str(uuid.uuid4()),
        session_id=result.session_id,
        event_type="result",
        phase="answer",
        payload={"answer": result.answer},
    ),
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_gateway_api.py tests\test_chat_sse.py tests\test_realtime_ws.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/event_stream_service.py app/routers/gateway.py app/routers/chat.py app/routers/realtime.py app/main.py tests/test_gateway_api.py
git commit -m "feat: add gateway event stream"
```

---

### Task 3: Surface the unified event stream in the desktop console

**Files:**
- Create: `D:\Jarvis\jarvis-ui\src\app\api\gateway-client.ts`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\trace-panel-model.ts`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\TracePanel.tsx`
- Create: `D:\Jarvis\jarvis-ui\src\features\console\TracePanel.test.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`

- [ ] **Step 1: Write the failing client/model test**

```ts
import { applyGatewayEventToTracePanel } from "../../features/console/trace-panel-model";

it("maps gateway thought events into the trace panel", () => {
  const next = applyGatewayEventToTracePanel(undefined, {
    event_id: "evt-1",
    session_id: "session-1",
    event_type: "thought",
    phase: "understanding",
    payload: { summary: "正在读取长期记忆" },
  });

  expect(next.current?.title).toContain("长期记忆");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src/features/console/TracePanel.test.tsx src/features/console/MainConsole.test.tsx
```

Expected: FAIL because gateway event support is missing.

- [ ] **Step 3: Write minimal implementation**

```ts
export type GatewayConsoleEvent = {
  event_id: string;
  session_id: string;
  event_type: string;
  phase: TracePhase;
  payload: Record<string, unknown>;
};

export function applyGatewayEventToTracePanel(
  current: TracePanelState | undefined,
  event: GatewayConsoleEvent,
): TracePanelState {
  return applyTracePatch(current, {
    id: event.event_id,
    phase: event.phase,
    status: event.event_type === "error" ? "failed" : "in_progress",
    title: String(event.payload.summary ?? event.payload.answer ?? event.event_type),
  });
}
```

```ts
export function TracePanel({ state }: { state: TracePanelState }) {
  return <section>{state.current?.title}</section>;
}
```

```ts
export async function listGatewayEvents(sessionId: string) {
  const response = await fetch(`/api/gateway/sessions/${sessionId}/events`);
  return response.json() as Promise<{ session_id: string; events: GatewayConsoleEvent[] }>;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src/features/console/TracePanel.test.tsx src/features/console/MainConsole.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add jarvis-ui/src/app/api/gateway-client.ts jarvis-ui/src/features/console/trace-panel-model.ts jarvis-ui/src/features/console/TracePanel.tsx jarvis-ui/src/features/console/MainConsole.tsx
git commit -m "feat: surface gateway event stream"
```

---

## Self-Review

- **Spec coverage:** This plan covers the OpenHands-style event-stream direction and multi-entry gateway layer that Stage 2 is supposed to establish.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** `GatewayRequest`, `GatewayEvent`, `EventStreamService`, and `applyGatewayEventToTracePanel` are used consistently.
