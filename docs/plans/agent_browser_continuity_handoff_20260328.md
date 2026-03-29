# Agent Browser Continuity Handoff (2026-03-28)

## 1. Handoff Purpose

This document is the full handoff for the current Yue `agent-browser` workstream after:

1. browser foundation contract
2. safe backend integration
3. target/session contract hardening
4. initial mutation continuity contract and resolver seam work

This handoff is intended to let the next thread continue without re-deriving scope, boundary, or current implementation status.

## 2. Executive Summary

The current branch has moved beyond browser contract-only status.

It now contains:

1. a stable builtin browser tool family
2. tool-backed browser skill package wiring
3. requested-action / preflight / approval / execution lifecycle compatibility
4. real minimal Playwright-backed execution for:
   - `browser_open`
   - `browser_snapshot`
   - `browser_screenshot`
   - `browser_press`
   - `browser_click`
   - `browser_type`
5. authoritative snapshot-minted target references for reuse-sensitive mutation operations
6. structured browser continuity metadata, continuity-resolution metadata, and a concrete explicit-context continuity resolver path
7. a first Yue adapter-owned continuity lookup backend backed by persisted action-state metadata
8. optional browser runtime installation semantics so Playwright is not required for non-browser Yue deployments
9. screenshot export/download wiring plus frontend screenshot preview rendering
10. readable snapshot-result sections in the Intelligence Panel for interactive elements and binding context

The branch does not yet contain:

1. persistent browser session storage
2. a real session/tab lookup backend
3. a resumed browser continuity engine
4. a runtime invalidation engine beyond the current preflight-first checks
5. login persistence, CAPTCHA, or autonomous browser orchestration
6. inline browser image rendering in the assistant response body itself beyond link-style artifact summaries

## 3. Current Completion Assessment

Recommended current assessment:

1. browser foundation and safe integration: effectively complete
2. mutation continuity contract and lifecycle coverage: effectively complete for current single-use scope
3. resumable continuity implementation: started, with explicit-context resolver contract delivered but no real persistence/restore backend

Working estimate:

1. completed for the current stage: `95%` around the original foundation/integration target
2. completed for the next continuity stage: `35% - 45%`

Interpretation:

1. the prior stage should be treated as closed
2. the current work is now in the next phase: continuity implementation

## 4. Non-Negotiable Boundary Decisions

These decisions should remain fixed unless explicitly re-opened:

1. no skill-owned browser runner
2. browser capability must stay behind Yue platform tool boundaries
3. no hidden selector fallback behind `element_ref`
4. no implicit browser subsystem redesign hidden inside tactical changes
5. no login persistence / CAPTCHA / autonomous workflow expansion in this continuity phase
6. compatibility-first incremental delivery remains the operating rule

## 5. What Is Implemented

### 5.1 Builtin Browser Contract

Implemented in:

- [backend/app/mcp/builtin/browser.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)

Available builtin tools:

1. `builtin:browser_open`
2. `builtin:browser_snapshot`
3. `builtin:browser_click`
4. `builtin:browser_type`
5. `builtin:browser_press`
6. `builtin:browser_screenshot`

Shared result payload contract:

1. `browser_context`
2. `target`
3. `artifact`
4. `snapshot`
5. `metadata`

### 5.2 Runtime Metadata Contract

Stable metadata keys already flowing through invocation / preflight / execution:

1. `tool_family`
2. `operation`
3. `runtime_metadata_expectations`
4. `runtime_metadata`
5. `browser_continuity`
6. `browser_continuity_resolution`
7. `browser_continuity_resolver`

### 5.3 Browser Skill Package

Implemented in:

- [backend/data/skills/browser-operator/SKILL.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/browser-operator/SKILL.md)
- [backend/data/skills/browser-operator/manifest.yaml](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/browser-operator/manifest.yaml)

Current actions:

1. `open_page`
2. `snapshot_page`
3. `click_element`
4. `type_into_field`
5. `press_key`
6. `capture_screenshot`

### 5.4 Real Execution Status

Current real execution is intentionally narrow:

1. all browser tools execute through minimal Playwright-backed single-use flows
2. `click` and `type` consume authoritative snapshot-minted targets only
3. current mutation execution is URL-scoped and single-use
4. no resumable session continuity exists yet
5. Playwright is now explicitly optional:
   - default backend installs do not require it
   - browser tools fail clearly when it is absent
   - browser execution activates when the optional `browser` extra is installed

