# Chat Request and Tool Call Trace Inspection Plan

> **Purpose:** Define a read-only debugging and analysis feature that lets the team inspect historical chat runs exactly as they were assembled for the model, and trace every tool invocation in those runs with complete execution detail. The goal is to understand prompt construction, tool-chain behavior, and failure causes without changing, retrying, or re-executing anything.

## Executive Summary

This feature introduces a historical inspection surface for chat runs. It is designed for developers and authorized power users who need to:

- inspect the exact request payload that reached the model
- inspect the full tool-call chain for the same run
- understand nested, chained, or repeated tool usage
- review failures without altering runtime behavior

The implementation is intentionally read-only. It captures and renders historical data, but does not provide any control surface for retries, re-execution, or mutation.

## Implementation Status

### Current status as of 2026-04-03

- PR 1 completed: trace schema baseline added and covered by backend tests.
- PR 2 completed: request snapshot capture added in a fail-open path.
- PR 3 completed: tool trace lifecycle capture added in a fail-open path.
- PR 4 completed: read-only summary endpoint added for request-and-trace bundles.
- PR 5 completed: raw mode API support and backend gating added.
- PR 6 completed: isolated frontend shell entry added without coupling to normal chat interactions.
- PR 7 completed: summary bundle fetching and basic read-only summary rendering added.
- PR 8 partially completed: richer summary rendering, raw-mode toggle, raw payload inspection, and a trace-tree view are implemented in the isolated drawer.
- PR 9 completed for backend and rollout wiring: default-hidden UI gating, config endpoint support, and rollout guardrails added.

### Known validation gap

- Backend tests for the implemented steps have been executed and are passing.
- Frontend tests and build have now been executed successfully using the Homebrew-installed Node runtime at `/opt/homebrew/bin/node`.
- The remaining gap is product-level validation and optional UX refinement rather than missing execution environment support.

## 1. Background

The current chat UI shows the conversation at the message level, but that is not enough for deep debugging. A single user request can fan out into:

- a final model-bound request payload
- multiple tool calls
- ReAct-style reasoning and action loops
- chained function calls where one tool output feeds the next call
- nested or delegated executions

When a run becomes complex, the most useful debugging question is not just "what did the user say?" but:

- What exact payload reached the model?
- What sequence of tool calls happened after that?
- Which tool produced which output?
- Where did the chain branch or fail?
- What did the runtime actually send and receive at each step?

This plan defines a read-only historical inspection feature that answers those questions with full traceability.

## 2. Goals

1. Allow developers or authorized power users to inspect historical chat runs.
2. Show the final request payload that was actually sent to the model.
3. Show every tool call in the run, in execution order, with full detail.
4. Preserve the causal relationship between request, tool call, and response.
5. Keep the feature strictly read-only.
6. Make the output useful for prompt analysis, tool-chain debugging, and regression diagnosis.

## 3. Non-Goals

1. This is not a tool execution console.
2. This must not modify, retry, re-run, or reissue any tool calls.
3. This is not a prompt editor.
4. This is not a general analytics warehouse.
5. This is not a redesign of the main chat experience.
6. This should not expose secrets or hidden prompts in default mode.

## 4. Current State

The codebase already has several pieces that are useful, but they are not yet assembled into a coherent read-only inspection workflow.

### Relevant backend entry points

- `backend/app/api/chat.py`
  - Receives chat stream requests
  - Resolves chat history, model settings, and runtime context
- `backend/app/api/chat_stream_runner.py`
  - Owns the runtime execution path
  - Is the best place to attach request and tool-call trace capture
- `backend/app/api/chat_tool_events.py`
  - Already sits near the tool event lifecycle
  - Can be extended to preserve detailed call records
- `backend/app/services/chat_runtime.py`
  - Already contains structured request/response logging helpers
- `backend/app/services/chat_prompting.py`
  - Reconstructs model history from chat messages
- `backend/app/services/chat_streaming.py`
  - Handles streaming state and event delivery

### Relevant frontend entry points

- `frontend/src/hooks/useChatState.ts`
  - Loads chats, messages, and historical events
- `frontend/src/hooks/chat/chatSubmission.ts`
  - Builds chat submission payloads
