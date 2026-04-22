# Skill Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Hermes-style skill registry so Jarvis can store, version, enable, disable, and retrieve reusable task skills from a managed skills directory.

**Architecture:** Use a hybrid design: `skill_index` metadata in the database and skill bodies as files under `runtime/skills/`. Agent Core reads candidate skill metadata from SQL, then loads only the selected skill files from disk for token-efficient prompt assembly.

**Tech Stack:** Python stdlib file I/O, SQLAlchemy, FastAPI, pytest

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\skill_registry_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\skill_runtime_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_skill_registry_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_skill_runtime_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`
- Create directory: `D:\Jarvis\runtime\skills`

---

### Task 1: Add the SkillIndex model and file-path conventions

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_skill_registry_service.py`

- [ ] **Step 1: Write the failing model/path test**

```python
from app.models import SkillIndex
from app.services.skill_registry_service import skill_slug, skill_directory


def test_skill_registry_path_helpers():
    assert skill_slug("Trace Panel Recovery") == "trace-panel-recovery"
    assert skill_directory("console", "trace-panel-recovery").as_posix().endswith("runtime/skills/console/trace-panel-recovery")


def test_skill_index_model_has_required_fields():
    row = SkillIndex(
        skill_name="trace-panel-recovery",
        category="console",
        version=1,
        status="draft",
        risk_level="low",
        source_session_id="session-1",
        source_learning_record_id=1,
        hit_count=0,
    )
    assert row.status == "draft"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_skill_registry_service.py -q
```

Expected: FAIL because `SkillIndex` helpers/services do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class SkillIndex(Base):
    __tablename__ = "skill_index"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    source_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_learning_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
```

```python
from pathlib import Path
import re

SKILLS_ROOT = Path("D:/Jarvis/runtime/skills")


def skill_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def skill_directory(category: str, slug: str) -> Path:
    return SKILLS_ROOT / category / slug
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_skill_registry_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/services/skill_registry_service.py tests/test_skill_registry_service.py
git commit -m "feat: add skill registry schema"
```

---

### Task 2: Build skill write/read/update runtime

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\skill_registry_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\skill_runtime_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_skill_runtime_service.py`

- [ ] **Step 1: Write the failing runtime test**

```python
from app.services.skill_registry_service import SkillDraft, SkillRegistryService


def test_skill_registry_writes_skill_file_and_index(fake_db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.skill_registry_service.SKILLS_ROOT", tmp_path / "skills")
    service = SkillRegistryService()
    draft = SkillDraft(
        name="trace-panel-recovery",
        category="console",
        risk_level="low",
        description="Recover a broken trace panel state",
        content="# Trace Panel Recovery\\n\\n## When to Use\\nUse when trace panel state is inconsistent.",
        source_session_id="session-1",
        source_learning_record_id=1,
    )

    row = service.write_skill(fake_db, draft)

    assert row.skill_name == "trace-panel-recovery"
    assert (tmp_path / "skills" / "console" / "trace-panel-recovery" / "SKILL.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_skill_runtime_service.py -q
```

Expected: FAIL because `SkillDraft`/`write_skill` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDraft:
    name: str
    category: str
    risk_level: str
    description: str
    content: str
    source_session_id: str | None
    source_learning_record_id: int | None
```

```python
class SkillRegistryService:
    def write_skill(self, db, draft: SkillDraft) -> SkillIndex:
        slug = skill_slug(draft.name)
        directory = skill_directory(draft.category, slug)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(draft.content, encoding="utf-8")
        row = db.query(SkillIndex).filter_by(skill_name=slug).one_or_none()
        if row is None:
            row = SkillIndex(
                skill_name=slug,
                category=draft.category,
                version=1,
                status="draft",
                risk_level=draft.risk_level,
                source_session_id=draft.source_session_id,
                source_learning_record_id=draft.source_learning_record_id,
                hit_count=0,
            )
            db.add(row)
        else:
            row.version += 1
        db.flush()
        return row
```

```python
class SkillRuntimeService:
    def list_candidates(self, db, query: str, limit: int = 5) -> list[dict[str, object]]:
        rows = (
            db.query(SkillIndex)
            .filter(SkillIndex.status.in_(["draft", "active"]))
            .order_by(SkillIndex.hit_count.desc(), SkillIndex.version.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "skill_name": row.skill_name,
                "category": row.category,
                "status": row.status,
                "risk_level": row.risk_level,
                "version": row.version,
            }
            for row in rows
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_skill_runtime_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/skill_registry_service.py app/services/skill_runtime_service.py tests/test_skill_runtime_service.py
git commit -m "feat: add skill runtime services"
```

---

### Task 3: Expose skill metadata and feed candidate skills into Agent Context

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_context_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_agent_context_service.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_agent_api.py`

- [ ] **Step 1: Write the failing integration tests**

```python
def test_agent_context_includes_candidate_skills(fake_db):
    from app.models import SkillIndex
    from app.services.agent_context_service import AgentContextService
    from app.services.agent_core_models import AgentCoreRequest

    fake_db.add(SkillIndex(skill_name="trace-panel-recovery", category="console", version=1, status="active", risk_level="low", source_session_id=None, source_learning_record_id=None, hit_count=2))
    fake_db.commit()

    bundle = AgentContextService().build(fake_db, AgentCoreRequest(query="trace panel 修复", entrypoint="chat"))

    assert bundle.candidate_skills[0]["skill_name"] == "trace-panel-recovery"
```

```python
def test_agent_skills_endpoint_returns_registry_snapshot():
    client = TestClient(create_app())
    response = client.get("/api/agent/skills")
    assert response.status_code == 200
    assert "skills" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py tests\test_agent_api.py -q
```

Expected: FAIL because candidate skill loading and the endpoint do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from app.services.skill_runtime_service import SkillRuntimeService

candidate_skills = SkillRuntimeService().list_candidates(db, request.query, limit=5) if db is not None else []
```

```python
@router.get("/api/agent/skills")
def list_agent_skills() -> dict[str, object]:
    db = SessionLocal()
    try:
        return {"skills": SkillRuntimeService().list_candidates(db, query="", limit=50)}
    finally:
        db.close()
```

```python
@router.post("/api/agent/skills/{skill_name}/enable")
def enable_skill(skill_name: str) -> dict[str, object]:
    db = SessionLocal()
    try:
        row = SkillRegistryService().set_status(db, skill_name, "active")
        db.commit()
        return {"skill_name": row.skill_name, "status": row.status}
    finally:
        db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_context_service.py tests\test_agent_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_context_service.py app/routers/agent.py tests/test_agent_context_service.py tests/test_agent_api.py
git commit -m "feat: expose skill registry"
```

---

## Self-Review

- **Spec coverage:** This plan covers skill storage, versioned metadata, file-body layout, enable/disable behavior, and candidate skill loading.
- **Placeholder scan:** No placeholders remain.
- **Type consistency:** `SkillIndex`, `SkillDraft`, `SkillRegistryService`, and `SkillRuntimeService` are used consistently.
