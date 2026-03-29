# Skill Kernel Boundary Map (2026-03-29)

## 1. Purpose

This document translates the current Yue skill workstream into a reusable-module extraction map.

It is not a restart of the existing plans.

It is a boundary clarification layer on top of the existing work so the team can answer, concretely:

1. what the long-term reusable `skills kernel` should contain
2. what must remain in Yue adapters
3. where the current branch already aligns with that boundary
4. what still needs to happen before extraction is realistic

This document should be read together with:

1. [`docs/plans/skill_package_contract_plan_20260327.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [`docs/plans/skill_package_contract_handoff_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md)
3. [`docs/plans/skill_kernel_extraction_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_kernel_extraction_plan_20260328.md)
4. [`docs/plans/skill_action_runtime_modularization_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_action_runtime_modularization_plan_20260328.md)
5. [`docs/plans/agent_browser_continuity_handoff_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_handoff_20260328.md)
6. [`docs/plans/agent_browser_continuity_resolver_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_resolver_plan_20260328.md)

## 2. Primary Goal Alignment

The top-level goal is not only to make Yue's skill system stronger.

The top-level goal is to turn Yue's current skill implementation into the basis for a reusable module that another AI product could adopt even if that product does not yet have:

1. a skill registry
2. a requested-action flow
3. a browser continuity contract
4. a React intelligence panel
5. Yue's chat/session persistence model

That means the extraction target is:

1. a reusable `skills kernel`
2. plus Yue-specific adapters
3. plus Yue-specific app/runtime/UI integration

## 3. The Three-Layer Target Architecture

### 3.1 Layer A: Reusable `skills kernel`

This layer should contain:

1. skill package contract models
2. manifest/resource/overlay parsing and normalization
3. registry and version-aware skill lookup
4. action descriptor models
5. action argument validation and normalization
6. action preflight / approval-needed / blocked / executable decision logic
7. action lifecycle result/event contract builders
8. browser continuity vocabulary and normalized contracts
9. continuity resolver / lookup interfaces
10. normalized `resolved_context` contract

This layer should not depend on:

1. FastAPI route handlers
2. Yue chat sessions
3. Yue database tables
4. Yue built-in tool registry wiring
5. Yue frontend rendering

### 3.2 Layer B: Yue adapters

This layer should contain:

1. Yue tool bridge integration
2. Yue persistence-backed action event/state lookup
3. Yue browser continuity lookup implementation
4. Yue-specific requested-action orchestration helpers
5. Yue-specific policy overlays where product behavior differs from generic contract behavior

This layer may depend on:

1. Yue chat service
2. Yue persistence
3. Yue built-in tools
4. Yue runtime dependency objects

But this layer should still preserve kernel contracts rather than inventing new ones.

### 3.3 Layer C: Yue app/runtime/UI integration

This layer should contain:

1. FastAPI endpoints
2. stream orchestration
3. SSE transport
4. approval buttons and intelligence panel rendering
5. tool result presentation
6. any product-specific UX around action history and trace display

## 4. Current Progress Snapshot

Recommended current assessment:

1. package-first skill contract baseline: complete
2. action lifecycle contract baseline: complete
3. requested-action runtime baseline: complete
4. browser continuity contract baseline: complete
5. adapter-owned continuity lookup baseline: materially complete for first version
6. reusable-kernel boundary clarity: emerging but not fully codified in code layout
7. extraction readiness: partial

Working estimate:

1. feature-level delivery on the current branch: high
2. extraction readiness for a reusable module: medium

Interpretation:

1. the branch already contains a large amount of kernel-worthy logic
2. the main remaining gap is not missing feature breadth
3. the main remaining gap is still responsibility separation and adapter boundaries

## 5. Current File Classification Map

### 5.1 Strong kernel candidates now

These files are already close to reusable-kernel responsibilities:

1. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
2. [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
3. [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
4. [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
5. [`backend/app/services/skills/runtime_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_contracts.py)
6. [`backend/app/services/skills/browser_continuity_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/browser_continuity_contracts.py)
7. [`backend/app/services/skills/runtime_planning.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_planning.py)
8. parts of [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
9. parts of [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py)

What these files already contribute:

1. normalized package contracts
2. loading/parsing/registry semantics
3. schema-aware action argument validation
4. approval and preflight policy
5. lifecycle/result contract builders
6. continuity resolver and lookup interfaces
7. preflight planning/result assembly helpers

### 5.2 Likely kernel candidates after cleanup

These files contain kernel-worthy logic, but are still mixed with Yue-specific concerns:

1. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
2. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
3. [`backend/app/api/chat_requested_action_tools.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_tools.py)
4. [`backend/app/api/chat_requested_action_flow.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)

Why only "after cleanup":

1. they currently mix generic lifecycle logic with Yue runtime wiring
2. they are structurally reusable, but not yet dependency-clean

### 5.2.1 Current module grouping after recent cleanup

The current `skills` backend now already falls into more explicit groups:

1. contracts and models:
   - [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
   - [`backend/app/services/skills/runtime_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_contracts.py)
   - [`backend/app/services/skills/browser_continuity_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/browser_continuity_contracts.py)
2. loading and registry:
   - [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
   - [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
   - [`backend/app/services/skills/directories.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/directories.py)
3. policy and planning:
   - [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
   - [`backend/app/services/skills/runtime_planning.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_planning.py)
4. orchestration:
   - [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
5. Yue adapter wiring:
   - [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
   - [`backend/app/services/browser_continuity.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/browser_continuity.py)
   - [`backend/app/api/chat_requested_action_adapter.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_adapter.py)
   - [`backend/app/api/chat_requested_action_flow.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)
   - [`backend/app/api/chat_requested_action_tools.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_tools.py)
   - [`backend/app/api/chat_requested_action_events.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_events.py)

### 5.3 Yue adapter files

These files should stay outside the reusable kernel:

1. [`backend/app/services/chat_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
2. [`backend/app/services/browser_continuity.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/browser_continuity.py)
3. [`backend/app/mcp/builtin/browser.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)
4. [`backend/app/api/chat_requested_action_events.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_events.py)
5. [`backend/app/api/chat_requested_action_adapter.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_adapter.py)

Why adapter-owned:

1. they depend on Yue persistence or Yue built-in tool implementation
2. they express Yue-specific storage/runtime boundaries
3. they should consume kernel contracts rather than define host-agnostic ones

### 5.4 Yue app/UI files

These should remain Yue app-specific:

1. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
2. [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)
3. [`frontend/src/components/IntelligencePanel.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
4. [`frontend/src/components/intelligence/actionHelpers.ts`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/actionHelpers.ts)
5. [`frontend/src/components/intelligence/ActionGroupList.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/ActionGroupList.tsx)
6. [`frontend/src/components/intelligence/FocusedActionTrace.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/intelligence/FocusedActionTrace.tsx)

Recent Yue-only UI/runtime additions that should not be mistaken for kernel candidates:

1. optional Playwright install semantics exposed through backend packaging
2. screenshot export/download URL presentation
3. assistant-side artifact summary phrasing such as `Screenshot ready: ...`
4. inline screenshot preview rendering in the Intelligence Panel
5. browser snapshot readability sections for interactive element inspection

## 6. Browser Continuity Boundary Map

Browser continuity is the best current test case for kernel-vs-adapter separation because it is easy to over-couple to Yue runtime details.

### 6.1 Kernel-friendly continuity pieces

These parts should eventually live in the reusable kernel:

1. `browser_continuity` metadata vocabulary
2. `browser_continuity_resolution` metadata vocabulary
3. `BrowserContinuityResolver`
4. `BrowserContinuityLookupBackend`
5. `DefaultBrowserContinuityResolver`
6. `DefaultBrowserContinuityLookupBackend`
7. `ExplicitContextBrowserContinuityResolver`
8. normalized `resolved_context` shape
9. continuity statuses and failure/status vocabulary
10. authoritative target semantics around `element_ref` and binding metadata

### 6.2 Yue adapter continuity pieces

These should remain Yue-owned:

1. lookup backed by Yue `action_states`
2. request-id-scoped continuity record selection
3. Yue-specific candidate ranking and ambiguity blocking
4. persistence indexes and query helpers
5. builtin browser execution implementation
6. optional browser runtime packaging / install behavior for Yue deployments
7. screenshot export-path generation and `/exports/...` URL surfacing

### 6.3 Current status

Current state on the active branch:

1. continuity contracts are already mostly kernel-shaped
2. the first persistence-backed lookup backend is already adapter-shaped
3. this is the right direction and should be preserved

## 7. Extraction Readiness By Concern

### 7.1 Ready or close to ready

These are already close to extraction:

1. package/resource/action models
2. package parsing and normalization
3. registry logic
4. validation/policy logic
5. lifecycle event/result contract builders
6. continuity resolver/lookup interfaces

### 7.2 Needs one more cleanup pass first

These need more boundary cleanup before extraction:

1. `SkillActionExecutionService`
2. requested-action tool-arg hydration helpers
3. requested-action orchestration helpers
4. skill routing seams that still assume Yue-specific visibility or stores

### 7.3 Must stay host-owned

These should not move into the reusable kernel:

1. chat persistence models
2. chat session lookup
3. SSE emission and replay storage
4. built-in browser runtime implementation
5. intelligence panel rendering

## 8. Recommended Extraction Sequence

### Phase 1: Stabilize kernel contracts inside Yue

Objective:

1. stop changing core skill and continuity vocabularies casually
2. finish contract hardening before moving files around

Success condition:

1. contract models and metadata shapes are stable enough that later extraction is mostly file movement and interface cleanup

### Phase 2: Split kernel-facing logic from Yue adapters in place

Objective:

1. reduce import entanglement before physical extraction
2. keep current runtime behavior unchanged

Recommended moves:

1. isolate pure lifecycle/contract logic in `backend/app/services/skills/`
2. keep persistence-backed lookup in adapter modules
3. keep chat runtime orchestration in API/runtime modules

Success condition:

1. kernel-like modules no longer import Yue persistence/runtime modules directly

### Phase 3: Introduce explicit host adapter interfaces

Objective:

1. formalize the host integration points a non-Yue project would need to implement

Recommended adapter seams:

1. skill directory/source provider
2. tool availability/provider bridge
3. action event persistence sink
4. action state lookup adapter
5. browser continuity lookup adapter

Success condition:

1. another host app could theoretically wire the kernel without copying Yue internals

### Phase 4: Extract a first internal `skills kernel` package

Objective:

1. move reusable code without changing behavior

Recommended first extraction scope:

1. contracts/models
2. parsing/loading
3. registry
4. policy/validation
5. lifecycle result/event builders
6. continuity interfaces and default resolvers

Keep out initially:

1. Yue persistence adapters
2. Yue browser implementation
3. chat runtime entrypoints

## 8.1 Suggested extraction bundles

To reduce risk, extraction should not happen file-by-file in arbitrary order.

Recommended bundles:

### Bundle A: pure contracts

Safest first extraction group:

1. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
2. [`backend/app/services/skills/runtime_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_contracts.py)
3. [`backend/app/services/skills/browser_continuity_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/browser_continuity_contracts.py)

Why first:

1. these files are already strongly contract-shaped
2. they have little or no host-specific behavior
3. they form the vocabulary foundation for every later extraction step

### Bundle B: loading and registry

Second extraction group:

1. [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
2. [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
3. [`backend/app/services/skills/directories.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/directories.py)
4. [`backend/app/services/skills/adapters.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/adapters.py)

Why second:

1. this bundle is still mostly host-neutral
2. it depends on the contract layer but not on Yue persistence/runtime

### Bundle C: validation and planning

Third extraction group:

1. [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
2. [`backend/app/services/skills/runtime_planning.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_planning.py)

Why third:

1. these files turn contract models into execution decisions
2. they are reusable, but should follow after contract and registry stabilization

### Bundle D: orchestration facade

Fourth extraction group, only after the previous bundles are stable:

1. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
2. parts of [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py)

Why later:

1. this layer still coordinates multiple contracts at once
2. it is closer to a reusable facade, but it is not as clean as the lower bundles yet

### Keep in Yue for now

These should not be part of the first extraction wave:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/services/browser_continuity.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/browser_continuity.py)
3. [`backend/app/services/chat_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
4. [`backend/app/api/chat_requested_action_adapter.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_adapter.py)
5. [`backend/app/api/chat_requested_action_flow.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py)
6. [`backend/app/api/chat_requested_action_tools.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_tools.py)
7. [`backend/app/api/chat_requested_action_events.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_events.py)
8. [`backend/app/mcp/builtin/browser.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)

### Phase 5: Rebind Yue to the extracted kernel

Objective:

1. prove the extracted module still serves the current Yue app without regressions

Success condition:

1. Yue behavior stays the same
2. code ownership boundaries are clearer
3. another AI project could begin from the same kernel with different adapters

## 9. Immediate Concrete Next Steps

Recommended next execution steps after the current branch state:

1. continue treating `backend/app/services/skills/` as the kernel candidate zone
2. keep all persistence-backed continuity logic in Yue adapter modules such as [`backend/app/services/browser_continuity.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/browser_continuity.py)
3. avoid moving built-in browser runtime code into the kernel candidate zone
4. progressively extract any remaining generic lifecycle helpers out of Yue API flow modules
5. start introducing explicit adapter interface names in documentation and code comments where the boundary is already clear

## 9.1 Immediate migration checklist

The next focused extraction session should aim to complete this checklist:

1. add a short module-level boundary note to `backend/app/services/skills/__init__.py`
2. decide whether `backend/app/services/skills/routing.py` is kernel-worthy as-is or needs Yue visibility concerns pushed outward first
3. split tests into module-aligned files once the code layout stops moving
4. document which `app.services.skills` exports are intended as stable kernel-facing surface
5. avoid adding new Yue persistence imports inside the `backend/app/services/skills/` tree unless explicitly adapter-owned

## 10. Anti-Goals

The extraction effort should not:

1. turn Yue browser built-ins into a generic browser runtime package
2. move Yue persistence models into the reusable kernel
3. force frontend UI code into the kernel boundary
4. redesign requested-action semantics while extracting
5. hide host-specific behavior behind vague abstractions

## 11. Current One-Sentence Alignment

The current branch is building Yue product functionality, but the architectural goal is to shape that functionality into a future-extractable, adapter-separated reusable skills module.