- `frontend/src/pages/Chat.tsx`
  - Main surface where the inspection view can be opened

### Important current behavior

- The backend already logs a sanitized request payload, but logging is not a usable inspection surface.
- The current UI can load chat history and some events, but not a full read-only trace bundle.
- History reconstruction may differ from the visible message list because the runtime applies token-budget and multimodal transforms.

## 5. Execution Principles

### 5.1 Small-step delivery

- Implement this feature in small, isolated increments.
- Each increment should touch the smallest possible surface area.
- Each increment should be independently reviewable and reversible.

### 5.2 Test-first safety gate

- Every increment must have a matching automated test plan before implementation starts.
- Every increment must include tests that validate the changed behavior.
- No increment is complete until the related tests pass.

### 5.3 Compatibility guardrails

- Do not break existing chat send, reply, stream, history, or replay flows.
- Keep the inspection surface additive and independent.
- If a change risks the default chat UX, split it into a smaller step.

### 5.4 Rollout discipline

- Prefer backend capture and API work before UI exposure.
- Prefer summary mode before raw mode.
- Prefer hidden or disabled-by-default surfaces before visible chat entry points.

## 6. Functional Requirements

### 6.1 Core capability

Add a feature that lets the user inspect a historical run after the fact.

The inspection view should include:

- the final request payload sent to the model
- the reconstructed message history used to build that request
- the final system prompt
- runtime metadata such as provider, model, agent, and skill state
- multimodal attachment summary
- timestamp and chat/session identifiers

### 6.2 Tool-call trace capability

Add a read-only trace view that shows every tool invocation in the order it occurred.

Each tool-call record should include:

- tool name
- tool type or adapter source
- call identifier
- parent call identifier or chain identifier when available
- exact input arguments
- exact output result
- lifecycle status
- start and end timestamps
- elapsed duration
- attempt index or chain depth if relevant
- error type and full error detail if the call failed
- linkage back to the assistant turn or reasoning step that triggered it

The trace should support:

- chronological timeline mode
- grouped chain mode
- nested expansion for call trees
- filtering by tool name, status, or run segment
- jumping between the request snapshot and the tool trace

### 6.3 Fidelity requirement

This feature is meant for full historical inspection. The raw trace view should preserve complete information instead of collapsing or omitting tool details.

If the deployment must apply policy-based protection, the default view can still present a safe summary, but the historical raw view should remain available in a strictly read-only debug mode.

### 6.4 UX behavior

- The feature should be accessible from the chat UI, preferably through a dedicated debug entry point, side drawer, or session action.
- The inspection UI must be an independent feature surface, mounted separately from the normal chat composition and message flow.
- The inspection UI must not change, block, or visually disrupt the existing chat send/reply/replay interactions.
- The inspection UI should load lazily so the normal chat experience stays fast and unaffected when the feature is not used.
- The view should default to the latest historical run for the selected chat.
- The user should be able to switch between:
  - a readable summary view
  - a structured JSON view
  - a full-fidelity raw trace view when permitted
- The inspection panel should clearly separate:
  - user-provided content
  - runtime-generated request content
  - tool execution history

### 6.5 Read-only behavior

- No retry button.
- No re-run button.
- No edit or patch action.
- No tool re-execution path.
- No mutation of chat history from the inspection surface.
- No coupling to the normal chat input state, send flow, or streaming lifecycle beyond read-only data fetching.

## 7. Scope

### Included

- Backend capture of the final request payload for each run.
- Backend capture of every tool invocation for that same run.
- A structured read-only endpoint for retrieving a request-and-trace bundle.
- Frontend UI for viewing the bundle.
- Detailed timeline and chain visualization for tool calls.
- Tests for capture integrity, API shape, and UI rendering.

### Excluded

- Cross-chat analytics dashboards
- Tool execution controls
- Execution control operations
- Persistent export pipelines
- A full observability warehouse
- Any redesign of the primary chat interaction model or message composition flow

## 8. Architecture and Delivery Plan

## 7.1 High-level design

The plan is to record two linked artifacts for each run:

1. a request snapshot, which represents the exact model-bound input
2. a tool-call trace, which represents the full causal execution path after the request entered the runtime

