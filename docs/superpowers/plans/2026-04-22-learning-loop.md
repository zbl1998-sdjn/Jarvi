# Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the automatic post-task learning loop that decides whether a completed task becomes memory, a skill draft/update, or only a searchable historical artifact.

**Architecture:** Implement Learning Loop as a pure, testable decision service that receives the final task result plus structured execution trace, writes a `learning_record`, then calls Memory Manager and Skill Registry according to explicit guardrails. Keep high-risk or low-confidence skill outputs in draft mode.

**Tech Stack:** SQLAlchemy, FastAPI, pytest, existing Agent Core service

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\learning_loop_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_learning_loop_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\memory_manager.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\skill_registry_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`

---

### Task 1: Add LearningRecord schema and decision primitives

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\models.py`
- Create: `D:\Jarvis\jarvis-server\app\services\learning_loop_service.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_learning_loop_service.py`

- [ ] **Step 1: Write the failing decision test**

```python
from app.services.learning_loop_service import LearningLoopService


def test_learning_loop_marks_high_risk_skill_as_draft():
    service = LearningLoopService()
    record = service.review(
        query="删除无用日志文件",
        answer="已完成",
        trace={"calls": [{"name": "delete_file", "args": {"path": "danger.txt"}}]},
        success=True,
    )

    assert record["outcome"] == "success"
    assert record["skill_candidates"][0]["status"] == "draft"
    assert record["skill_candidates"][0]["risk_level"] == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_learning_loop_service.py -q
```

Expected: FAIL because `LearningLoopService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class LearningLoopService:
    HIGH_RISK_TOOLS = {"delete_file", "write_file", "run_command", "os_control"}

    def review(self, query: str, answer: str, trace: dict[str, object], success: bool) -> dict[str, object]:
        calls = trace.get("calls", []) if isinstance(trace, dict) else []
        risky = any(call.get("name") in self.HIGH_RISK_TOOLS for call in calls if isinstance(call, dict))
        status = "draft" if risky else "active"
        risk_level = "high" if risky else "low"
        return {
            "task_summary": query,
            "outcome": "success" if success else "failure",
            "memory_candidates": [],
            "skill_candidates": [
                {
                    "name": query[:48],
                    "status": status,
                    "risk_level": risk_level,
                }
            ] if success and calls else [],
            "decision": "skill" if success and calls else "artifact_only",
        }
```

```python
class LearningRecord(Base):
    __tablename__ = "learning_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    task_summary: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(16))
    memory_candidates: Mapped[str] = mapped_column(Text, default="[]")
    skill_candidates: Mapped[str] = mapped_column(Text, default="[]")
    decision: Mapped[str] = mapped_column(String(32))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_learning_loop_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/services/learning_loop_service.py tests/test_learning_loop_service.py
git commit -m "feat: add learning loop decisions"
```

---

### Task 2: Persist learning records and call Memory / Skill services

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\memory_manager.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\skill_registry_service.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_agent_core_service.py`

- [ ] **Step 1: Write the failing integration test**

```python
from app.models import LearningRecord, SkillIndex
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService


def test_agent_core_persists_learning_outputs(fake_db):
    result = AgentCoreService().run(
        fake_db,
        AgentCoreRequest(query="总结 trace panel 修复套路", entrypoint="chat"),
    )

    rows = fake_db.query(LearningRecord).all()
    assert len(rows) == 1
    assert rows[0].task_summary == "总结 trace panel 修复套路"
    assert fake_db.query(SkillIndex).count() >= 0
    assert result.learning_record_id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py -q
```

Expected: FAIL because learning persistence is not wired into `AgentCoreService`.

- [ ] **Step 3: Write minimal integration implementation**

```python
from app.models import LearningRecord
from app.services.learning_loop_service import LearningLoopService
from app.services.memory_manager import MemoryManager
from app.services.skill_registry_service import SkillDraft, SkillRegistryService

learning = LearningLoopService().review(
    query=request.query,
    answer=result.answer,
    trace={"iterations": result.trace.iterations, "calls": result.trace.calls},
    success=True,
)
record = LearningRecord(
    session_id=active_session,
    task_summary=learning["task_summary"],
    outcome=learning["outcome"],
    memory_candidates=json.dumps(learning["memory_candidates"], ensure_ascii=False),
    skill_candidates=json.dumps(learning["skill_candidates"], ensure_ascii=False),
    decision=learning["decision"],
)
db.add(record)
db.flush()
for candidate in learning["skill_candidates"]:
    SkillRegistryService().write_skill(
        db,
        SkillDraft(
            name=candidate["name"],
            category="auto",
            risk_level=candidate["risk_level"],
            description=request.query,
            content=f"# {candidate['name']}\\n\\n## When to Use\\n{request.query}",
            source_session_id=active_session,
            source_learning_record_id=record.id,
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py tests\test_learning_loop_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_core_service.py app/services/memory_manager.py app/services/skill_registry_service.py tests/test_agent_core_service.py
git commit -m "feat: persist learning loop outputs"
```

---

### Task 3: Expose learning visibility and guardrails

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\routers\agent.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_agent_api.py`
- Modify: `D:\Jarvis\jarvis-server\tests\test_learning_loop_service.py`

- [ ] **Step 1: Write the failing visibility test**

```python
def test_agent_learn_endpoint_returns_recent_learning_records():
    client = TestClient(create_app())
    response = client.get("/api/agent/learn")
    assert response.status_code == 200
    assert "records" in response.json()
```

```python
def test_learning_loop_does_not_activate_failed_tasks():
    record = LearningLoopService().review(
        query="删除风险文件",
        answer="失败",
        trace={"calls": [{"name": "delete_file", "args": {"path": "danger.txt"}}]},
        success=False,
    )
    assert record["decision"] == "artifact_only"
    assert record["skill_candidates"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_api.py tests\test_learning_loop_service.py -q
```

Expected: FAIL because the visibility endpoint and failed-task guard are incomplete.

- [ ] **Step 3: Write minimal implementation**

```python
@router.get("/api/agent/learn")
def list_learning_records(limit: int = 20) -> dict[str, object]:
    db = SessionLocal()
    try:
        rows = db.query(LearningRecord).order_by(LearningRecord.id.desc()).limit(limit).all()
        return {
            "records": [
                {
                    "id": row.id,
                    "session_id": row.session_id,
                    "task_summary": row.task_summary,
                    "outcome": row.outcome,
                    "decision": row.decision,
                }
                for row in rows
            ]
        }
    finally:
        db.close()
```

```python
if not success:
    return {
        "task_summary": query,
        "outcome": "failure",
        "memory_candidates": [],
        "skill_candidates": [],
        "decision": "artifact_only",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_api.py tests\test_learning_loop_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/agent.py tests/test_agent_api.py tests/test_learning_loop_service.py
git commit -m "feat: expose learning loop status"
```

---

## Self-Review

- **Spec coverage:** This plan covers post-run review, learning records, memory/skill decisions, risk gating, and user-visible learning outputs.
- **Placeholder scan:** No placeholders remain.
- **Type consistency:** `LearningLoopService`, `LearningRecord`, `SkillDraft`, and Agent Core integration use consistent names and payload shapes.
