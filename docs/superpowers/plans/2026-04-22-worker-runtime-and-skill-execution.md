# Worker Runtime and Skill Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce manager/worker execution so Jarvis can delegate terminal, research, and browser work to explicit worker profiles while reusing the Stage 1 skill registry and approval system.

**Architecture:** The Agent Core stays the manager. A worker runtime chooses a worker profile, executes tools under that profile, and emits observations back into the unified event stream. Skill hits bias worker selection and prompt assembly, but no worker may bypass existing proposal/approval policy.

**Tech Stack:** FastAPI, SQLAlchemy, existing `agent_loop.py`, existing `agent_tools.py`, pytest

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\worker_runtime_models.py`
- Create: `D:\Jarvis\jarvis-server\app\services\worker_runtime_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\worker_selection_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_tools.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\gateway.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_worker_runtime.py`

---

### Task 1: Define worker runtime contracts

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\worker_runtime_models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_worker_runtime.py`

- [ ] **Step 1: Write the failing contract test**

```python
from app.services.worker_runtime_models import WorkerExecutionRequest, WorkerProfile


def test_worker_runtime_contract_captures_profile_and_goal():
    profile = WorkerProfile(
        worker_name="terminal-coder",
        tool_names=["read_file", "run_command"],
        prompt_preamble="你是负责终端实现的执行工人。",
    )
    request = WorkerExecutionRequest(
        session_id="session-1",
        goal="修复构建错误",
        worker_name="terminal-coder",
    )

    assert profile.worker_name == "terminal-coder"
    assert request.goal == "修复构建错误"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_worker_runtime.py -q
```

Expected: FAIL with import errors for worker runtime models.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerProfile:
    worker_name: str
    tool_names: list[str]
    prompt_preamble: str


@dataclass(frozen=True)
class WorkerExecutionRequest:
    session_id: str
    goal: str
    worker_name: str
    skill_names: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_worker_runtime.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/worker_runtime_models.py tests/test_worker_runtime.py
git commit -m "feat: add worker runtime contracts"
```

---

### Task 2: Build worker selection and execution services

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\worker_selection_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\worker_runtime_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_tools.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_worker_runtime.py`

- [ ] **Step 1: Write the failing selection/execution test**

```python
from app.services.worker_runtime_models import WorkerExecutionRequest
from app.services.worker_runtime_service import WorkerRuntimeService


def test_worker_runtime_executes_under_selected_profile(fake_db):
    service = WorkerRuntimeService()
    result = service.run(
        fake_db,
        WorkerExecutionRequest(
            session_id="session-1",
            goal="列出当前工作区文件",
            worker_name="terminal-coder",
        ),
    )

    assert result.worker_name == "terminal-coder"
    assert isinstance(result.observations, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_worker_runtime.py -q
```

Expected: FAIL because `WorkerRuntimeService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field

from app.services.worker_runtime_models import WorkerExecutionRequest, WorkerProfile


DEFAULT_WORKERS = {
    "terminal-coder": WorkerProfile(
        worker_name="terminal-coder",
        tool_names=["read_file", "write_file", "run_command"],
        prompt_preamble="你负责代码与终端实现。",
    ),
    "researcher": WorkerProfile(
        worker_name="researcher",
        tool_names=["search_local", "search_web", "summarize_text"],
        prompt_preamble="你负责检索和总结。",
    ),
}


class WorkerSelectionService:
    def choose(self, request: WorkerExecutionRequest) -> WorkerProfile:
        return DEFAULT_WORKERS[request.worker_name]


@dataclass(frozen=True)
class WorkerExecutionResult:
    worker_name: str
    observations: list[dict[str, object]] = field(default_factory=list)


class WorkerRuntimeService:
    def __init__(self) -> None:
        self.selection = WorkerSelectionService()

    def run(self, db, request: WorkerExecutionRequest) -> WorkerExecutionResult:
        profile = self.selection.choose(request)
        return WorkerExecutionResult(
            worker_name=profile.worker_name,
            observations=[{"type": "worker_started", "goal": request.goal}],
        )
```

- [ ] **Step 4: Add profile-aware tool filtering**

```python
def filter_tools_for_worker(all_tools: list[dict[str, object]], profile: WorkerProfile) -> list[dict[str, object]]:
    allowed = set(profile.tool_names)
    return [tool for tool in all_tools if str(tool["name"]) in allowed]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_worker_runtime.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/worker_selection_service.py app/services/worker_runtime_service.py app/services/agent_tools.py tests/test_worker_runtime.py
git commit -m "feat: add worker runtime services"
```

---

### Task 3: Delegate worker runs from Agent Core and emit worker events

**Files:**
- Modify: `D:\Jarvis\jarvis-server\app\services\agent_core_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\gateway.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_worker_runtime.py`

- [ ] **Step 1: Write the failing Agent Core integration test**

```python
from app.services.agent_core_models import AgentCoreRequest
from app.services.agent_core_service import AgentCoreService


def test_agent_core_can_delegate_to_terminal_worker(fake_db):
    result = AgentCoreService().run(
        fake_db,
        AgentCoreRequest(
            query="帮我查看当前目录并总结结构",
            entrypoint="gateway",
            session_id="session-1",
        ),
    )

    assert "worker" in result.trace
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py tests\test_worker_runtime.py -q
```

Expected: FAIL because Agent Core does not attach worker traces yet.

- [ ] **Step 3: Write minimal implementation**

```python
worker_request = WorkerExecutionRequest(
    session_id=active_session,
    goal=request.query,
    worker_name="terminal-coder" if "目录" in request.query else "researcher",
    skill_names=[skill["skill_name"] for skill in bundle.candidate_skills if "skill_name" in skill],
)
worker_result = WorkerRuntimeService().run(db, worker_request)
trace = {
    "iterations": result.trace.iterations,
    "calls": result.trace.calls,
    "worker": {
        "worker_name": worker_result.worker_name,
        "observations": worker_result.observations,
    },
}
```

```python
EventStreamService().append(
    db,
    GatewayEvent(
        event_id=str(uuid.uuid4()),
        session_id=active_session,
        event_type="observation",
        phase="tool",
        payload={"worker": worker_result.worker_name, "observations": worker_result.observations},
    ),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_agent_core_service.py tests\test_worker_runtime.py tests\test_gateway_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_core_service.py app/routers/gateway.py tests/test_worker_runtime.py
git commit -m "feat: delegate worker execution from agent core"
```

---

## Self-Review

- **Spec coverage:** This plan covers the manager/worker direction the user asked for, while keeping skill reuse and approval gates in the loop.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** `WorkerProfile`, `WorkerExecutionRequest`, `WorkerExecutionResult`, and `WorkerRuntimeService` are used consistently.