These artifacts should be linked by stable run and turn identifiers so the UI can move from the prompt to the tool chain and back again.

### Data flow

1. The frontend submits a normal chat request.
2. The backend resolves runtime state and assembles the final model input.
3. A request snapshot is recorded.
4. Tool calls emit trace events as they start, stream, finish, or fail.
5. The backend persists or indexes the trace records.
6. The frontend requests the historical bundle when the user opens the inspection panel.

### Read-only principle

The capture path is observational only. It must not alter tool behavior, timing semantics, or execution order.

## 7.2 Backend architecture

### Capture points

The main capture points are:

- request assembly in `backend/app/api/chat_stream_runner.py`
- tool lifecycle hooks in `backend/app/api/chat_tool_events.py`
- stream/event transport in `backend/app/services/chat_streaming.py`

### Storage strategy

There are two viable options:

1. **Persisted per-run trace store**
   - Best for historical debugging.
   - Supports inspection of old runs.
   - Requires schema and retention policy.

2. **Ephemeral indexed trace cache**
   - Simpler to add initially.
   - Good for recent runs.
   - Less suitable for long-term analysis.

### Recommended path

Use a persisted per-run store if the codebase already has a pattern for event-level runtime artifacts. Otherwise, start with an indexed trace cache and upgrade to persisted storage once the schema is stable.

## 7.3 Suggested data model

The inspection data should be structured rather than flattened into one log string.

### Suggested request snapshot fields

- `chat_id`
- `assistant_turn_id`
- `request_id`
- `created_at`
- `provider`
- `model`
- `agent_id`
- `requested_skill`
- `deep_thinking_enabled`
- `system_prompt`
- `user_message`
- `message_history`
- `attachments`
- `tool_context`
- `skill_context`
- `runtime_flags`
- `redaction`
- `truncation`

### Suggested tool-call record fields

- `chat_id`
- `run_id`
- `assistant_turn_id`
- `trace_id`
- `parent_trace_id`
- `tool_name`
- `tool_type`
- `call_index`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `input_arguments`
- `output_result`
- `error_type`
- `error_message`
- `error_stack`
- `chain_depth`
- `replayed_from_event_id`

### Suggested history item shape

Each reconstructed history item should preserve:

- role
- content type
- content summary
- image count or image metadata
- truncation state

## 7.4 Fidelity and safety rules

Because the request is for full historical inspection, the implementation should favor fidelity in the raw debug view.

### Default view

- safe summary
- redaction where needed
- clear labels for truncated sections

### Raw historical view

- complete tool inputs and outputs
- full error details
- full ordering information
- no re-execution, only display

### Annotate

For any redacted or policy-limited field, include:

- the reason it was hidden
- whether a raw debug mode exists
- the associated run and trace identifiers

## 7.5 API design

Add read-only endpoints for historical inspection.

### Candidate endpoints

- `GET /api/chat/{chat_id}/request-snapshot`
- `GET /api/chat/{chat_id}/last-request`
- `GET /api/chat/{chat_id}/payload`
- `GET /api/chat/{chat_id}/trace`
- `GET /api/chat/{chat_id}/trace/bundle`
- `GET /api/chat/{chat_id}/tool-calls`

### Recommended contract

Return a single structured object with:

- metadata
- request snapshot
- tool-call trace events
- ordered call chains
- request-to-tool linkage
- safety and redaction markers

### Response modes

Support at least two modes:

1. `summary`
   - compact
   - safe by default
2. `raw`
   - full-fidelity historical trace
   - read-only
   - gated by debug policy if required

## 7.6 Frontend design

### UI placement

Good placement options:

- a chat header action
- a debug drawer anchored on the right
- a session context menu action

The preferred implementation is a standalone inspection drawer or modal that is rendered outside the main chat message composition tree, so it can evolve independently without altering default chat interactions.

### UI content

The inspection view should render sections like:

- Request metadata
- User message
- Assembled history
- System prompt
- Tool execution timeline
- Nested tool chain view
- Runtime flags
- Redaction / truncation notes

### UI behavior

