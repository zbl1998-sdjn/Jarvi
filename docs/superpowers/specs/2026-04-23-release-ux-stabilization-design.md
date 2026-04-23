# Jarvis Release UX Stabilization Design

Date: 2026-04-23
Repo: `jarvis-public-release`
Status: Draft approved in conversation, written for implementation planning

## 1. Problem Statement

The public release snapshot is buildable and testable, but it still has several experience-breaking gaps:

1. Fresh installs can fail on the first voice interaction because default voice configuration is inconsistent with the active speech provider.
2. File actions do not present a trustworthy safety boundary because path resolution and permission classification are not aligned.
3. Realtime and chat handlers perform blocking network work inside async request paths, which harms responsiveness and error recovery.
4. Voice and text interactions are not clearly separated in the UI, so users can trigger overlapping behaviors and confusing replies.
5. The homepage exposes many capabilities, but its hierarchy does not yet optimize for either first-use success or clear operator confidence.
6. Model/provider/runtime settings are partially configurable, but not unified into a clear user-facing control surface.

This iteration should stabilize the public release so that the first-run experience, recovery flows, action trust model, and runtime configurability all feel coherent.

## 2. Goals

This iteration must:

1. Fix all currently known high- and medium-priority release issues found in the public-repo audit.
2. Keep the cockpit-style homepage, but improve its information hierarchy and reduce ambiguity.
3. Make LLM model/provider, speech provider/voice, and knowledge-root settings user-configurable from the main experience.
4. Ensure text and voice interactions have distinct semantics and no longer race on the same reply surface.
5. Improve failure visibility so users always get a clear next step when configuration or voice transport is broken.
6. Preserve the current Electron + React + FastAPI architecture rather than introducing a larger product rewrite.

## 3. Non-Goals

This iteration does not:

1. Add accounts, sync, or multi-user collaboration.
2. Reposition the product away from a Windows-first desktop AI assistant prototype.
3. Rebuild the whole information architecture around a wizard/onboarding flow.
4. Introduce a large database migration beyond what is needed to normalize current defaults and settings behavior.
5. Add new major product capabilities unrelated to stabilization and UX clarity.

## 4. Chosen Product Direction

The chosen direction is a **cockpit-style homepage with restrained guidance**:

1. Keep the operator-facing control-center feeling.
2. Keep left/right contextual surfaces for learning state and action review.
3. Avoid a large onboarding card that dominates the main screen.
4. Add a compact, expandable diagnostics strip under the top status bar.
5. Make the center column clearly own input, voice state, reply output, and runtime controls.

This direction preserves the product identity while fixing first-use confusion and recovery gaps.

## 5. UX Design

### 5.1 Homepage hierarchy

The homepage remains a cockpit, but with explicit priority ordering:

1. **Top status bar**
   - Shell mode
   - Service health
   - Current LLM provider/model
   - Current speech provider/voice
   - Active session/resume state

2. **Diagnostics strip**
   - Collapsed when healthy
   - Auto-expands when any critical dependency is degraded or missing
   - Shows actionable messages, not raw status dumps
   - Supports direct actions such as re-check runtime, reconnect voice, resume last session, or open settings

3. **Center command surface**
   - Text input and send action
   - Voice connect and voice capture actions
   - Reply/result panel with structured state messaging
   - Compact runtime settings summary with expandable advanced controls

4. **Side surfaces**
   - Left side: learning progress, memories, reminders, task context
   - Right side: action approvals, resolved action history

### 5.2 Interaction semantics

Text and voice must no longer share ambiguous controls:

1. **Send text** always means chat submission over the text flow.
2. **Start voice** always means realtime voice capture/turn handling.
3. A typed query must never trigger both text-generation and voice-interpretation logic in parallel.
4. Voice state must be visible as explicit phases:
   - idle
   - connecting
   - listening
   - transcribing
   - thinking
   - speaking
   - interrupted
   - error

### 5.3 Error and recovery UX

Failure states must be actionable:

1. Voice socket failures should surface a specific error and a reconnect path.
2. Missing model/provider configuration should open into the settings surface with the failed field highlighted.
3. Invalid knowledge root should be shown as a diagnosable state, not a silent empty-search condition.
4. Degraded mode should explain what still works and what is unavailable.
5. Summary failures should be visible in the same result surface rather than disappearing into console errors.

### 5.4 Runtime settings UX

The user-facing settings experience should support:

1. LLM provider selection
2. LLM model selection
3. Speech provider selection
4. Speech voice selection
5. Knowledge-root path editing
6. Runtime reload/check actions

The default presentation should be compact:

- Example summary row: `Kimi / kimi-k2.5 / DashScope / longxiaochun`
- Expanding the settings reveals editable controls inline
- Saving settings refreshes status surfaces immediately

## 6. Technical Design

### 6.1 Configuration normalization

Current defaults are inconsistent across UI, models, and runtime services. This iteration will introduce a single consistent behavior:

1. Server-side defaults must reflect the active public release provider stack.
2. UI fallback defaults must match server defaults.
3. Runtime-config state should be the primary source of truth for provider/model/voice behavior where supported.
4. README and type declarations must match the resulting behavior.

