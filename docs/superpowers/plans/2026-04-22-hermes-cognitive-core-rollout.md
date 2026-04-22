# Hermes Cognitive Core Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the full first-stage Hermes-style cognitive core for Jarvis by sequencing Agent Core, Memory/Recall, Skill Registry, and Learning Loop into a safe rollout.

**Architecture:** This rollout treats the cognitive core as four dependent subsystems behind a single server-side Agent Core. Each subsystem gets its own implementation plan, but this file defines execution order, shared boundaries, and validation checkpoints so the work lands as one coherent system instead of four disconnected patches.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite runtime compatibility, pytest, existing Jarvis Electron + FastAPI stack

---

## File Structure

- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-hermes-cognitive-core-design.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-agent-core-service.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-memory-recall-layer.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-skill-registry.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-learning-loop.md`

---

### Task 1: Establish rollout order and hard dependencies

**Files:**
- Review: `D:\Jarvis\docs\superpowers\specs\2026-04-22-hermes-cognitive-core-design.md`
- Review: `D:\Jarvis\jarvis-server\app\services\agent_loop.py`
- Review: `D:\Jarvis\jarvis-server\app\services\chat_service.py`
- Review: `D:\Jarvis\jarvis-server\app\routers\realtime.py`

- [ ] **Step 1: Confirm execution order**

Use this rollout order exactly:

```text
1. Agent Core service boundary
2. Memory / Recall layer
3. Skill Registry
4. Learning Loop
5. End-to-end acceptance + UI visibility follow-up
```

- [ ] **Step 2: Verify the current backend still centers on chat/realtime entrypoints**

Run:

```powershell
Set-Location 'D:\Jarvis'
python - <<'PY'
from pathlib import Path
for path in [
    Path('jarvis-server/app/services/chat_service.py'),
    Path('jarvis-server/app/routers/realtime.py'),
    Path('jarvis-server/app/services/agent_loop.py'),
]:
    print(path, path.exists())
PY
```

Expected: all three paths print `True`.

- [ ] **Step 3: Lock the dependency map**

Use this dependency map for all execution tracking:

```text
agent-core-service
  -> memory-recall-layer
  -> skill-registry-layer
  -> learning-loop-layer
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-cognitive-core-rollout.md
git commit -m "docs: add cognitive core rollout plan"
```

---

### Task 2: Execute the subsystem plans in sequence

**Files:**
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-agent-core-service.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-memory-recall-layer.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-skill-registry.md`
- Review: `D:\Jarvis\docs\superpowers\plans\2026-04-22-learning-loop.md`

- [ ] **Step 1: Execute the Agent Core plan first**

```text
Implement docs/superpowers/plans/2026-04-22-agent-core-service.md completely before touching the other three plans.
```

- [ ] **Step 2: Execute Memory / Recall second**

```text
Implement docs/superpowers/plans/2026-04-22-memory-recall-layer.md only after Agent Core API/contracts are stable.
```

- [ ] **Step 3: Execute Skill Registry third**

```text
Implement docs/superpowers/plans/2026-04-22-skill-registry.md only after Memory / Recall persistence exists.
```

- [ ] **Step 4: Execute Learning Loop fourth**

```text
Implement docs/superpowers/plans/2026-04-22-learning-loop.md only after Skill Registry write/update flows exist.
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-cognitive-core-rollout.md
git commit -m "docs: sequence cognitive core rollout"
```

---

### Task 3: Run final system acceptance

**Files:**
- Test: `D:\Jarvis\jarvis-server\tests\test_agent_core_service.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_memory_recall_layer.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_skill_registry_service.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_learning_loop_service.py`
- Test: `D:\Jarvis\jarvis-server\tests\test_agent_api.py`

- [ ] **Step 1: Run the focused backend acceptance suite**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest `
  tests\test_agent_core_service.py `
  tests\test_memory_recall_layer.py `
  tests\test_skill_registry_service.py `
  tests\test_learning_loop_service.py `
  tests\test_agent_api.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run the existing backend regression suite that exercises current entrypoints**

Run:

```powershell
Set-Location 'D:\Jarvis\jarvis-server'
python -m pytest `
  tests\test_chat_sse.py `
  tests\test_realtime_ws.py `
  tests\test_assistant_api.py -q
```

Expected: all tests pass; no regressions in current desktop-facing APIs.

- [ ] **Step 3: Record rollout acceptance**

Acceptance is complete only if the system can demonstrate:

```text
- cross-session recall works
- user profile survives across sessions
- a finished task generates or updates a skill
- a repeated task hits an existing skill
- failed/high-risk tasks do not auto-enable bad skills
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-22-hermes-cognitive-core-rollout.md
git commit -m "docs: finalize cognitive core rollout plan"
```

---

## Self-Review

- **Spec coverage:** This rollout plan covers sequencing, dependency order, and acceptance for all four cognitive-core subplans.
- **Placeholder scan:** No TBD/TODO/placeholders remain.
- **Type consistency:** The rollout plan consistently refers to the same four subsystem plans and their shared execution order.