- Default to the latest historical run.
- Allow copy-to-clipboard for the structured payload or trace JSON.
- Make the distinction between request data and tool execution data obvious.
- Preserve the main chat flow and avoid interrupting generation.
- Keep all inspection state local to the inspection surface rather than mixing it into the core chat state machine.
- Treat the feature as an additive debug surface, not as a replacement for any existing chat controls.

## 9. Delivery Phases

## Phase 1: Trace contract definition

### Tasks

- Confirm the exact request assembly path in `backend/app/api/chat_stream_runner.py` and the tool lifecycle sources in `backend/app/api/chat_tool_events.py`.
- Define the request snapshot schema as a Pydantic model or typed schema in the backend service layer.
- Define the tool-call trace schema, including parent-child chain fields and stable identifiers.
- Mark which fields are safe for default summary mode and which fields require raw debug mode.
- Decide whether the first implementation stores historical data persistently or in an indexed cache.
- Map the initial endpoint contract and response shape before any UI work begins.
- Add backend unit tests for schema serialization and identifier stability.

### Suggested worker split

- Worker A owns the contract and schema design in `backend/app/api/chat_stream_runner.py`, `backend/app/api/chat_tool_events.py`, and any new backend schema module that is introduced.
- Worker B owns the test matrix and contract validation coverage, focused on schema serialization, identifier stability, and raw vs safe field classification.
- The two workers should not both edit the same endpoint implementation file until the contract is frozen.

### Deliverables

- A finalized request and trace schema.
- A documented endpoint contract.
- A list of raw vs safe fields.
- A file-level implementation map for backend and frontend work.
- Baseline tests for the new schema and contract.

## Phase 2: Backend capture

### Step 2.1: request snapshot capture

### Tasks

- Add request snapshot creation at the request assembly boundary in `backend/app/api/chat_stream_runner.py`.
- Keep capture fail-open so the chat stream continues even if inspection persistence fails.
- Add backend tests for snapshot presence, shape, and fail-open behavior.

### Suggested worker split

- Worker A owns the request snapshot capture path in `backend/app/api/chat_stream_runner.py`.
- Worker B owns the backend tests for snapshot presence, shape, and fail-open behavior, plus any supporting schema helpers.
- Worker B should not touch the main request assembly logic unless the test discovery proves a helper extraction is needed.

### Deliverables

- Request snapshot capture logic.
- Tests for snapshot capture and fail-open behavior.

### Step 2.2: tool trace event capture

### Tasks

- Extend `backend/app/api/chat_tool_events.py` so each tool lifecycle event emits a stable trace record.
- Persist or index the request snapshot together with the tool trace using shared `run_id` and `assistant_turn_id` values.
- Preserve parent-child and chain relationships for ReAct loops and tool chains.
- Add backend-side sanitization only for the safe summary mode; keep raw mode as a separate representation.
- Add backend tests for tool ordering, parent-child linkage, and chained tool records.

### Suggested worker split

- Worker A owns `backend/app/api/chat_tool_events.py` and the tool trace record emission path.
- Worker B owns the persistence/indexing layer and any trace storage schema updates.
- Worker C owns the backend tests for ordering, linkage, and chained tool records.
- Worker A and Worker B should align on the final trace schema before modifying shared storage code.

### Deliverables

- Tool trace event capture logic.
- Persisted or indexed trace records.
- Logging and error handling for capture failures.
- Backend tests for tool trace ordering and linkage.

## Phase 3: API exposure

### Step 3.1: summary endpoint

### Tasks

- Add a read-only endpoint for the request-and-trace bundle in `backend/app/api/chat.py` or a dedicated router if the surface grows too large.
- Expose summary mode first using explicit query parameters or a request DTO.
- Return both the request snapshot and the ordered tool trace in one bundle response.
- Validate missing-data handling and access constraints.
- Add API tests for schema shape, ordering, and fallback behavior in summary mode.

### Suggested worker split

- Worker A owns the API route in `backend/app/api/chat.py` or the dedicated router if one is introduced.
- Worker B owns the response DTOs and serialization helpers for the request-and-trace bundle.
- Worker C owns the summary-mode API tests and missing-data behavior tests.
- Workers should not split the same route handler unless the payload contract is already frozen.

### Deliverables

