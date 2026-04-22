# Hermes Roadmap Stages 2-5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the post-cognitive-core Hermes roadmap so Jarvis can progress from a single desktop agent into a multi-entry, worker-driven, perceptive, and governed autonomous system.

**Architecture:** Stage 1 remains the cognitive core. Stages 2-5 layer on top in this order: gateway/event stream, worker runtime, continuous perception, then autonomy/governance. Each stage gets its own executable plan and must preserve the server-side Agent Core as the shared center of gravity.

**Tech Stack:** FastAPI, WebSocket, SQLAlchemy, SQLite/PostgreSQL, Electron, React, existing Jarvis orchestrator/tool runtime

---

## File Structure

- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-hermes-cognitive-core-design.md`
- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-agent-orchestrator-design.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-hermes-cognitive-core-rollout.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-platform-gateway-event-stream.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-worker-runtime-and-skill-execution.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-continuous-perception.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-autonomy-and-governance.md`

---

### Task 1: Lock the 5-stage roadmap and dependency order

**Files:**
- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-hermes-cognitive-core-design.md`
- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-agent-orchestrator-design.md`

- [ ] **Step 1: Confirm the stage map**

```text
Stage 1: Cognitive Core
Stage 2: Platform Gateway + Event Stream
Stage 3: Worker Runtime + Skill Execution
Stage 4: Continuous Perception + Ambient Recall
Stage 5: Autonomy + Governance + Ops
```

- [ ] **Step 2: Lock the dependency chain**

```text
stage-2-platform-gateway-event-stream
  -> stage-3-worker-runtime
  -> stage-4-continuous-perception
  -> stage-5-autonomy-governance
```

- [ ] **Step 3: Verify Stage 1 remains the prerequisite**

Run:

```powershell
Set-Location 'D:\Jarvis'
python - <<'PY'
from pathlib import Path
required = [
    Path('docs/superpowers/plans/2026-04-22-agent-core-service.md'),
    Path('docs/superpowers/plans/2026-04-22-memory-recall-layer.md'),
    Path('docs/superpowers/plans/2026-04-22-skill-registry.md'),
    Path('docs/superpowers/plans/2026-04-22-learning-loop.md'),
]
for path in required:
    print(path.name, path.exists())
PY
```

Expected: all four files print `True`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-roadmap-stages-2-5.md
git commit -m "docs: add hermes stages 2-5 roadmap"
```

---

### Task 2: Sequence the implementation plans

**Files:**
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-platform-gateway-event-stream.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-worker-runtime-and-skill-execution.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-continuous-perception.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-autonomy-and-governance.md`

- [ ] **Step 1: Execute Stage 2 first**

```text
Implement the gateway and event-stream plan before adding new worker types or background autonomy. Every later stage depends on a stable cross-entrypoint event protocol.
```

- [ ] **Step 2: Execute Stage 3 second**

```text
Implement the worker runtime only after Stage 2 event envelopes, session routing, and stream persistence are stable.
```

- [ ] **Step 3: Execute Stage 4 third**

```text
Implement continuous perception only after Stage 3 can safely consume new recall artifacts without bypassing the Agent Core.
```

- [ ] **Step 4: Execute Stage 5 fourth**

```text
Implement autonomy/governance only after the system can route events, execute workers, and recall ambient context safely.
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-roadmap-stages-2-5.md
git commit -m "docs: sequence hermes stages 2-5"
```

---

### Task 3: Define the stage-by-stage acceptance bar

**Files:**
- Test: `D:\Jarvis\jarvis-server\tests\test_gateway_api.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_worker_runtime.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_perception_store.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_autonomy_api.py`

- [ ] **Step 1: Record Stage 2 acceptance**

```text
- desktop chat and realtime voice emit the same event envelope
- at least one future gateway can reuse the same `/api/gateway/*` contract
- trace/proposal/result events can be replayed from persistence
```

- [ ] **Step 2: Record Stage 3 acceptance**

```text
- manager can delegate to a named worker profile
- terminal/native execution returns observation events, not hidden logs
- skill hits can bias worker selection without skipping approval gates
```

- [ ] **Step 3: Record Stage 4 acceptance**

```text
- the system can recall a recent screen snippet or OCR fact
- perception storage is bounded and locally retained
- ambient context can be attached to an Agent Core request on demand
```

- [ ] **Step 4: Record Stage 5 acceptance**

```text
- a background job can run unattended under policy
- high-risk autonomous actions still require approval
- telemetry/eval records make failures auditable
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-roadmap-stages-2-5.md
git commit -m "docs: define hermes stages 2-5 acceptance"
```

---

## Self-Review

- **Spec coverage:** This roadmap bridges Stage 1 cognitive core into the later Hermes-inspired capabilities the user requested: gateway/event stream, worker runtime, continuous perception, and autonomy/governance.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** The stage identifiers and plan filenames are consistent across the roadmap.
