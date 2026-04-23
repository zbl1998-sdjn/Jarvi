# Jarvis Release Stability Enhancements Design

Date: 2026-04-24
Repo: `jarvis-public-release`
Status: Draft approved in conversation, written for implementation planning

## 1. Problem Statement

The public release is already buildable, testable, and much more coherent than the first snapshot, but the real-folder acceptance run exposed three remaining experience gaps:

1. A stale Jarvis process on port `8001` can make a fresh launch look successful while the UI is actually connected to the wrong backend.
2. `/api/summary` still collapses provider/auth/timeout failures into a generic server error, which gives users no clear next step.
3. Knowledge search only scans Markdown files and returns a very small result set, which under-serves real study folders that contain mixed documentation and source files.

This iteration should close those gaps without expanding into a broader rewrite. The goal is to make the public release more trustworthy, more diagnosable, and more useful against real learning material.

## 2. Goals

This iteration must:

1. Block startup when the configured backend port is already occupied by a different or unidentifiable Jarvis instance.
2. Make summary failures return structured, user-actionable HTTP errors instead of a generic `500`.
3. Extend knowledge search to support `.md`, `.txt`, `.py`, `.json`, `.yaml`, and `.yml`.
4. Raise or centralize the search result cap so the product surfaces more than a tiny slice of valid matches.
5. Preserve the existing Electron + React + FastAPI structure and current successful response shapes where practical.

## 3. Non-Goals

This iteration does not:

1. Introduce automatic port hopping or silent fallback to a different server port.
2. Redesign the whole app shell, cockpit layout, or action workflow.
3. Add a full indexing engine, vector retrieval layer, or advanced ranking system.
4. Unify all backend error handling under one cross-product protocol.
5. Expand the search feature into binary/document parsers such as PDF or Office formats.

## 4. Chosen Product Direction

The chosen direction is a restrained stability pass:

1. Detect backend-port conflicts early and fail loudly instead of connecting to an ambiguous instance.
2. Keep summary generation in the existing service path, but translate upstream failures into explicit `502` or `503` responses with actionable metadata.
3. Expand file-based search just enough to cover common study and code text formats while keeping the current local scan model.

This direction matches the user request for a balanced implementation: complete enough to remove real friction, but small enough to preserve the current stable release baseline.

## 5. User Experience Design

### 5.1 Port conflict behavior

When the app starts, users should no longer have to infer whether the visible UI is talking to the expected backend:

1. If the target port is free, startup proceeds normally.
2. If the target port is occupied by the current expected instance, startup may continue.
3. If the port is occupied by an old instance, an unknown Jarvis instance, or an unidentifiable service, startup is blocked.
4. The user-facing message must explain:
   - which port is affected
   - that an existing service is already running there
   - what action to take next (for example: close the old process or change the port intentionally)

The important UX change is not a visual redesign; it is removing silent ambiguity.

### 5.2 Summary failure UX

Summary failures must become understandable and actionable:

1. Invalid or missing model credentials should be presented as a configuration problem.
2. Provider timeouts or temporary upstream outages should be presented as a service-availability problem.
3. The frontend should show a short readable message first and expose a concrete hint for what the user should do next.

This keeps the summary surface honest: if the provider is broken, the user sees why instead of assuming the feature is randomly unreliable.

### 5.3 Search UX

Knowledge search should better match real study folders:

1. Common text and code files should be searchable alongside Markdown.
2. The result cap should be high enough to make the feature feel useful on non-trivial folders.
3. Search behavior should remain predictable: filename match and text containment remain the primary discovery rules.
4. `auto` search should keep its current bias toward local and knowledge results before falling back to web results.

This improves relevance without making the search feature feel materially different or harder to reason about.

## 6. Technical Design

### 6.1 Port conflict detection

Port conflict handling should live at the startup boundary rather than deep inside runtime request handling:

1. The startup path should probe the configured backend address before launching or attaching.
2. If the port is in use, the app should attempt to identify the responding service through an existing health or instance-identifying endpoint.
3. If the responder cannot be identified as the expected current release instance, startup should fail explicitly.
4. The failure should propagate through the current desktop/dev startup flow so the user sees a deterministic error instead of an apparently working window connected to stale state.

