# Autonomy and Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Jarvis run bounded background jobs and proactive workflows while preserving explicit approval policies, telemetry, and failure review.

**Architecture:** Background autonomy is built as policy-governed jobs on top of the unified gateway, Agent Core, worker runtime, and perception layers. Every autonomous run must produce replayable events, telemetry, and a review record so “working in the background” never means “invisible and unauditable.”

**Tech Stack:** FastAPI, SQLAlchemy, background tasks/APScheduler-compatible service design, pytest, existing permission/proactive services

---

## File Structure

- Create: `D:\Jarvis\jarvis-server\app\services\autonomy_models.py`
- Create: `D:\Jarvis\jarvis-server\app\services\job_scheduler_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\approval_policy_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\eval_review_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\proactive.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\telemetry.py`
- Create: `D:\Jarvis\jarvis-server\app\routers\autonomy.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_autonomy_api.py`

---

### Task 1: Define autonomy job and review contracts

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\autonomy_models.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_autonomy_api.py`

- [ ] **Step 1: Write the failing contract test**

```python
from app.services.autonomy_models import AutonomyJobRequest, AutonomyReviewRecord


def test_autonomy_job_contract_contains_policy_fields():
    job = AutonomyJobRequest(
        job_name="nightly-follow-up",
        session_id="session-1",
        goal="检查昨天中断的任务",
        risk_level="medium",
        approval_mode="proposal_required",
    )
    review = AutonomyReviewRecord(
        job_name="nightly-follow-up",
        outcome="completed",
        summary="已生成提醒但未执行危险动作",
    )

    assert job.approval_mode == "proposal_required"
    assert review.outcome == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py -q
```

Expected: FAIL with import errors for autonomy models.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomyJobRequest:
    job_name: str
    session_id: str
    goal: str
    risk_level: str
    approval_mode: str


@dataclass(frozen=True)
class AutonomyReviewRecord:
    job_name: str
    outcome: str
    summary: str
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/autonomy_models.py tests/test_autonomy_api.py
git commit -m "feat: add autonomy contracts"
```

---

### Task 2: Add policy-checked background job execution

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\approval_policy_service.py`
- Create: `D:\Jarvis\jarvis-server\app\services\job_scheduler_service.py`
- Create: `D:\Jarvis\jarvis-server\app\routers\autonomy.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\proactive.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_autonomy_api.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_autonomy_job_creation_requires_policy_decision():
    client = TestClient(app)
    response = client.post(
        "/api/autonomy/jobs",
        json={
            "job_name": "nightly-follow-up",
            "session_id": "session-1",
            "goal": "继续昨天的修复",
            "risk_level": "medium",
            "approval_mode": "proposal_required",
        },
    )

    assert response.status_code == 200
    assert "policy" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py -q
```

Expected: FAIL because `/api/autonomy/jobs` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class ApprovalPolicyService:
    def decide(self, request: AutonomyJobRequest) -> dict[str, object]:
        requires_confirmation = request.risk_level in {"high", "critical"} or request.approval_mode != "auto"
        return {
            "requires_confirmation": requires_confirmation,
            "decision": "proposal_required" if requires_confirmation else "auto_run",
        }
```

```python
class JobSchedulerService:
    def schedule(self, request: AutonomyJobRequest, policy: dict[str, object]) -> dict[str, object]:
        return {
            "job_name": request.job_name,
            "session_id": request.session_id,
            "scheduled": True,
            "policy": policy,
        }
```

```python
@router.post("/api/autonomy/jobs")
def create_autonomy_job(request: dict[str, object]) -> dict[str, object]:
    job = AutonomyJobRequest(**request)
    policy = ApprovalPolicyService().decide(job)
    result = JobSchedulerService().schedule(job, policy)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py tests\test_proactive.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/approval_policy_service.py app/services/job_scheduler_service.py app/routers/autonomy.py app/routers/proactive.py tests/test_autonomy_api.py
git commit -m "feat: add policy-checked autonomy jobs"
```

---

### Task 3: Record telemetry and automatic post-run review

**Files:**
- Create: `D:\Jarvis\jarvis-server\app\services\eval_review_service.py`
- Modify: `D:\Jarvis\jarvis-server\app\routers\telemetry.py`
- Create: `D:\Jarvis\jarvis-server\tests\test_autonomy_api.py`

- [ ] **Step 1: Write the failing telemetry/review test**

```python
from app.services.autonomy_models import AutonomyReviewRecord
from app.services.eval_review_service import EvalReviewService


def test_eval_review_service_returns_review_record():
    review = EvalReviewService().build_review(
        job_name="nightly-follow-up",
        outcome="completed",
        summary="任务完成，无危险动作。",
    )

    assert isinstance(review, AutonomyReviewRecord)
    assert review.summary == "任务完成，无危险动作。"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py -q
```

Expected: FAIL because `EvalReviewService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class EvalReviewService:
    def build_review(self, job_name: str, outcome: str, summary: str) -> AutonomyReviewRecord:
        return AutonomyReviewRecord(
            job_name=job_name,
            outcome=outcome,
            summary=summary,
        )
```

```python
@router.post("/api/telemetry/autonomy-review")
def record_autonomy_review(payload: dict[str, str]) -> dict[str, str]:
    review = EvalReviewService().build_review(
        job_name=payload["job_name"],
        outcome=payload["outcome"],
        summary=payload["summary"],
    )
    return {"job_name": review.job_name, "outcome": review.outcome}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest tests\test_autonomy_api.py tests\test_telemetry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/eval_review_service.py app/routers/telemetry.py tests/test_autonomy_api.py
git commit -m "feat: add autonomy review telemetry"
```

---

## Self-Review

- **Spec coverage:** This plan covers the later-phase background autonomy, approval gates, and auditability the user asked for.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** `AutonomyJobRequest`, `AutonomyReviewRecord`, `ApprovalPolicyService`, `JobSchedulerService`, and `EvalReviewService` are used consistently.