### 5.5 Authoritative Target Path

Current target path:

1. `browser_snapshot` mints authoritative refs shaped like:
   - `snapshot:<binding_source>#node:<index>`
2. `click` and `type` require:
   - `element_ref`
   - `binding_source`
   - `binding_session_id`
   - `binding_tab_id`
   - optional `binding_url`
   - optional `binding_dom_version`
   - optional `active_dom_version`

Current structured failure codes:

1. `browser_session_required`
2. `browser_tab_required`
3. `browser_target_required`
4. `browser_target_stale`
5. `browser_target_context_mismatch`

### 5.6 Continuity Contract

Current `browser_continuity` metadata expresses:

1. `contract_mode`
2. `current_execution_mode`
3. `authoritative_target_required`
4. `resumable_continuity`

Current `browser_continuity_resolution` metadata expresses:

1. `resolver_contract_version`
2. `resolution_mode`
3. `continuity_status`
4. `session_lookup_required`
5. `tab_lookup_required`
6. `target_lookup_required`
7. `provided_context`
8. `missing_context`
9. `contract_mode` for mutation paths
10. optional `resolved_context` when continuity is resolved explicitly

Current normalized `resolved_context` contract expresses:

1. `resolved_context_id`
2. `session_id`
3. `tab_id`
4. `element_ref`
5. `resolution_mode`
6. `resolution_source`
7. `resolved_target_kind`

Current resolver seam:

1. `BrowserContinuityResolver` interface exists
2. `DefaultBrowserContinuityResolver` exists
3. `ExplicitContextBrowserContinuityResolver` exists
4. default service behavior now uses `explicit_context`
5. explicit resolution currently operates only on already-provided `session_id` / `tab_id` / `element_ref`
6. requested-action tool-arg normalization now consumes `resolved_context` to fill missing `session_id` / `tab_id` / `element_ref` without overriding explicit inputs
7. this tool-arg hydration is now covered both at helper level and flow level around `run_requested_action_flow` / requested-action dispatch
8. browser builtin mutation tools now also distinguish:
   - generic missing-URL single-use calls
   - resumable continuity candidates that already carry hydrated `session_id` / `tab_id` / `element_ref`
9. continuity-candidate mutation calls are still rejected at the builtin boundary because no restore backend exists yet
10. `BrowserContinuityLookupBackend` and `DefaultBrowserContinuityLookupBackend` now exist as a lookup seam
11. the default lookup backend currently reports `not_configured`
12. a first storage-backed Yue adapter lookup backend now exists and reads authoritative continuity candidates from persisted `action_states`
13. lookup status now materially covers:
   - `not_configured`
   - `not_found`
   - `resolved`
   - `blocked`
14. no browser restoration backend is wired yet

### 5.7 Artifact And UI Presentation Status

Current browser artifact/UI behavior:

1. `browser_screenshot` now writes screenshots into Yue export storage instead of opaque temp-only paths
2. screenshot success payloads now include:
   - `filename`
   - `file_path`
   - `download_url`
   - `download_markdown`
3. assistant requested-action messages now append a natural artifact summary when a structured browser artifact is returned
4. current screenshot assistant copy is shaped like:
   - `Screenshot ready: [filename](/exports/...)`
5. Intelligence Panel now renders screenshot artifacts with:
   - artifact summary
   - download link
   - inline image preview
6. Intelligence Panel now renders `browser_snapshot` results with readable sections for:
   - snapshot summary
   - interactive elements
   - visible text
   - snapshot binding context
7. this is explicitly Yue UI integration work, not reusable kernel logic

## 6. Key Files To Understand First

Core backend:

1. [backend/app/mcp/builtin/browser.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)
2. [backend/app/services/skills/policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
3. [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
4. [backend/app/services/skills/models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
5. [backend/app/api/chat_requested_action_flow.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)
6. [backend/app/services/skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)

Skill package:

1. [backend/data/skills/browser-operator/manifest.yaml](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/browser-operator/manifest.yaml)

Frontend:

1. [frontend/src/components/intelligence/actionHelpers.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/actionHelpers.ts)
2. [frontend/src/components/IntelligencePanel.actions.test.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.actions.test.ts)

Planning baseline:

1. [docs/plans/agent_browser_phase2_completion_summary_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_phase2_completion_summary_20260328.md)
2. [docs/plans/agent_browser_mutation_continuity_plan_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_mutation_continuity_plan_20260328.md)

## 7. Verification Status

Current verified areas:

1. builtin browser contract tests
2. skill-policy / preflight browser contract tests
3. requested-action lifecycle tests
4. frontend browser detail rendering tests
5. preflight event metadata wiring for blocked/resolved continuity states
6. requested-action tool-arg normalization from `resolved_context`
7. flow-level requested-action dispatch coverage for resolved-context hydration
8. builtin boundary rejection for resumable continuity candidates without restore backend
9. lookup-backend seam compatibility for default no-op and injected resolver behavior

Most relevant recent test commands:

1. `PYTHONPATH=backend pytest backend/tests/test_browser_builtin_contract.py`
2. `PYTHONPATH=backend pytest backend/tests/test_skill_foundation_unit.py -k browser`
3. `PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py -k 'browser_type or browser_click or requested_action'`
4. `npm --prefix frontend run test -- IntelligencePanel.actions.test.ts`
5. `PYTHONPATH=backend pytest backend/tests/test_chat_requested_action_helpers_unit.py backend/tests/test_chat_stream_runner_unit.py -k 'browser_requested_action_merges_resolved_context_into_tool_args or run_requested_action_flow_hydrates_browser_tool_args_from_resolved_context or requested_action_resume_after_approval'`
6. `PYTHONPATH=backend pytest backend/tests/test_browser_builtin_contract.py -k 'browser_click or browser_type'`
7. `PYTHONPATH=backend pytest backend/tests/test_skill_foundation_unit.py -k 'continuity_lookup_backend or explicit_context_browser_continuity_resolver or browser'`
8. `PYTHONPATH=backend pytest backend/tests/test_chat_requested_action_helpers_unit.py`

Recent outcomes on this branch:

1. browser builtin contract: passing
2. browser skill foundation / preflight: passing
3. requested-action browser lifecycle set: passing
4. frontend browser detail tests: passing

## 8. What Is Still Missing

The next thread should assume these are not implemented:

1. persisted session store
2. resumed tab lookup backend
3. storage-backed continuity lookup backend beyond the current no-op seam
4. runtime-level continuity resolution before browser tool execution beyond explicit request context normalization, lookup seam exposure, tool-arg hydration, and builtin-boundary candidate detection
5. browser target replay against resumed session state
6. resumed stale-target detection beyond current preflight metadata checks

## 9. Recommended Next Objective

The next objective should remain narrow:

1. consume the delivered explicit-context continuity contract in the next runtime-hardening step without introducing browser persistence redesign

Recommended interpretation:

1. treat explicit `resolved_context` as the authoritative continuity handoff object already available in preflight/requested-action metadata
2. next work should implement the first adapter-owned storage-backed lookup backend behind `BrowserContinuityLookupBackend`
3. do not yet restore browser processes, tabs, cookies, or login state
4. keep all further work metadata-first and lifecycle-compatible

Exact next coding target:

1. add a minimal Yue-adapter lookup implementation that can resolve continuity from already-persisted action/runtime records when enough authoritative inputs exist
2. return normalized `RuntimeBrowserContinuityLookupResult` / `resolved_context` data through the existing resolver seam
3. stop at lookup resolution and structured metadata
4. do not execute resumed browser mutations and do not add browser restore mechanics

## 10. Explicit Do / Do Not For The Next Thread

Do:

1. keep using the current requested-action lifecycle
2. preserve `browser_continuity`, `browser_continuity_resolution`, and `browser_continuity_resolver`
3. keep default resolver fallback available
4. make new resolver behavior opt-in or cleanly substitutable
5. add focused tests for resolver output, lookup-seam behavior, and lifecycle metadata

Do not:

1. build a hidden browser persistence layer
2. introduce selector fallback
3. silently weaken authoritative target requirements
4. mix in login persistence or CAPTCHA work
5. redesign the frontend beyond incremental metadata display
6. turn lookup success into browser restore or resumed execution in the same round

## 11. Handoff Recommendation

Treat the current branch state as:

1. browser foundation complete
2. single-use mutation continuity contract complete
3. continuity resolver seam complete
4. resumable continuity backend not yet implemented
5. adapter lookup seam prepared but still mostly no-op by default

The next work should start from the new plan document:

- [docs/plans/agent_browser_continuity_resolver_plan_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_resolver_plan_20260328.md)
