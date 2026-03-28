# Yue Skill Package Contract Handoff

Last updated: 2026-03-28
Scope: package-first skill system, compatibility-first incremental migration
Primary owner context: backend skill package contract, action runtime contract, chat runtime integration

## 0. Boundary Decision

Yue's current skill boundary is now explicit:

- skills may package prompts, references, templates, overlays, and action/workflow metadata
- skills may orchestrate only Yue's already-available built-in tools and MCP tools
- skills may use existing platform tools, including `builtin:exec`, when those tools are explicitly exposed and authorized by Yue
- Yue should not add a skill-owned script runner or any execution surface outside the platform tool boundary

## 1. Executive Summary

This workstream is moving Yue from a prompt-time skill system toward a package-first skill system without breaking the current chat runtime, skill routing, prompt injection, or public API behavior.

The current state is:

- Package-level skill modeling is in place.
- Package parsing and registry loading are package-aware.
- Legacy flat markdown skills remain supported.
- Provider/model overlays are wired into runtime skill resolution.
- Package actions are modeled, validated, registered, exposed to runtime, and integrated into a platform-tool lifecycle.
- Chat runtime can explicitly drive action preflight, approval, and stub execution transitions.
- `skill.action.*` events stream through SSE, pass the contract gate, persist to chat storage, replay correctly, and now also maintain direct `action_states`.
- Backend now exposes direct action-state lookup/list APIs, including approval-token lookup.
- Frontend now consumes `action_states` directly and shows a minimal action lifecycle view in the chat intelligence panel.
- Requested-action flow can now hand off approved actions directly into existing platform tools, including `builtin:exec`, while preserving `tool.call.*` SSE and persistence.
- Action state identity now includes `invocation_id`, so repeated invocations of the same action no longer overwrite one another.
- Frontend action UX now includes grouped invocation history, structured detail sections, search/filter/summary controls, collapsed history pagination, and a first tool-specific renderer for `builtin:exec` stdout/stderr/exit-code output.
- Skill-owned script execution remains outside the intended Yue skill boundary, while platform-level tools such as `builtin:exec` remain available.

This means the contract and lifecycle scaffolding are largely in place. The remaining work should focus on tool-backed action/state APIs and UX, not a runner.

At this point, the main high-value stories for the current action/runtime contract are effectively complete. Remaining work is enhancement-oriented rather than foundational.

## 1.1 Completion Snapshot

Estimated completion for the original high-value package/action contract line:

- approximately 90%+ of the intended high-value scope is complete

Delivered baseline:

- package-first skill contract
- compatibility with legacy markdown skills
- parser/registry/provider overlays
- tool-backed action descriptor/preflight/approval/runtime lifecycle
- requested-action chat runtime integration
- platform-tool continuation including `builtin:exec`
- SSE/event persistence/action-state persistence
- approval-token lookup and `invocation_id`-based identity
- frontend action lifecycle/history/approval UX
- structured detail rendering, filters, summaries, collapse/pagination
- first tool-specific renderer for `builtin:exec`

Remaining backlog should be treated as enhancement work:

- broader JSON Schema support
- more tool-specific renderers
- deeper trace/detail UX and exportability

## 2. Original Goal

The original Phase 1 goal was:

1. Introduce package-first skill contracts.
2. Preserve compatibility with existing runtime behavior.
3. Continue supporting:
   - legacy flat `.md` skills
   - package directory + `SKILL.md`
   - package directory + `manifest.yaml`
4. Avoid large rewrites of current API and chat runtime.
5. Do not implement a real script runner.
6. Model and register scripts/actions as structured metadata so actions remain tool-backed and stay inside Yue's platform tool boundary.

The guiding rule throughout this work has been:

"Compatibility first, structure now, platform-tool bounded."

## 3. Canonical Planning Documents

These documents were the initial reference inputs and should continue to be treated as the planning baseline:

- [Skill_Feature_Roadmap.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/Skill_Feature_Roadmap.md)
- [skill_package_contract_plan_20260327.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
- [skill_service_modularization_plan_20260323.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md)

## 4. What Has Been Completed

### 4.1 Package Models

Implemented in:

- [models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)

Added package-level models:

- `SkillPackageSpec`
- `SkillResourceSpec`
- `SkillReferenceSpec`
- `SkillScriptSpec`
- `SkillOverlaySpec`
- `SkillActionSpec`
- `SkillLoadingPolicy`

Added runtime action-related models:

- `RuntimeSkillActionDescriptor`
- `RuntimeSkillActionInvocationRequest`
- `RuntimeSkillActionInvocationResult`
- `RuntimeSkillActionExecutionRequest`
- `RuntimeSkillActionExecutionResult`
- `RuntimeSkillActionApprovalRequest`
- `RuntimeSkillActionApprovalResult`

Compatibility additions to `SkillSpec`:

- `package_format`
- `manifest_path`

Current lifecycle vocabulary in use:

- preflight:
  - `preflight_ready`
  - `preflight_approval_required`
  - `preflight_blocked`
- approval:
  - `approved`
  - `rejected`
  - `invalid`
- execution:
  - `awaiting_approval`
  - `queued`
  - `running` (contract only)
  - `succeeded` (contract only)
  - `failed` (contract only)
  - `skipped`

### 4.2 Package Parsing

Implemented in:

- [parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)

Completed capabilities:

- package format detection
- `manifest.yaml` parsing
- normalized package metadata derivation from package directory
- minimal manifest synthesis for package skills without `manifest.yaml`
- discovery of:
  - references
  - scripts
  - overlays
- normalization from package manifest back into runtime-compatible `SkillSpec`

Current compatibility behavior:

- legacy `.md` skills are wrapped as synthetic package-like metadata
- package directory + `SKILL.md` works without manifest
- package directory + `manifest.yaml` works with richer structured metadata

### 4.3 Manifest Validation

Implemented in:

- [parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
- [registry.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)

Completed validation behavior:

- declared reference/script/overlay/action paths must exist
- duplicate script ids are rejected
- duplicate action ids are rejected
- duplicate provider overlays are rejected where invalid
- invalid overlay YAML is rejected
- undeclared files discovered on disk become warnings, not hard errors

Validation posture:

- manifest-declared contract violations are blocking
- undeclared disk extras are warn-only for compatibility

### 4.4 Package-Aware Registry

Implemented in:

- [registry.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)

Completed behaviors:

- package manifest storage and retrieval
- `get_package_manifest(...)`
- `list_package_manifests(...)`
- compatibility preservation for:
  - `list_skills()`
  - `get_skill()`
  - `get_full_skill()`
- layered loading and hot reload kept intact
- package contents included in watch snapshot / reload inputs

### 4.5 Provider and Model Overlays

Implemented in:

- [parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
- [registry.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
- [chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py)

Completed behavior:

- overlay discovery from filenames such as `openai.gpt-4o.yaml`
- provider-level overlay merge
- model-specific overlay merge on top of provider-level overlay
- runtime `get_full_skill(...)` can take `provider` and `model_name`
- prompt assembly passes provider/model into skill resolution

### 4.6 Action Descriptor Contract

Implemented in:

- [adapters.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/adapters.py)
- [registry.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
- [policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)

Completed behavior:

- package actions exposed as runtime descriptors
- actions included in capability descriptors
- action-to-tool policy mapping
- preflight validation of action invocation
- requirement checks such as missing tool or missing action descriptor

### 4.7 Stub Execution Service

Implemented in:

- [actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)

Completed behavior:

- preflight result builder
- execution transition result builder
- execution transition event builder
- approval event builder
- user-facing message builders for:
  - preflight
  - approval
  - execution stub

Important current design constraint:

- no scripts are executed
- everything after preflight/approval stays inside Yue's platform tool boundary, without adding a skill-owned runner

### 4.8 Chat Runtime Integration

Implemented in:

- [chat_schemas.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_schemas.py)
- [chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)
- [chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)

Chat request fields added:

- `requested_action`
- `requested_action_arguments`
- `requested_action_approved`
- `requested_action_approval_token`

Completed runtime behavior:

- explicit requested-action path short-circuits model execution
- preflight runs before any actual model/tool execution
- if approval is required and no approval decision is supplied:
  - runtime emits `awaiting_approval`
- if approval decision is supplied:
  - runtime emits `skill.action.approval`
  - valid approval resumes into stub execution `queued -> skipped`
  - invalid approval token yields approval `invalid`

Current chain in the approved stub path:

1. `skill.action.preflight`
2. `skill.action.result` with `preflight_approval_required`
3. `skill.action.approval`
4. `skill.action.result` with `queued`
5. `skill.action.result` with `skipped`

### 4.9 SSE Contract Gate and Replay

Implemented in:

- [contract_gate.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/contract_gate.py)
- [chat_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
- [chat.py model](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/models/chat.py)

Completed behavior:

- `skill.action.*` classified as trace events
- action events persisted in `action_events`
- action events included in chat replay
- `action_states` now maintained as the current normalized action lifecycle view

### 4.10 Current Direct State Lookup

Implemented in:

- [chat_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
- [chat.py model](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/models/chat.py)
- [chat_schemas.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_schemas.py)
- [chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)

Added:

- `ActionState` SQLAlchemy table
- `ActionState` Pydantic model
- `ChatService.get_action_state(...)`
- `ChatService.get_action_state_by_approval_token(...)`
- `ChatService.list_action_states(...)`
- `GET /api/chat/{chat_id}/actions/state`
- `GET /api/chat/{chat_id}/actions/states`
- automatic `ActionEvent -> ActionState` upsert during `add_action_event(...)`

Current state keying:

- one current row per `session_id + skill_name + action_id`

This is sufficient for current stub flows, but not ideal for future concurrent invocations.

### 4.11 Frontend Action State Consumption

Implemented in:

- [useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts)
- [chatStream.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatStream.ts)
- [chatSubmission.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatSubmission.ts)
- [IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [Chat.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/Chat.tsx)

Completed behavior:

- chat load prefers direct action-state API and falls back to replayed `skill.action.*` events
- SSE `skill.action.*` updates incrementally refresh current frontend action states
- chat UI exposes a minimal read-only action lifecycle panel
- UI wording stays explicit that Yue skill actions are tool-backed metadata, not code execution

## 5. Files That Matter Most

### Core skill package/runtime files

- [backend/app/services/skills/models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
- [backend/app/services/skills/parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
- [backend/app/services/skills/registry.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
- [backend/app/services/skills/policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
- [backend/app/services/skills/adapters.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/adapters.py)
- [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
- [backend/app/services/skills/__init__.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py)
- [backend/app/services/skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)

### Chat/runtime integration files

- [backend/app/api/chat_schemas.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_schemas.py)
- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)
- [backend/app/api/chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
- [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py)
- [backend/app/services/contract_gate.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/contract_gate.py)

### Persistence/state files

- [backend/app/models/chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/models/chat.py)
- [backend/app/services/chat_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)

### Key tests

- [backend/tests/test_skill_foundation_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
- [backend/tests/test_skill_runtime_integration.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_integration.py)
- [backend/tests/test_chat_stream_runner_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_stream_runner_unit.py)
- [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py)
- [backend/tests/test_chat_service_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_service_unit.py)
- [backend/tests/test_contract_gate_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_contract_gate_unit.py)

## 6. Current Behavior Snapshot

If a package skill declares an action that requires approval:

1. User sends chat request with `requested_action`
2. Runtime selects skill as usual
3. Runtime runs action preflight
4. Runtime emits:
   - `skill.action.preflight`
   - `skill.action.result` with `preflight_approval_required`
5. Runtime emits execution lifecycle:
   - `skill.action.result` with `awaiting_approval`
6. Events are:
   - streamed via SSE
   - persisted in `action_events`
   - replayable
   - collapsed into `action_states`

If approval is later supplied in the request:

1. Runtime recomputes preflight
2. Runtime validates approval token
3. Runtime emits:
   - `skill.action.approval`
4. Runtime emits stub execution:
   - `skill.action.result` with `queued`
   - `skill.action.result` with `skipped`
5. Current action state becomes `queued` or later `skipped`, depending on latest event written

## 7. What Has Not Been Done Yet

### 7.1 Real Script Runner

Not planned:

- no actual script execution
- no sandboxed runner integration
- no stdout/stderr/result capture contract
- no process supervision
- no retries or resume semantics for real execution

### 7.2 Durable Approval Entity

Not implemented:

- no separate approval table/entity
- no dedicated approval workflow store
- no approval history beyond events/state payloads
- approval token is deterministic, not a first-class persisted approval record

### 7.3 Enhancement Backlog For The Next Thread

The next thread should treat the following as enhancement work on top of a stable baseline, not as missing foundational work.

Recommended implementation order:

1. broader action argument schema support
2. more tool-specific result renderers
3. deeper action trace/detail UX

#### A. Broader action argument schema support

Current baseline already supports:

- nested objects
- arrays
- defaults
- path-aware validation errors
- `type`, `enum`, `required`, `additionalProperties`

Recommended next scope:

- nullable/null handling
- string constraints such as `minLength`, `maxLength`, and `pattern`
- numeric bounds such as `minimum` and `maximum`
- array bounds such as `minItems` and `maxItems`
- combinators like `oneOf/allOf/anyOf` only if a concrete action contract needs them

Primary files to continue in:

- [backend/app/services/skills/policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
- [backend/tests/test_skill_foundation_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
- [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py)

Key guardrails:

- keep the validator a bounded subset, not a full JSON Schema engine
- keep SSE/user-visible error strings readable
- preserve `validated_arguments` as the normalized runtime payload

#### B. More tool-specific result renderers

Current baseline already supports:

- generic structured detail sections
- a dedicated `builtin:exec` renderer for stdout/stderr/exit-code output

Recommended next scope:

- doc/search-style tool renderers
- artifact-generation result renderers
- safer structured rendering for common JSON result payloads

Primary files to continue in:

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/components/IntelligencePanel.actions.test.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.actions.test.ts)

Possible backend touchpoint only if required:

- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

Key guardrails:

- always keep a generic fallback renderer
- never hide raw debugging information
- avoid backend payload churn unless frontend rendering is impossible without it

#### C. Deeper action trace/detail UX

Current baseline already supports:

- grouped action history
- invocation identity
- approval controls
- search/filter/summary
- collapsed invocation history with show-more pagination

Recommended next scope:

- dedicated invocation drill-down
- pinned/focused invocation view
- copy/export trace payloads
- better dense-session navigation

Primary files to continue in:

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/pages/Chat.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/Chat.tsx)
- [frontend/src/hooks/useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts)

Key guardrails:

- keep the compact grouped list as the default view
- add drill-down as a second-level experience
- preserve approval affordances in both compact and expanded flows

#### D. Optional cleanup and normalization

Only after A-C, if desired:

- split `IntelligencePanel` helpers into smaller modules
- normalize more result payloads before they hit the frontend
- add regression coverage for large histories and dense action sessions

### 7.4 Suggested round-by-round execution plan

Use this order for the next thread:

1. Round 1: broaden schema support
   - nullable
   - string length/pattern
   - numeric bounds
   - array bounds
2. Round 2: add the next tool-specific renderer
   - recommended next target: doc/search-style tool output
3. Round 3: add invocation drill-down
   - focused inspection view without removing the compact grouped list
4. Round 4: optional polish
   - combinators
   - more renderers
   - export/copy trace
   - helper cleanup

If the new thread wants the highest signal-to-effort path, start with Round 1 and do not mix Round 2 or Round 3 into the same first pass.

### 7.5 Stronger Manifest Schema Governance

Still incomplete:

- schema version evolution rules
- unknown field policy
- richer validation for nested action/resource schema
- more sophisticated overlay deep-merge semantics

## 8. Known Risks and Caveats

### Risk 1: Approval token is still lightweight rather than a durable approval record

Impact:

- fine for current flows
- not sufficient if approval becomes a stronger policy boundary later

Mitigation:

- introduce a persisted approval entity only if the product needs richer approval history or audit semantics

### Risk 2: Schema breadth can grow faster than UX clarity

Impact:

- a larger validator surface may produce confusing or noisy errors if added too quickly

Mitigation:

- keep validation support incremental and contract-driven, not spec-completion-driven

### Risk 3: Tool-specific renderers can overfit to narrow payload assumptions

Impact:

- renderers may drift from real tool output if they are based on idealized test shapes only

Mitigation:

- keep a generic fallback and verify renderer behavior against real payload examples

### Risk 4: Deeper detail UX can make the side panel visually heavy

Impact:

- a stronger trace/detail view could reduce scanability if added directly into the compact panel without hierarchy

Mitigation:

- keep compact list as default and make detailed inspection a second-level interaction

## 9. Recommended Next Tasks

Recommended order for the next session:

1. Tighten tool-backed action semantics across remaining manifests/examples
2. Expand frontend from read-only action status into approval-aware UX only if needed
3. Define invocation identity only if repeated attempts become common
4. Add a dedicated approval persistence entity only if approval UX expands
5. Keep runner/code-execution scope explicitly out of Yue skills

### Task A: Add action state API

Suggested output:

- endpoint to fetch current action state by:
  - `session_id + skill_name + action_id`
  - optionally `approval_token`

Why:

- frontend and operators should not need to reconstruct current state by replaying all events

### Task B: Add action approval/state schemas

Suggested output:

- API schema models for action state response
- API schema models for approval resume request/response

Why:

- current contracts live in service/model layer but are not exposed in a stable API surface

### Task C: Prepare invocation identity if needed

Suggested output:

- `invocation_id` or `execution_id`
- thread this through:
  - action events
  - action state
  - approval token/persistence

Why:

- only needed if multiple action attempts per session become common

### Task D: Add durable approval store if approval UX expands

Suggested output:

- separate table for approval requests and decisions

Why:

- current token approach is enough for current non-executing control flow

### Task E: Tighten tool-backed action governance

Suggested output:

- explicit prohibition on skill-owned execution
- stronger validation that actions map only to existing built-in/MCP tools
- clearer frontend/operator UX for non-executing action states

Why:

- keep skill actions inside Yue's intended tool boundary

## 10. Suggested New-Session Startup Checklist

When starting the next session, do this first:

1. Read these three planning docs:
   - [Skill_Feature_Roadmap.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/Skill_Feature_Roadmap.md)
   - [skill_package_contract_plan_20260327.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
   - [skill_service_modularization_plan_20260323.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md)
2. Read this handoff document:
   - [skill_package_contract_handoff_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md)
3. Inspect these files before changing anything:
   - [backend/app/services/skills/models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
   - [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
   - [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)
   - [backend/app/services/chat_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
   - [backend/app/models/chat.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/models/chat.py)
4. Run the focused regression suite before and after changes:
```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest \
  backend/tests/test_chat_service_unit.py \
  backend/tests/test_skill_foundation_unit.py \
  backend/tests/test_chat_stream_runner_unit.py \
  backend/tests/test_api_chat_unit.py \
  backend/tests/test_contract_gate_unit.py \
  backend/tests/test_skill_runtime_integration.py
```

## 11. Recommended Prompt For the Next Session

Use this prompt in a new session:

```text
请继续推进 Yue 的 skill package contract / action runtime contract 工作，先不要重做分析，直接基于当前代码和已有 handoff 接着实现。

开始前请先阅读并严格参考：
1. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/Skill_Feature_Roadmap.md
2. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md
3. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md
4. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md

当前状态简述：
- package-level skill contract 已实现，并保持了 legacy skill / package skill 兼容
- parser / registry / provider-model overlays 已接入
- action descriptor / invocation / preflight / approval / stub execution lifecycle 已接入
- chat runtime 已支持 requested_action、approval resume、skill.action.* SSE、event persistence、action_states
- Skill 只能基于现有 tools / MCP 能力工作，可使用平台级 builtin:exec，但不引入 skill-owned runner

这次优先目标：
1. 暴露 action state lookup 的最小 API contract
2. 支持按 session + skill + action 查询当前 state
3. 支持按 approval_token 查询当前 state
4. 保持现有 skill routing / prompt injection / chat runtime 兼容
5. 不要实现真实 script runner，也不要引入新的代码执行能力

建议先查看这些文件：
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/models/chat.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_schemas.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_service_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_stream_runner_unit.py

实现要求：
- 兼容性优先，增量改造，不大重写
- 直接进行代码修改与必要测试，不要只停留在分析
- 不要引入 subagent/delegation
- 新增测试优先覆盖 action state query contract
- 跑相关测试并修复失败

完成后请汇报：
- 改了哪些文件
- 新增了哪些模型/API
- 做了哪些兼容处理
- 跑了哪些测试，结果如何
- 剩余风险是什么
```

## 12. Latest Verified Test Status

Latest verified command:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest \
  backend/tests/test_chat_service_unit.py \
  backend/tests/test_skill_foundation_unit.py \
  backend/tests/test_chat_stream_runner_unit.py \
  backend/tests/test_api_chat_unit.py \
  backend/tests/test_contract_gate_unit.py \
  backend/tests/test_skill_runtime_integration.py
```

Latest result:

- `125 passed, 2 warnings`

Warnings observed:

- FastAPI deprecation warnings around `HTTP_422_UNPROCESSABLE_ENTITY`

These warnings are unrelated to this workstream.
