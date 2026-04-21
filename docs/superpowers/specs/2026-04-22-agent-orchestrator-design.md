# Unified Agent Orchestrator Design

**Date:** 2026-04-22  
**Project:** `D:\Jarvis`  
**Status:** Draft approved in conversation, written for review

---

## 1. Problem Statement

Jarvis has already grown a partial agent skeleton, but its core control path is still split:

1. `wakeword_service.py` still performs regex-based semantic interpretation and can directly infer actions such as delete/search from raw text.
2. `kimi_client.py` is still a transport-oriented chat client, not a provider abstraction with tool-calling support.
3. `agent_loop.py` exists and can run a ReAct-style loop, but it does not yet own all entrypoints.
4. `memory_service.py` mostly stores events and snapshots, not structured user/project knowledge.
5. Safety policy is not yet centralized enough to guarantee that all high-risk actions go through one confirmation gate.

This makes Jarvis feel inconsistent: part assistant, part agent, part rules engine. The first-stage design goal is to establish **one brain, one tool runtime, one safety gate** across text, voice, and legacy assistant APIs.

---

## 2. Goals

### 2.1 Primary goals

1. Replace regex-driven semantic decision-making with a unified agent orchestration layer.
2. Route **all** major entrypoints through the same orchestration path:
   - chat
   - realtime voice
   - legacy assistant APIs
3. Support dual tool-calling protocols:
   - provider-native `tools` / function calling when available
   - `<tool_call>...</tool_call>` text protocol as fallback
4. Centralize risk policy so the model can propose actions, but cannot bypass execution safeguards.
5. Upgrade memory from flat event storage toward structured, graph-friendly memory primitives.

### 2.2 Non-goals for this phase

1. Do not introduce LangGraph or AutoGen in this phase.
2. Do not implement a full knowledge graph engine yet.
3. Do not implement continuous Recall-style screen capture yet.
4. Do not implement contextual TTS prosody tags yet.

This phase is the foundation that later phases will build on.

---

## 3. Current-State Findings

### 3.1 Confirmed issues

- `wakeword_service.py` currently contains regex and keyword logic that can interpret user intent too early.
- `assistant.py` still has direct action/search/summary/task paths that bypass a unified orchestration model.
- `memory_service.py` is mostly a persistence helper, not a semantic memory pipeline.

### 3.2 Existing assets worth keeping

- `agent_loop.py` already provides a functioning ReAct-style loop.
- `agent_tools.py` already provides a tool catalog and execution path.
- `local_recall_service.py` already provides a practical local BM25 recall layer.
- trace events already exist conceptually and can be evolved into a more structured observability layer.

The design should therefore **refactor toward a unified agent core**, not replace the project with a new framework.

---

## 4. Target Architecture

Jarvis will be reorganized into five logical layers.

### 4.1 Perception Layer

**Responsibilities**

- wake word detection
- hotkey awareness
- ASR transcript normalization
- terminology/path correction
- low-level input sanitation

**Explicit non-responsibilities**

- no action selection
- no workspace routing
- no delete/search/summary intent inference

`wakeword_service` should become a thin normalization helper. `wakeword_local_service` remains a low-level detector. Semantic interpretation is removed from this layer.

### 4.2 Agent Orchestrator Layer

This is the new single “brain” of the system.

**Responsibilities**

- build model context
- attach tool catalog
- run ReAct loop
- manage iteration limits and timeouts
- collect trace data
- emit structured outputs
- decide whether the result is:
  - `final_answer`
  - `proposal`
  - `tool_trace`
  - `error`

All text, voice, and legacy assistant entrypoints should delegate here.

### 4.3 Provider Adapter Layer

This layer abstracts model providers.

**Responsibilities**

- hide provider-specific API shape
- expose a common completion interface
- expose provider capability flags, especially native tool-calling support
- translate between internal tool definitions and provider-native JSON schema

This prevents upper layers from depending directly on Kimi, DeepSeek, or OpenAI request formats.

### 4.4 Tool Runtime Layer

This layer owns execution.