Specific corrections required:

1. Remove Azure voice identifiers from public release defaults.
2. Ensure fresh preference rows pick a valid Aliyun-compatible voice by default.
3. Ensure the homepage shows the real active provider/model pair instead of stale placeholder assumptions.

### 6.2 Realtime and chat execution model

The current async request surfaces call blocking network work directly. This iteration will:

1. Move blocking LLM/ASR/TTS work off the event loop.
2. Preserve existing API shape where possible.
3. Introduce structured realtime error events.
4. Add bounded handling for accumulated audio buffers.

Expected backend behavior:

1. `chat` remains stream-oriented but does not block the whole app when the model is slow.
2. `realtime` wraps speech-turn execution in an off-thread boundary.
3. Realtime failures emit a transport-safe error payload before closing or resetting state.
4. Long or invalid audio capture is rejected with a user-facing explanation.

### 6.3 Action safety boundary

Permission evaluation and path resolution must use the same view of the target:

1. Resolve the actual filesystem target first.
2. Determine whether it is inside or outside the workspace/root boundary.
3. Apply risk classification based on both action type and resolved target.
4. Show the resolved target path in approval UI and audit records.

Expected action policy:

1. `read_file` and `write_file` outside the trusted workspace require strong confirmation.
2. Relative path traversal cannot silently bypass confirmation.
3. The approval UI explains why the action is risky, not just that it is risky.

### 6.4 Summary behavior

The public release should not present a fake summary feature. This iteration upgrades summary generation so that:

1. Summary output is genuinely useful to the user.
2. The result includes both a concise lead summary and scan-friendly bullets.
3. Failure or unavailable-provider states are surfaced cleanly.

The implementation should prefer reusing the existing LLM path rather than introducing a second summarization architecture.

## 7. Component-Level Changes

### 7.1 Backend

Expected areas of change:

1. `jarvis-server/app/models.py`
   - Normalize preference defaults

2. `jarvis-server/app/services/permission_service.py`
   - Rework classification around resolved paths and action semantics

3. `jarvis-server/app/services/action_service.py`
   - Resolve paths before permission decisions
   - Strengthen audit detail

4. `jarvis-server/app/routers/realtime.py`
   - Add bounded buffering
   - Offload blocking work
   - Emit structured error events

5. `jarvis-server/app/routers/chat.py`
   - Ensure blocking completion work does not freeze the app

6. `jarvis-server/app/services/speech_service.py`
   - Align provider defaults and failure behavior

7. `jarvis-server/app/services/summary_service.py`
   - Replace placeholder summary logic with real summarization behavior

8. `jarvis-server/app/services/runtime_config_service.py`
   - Support surfaced model/provider state used by the homepage

### 7.2 Frontend

Expected areas of change:

1. `jarvis-ui/src/features/console/MainConsole.tsx`
   - Separate text and voice actions
   - Add diagnostics strip and clearer state handling
   - Remove reply-surface races

2. `jarvis-ui/src/features/console/TopStatusBar.tsx`
   - Show active provider/model/voice state

3. Runtime settings components
   - Support inline provider/model/voice/knowledge-root edits

4. Right-side action approval UI
   - Show resolved target and stronger risk explanation

5. Reply/result surface
   - Show current phase and recoverable failures

6. `jarvis-ui/src/types/desktop.d.ts`
   - Match the preload-exposed API

### 7.3 Docs

1. `README.md`
   - Update environment-variable and runtime-setting behavior
   - Document the new user-configurable provider/model flow

2. Any docs referencing outdated defaults
   - Align with Aliyun/Kimi public-release reality

## 8. Testing Strategy

### 8.1 Required regression coverage

Add or update tests for:

1. Fresh preference/default voice behavior
2. Path traversal and workspace-boundary enforcement for file actions
3. Realtime error emission on speech failure
4. Audio buffer bounds and cleanup behavior
5. Text and voice interaction separation in the main console
6. Runtime settings display/update behavior
7. Summary output behavior

### 8.2 Verification gates

Before the work can be considered complete:

1. Backend pytest must pass
2. Frontend vitest must pass
3. Frontend build must pass
4. Electron tests must pass
5. Electron build must pass
6. No new static/type errors may remain
7. README must accurately describe the resulting product behavior

## 9. Implementation Sequence

The implementation should proceed in this order:

1. Add failing tests for the identified release bugs and UX regressions
2. Fix backend defaults, safety boundaries, and realtime stability
3. Fix frontend interaction semantics and diagnostics/recovery surfaces
4. Add inline provider/model/voice/knowledge-root controls
5. Upgrade summary behavior
6. Sync docs and type definitions
7. Re-run full verification on the public release clone

## 10. Success Criteria

This iteration is successful when:

1. A fresh user can understand current runtime status from the homepage without opening config files.
2. First voice use no longer silently fails because of mismatched defaults.
3. Voice failures are recoverable from the UI.
4. File-action approvals feel trustworthy because the true target is visible.
5. Text and voice no longer fight over the same reply area.
6. Model/provider settings are user-editable inside the product.
7. The cockpit-style homepage feels powerful without being misleading or chaotic.
