# Agent Browser Mutation Continuity Plan (2026-03-28)

## 1. Purpose

This document defines the recommended next stage after the current `agent-browser` foundation and safe integration work.

This stage should be treated as a new phase.

Its purpose is not to broaden browser capability in general.

Its purpose is to solve one narrow problem well:

1. how Yue mints, validates, and consumes reusable browser targets for mutation operations

The first goal is not "make click and type work somehow".

The first goal is:

1. make `element_ref` authoritative
2. make stale-target failure explicit
3. keep all mutation work inside Yue's current tool-backed action lifecycle

## 2. Why This Must Be A Separate Stage

The prior stage intentionally stopped before real `click` and `type`.

That is no longer the current branch state.

The branch now has minimal single-use URL-scoped execution for both operations.

What remains unsolved is not "whether click/type exist".

What remains unsolved is continuity-strengthening for those operations.

That distinction matters because the remaining work now depends on contracts that do not matter for:

1. `open`
2. `snapshot`
3. `screenshot`
4. page-level `press`

Mutation work now depends on explicit answers for:

1. where `element_ref` comes from
2. what context it is bound to
3. when it becomes invalid
4. how validation failure is represented

If Yue skips those answers and goes straight to execution, the likely failure mode is:

1. selector guessing
2. hidden state reuse
3. weak contract semantics
4. hard-to-debug runtime behavior

## 3. Stage Goal

The target outcome for this stage is:

1. Yue can authoritatively mint a target from a browser inspection/snapshot step
2. Yue can validate that target against current browser context before mutation
3. Yue can reject stale or mismatched targets with structured failure codes
4. existing real `click` and `type` paths can be strengthened toward resumable continuity semantics without hidden fallback

This stage does not need to solve full browser platform concerns.

## 4. Required Architectural Guardrails

This stage must preserve the current boundaries.

### 4.1 Must Preserve

1. tool-backed requested-action lifecycle
2. Yue platform tool boundary
3. approval-required behavior for mutation
4. current action-state/history/trace compatibility
5. current browser contract vocabulary unless changed deliberately and consistently

### 4.2 Must Not Introduce

1. skill-owned browser runners
2. ad hoc selector fallback hidden behind `element_ref`
3. browser-specific persistence redesign
4. autonomous browser planning loops
5. UI-driven runtime semantics

## 5. Core Design Problem

The central question is:

1. what makes an `element_ref` valid enough for a real mutation action

Recommended answer:

1. `element_ref` must be platform-issued
2. it must be bound to a session/tab/browser context
3. it must be minted from a platform-owned inspection result
4. it must be rejected when required continuity checks fail

## 6. Recommended Contract Model

### 6.1 Authoritative Target Minting

Recommended minting source:

1. `browser_snapshot`

Recommended output behavior:

1. each interactive node returned by snapshot should carry:
   - `ref`
   - `target_binding`
2. snapshot should also expose a snapshot-level binding context

Recommended rule:

1. only platform-produced target references may be used for real `click` or `type`

### 6.2 Minimum Binding Vocabulary

The minimum binding set should remain:

1. `binding_source`
2. `binding_session_id`
3. `binding_tab_id`
4. `binding_url`
5. `binding_dom_version`

Recommended semantics:

1. `binding_source`
   - identifies the platform event or snapshot that minted the target
2. `binding_session_id`
   - the browser session expected by the target
3. `binding_tab_id`
   - the tab expected by the target
4. `binding_url`
   - the URL observed when the target was minted
5. `binding_dom_version`
   - an optional future-strengthening field for structural validation

### 6.3 Minimum Validity Rules

A target should be considered executable only if:

1. `element_ref` is present
2. `session_id` is present
3. `tab_id` is present
4. target binding metadata is present
5. the runtime can confirm that:
   - session matches
   - tab matches
   - target belongs to the current browser context

Recommended rule for URL:

1. URL continuity should be treated as a soft or hard validation input depending on runtime confidence
2. Yue should not silently ignore a clearly mismatched binding URL

## 7. Recommended Failure Model

The current structured failure vocabulary should become runtime-meaningful in this stage.

Required failure codes:

1. `browser_session_required`
2. `browser_tab_required`
3. `browser_target_required`
4. `browser_target_stale`
5. `browser_target_context_mismatch`

Recommended meaning:

1. `browser_session_required`
   - no reusable browser session was supplied for a reuse-sensitive operation
