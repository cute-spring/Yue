# Skill Action Runtime Modularization Plan (2026-03-28)

## 1. Purpose

This document defines the next cleanup and modularization plan for the current skill package contract / action runtime enhancement branch.

The goal is not to redesign the feature set. The goal is to reduce responsibility mixing, make the code easier to review and extend, and preserve the contracts that were just stabilized in:

1. [`docs/plans/skill_package_contract_plan_20260327.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [`docs/plans/skill_package_contract_handoff_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md)
3. [`docs/plans/skill_service_modularization_plan_20260323.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md)

This plan should be treated as the follow-on execution guide for the next session if we want to improve cohesion without reopening the feature scope.

## 2. Why This Plan Is Needed

The current branch successfully landed substantial product value:

1. package-first skill contracts with legacy markdown compatibility
2. tool-backed action descriptors and runtime lifecycle
3. requested-action preflight / approval / execution bridging
4. action event persistence and action state lookup
5. frontend action history, structured details, and tool-specific renderers

The remaining concern is structural rather than product-level.

Several files now carry too many reasons to change at once. That increases:

1. regression risk for future enhancements
2. review difficulty for follow-up PRs
3. test maintenance cost
4. onboarding cost for anyone touching the action runtime

The code is working in the right direction. The next improvement should therefore be extraction and boundary cleanup, not a rewrite.

## 3. Primary Refactor Targets

### 3.1 `backend/app/api/chat_stream_runner.py`

Current concerns mixed in one file:

1. runtime dependency preparation
2. requested-action preflight and approval orchestration
3. platform-tool invocation bridging
4. SSE event emission
5. prompt/runtime assembly
6. stream execution and retry handling
7. final message and usage post-processing

Why this matters:

1. the requested-action path is now large enough to behave like its own runtime pipeline
2. changes to action lifecycle behavior are harder to isolate from normal chat streaming behavior
3. focused unit testing is harder because orchestration and transport are interleaved

### 3.2 `frontend/src/components/IntelligencePanel.tsx`

Current concerns mixed in one file:

1. action grouping/filtering helpers
2. formatting and summarization helpers
3. tool-specific result renderers
4. focused trace drill-down rendering
5. list/pagination/collapse UI
6. panel-level state management

Why this matters:

1. display-only renderer changes now require editing a large composite UI file
2. action trace UX changes risk disturbing unrelated list behavior
3. the file is harder to scan than the actual feature complexity warrants

### 3.3 `backend/app/services/skills/parsing.py`

Current concerns mixed in one file:

1. package and markdown skill loading
2. YAML and manifest parsing
3. resource discovery and normalization
4. provider/model overlay normalization
5. package synthesis for implicit manifests
6. validation

Why this matters:

1. package contract follow-up work will likely continue in this area
2. loader behavior and validation rules change for different reasons
3. testing and review are more difficult when all contract responsibilities sit together

### 3.4 `backend/app/services/chat_service.py`

Current concerns mixed in one service:

1. session persistence
2. message persistence
3. tool-call persistence
4. action event persistence
5. action state projection and lookup
6. related read/query helpers

Why this matters:

1. action-runtime storage logic is now large enough to justify narrower seams
2. persistence behavior is hard to reason about when all record types share one owner
3. action-state enhancements will keep landing here unless storage boundaries are clarified

### 3.5 Broad Test Files

Primary hotspot:

1. [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)

Why this matters:

1. broad test files hide module boundaries
2. failures are slower to localize
3. extraction work is safer when tests already mirror the intended module structure

## 4. Design Principles For The Refactor

The next session should follow these principles:

1. prefer extract-and-delegate over redesign
2. preserve external behavior and wire contracts
3. preserve import compatibility where practical
4. keep entrypoints thin and move orchestration into bounded modules
5. move pure helpers first, then move orchestrators
6. avoid changing SSE payloads, action state shapes, approval semantics, or renderer inputs during structural refactors

## 5. Proposed Target Structure

### 5.1 Chat Streaming / Requested Action Runtime

Recommended target:

1. keep [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py) as the top-level stream pipeline entrypoint
2. extract requested-action orchestration into a dedicated module, for example:
   - `backend/app/api/chat_requested_action_flow.py`
   - or `backend/app/services/chat_requested_action_runtime.py`
3. group action-runtime responsibilities behind a narrow API such as:
   - prepare requested-action execution context
   - evaluate preflight / approval status
   - execute approved platform tool
   - persist and emit lifecycle updates

Desired result:

1. `chat_stream_runner.py` owns stream lifecycle
2. requested-action modules own action lifecycle

### 5.2 Intelligence Panel

Recommended target:

1. keep [`frontend/src/components/IntelligencePanel.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx) as the top-level panel shell
2. extract pure data helpers into:
   - `frontend/src/components/intelligence/actionHelpers.ts`
3. extract tool-specific display logic into:
   - `frontend/src/components/intelligence/toolRenderers.tsx`
4. extract grouped list UI into:
   - `frontend/src/components/intelligence/ActionGroupList.tsx`
5. extract focused trace UI into:
   - `frontend/src/components/intelligence/FocusedActionTrace.tsx`

Desired result:

1. tool renderer work does not require editing the full panel
2. trace UX and list UX can evolve independently

### 5.3 Skill Parsing / Validation

Recommended target:

1. keep [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py) as a temporary facade if needed
2. extract contract loading and normalization into:
   - `backend/app/services/skills/skill_loader.py`
   - `backend/app/services/skills/skill_manifest.py`
   - `backend/app/services/skills/skill_resources.py`
   - `backend/app/services/skills/skill_validation.py`

Desired result:

1. loader behavior can evolve without touching validation
2. manifest/resource logic becomes directly unit-testable

### 5.4 Chat Persistence Boundaries

Recommended target:

1. keep [`backend/app/services/chat_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py) as an orchestration facade first
2. extract persistence-focused collaborators such as:
   - `backend/app/services/chat_sessions.py`
   - `backend/app/services/chat_messages.py`
   - `backend/app/services/chat_tool_calls.py`
   - `backend/app/services/chat_action_events.py`
   - `backend/app/services/chat_action_states.py`

Desired result:

1. the main service becomes easier to reason about
2. future state-lookup changes stay local to action-state storage code

### 5.5 Test Layout

Recommended target:

1. split broad backend tests into module-aligned suites such as:
   - `backend/tests/test_skill_parsing_unit.py`
   - `backend/tests/test_skill_policy_unit.py`
   - `backend/tests/test_skill_registry_unit.py`
   - `backend/tests/test_skill_actions_unit.py`
2. split intelligence panel tests by concern:
   - renderer tests
   - focused trace tests
   - list/filter/state tests

Desired result:

1. structure-only refactors become safer to validate
2. failures point to the right module boundary more quickly

## 6. Phased Migration Plan

### Phase 1: Extract Requested-Action Runtime Seams

Scope:

1. move requested-action helper functions and orchestration out of `chat_stream_runner.py`
2. keep public event contracts and top-level generator flow unchanged
3. add narrow unit coverage around the extracted orchestration seam if missing

Success condition:

1. no SSE contract changes
2. no action-state behavior changes
3. `chat_stream_runner.py` becomes materially smaller and easier to scan

Risk level:

1. medium

Why first:

1. this is the highest backend maintenance hotspot
2. it reduces risk for any future action-runtime enhancement work

### Phase 2: Split Intelligence Panel By Concern

Scope:

1. extract pure helpers first
2. extract tool renderers second
3. extract focused trace and grouped list components last

Success condition:

1. no visible UX regressions
2. tool-specific rendering coverage remains green
3. trace drill-down behavior stays intact

Risk level:

1. low to medium

Why second:

1. this file is one of the largest frontend hotspots
2. the logic already has natural view/helper boundaries

### Phase 3: Separate Skill Parsing From Validation

Scope:

1. isolate manifest loading, resource normalization, and validation into separate modules
2. keep `SkillLoader` as a temporary compatibility facade where helpful
3. avoid any schema-expansion work during this phase

Success condition:

1. no package contract behavior change
2. no registry API change
3. existing skill package and legacy markdown tests remain green

Risk level:

1. medium

Why third:

1. the package contract is now stable enough to refactor safely
2. this creates better seams for future follow-up enhancements

### Phase 4: Split Chat Persistence Responsibilities

Scope:

1. extract action state and action event storage first
2. extract tool-call and message storage next if still beneficial
3. keep `ChatService` as the stable orchestration entrypoint during migration

Success condition:

1. all action history and lookup APIs behave exactly the same
2. event persistence remains unchanged
3. tests continue to patch and construct the service without churn

Risk level:

1. medium to high

Why later:

1. it touches more persistence behavior than the earlier phases
2. it is worth doing, but only after action-runtime orchestration is cleaner

### Phase 5: Align Test Modules With Runtime Boundaries

Scope:

1. split broad test files after or alongside each extraction phase
2. avoid changing assertions unless behavior coverage needs clarification

Success condition:

1. tests become easier to navigate
2. failures map more directly to implementation boundaries

Risk level:

1. low

Why last:

1. the final structure should inform the test split

## 7. Regression Strategy

Each phase should keep the current contracts frozen.

High-priority regression coverage:

1. `requested_action` blocked / awaiting approval / approved execution paths
2. action event persistence and action-state lookup APIs
3. repeated invocation handling with `invocation_id`
4. tool-specific renderers for `builtin:exec`, docs tools, and PPT generation
5. package-first and legacy-markdown skill loading compatibility

Recommended test cadence per phase:

1. run the narrowest module tests first
2. run the targeted API/runtime tests second
3. run broader regression suites only after the extraction stabilizes

## 8. Suggested PR / Session Split

Recommended order for follow-up implementation sessions:

1. PR 1: requested-action runtime extraction
2. PR 2: intelligence panel split
3. PR 3: skill parsing / validation split
4. PR 4: chat persistence boundary extraction
5. PR 5: broad test file cleanup

This keeps each review focused and makes rollback straightforward if one phase introduces churn.

## 9. Open Questions To Reconfirm Before Implementation

These are not blockers for the plan, but they should be reaffirmed before code changes:

1. whether the requested-action orchestration should live under `app/api` or `app/services`
2. whether `parsing.py` should remain as a compatibility facade or be fully replaced after migration
3. how much import-path stability we want to preserve for `chat_service.py` internals during the cleanup

## 10. Recommendation

If we continue this work in another session, the best next step is:

1. implement Phase 1 first
2. keep it strictly structural
3. use the existing tests as a freeze harness
4. update this document with execution notes as each phase lands

That approach gives the best balance of safety, reviewability, and long-term maintainability without reopening the product scope that the current branch already delivered.