- Stable read-only summary endpoint.
- API documentation or inline schema docs.
- API tests covering summary mode.

### Step 3.2: raw mode and debug gating

### Tasks

- Add raw mode for full-fidelity historical trace output.
- Validate debug gating and access constraints for raw mode.
- Add API tests for raw mode, access constraints, and ordered trace fidelity.

### Suggested worker split

- Worker A owns the raw-mode response path and debug gating logic.
- Worker B owns the access-control and policy checks for raw data exposure.
- Worker C owns the raw-mode and ordered-trace API tests.
- Worker A and Worker B should coordinate on the exact raw payload shape before shipping.

### Deliverables

- Stable raw-mode API support.
- API tests covering summary and raw modes.

## Phase 4: Frontend inspection UI

### Step 4.1: isolated shell

### Tasks

- Add a UI control in `frontend/src/pages/Chat.tsx` to open the inspection panel or drawer.
- Render the inspection surface as a standalone component mounted outside the main chat composition tree.
- Keep all inspection state local to the inspection surface rather than mixing it into the core chat state machine.
- Add frontend tests that verify the shell opens without affecting existing chat interactions.

### Suggested worker split

- Worker A owns the shell entry point in `frontend/src/pages/Chat.tsx` and the open/close wiring.
- Worker B owns the standalone inspection container component and its local state boundary.
- Worker C owns the shell-level tests that prove the normal chat interaction model is unaffected.
- Worker A and Worker B should not both modify the same chat page branches unless the entry surface is already separated.

### Deliverables

- Standalone inspection shell.
- Frontend tests proving the main chat flow is unaffected.

### Step 4.2: read-only bundle rendering

### Tasks

- Fetch the historical request-and-trace bundle on demand from the new backend endpoint.
- Create a dedicated inspection component for the snapshot, tool timeline, and nested call tree.
- Render raw JSON and readable summary views without changing the main chat flow.
- Handle loading, empty, permission, and error states explicitly.
- Add frontend tests for rendering, selection, and expand/collapse behavior.
- Confirm that opening the panel does not alter chat streaming, message state, or compose input state.

### Suggested worker split

- Worker A owns the inspection content component for request snapshot rendering.
- Worker B owns the tool timeline and nested call-tree rendering.
- Worker C owns the frontend tests for rendering, loading states, and panel independence.
- Worker A and Worker B should keep their props contract stable so the shell remains additive.

### Deliverables

- Working read-only inspection drawer or panel.
- Clear visual distinction between request and tool trace data.
- Frontend tests for the inspection UI.

## Phase 5: Hardening and rollout

### Step 5.1: safety regression checks

### Tasks

- Add redaction regression tests for secret-like values and oversized payloads.
- Validate that raw mode remains read-only and never exposes an action surface.
- Measure performance impact on long tool chains and high-event runs.
- Add feature flags or debug-mode gating if needed in the existing configuration layer.
- Verify that the default chat path still behaves exactly as before after the feature is enabled.

### Suggested worker split

- Worker A owns redaction and payload-safety regression tests.
- Worker B owns feature-flag wiring and any fallback/disablement behavior.
- Worker C owns the compatibility verification tests that prove the default chat path remains unchanged.
- Workers should not expand the scope beyond defensive checks and rollout controls.

### Deliverables

- Regression test coverage for redaction and safety.
- Verified compatibility with existing chat behavior.

### Step 5.2: rollout and fallback

### Tasks

- Add a rollout note and a rollback switch so the feature can be disabled safely.
- Confirm the feature can remain disabled without affecting existing functionality.

### Deliverables

- Safe default behavior.
- Release checklist.
- Rollback or disablement plan.
- Final documentation updates in the plan and index.
- Compatibility confirmation for the normal chat flow.

## 10. Dependencies

- `backend/app/api/chat_stream_runner.py`
- `backend/app/api/chat_tool_events.py`
- `backend/app/services/chat_prompting.py`
- `backend/app/services/chat_runtime.py`
- `backend/app/services/chat_streaming.py`
- `frontend/src/hooks/useChatState.ts`
- `frontend/src/pages/Chat.tsx`

Potential secondary dependency:

- A trace storage decision if historical tool-call data needs to be queried independently of the chat snapshot

## 11. Recommended PR Sequence

The implementation should land as a sequence of small PRs. Each PR should be independently testable and safe to revert.

### PR 1: contract and schema baseline

- Scope:
  - request snapshot schema
  - tool trace schema
  - raw vs safe field classification
  - baseline backend tests for schema serialization and stable identifiers
- Preferred files:
  - `backend/app/api/chat_stream_runner.py`
  - `backend/app/api/chat_tool_events.py`
  - a new schema/helper module if needed
  - new backend tests for schema validation
- Gate:
  - no UI changes
  - no route changes
  - tests must pass before moving to PR 2
- Status:
  - completed

### PR 2: request snapshot capture only

- Scope:
  - capture the final request snapshot at the request assembly boundary
  - fail-open behavior
  - backend tests for snapshot capture
- Preferred files:
  - `backend/app/api/chat_stream_runner.py`
  - any new storage/helper module for snapshot persistence
  - backend tests for snapshot behavior
- Gate:
  - no tool trace changes yet
  - no frontend changes yet
  - existing chat stream behavior must remain unchanged
- Status:
  - completed

### PR 3: tool trace capture only

- Scope:
  - emit tool lifecycle trace records
  - persist/index ordered tool trace records
  - backend tests for ordering and linkage
- Preferred files:
  - `backend/app/api/chat_tool_events.py`
  - storage/indexing files used by trace persistence
  - backend tests for tool trace capture
- Gate:
  - request snapshot behavior from PR 2 must stay green
  - no UI exposure yet
- Status:
  - completed

### PR 4: read-only summary endpoint

- Scope:
  - add a summary-mode request-and-trace bundle endpoint
  - add API tests for schema, ordering, and missing-data handling
- Preferred files:
  - `backend/app/api/chat.py` or a dedicated router
  - response DTO helpers
  - API tests
- Gate:
  - summary mode only
  - raw mode deferred to next PR
  - no frontend visible surface yet unless needed for local verification
- Status:
  - completed

### PR 5: raw mode and debug gating

- Scope:
  - add raw mode
  - enforce debug gating or policy controls
  - add raw mode API tests
- Preferred files:
  - API route layer
  - policy/config wiring
  - API tests
- Gate:
  - safe summary mode remains default
  - raw mode remains read-only
- Status:
  - completed

### PR 6: isolated frontend shell

- Scope:
  - add the standalone inspection entry point and shell
  - keep it mounted outside the main chat composition tree
  - add shell-level frontend tests
- Preferred files:
  - `frontend/src/pages/Chat.tsx`
  - new inspection shell component files
  - frontend tests for shell isolation
- Gate:
  - no trace rendering complexity yet
  - opening the shell must not alter chat input or streaming behavior
- Status:
  - completed in code
  - frontend automated verification completed

### PR 7: summary rendering in the inspection UI

- Scope:
  - fetch summary endpoint on demand
  - render request snapshot and basic tool trace summary
  - add frontend tests for render, loading, and error states
- Preferred files:
  - new inspection UI components
  - frontend tests
- Gate:
  - raw mode rendering deferred
  - main chat flow unchanged
- Status:
  - completed in code
  - frontend automated verification completed

### PR 8: raw trace rendering

- Scope:
  - render raw JSON and nested tool timeline/tree views
  - add frontend tests for expansion, selection, and raw mode behavior
- Preferred files:
  - inspection content components
  - frontend tests
- Gate:
  - no action controls
  - raw mode must remain read-only
- Status:
  - partially completed
  - richer summary rendering, history, attachments, field policies, and hardening are implemented
  - raw-mode toggle and raw payload inspection are implemented behind existing gating
  - trace tree / parent-child inspection is implemented as a read-only tree view
  - frontend automated verification completed

### PR 9: hardening and rollout controls

- Scope:
  - feature flags
  - redaction regression tests
  - compatibility verification
  - rollout/disablement documentation
- Preferred files:
  - config wiring
  - tests
  - docs
- Gate:
  - existing chat path must be verified unchanged
  - feature must remain safely disableable
