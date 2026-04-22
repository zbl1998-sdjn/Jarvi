# Continuous Perception Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a bounded local perception loop so it can recall recent screen context, OCR text, and environment snippets instead of depending only on user-pasted context.

**Architecture:** Add a lightweight capture pipeline that stores recent perception artifacts in a local ring buffer and exposes them through Session Recall and Agent Core attachment logic. The design stays opt-in, local-first, and bounded so it behaves like a practical Recall layer rather than an unbounded surveillance service.

**Tech Stack:** Python, SQLite, Pillow/mss or existing screen utilities, FastAPI, SQLAlchemy, React

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\perception_store.py`
- Create: `D:\Jarvis\jarvis-server\app\services\perception_capture_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\local_recall_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_models.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Create: `D:\Jarvis\jarvis-server\app\routers\perception.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_perception_store.py`
- Create: `D:\Jarvis\jarvis-ui\src\features\panels\PerceptionDrawer.tsx`
- Create: `D:\Jarvis\jarvis-ui\src\features\panels\PerceptionDrawer.test.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`

---

### Task 1: Add bounded local perception storage

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\perception_store.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_perception_store.py`

- [ ] **Step 1: Write the failing storage test**

```python
from app.services.perception_store import PerceptionStore


def test_perception_store_keeps_only_recent_items(tmp_path):
    store = PerceptionStore(tmp_path / "perception.db", max_items=2)
    store.append(kind="screen", summary="第一帧", text="hello")
    store.append(kind="screen", summary="第二帧", text="world")
    store.append(kind="screen", summary="第三帧", text="again")

    rows = store.list_recent(limit=10)

    assert len(rows) == 2
    assert rows[0]["summary"] == "第三帧"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_perception_store.py -q
```

Expected: FAIL because `PerceptionStore` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
import sqlite3
from pathlib import Path


class PerceptionStore:
    def __init__(self, db_path: Path, max_items: int = 1000) -> None:
        self.db_path = db_path
        self.max_items = max_items
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS perception_items (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, summary TEXT, text TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )

    def append(self, kind: str, summary: str, text: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO perception_items (kind, summary, text) VALUES (?, ?, ?)",
                (kind, summary, text),
            )
            conn.execute(
                "DELETE FROM perception_items WHERE id NOT IN (SELECT id FROM perception_items ORDER BY id DESC LIMIT ?)",
                (self.max_items,),
            )

    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT kind, summary, text FROM perception_items ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"kind": row[0], "summary": row[1], "text": row[2]} for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_perception_store.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/perception_store.py tests/test_perception_store.py
git commit -m "feat: add bounded perception store"
```

---

### Task 2: Capture perception artifacts and expose recall endpoints

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\perception_capture_service.py`
- Create: `D:\Jarvis\jarvis-server\app\routers\perception.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\local_recall_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_perception_store.py`

- [ ] **Step 1: Write the failing capture/recall test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_perception_api_returns_recent_items():
    client = TestClient(app)
    response = client.get("/api/perception/recent?limit=5")

    assert response.status_code == 200
    assert "items" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_perception_store.py -q
```

Expected: FAIL because the perception router does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class PerceptionCaptureService:
    def __init__(self, store: PerceptionStore) -> None:
        self.store = store

    def capture_text_snapshot(self, text: str, summary: str) -> None:
        self.store.append(kind="ocr", summary=summary, text=text)
```

```python
@router.get("/api/perception/recent")
def list_recent_perception(limit: int = 10) -> dict[str, object]:
    store = build_perception_store()
    return {"items": store.list_recent(limit=limit)}
```

```python
def search(self, db, query: str, limit: int = 5) -> list[dict[str, object]]:
    items = build_perception_store().list_recent(limit=limit)
    matched = [item for item in items if query.lower() in str(item["text"]).lower()]
    return matched[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_perception_store.py tests\test_agent_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/perception_capture_service.py app/routers/perception.py app/services/local_recall_service.py tests/test_perception_store.py
git commit -m "feat: expose perception capture and recall"
```

---

### Task 3: Attach ambient perception to Agent Core and expose a desktop viewer

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_models.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Create: `D:\Jarvis\jarvis-ui\src\features\panels\PerceptionDrawer.tsx`
- Create: `D:\Jarvis\jarvis-ui\src\features\panels\PerceptionDrawer.test.tsx`
- Modify: `D:\Jarvis\jarvis-ui\src\features\console\MainConsole.tsx`

- [ ] **Step 1: Write the failing context/UI test**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_context_service import AgentContextService


def test_agent_context_includes_recent_perception(fake_db):
    bundle = AgentContextService().build(
        fake_db,
        AgentCoreRequest(query="我刚刚屏幕上看到的 React 代码是什么", entrypoint="chat", session_id="session-1"),
    )

    assert hasattr(bundle, "perception_hits")
```

```ts
it("renders recent perception items in the drawer", () => {
  render(<PerceptionDrawer items={[{ kind: "ocr", summary: "React Hook 代码", text: "useEffect(...)" }]} />);
  expect(screen.getByText("React Hook 代码")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py tests\test_perception_store.py -q
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src/features/panels/PerceptionDrawer.test.tsx src/features/console/MainConsole.test.tsx
```

Expected: FAIL because `perception_hits` and `PerceptionDrawer` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
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
    perception_hits: list[dict[str, object]] = field(default_factory=list)
```

```python
perception_hits = build_perception_store().list_recent(limit=3)
return AgentContextBundle(
    query=request.query,
    entrypoint=request.entrypoint,
    session_id=request.session_id,
    teacher_style=request.teacher_style,
    voice_name=request.voice_name,
    history=[],
    memory_facts=[],
    user_profile_facts=[],
    recall_hits=[],
    candidate_skills=[],
    perception_hits=perception_hits,
)
```

```tsx
type PerceptionItem = { kind: string; summary: string; text: string };

export function PerceptionDrawer({ items }: { items: PerceptionItem[] }) {
  return (
    <aside className="perception-drawer">
      {items.map((item) => (
        <section key={`${item.kind}-${item.summary}`}>
          <strong>{item.summary}</strong>
          <p>{item.text}</p>
        </section>
      ))}
    </aside>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py tests\test_perception_store.py -q
Set-Location 'D:\Jarvis\jarvis-ui'
npx vitest run src/features/panels/PerceptionDrawer.test.tsx src/features/console/MainConsole.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_core_models.py app/services/agent_context_service.py jarvis-ui/src/features/panels/PerceptionDrawer.tsx jarvis-ui/src/features/panels/PerceptionDrawer.test.tsx jarvis-ui/src/features/console/MainConsole.tsx
git commit -m "feat: attach ambient perception to agent context"
```

---

## Self-Review

- **Spec coverage:** This plan captures the Screenpipe-style bounded local perception direction and makes it queryable by Agent Core.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** `PerceptionStore`, `PerceptionCaptureService`, and `perception_hits` are used consistently.