This avoids adding background heuristics later in the app where recovery would be noisier and less trustworthy.

### 6.2 Structured summary errors

`SummaryService` should remain focused on generating summaries, while route-level code is responsible for translating provider failures into stable HTTP semantics:

1. Authentication and configuration failures map to `502`.
2. Timeouts and temporary upstream unavailability map to `503`.
3. The response payload should include:
   - `code`
   - `message`
   - `hint`
   - `retryable`
4. Successful summary responses should keep their current shape so existing consumers do not need unrelated changes.

This keeps failure mapping explicit without turning this iteration into a full error-protocol migration.

### 6.3 Broader file search

`SearchService` should remain the owner of local and knowledge-root scanning:

1. Allowed text extensions should move into a clearly named constant or small configuration block.
2. Maximum returned results should also be centralized as an explicit constant.
3. The scan should continue to skip unreadable or non-UTF-8 files rather than failing the whole search.
4. The matching model remains simple:
   - path name contains query, or
   - file content contains query

The design deliberately avoids full-text indexing or fuzzy ranking because this iteration is about widening coverage, not replacing the search model.

## 7. Component-Level Changes

### 7.1 Electron and startup scripts

Expected change areas:

1. `electron\preload.ts`
   - Continue exposing the effective backend base URL
   - Optionally surface instance-aware startup information if needed by the current flow

2. `package.json` / `scripts\dev-server.ps1` / related startup utilities
   - Add the port-conflict probe at the point where the backend is launched or attached
   - Ensure failures stop startup rather than printing an ignorable warning

3. Electron startup tests
   - Cover free-port and blocked-port behavior

### 7.2 Backend

Expected change areas:

1. `jarvis-server\app\routers\assistant.py`
   - Translate summary-provider failures into structured HTTP errors

2. `jarvis-server\app\services\summary_service.py`
   - Preserve current useful summary behavior
   - Avoid swallowing provider-level failures that the router now needs to classify

3. `jarvis-server\app\services\search_service.py`
   - Expand supported extensions
   - Centralize result caps
   - Keep `auto` semantics stable

4. Related backend tests
   - Cover structured summary error mapping
   - Cover new search file types and result-limit behavior

### 7.3 Frontend

Expected change areas:

1. `jarvis-ui\src\app\api\assistant-client.ts`
   - Parse and preserve structured summary error payloads

2. Current summary-consuming UI surfaces
   - Show readable message + hint
   - Avoid collapsing everything into a generic failure string

3. Frontend tests
   - Cover structured summary failure rendering

## 8. Error Handling and Compatibility Rules

1. Existing successful API responses should remain backward compatible.
2. New behavior is concentrated in failure semantics and search coverage, not in broad API redesign.
3. Port conflict detection must fail closed rather than guessing.
4. Search should skip unreadable files quietly, but should not silently narrow the supported-extension set back to Markdown only.
5. Summary failures should remain explicit enough that logs and user messages describe the same category of problem.

## 9. Testing Strategy

This iteration requires focused regression coverage:

1. Startup-path tests for port conflict handling.
2. Backend API tests for summary auth/config failures, timeout failures, and generic upstream failures.
3. Backend search tests for `.md`, `.txt`, `.py`, `.json`, `.yaml`, and `.yml`.
4. Search result-limit tests so the higher cap remains intentional and stable.
5. Frontend tests for rendering structured summary failures as actionable guidance.

The test goal is confidence in the new boundaries, not a new end-to-end harness.

## 10. Documentation Changes

`README.md` should be updated to reflect:

1. startup behavior when the configured backend port is already occupied
2. the supported knowledge-search file types
3. the fact that summary failures now distinguish configuration/auth problems from temporary provider failures

## 11. Implementation Boundary

This spec is small enough for a single implementation plan and execution pass. The work should be implemented as one bounded release-hardening iteration, not decomposed into a larger product roadmap.