- Status:
  - backend rollout controls completed
  - frontend entry is now gated behind `chat_trace_ui_enabled` and defaults to hidden
  - backend automated verification completed
  - frontend automated verification completed

## 12. File Ownership Recommendation

Use disjoint ownership wherever possible so multiple workers can move in parallel without merge churn.

### Backend ownership

- Worker A:
  - `backend/app/api/chat_stream_runner.py`
  - request snapshot contract and capture path
- Worker B:
  - `backend/app/api/chat_tool_events.py`
  - tool trace lifecycle emission
- Worker C:
  - trace storage/indexing modules
  - response DTO helpers
- Worker D:
  - backend tests and API tests for the new trace feature

### Frontend ownership

- Worker E:
  - `frontend/src/pages/Chat.tsx`
  - shell entry point and mounting boundary
- Worker F:
  - inspection shell/container components
  - request snapshot rendering components
- Worker G:
  - tool timeline and nested call-tree rendering components
- Worker H:
  - frontend unit tests and UI regression checks

### Shared coordination rule

- No two workers should edit the same route handler or page entrypoint in parallel unless the interface contract is already frozen.
- Shared payload types should be frozen before frontend and backend proceed independently.
- Test workers should prefer adding coverage around stable contracts rather than racing ahead of schema changes.

## 13. Test Commands by Step

Use focused tests first, then widen to regression checks before merging.

### Backend step commands

- Contract/schema baseline:
  - `cd backend && PYTHONPATH=$(pwd) pytest tests -k "chat or tool_events or trace" -q`
- Request snapshot capture:
  - `cd backend && PYTHONPATH=$(pwd) pytest tests -k "snapshot or chat_stream_runner" -q`
- Tool trace capture:
  - `cd backend && PYTHONPATH=$(pwd) pytest tests -k "tool_events or tool_trace or registry" -q`
- Summary/raw API endpoint:
  - `cd backend && PYTHONPATH=$(pwd) pytest tests -k "api_chat and (trace or snapshot or raw)" -q`

### Frontend step commands

- Isolated shell:
  - `cd frontend && npm run test -- Chat`
- Summary rendering:
  - `cd frontend && npm run test -- useChatState MessageList Chat`
- Raw trace rendering:
  - `cd frontend && npm run test -- Chat useChatState`

### Cross-feature regression commands

- Backend regression sweep:
  - `cd backend && PYTHONPATH=$(pwd) pytest tests/test_api_chat_unit.py tests/test_chat_service_unit.py -q`
- Frontend regression sweep:
  - `cd frontend && npm run test -- src/hooks/useChatState.multimodal.test.ts src/hooks/useChatState.events.test.ts`
- Build verification:
  - `cd frontend && npm run build`

### Optional end-to-end validation

- If a UI workflow test is added for this feature:
  - `cd frontend && npx playwright test`
- If no dedicated E2E exists yet, keep E2E optional until the summary UI stabilizes.

Current E2E coverage added during implementation:

- `frontend/e2e/trace-inspector-smoke.spec.ts`
  - verifies seeded summary-mode rendering
  - verifies raw-mode toggle and gated raw payload rendering
  - verifies trace-tree rendering inside the independent drawer

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Exposing internal prompts or hidden runtime logic | High | Keep safe summary mode as default and gate raw historical view if required. |
| Exposing sensitive tool inputs or outputs | High | Redact by default and restrict raw mode to authorized debug contexts. |
| Breaking the chat request path | High | Make capture fail-open and non-blocking. |
| Trace records become too large | Medium | Use structured storage, indexed retrieval, and optional summary mode. |
| Tool chain becomes hard to read | Medium | Use timeline and tree views with stable parent-child identifiers. |
| Historical ambiguity across multiple runs | Medium | Include run IDs, turn IDs, timestamps, and trace IDs. |

## 15. Acceptance Criteria

- [x] A historical chat run can be inspected from the UI.
- [x] The final model-bound request is visible.
- [x] Every tool call in the run is visible in execution order.
- [ ] Each tool record includes name, inputs, outputs, timestamps, duration, and error details.
- [x] The trace view distinguishes nested or chained tool calls.
- [x] The feature is read-only and cannot modify or trigger tool actions.
- [x] Default mode is safe, and raw mode is explicitly controlled.
- [x] The inspection surface is independent and does not affect the normal chat interaction model.
- [x] Each increment has automated backend tests before it is considered complete.
- [x] Automated tests cover backend capture, API shape, and frontend rendering.
- [x] Each PR in the sequence can be merged and, if needed, reverted independently.

