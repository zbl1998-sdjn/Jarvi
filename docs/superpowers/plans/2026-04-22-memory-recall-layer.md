# Memory Recall Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first-stage persistent memory and session recall layer behind Agent Core so Jarvis can remember long-term facts and search past work across sessions.

**Architecture:** Extend the existing SQLAlchemy model set with structured memory/recall tables, then add two focused services: one for long-term fact/profile management and one for searchable session artifacts. Keep retrieval text-based for phase one and integrate it into Agent Context assembly without introducing a vector store.

**Tech Stack:** SQLAlchemy, FastAPI, PostgreSQL/SQLite-compatible schema, pytest

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\memory_manager.py`
- Create: `D:\Jarvis\jarvis-server\app\services\session_recall_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_memory_manager.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_session_recall_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_memory_recall_layer.py`
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Modify: `D:\Jarvis\jarvis-server\app\main.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`

---

### Task 1: Add structured memory and recall tables

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Modify: `D:\Jarvis\jarvis-server\app\main.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_memory_recall_layer.py`

- [ ] **Step 1: Write the failing schema test**

```python
from sqlalchemy import inspect

from app.db import Base, get_engine
from app.models import MemoryFact, SessionArtifact, UserProfileFact


def test_cognitive_core_tables_exist():
    engine = get_engine()
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())

    assert "memory_facts" in tables
    assert "user_profile_facts" in tables
    assert "session_artifacts" in tables
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_memory_recall_layer.py -q
```

Expected: FAIL because the new models do not exist yet.

- [ ] **Step 3: Write minimal model + lightweight migration support**

```python
class MemoryFact(Base):
    __tablename__ = "memory_facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_type: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(String(128), default="")
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    last_confirmed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class UserProfileFact(Base):
    __tablename__ = "user_profile_facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_type: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    last_confirmed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class SessionArtifact(Base):
    __tablename__ = "session_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, default="")
```

```python
def _apply_lightweight_migrations(engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {
        "memory_facts": MemoryFact.__table__,
        "user_profile_facts": UserProfileFact.__table__,
        "session_artifacts": SessionArtifact.__table__,
    }
    for name, table in required_tables.items():
        if name not in existing_tables:
            table.create(bind=engine)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_memory_recall_layer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/main.py tests/test_memory_recall_layer.py
git commit -m "feat: add memory recall schema"
```

---

### Task 2: Build Memory Manager

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\memory_manager.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_memory_manager.py`

- [ ] **Step 1: Write the failing service test**

```python
from app.services.memory_manager import MemoryManager


def test_memory_manager_upserts_memory_and_profile(fake_db):
    manager = MemoryManager()

    manager.upsert_memory_fact(fake_db, "project_path", "Jarvis", "D:\\Jarvis", "agent")
    manager.upsert_user_profile(fake_db, "reply_style", "简洁直接", "agent")
    fake_db.commit()

    snapshot = manager.snapshot(fake_db)
    assert snapshot["memory_facts"][0]["fact_type"] == "project_path"
    assert snapshot["user_profile"][0]["profile_type"] == "reply_style"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_memory_manager.py -q
```

Expected: FAIL because `MemoryManager` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from sqlalchemy import desc, select

from app.models import MemoryFact, UserProfileFact


class MemoryManager:
    def upsert_memory_fact(self, db, fact_type: str, subject: str, value: str, source: str) -> None:
        existing = db.scalar(
            select(MemoryFact).where(MemoryFact.fact_type == fact_type, MemoryFact.subject == subject)
        )
        if existing is None:
            db.add(MemoryFact(fact_type=fact_type, subject=subject, value=value, source=source))
            return
        existing.value = value
        existing.source = source

    def upsert_user_profile(self, db, profile_type: str, value: str, source: str) -> None:
        existing = db.scalar(select(UserProfileFact).where(UserProfileFact.profile_type == profile_type))
        if existing is None:
            db.add(UserProfileFact(profile_type=profile_type, value=value, source=source))
            return
        existing.value = value
        existing.source = source

    def snapshot(self, db) -> dict[str, list[dict[str, object]]]:
        return {
            "memory_facts": [
                {"fact_type": row.fact_type, "subject": row.subject, "value": row.value, "source": row.source}
                for row in db.scalars(select(MemoryFact).order_by(desc(MemoryFact.id)).limit(20))
            ],
            "user_profile": [
                {"profile_type": row.profile_type, "value": row.value, "source": row.source}
                for row in db.scalars(select(UserProfileFact).order_by(desc(UserProfileFact.id)).limit(20))
            ],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_memory_manager.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/memory_manager.py tests/test_memory_manager.py
git commit -m "feat: add memory manager"
```

---

### Task 3: Build Session Recall and wire it into Agent Core

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\session_recall_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_session_recall_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`

- [ ] **Step 1: Write the failing recall test**

```python
from app.models import SessionArtifact
from app.services.session_recall_service import SessionRecallService


def test_session_recall_service_returns_matching_artifacts(fake_db):
    fake_db.add(SessionArtifact(artifact_type="task_result", session_id="s1", summary="修复 trace panel 切换问题", payload="{}"))
    fake_db.commit()

    hits = SessionRecallService().search(fake_db, "trace panel", limit=3)

    assert len(hits) == 1
    assert hits[0]["summary"] == "修复 trace panel 切换问题"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_session_recall_service.py -q
```

Expected: FAIL because `SessionRecallService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from sqlalchemy import or_, select

from app.models import SessionArtifact


class SessionRecallService:
    def search(self, db, query: str, limit: int = 5) -> list[dict[str, object]]:
        stmt = (
            select(SessionArtifact)
            .where(
                or_(
                    SessionArtifact.summary.contains(query),
                    SessionArtifact.payload.contains(query),
                )
            )
            .limit(limit)
        )
        return [
            {
                "id": row.id,
                "artifact_type": row.artifact_type,
                "session_id": row.session_id,
                "summary": row.summary,
                "payload": row.payload,
            }
            for row in db.scalars(stmt)
        ]
```

```python
from app.services.memory_manager import MemoryManager
from app.services.session_recall_service import SessionRecallService


class AgentContextService:
    def build(self, db, request):
        recall_hits = SessionRecallService().search(db, request.query, limit=5) if db is not None else []
        memory_snapshot = MemoryManager().snapshot(db) if db is not None else {"memory_facts": [], "user_profile": []}
        return AgentContextBundle(
            query=request.query,
            entrypoint=request.entrypoint,
            session_id=request.session_id,
            teacher_style=request.teacher_style,
            voice_name=request.voice_name,
            memory_facts=memory_snapshot["memory_facts"],
            user_profile_facts=memory_snapshot["user_profile"],
            recall_hits=recall_hits,
            candidate_skills=[],
        )
```

```python
@router.get("/api/agent/recall")
def recall_agent_memory(query: str, limit: int = 5) -> dict[str, object]:
    db = SessionLocal()
    try:
        return {"results": SessionRecallService().search(db, query, limit=limit)}
    finally:
        db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_session_recall_service.py tests\test_agent_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/session_recall_service.py app/services/agent_context_service.py app/routers/agent.py tests/test_session_recall_service.py
git commit -m "feat: add session recall service"
```

---

## Self-Review

- **Spec coverage:** This plan covers long-term facts, user profile memory, session recall storage, and retrieval API exposure.
- **Placeholder scan:** No placeholders remain.
- **Type consistency:** `MemoryManager`, `SessionRecallService`, `MemoryFact`, `UserProfileFact`, and `SessionArtifact` are used consistently.