2. `browser_tab_required`
   - no tab context was supplied for a target-bound mutation operation
3. `browser_target_required`
   - no usable target reference was supplied
4. `browser_target_stale`
   - the target existed previously but no longer validates against current context
5. `browser_target_context_mismatch`
   - the supplied target was minted for a different session/tab/context

Recommended behavior:

1. these failures should be structured runtime errors
2. they should not degrade to selector search
3. they should remain visible in action history and tool result traces

## 8. Kernel-Friendly vs Yue-Adapter Boundary

### 8.1 Good Kernel Candidates

1. binding vocabulary
2. target validity rules
3. failure-code vocabulary
4. normalized mutation preconditions
5. reusable contract metadata for reuse-sensitive actions

### 8.2 Must Stay In Yue Adapters

1. where session state is persisted
2. how browser tabs are resumed in Yue storage
3. how requested-action SSE phrases these failures
4. how the IntelligencePanel renders binding/failure details
5. concrete Yue-specific browser session lookup APIs

## 9. Recommended Implementation Sequence

### 9.1 Step 1: Make Snapshot-Minted Targets Authoritative

Deliver:

1. confirm snapshot output shape and tests
2. make it explicit which fields are authoritative for reuse-sensitive actions
3. avoid expanding runtime behavior yet

Success signal:

1. `element_ref` + binding metadata are treated as the only acceptable mutation inputs
2. explicit continuity metadata can be surfaced without introducing hidden runtime fallback

Status update on the active branch:

1. authoritative snapshot-minted target inputs are already enforced for real `click` / `type`
2. explicit-context continuity resolution is now added on top of that contract
3. normalized `resolved_context` metadata now survives:
   - preflight result metadata
   - `skill.action.result` preflight events
   - requested-action lifecycle metadata
   - existing IntelligencePanel browser detail sections
4. this still does not imply real browser/session restoration

1. `element_ref` + binding metadata are treated as the only acceptable mutation inputs

### 9.2 Step 2: Add Validation Path Without Full Mutation Execution

Deliver:

1. a validation helper or validation layer for target-bound operations
2. structured failure results for missing/stale/mismatched targets
3. tests for:
   - missing session
   - missing tab
   - missing target
   - mismatched target context

Success signal:

1. Yue can explain why a mutation action is invalid before or during execution without hidden fallback behavior

### 9.3 Step 3: Implement One Mutation Operation

Recommended choice:

1. this step is already materially complete on the active branch:
   - `click`
   - `type`

Recommendation:

1. do not re-open "which mutation op first"
2. use the existing `click` and `type` implementations as the proving surface for continuity hardening

Success signal:

1. mutation actions continue to work end to end using authoritative targets only
2. resumed or invalidated continuity cases fail structurally rather than degrading to best-effort behavior

### 9.4 Step 4: UX / Trace Follow-Up

Deliver:

1. minimal frontend visibility for:
   - binding metadata
   - stale-target failure state
2. keep this incremental and avoid browser-only UI redesign

## 10. Recommended Acceptance Criteria

This stage should only be considered successful if:

1. `element_ref` is platform-issued and authoritative
2. mutation actions do not rely on raw selector fallback
3. target validation can fail structurally and observably
4. `click` and `type` both remain aligned to the validated target path
5. requested-action lifecycle compatibility remains intact
6. tests cover both:
   - success path
   - stale/mismatched target path

## 11. Recommended File Starting Points

Backend contract and tool layer:

1. [`backend/app/mcp/builtin/browser.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)
2. [`backend/app/mcp/builtin/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/registry.py)

Skill policy / runtime:

1. [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
2. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
3. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)

Requested-action integration:

1. [`backend/app/api/chat_requested_action_flow.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)
2. [`backend/app/api/chat_requested_action_events.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_events.py)

Skill package contract:

1. [`backend/data/skills/browser-operator/manifest.yaml`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/browser-operator/manifest.yaml)

Frontend follow-up:

1. [`frontend/src/components/intelligence/actionHelpers.ts`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/actionHelpers.ts)

## 12. Final Recommendation

Do not restart mutation work from scratch.

Start from the now-real authoritative target path and strengthen continuity semantics on top of it.

That is the smallest next step that preserves:

1. compatibility
2. boundary clarity
3. debuggability
4. kernel-friendly contract evolution
