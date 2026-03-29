# Agent Browser Continuity Resolver Plan (2026-03-28)

## 1. Purpose

This plan starts the next concrete implementation step after the current continuity contract and resolver-seam work.

The goal of this plan is not to implement browser session persistence.

The goal is:

1. turn the current no-op continuity resolver into a first real resolver backend
2. keep the implementation metadata-first and lifecycle-compatible
3. avoid expanding into a browser session subsystem

## 2. Starting Point

The current branch already has:

1. real single-use browser execution
2. authoritative target refs
3. preflight continuity metadata
4. continuity-resolution metadata
5. a `BrowserContinuityResolver` interface
6. a `DefaultBrowserContinuityResolver` no-op implementation

This means the next step should not redefine the contract.

It should start consuming the current contract.

## 3. Scope Of This Plan

This plan should only cover:

1. a first concrete continuity resolver backend
2. normalized resolved-context metadata
3. preflight/runtime plumbing needed to carry resolver output forward
4. focused tests

This plan should not cover:

1. browser persistence storage
2. real browser process/tab restoration
3. login persistence
4. cookie/session hydration
5. CAPTCHA
6. autonomous workflows
7. browser-specific frontend redesign

## 4. Target Outcome

After this plan:

1. the resolver seam remains the only continuity entry point
2. a non-trivial resolver implementation can return a resolved context object
3. the resolved context can flow through requested-action metadata
4. later runtime work can consume that resolved context without redesigning contracts

## 4.1 Current Status Update

This first resolver-plan step is now materially delivered on the active branch.

Delivered:

1. `ExplicitContextBrowserContinuityResolver`
2. normalized `resolved_context` metadata
3. preflight metadata wiring
4. requested-action metadata survival
5. requested-action tool-arg normalization that consumes `resolved_context` for missing `session_id` / `tab_id` / `element_ref`
6. flow-level requested-action dispatch coverage proving hydrated tool args reach runtime handoff
7. builtin-boundary continuity-candidate detection for mutation tools when hydrated context exists but no restore backend is available
8. focused backend tests
9. minimal frontend continuity-resolution visibility in the existing IntelligencePanel detail path

Still intentionally not delivered:

1. persistence-backed session/tab lookup
2. browser restore
3. login or cookie hydration
4. runtime browser-session validation beyond explicit request-context normalization

## 5. Proposed Resolver Semantics

### 5.1 First Real Resolver Behavior

The first resolver implementation should be intentionally small.

It should:

1. accept explicit `session_id` / `tab_id` / `element_ref` inputs
2. validate whether enough continuity context is present for a resumable path
3. emit a normalized `resolved_context` metadata object
4. avoid touching any browser runtime or persistence backend

### 5.2 Normalized Resolved Context

Recommended output shape:

1. `resolved_context_id`
2. `session_id`
3. `tab_id`
4. `element_ref`
5. `resolution_mode`
6. `resolution_source`
7. `resolved_target_kind`

Recommended first semantics:

1. `resolution_source = explicit_request_context`
2. `resolved_target_kind = authoritative_target` for `click` / `type`
3. resolved context should exist only when required inputs are present

### 5.3 Resolver Status Model

Recommended statuses:

1. `not_applicable`
2. `deferred`
3. `resolved`
4. `blocked`

Recommended meaning:

1. `not_applicable`
   - continuity resolution is unnecessary for this action
2. `deferred`
   - current contract expects a future resolver backend, but this implementation cannot resolve further
3. `resolved`
   - explicit request context was sufficient to produce normalized resolved metadata
4. `blocked`
   - the resolver determined required continuity inputs are missing or inconsistent

## 6. Implementation Strategy

### Step 1: Add A Concrete Explicit-Context Resolver

Deliver:

1. a resolver implementation that operates only on explicit request context
2. no storage lookup
3. no browser restoration

Success signal:

1. mutation preflight for explicit `session_id` / `tab_id` / minted target can produce `resolved` continuity metadata

Status:

1. complete on the active branch

### Step 2: Attach Resolved Context To Lifecycle Metadata

Deliver:

1. resolved-context metadata on preflight result
2. resolver status metadata on requested-action transitions
3. compatibility with existing action-state persistence

Success signal:

1. action traces can show the difference between:
   - deferred continuity
   - resolved continuity

Status:

1. complete for preflight and requested-action metadata propagation
2. complete for blocked preflight event metadata propagation
3. complete for requested-action tool-arg hydration from resolved continuity metadata
4. complete for flow-level requested-action dispatch coverage of hydrated tool args
5. complete for builtin-boundary detection of resumable continuity candidates without restore backend
6. still not consumed by a resumed browser runtime backend

### Step 3: Add Tests

Deliver:

1. unit tests for default no-op resolver
2. unit tests for explicit-context resolver
3. requested-action tests proving resolver metadata survives lifecycle transitions

Success signal:

1. the next runtime phase can rely on those shapes without revalidation work

Status:

1. complete for:
   - default no-op resolver compatibility
   - explicit-context resolved path
   - blocked explicit-context path
   - requested-action metadata survival
   - blocked preflight event metadata survival
   - requested-action runtime tool-arg hydration from `resolved_context`
   - flow-level requested-action dispatch coverage of hydrated browser tool args
   - builtin-boundary rejection coverage for hydrated continuity candidates without restore backend

## 7. Guardrails

Must preserve:

1. current browser contract vocabulary
2. current target-binding rules
3. current structured failure vocabulary
4. current requested-action lifecycle

Must not introduce:

1. hidden persistence
2. selector fallback
3. browser runtime restoration
4. UI-driven resolver semantics

## 8. Recommended Files To Start With

Primary files:

1. [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
2. [backend/app/services/skills/models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
3. [backend/app/api/chat_requested_action_flow.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)
4. [backend/tests/test_skill_foundation_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
5. [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py)

Optional follow-up:

1. [frontend/src/components/intelligence/actionHelpers.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/actionHelpers.ts)

## 9. Acceptance Criteria

This plan should be considered complete only if:

1. a concrete resolver implementation exists in addition to the no-op default
2. resolver output is structured and normalized
3. resolver output survives preflight and requested-action transitions
4. no browser persistence or browser restoration is introduced
5. tests prove both:
   - default no-op path
   - resolved explicit-context path

## 10. Immediate Next Coding Task

Start with:

1. implement `ExplicitContextBrowserContinuityResolver`
2. make it return `resolved` only when explicit `session_id` / `tab_id` and authoritative target inputs are sufficient
3. add `resolved_context` metadata to the resolver result
4. add unit tests before any broader runtime wiring