**Responsibilities**

- tool registration
- tool metadata
- risk classification
- proposal generation
- confirmation gating
- execution auditing

The model may request a tool call, but Tool Runtime and Risk Gate decide whether it executes immediately, emits a proposal, or is rejected.

### 4.5 Memory Pipeline Layer

This layer evolves memory from flat storage toward structured recall.

**Responsibilities**

- persist raw interaction events
- extract stable entities and preferences
- maintain user/project profile state
- serve recall queries

This phase does not require a full graph engine, but it must define stable interfaces that can support one later.

---

## 5. Entry Point Unification

All major user-facing paths should delegate to the same orchestrator.

### 5.1 Chat

`chat_service.py` remains an HTTP-facing entrypoint but becomes a thin wrapper around the orchestrator.

### 5.2 Realtime voice

`realtime.py` should:

1. receive audio
2. perform ASR
3. run wakeword detection / normalization
4. pass normalized user text into the orchestrator
5. stream back structured results, including answer text, trace, and proposals

It must not use a parallel intent engine.

### 5.3 Legacy assistant APIs

Existing endpoints such as interpret, actions, search, and summary may remain for compatibility, but internally they must delegate into the new orchestration or tool runtime path rather than preserving separate decision logic.

This means old URLs may survive, but old brains do not.

---

## 6. Unified Request Lifecycle

Every request should follow the same lifecycle:

1. **Input arrives**  
   From chat, voice transcript, or legacy adapter.

2. **Perception normalization**  
   Normalize wakeword artifacts, path terminology, technical terms, and hotkey context.

3. **Context assembly**  
   Gather:
   - system prompt
   - teacher style / preferences
   - recent conversation history
   - relevant uploads
   - local recall results
   - workspace/session state

4. **Model call via Provider Adapter**  
   Use native tools if supported; otherwise use text protocol fallback.

5. **Tool resolution**  
   If the model calls tools:
   - pass calls to Tool Runtime
   - enforce Risk Gate
   - execute safe tools
   - emit proposals for higher-risk actions
   - append tool results back into the loop

6. **Termination**  
   Stop when:
   - a final answer is produced
   - a proposal is emitted
   - loop limit is reached
   - timeout is reached
   - repeated-call guard is triggered

7. **Structured output**  
   Emit only one of:
   - `final_answer`
   - `proposal`
   - `error`
   plus optional `tool_trace`

This unified lifecycle is what turns Jarvis from a one-shot chat shell into a real multi-step agent.

---

## 7. Tool-Calling Protocol Strategy

Jarvis should support **dual protocol tool calling**.

### 7.1 Preferred path: provider-native tools

If the current provider supports native function calling:

- convert internal tool metadata into JSON schema
- send tools to the provider
- read structured tool requests from provider responses

### 7.2 Fallback path: text protocol

If the provider does not support native tools:

- continue using the current `<tool_call>{...}</tool_call>` convention
- parse tool requests from assistant output
- feed `<tool_result>...</tool_result>` back into the loop

### 7.3 Design rule

The orchestrator must depend only on an internal abstraction such as:

- `model_response.text`
- `model_response.tool_calls`
- `provider_capabilities.supports_native_tools`

No upper layer should know whether the model spoke native tool JSON or fallback text tags.

---

## 8. Risk Gate and Safety Model

Safety policy must live in the execution layer, not in the model prompt alone.

### 8.1 Tool metadata

Each tool must declare at least:

- `risk_level`
- `needs_confirmation`
- `side_effect_scope`
- `idempotent`

### 8.2 Risk categories

#### Safe

Examples:

- local recall
- upload listing
- memory recall
- read-only file inspection
- screenshot capture

These may execute directly.

#### Cautious

Examples:

- open URL
- launch app
- visual click proposal

These should usually emit a proposal before execution.

#### Dangerous

Examples:

- delete file
- overwrite file
- run shell command
- lock workstation
- sleep system
- browser/system control with side effects

These must go through a hard confirmation flow.

### 8.3 Audit chain

High-risk operations must always generate structured audit events:

1. `tool_requested`
2. `proposal_emitted`
3. `user_confirmed`
4. `execution_result`

This requirement applies regardless of entrypoint.

---

## 9. Memory Upgrade Path

This phase does not implement a full knowledge graph, but it does define graph-friendly memory contracts.

### 9.1 Memory primitives

The memory layer should expose three main capability groups:

1. `remember_event(...)`
2. `extract_entities(...)`
3. `recall(query, scope)`

### 9.2 Data classes

The system should move toward storing:

- **raw events**: immutable evidence
- **entities**: person, project, tool, path, preference, task, issue
- **relations**: user-works-on-project, user-prefers-tool, issue-affects-project
- **profile state**: stable user preferences and environment facts

### 9.3 First-phase extraction scope

The first phase should extract only high-value stable facts such as:

- user style preferences
- preferred model/provider
- primary project and workspace
- recently active tasks
- recurring directories, tools, or technologies

This keeps implementation pragmatic while making future graph expansion straightforward.

---

## 10. Error Handling and Observability

### 10.1 Error handling

The orchestrator should own these failure modes:

- provider timeout
- 429/rate limit
- malformed provider tool output
- unknown tool
- tool execution failure
- empty model response
- infinite or repetitive tool loops

Each should produce a structured `error` or `tool_error` event rather than ad hoc route-specific handling.

### 10.2 Repetition guard

The orchestrator must detect repeated calls such as:

- same tool
- same normalized arguments
- same result pattern

When repetition exceeds threshold, the loop should terminate and force a final answer or a visible failure.

### 10.3 Observability

Each agent request should record:

- entrypoint
- session id
- provider/model
- iteration count
- tool trace
- total latency
- termination reason

The frontend should read these as structured fields rather than parsing text blobs.

This also enables proactive and telemetry systems to consume agent behavior later.

---

## 11. Testing Strategy

The implementation plan derived from this spec must cover at least these test groups.

### 11.1 Orchestrator tests

- direct-answer completion
- native tool-calling path
- text fallback tool-calling path
- loop termination on max iterations
- loop termination on repetition guard

### 11.2 Entry consistency tests

- chat calls orchestrator
- realtime calls orchestrator
- assistant compatibility endpoints call orchestrator or tool runtime

### 11.3 Safety tests

- safe tool executes directly
- cautious tool emits proposal
- dangerous tool cannot execute without confirmation
- audit chain is written for dangerous tool execution

### 11.4 Memory tests

- event persistence
- entity extraction writes structured data
- recall still returns useful results after schema upgrade

### 11.5 Regression tests

- existing agent loop behavior remains valid under fallback mode
- existing UI trace rendering still receives compatible data

---

## 12. Acceptance Criteria

The phase is complete only when all of the following are true:

1. `wakeword_service` no longer performs regex-based semantic action selection as the primary path.
2. `chat`, `realtime`, and legacy assistant entrypoints all route through one orchestrator path.
3. `kimi_client.py` (or its replacement transport) no longer contains agent orchestration responsibilities.
4. Native tools and fallback text tool-calling are both supported behind one provider abstraction.
5. All dangerous tools require proposal/confirmation/execution flow.
6. Structured trace and termination reason are exposed consistently.
7. Memory is upgraded to store structured events and extracted facts, not only flat historical text.

---

## 13. Recommended Implementation Order

The implementation plan should execute in this order:

1. Provider Adapter abstraction
2. Agent Orchestrator extraction
3. chat/realtime/assistant entrypoint unification
4. Risk Gate centralization
5. wakeword semantic logic removal
6. structured memory pipeline introduction
7. observability and regression cleanup

This order minimizes breakage because it moves the brain first, then rewires callers, then upgrades memory.

---

## 14. Future Extensions Enabled by This Design

Once this phase is complete, the following become materially easier:

1. background worker agents
2. LangGraph-style durable workflows
3. Recall-style continuous perception
4. knowledge-graph reasoning
5. urgency-aware TTS prosody

Those should be separate specs, not squeezed into this one.