### Acceptance notes

- Summary-mode request inspection and ordered tool-trace inspection are implemented.
- Raw-mode UI inspection and a basic trace-tree view are implemented behind existing flags.
- Backend capture, API shape, and rollout controls have automated coverage.
- Frontend tests and build verification have been executed successfully in the current environment.
- Playwright smoke validation has been executed successfully against a seeded trace-inspection chat.
- Rollback validation has been executed successfully by disabling the trace flags and verifying both UI hide behavior and backend raw-mode denial.

## 16. Testing Plan

### Backend tests

- Verify the request snapshot stores the expected fields.
- Verify tool events are captured in order and linked to the correct run.
- Verify parent-child relationships are preserved for nested or chained calls.
- Verify the request path still streams successfully if trace capture fails.
- Verify each backend change is covered by focused unit or integration tests.
- Verify existing chat streaming and history endpoints continue to work unchanged.

### API tests

- Verify the snapshot endpoint returns a valid schema.
- Verify the trace endpoint returns ordered tool events and stable identifiers.
- Verify summary and raw modes behave as expected.
- Verify missing data is handled gracefully.
- Verify summary mode and raw mode are separately covered by tests.

### Frontend tests

- Verify the inspection panel opens and fetches the bundle.
- Verify request and trace sections render correctly.
- Verify nested call trees render correctly.
- Verify loading, empty, and error states.
- Verify the normal chat compose/send/stream flow remains unchanged when the inspection UI is unused.

### Manual validation

- Compare the trace view against a known complex run with multiple tool calls.
- Confirm the raw historical view preserves the full tool chain.
- Confirm the UI remains read-only.

## 17. Documentation Updates

- [x] Add an entry in `docs/plans/README.md` or `docs/plans/INDEX.md` if this becomes an active epic.
- [ ] Update chat developer docs when the endpoint is implemented.
- [x] Document safe mode, raw mode, and read-only behavior for operators.
- [x] Add an operator-facing release checklist for rollout and rollback.

## 20. Operator Enablement Note

The feature is now designed to remain invisible by default in normal chat usage.

- `chat_trace_ui_enabled`
  - default: `false`
  - purpose: controls whether the Trace Inspector entry point and drawer are exposed in the chat UI
- `chat_trace_raw_enabled`
  - default: `false`
  - purpose: controls whether raw trace bundle access is available from the backend API

Recommended rollout order:

1. Enable backend capture and summary endpoint in a non-production or internal environment.
2. Turn on `chat_trace_ui_enabled` only for internal validation environments first.
3. Keep `chat_trace_raw_enabled` disabled unless an authorized debug workflow explicitly requires it.
4. After frontend test/build verification is complete, promote the UI flag more broadly if needed.

Rollback guidance:

- Turn off `chat_trace_ui_enabled` to remove the UI entry point without affecting the normal chat path.
- Turn off `chat_trace_raw_enabled` to disable raw trace access while preserving safe summary mode.
- Because the feature is additive and read-only, disabling the flags should not affect normal send, stream, or history behavior.

Related operator checklist:

- `docs/plans/2026-04-03-chat-trace-inspection-release-checklist.md`

## 18. Recommended Definition of Done

This feature should be considered done when:

1. A historical run can be inspected from the chat UI.
2. The request snapshot reflects the actual assembled model input.
3. The tool trace shows the complete call chain for the run.
4. The raw historical view is read-only and does not allow retries or edits.
5. Sensitive content is protected by default.
6. The output is useful for prompt analysis and tool-chain debugging.

## 19. Implementation Notes

- Treat this as a trace viewer, not a control panel.
- Keep the core chat stream contract unchanged.
- Favor stable run and trace identifiers so historical runs can be followed end to end.
- Preserve full-fidelity information in raw historical mode, and keep the safe summary as the default surface.
- Make every change small enough to test independently before the next step begins.
