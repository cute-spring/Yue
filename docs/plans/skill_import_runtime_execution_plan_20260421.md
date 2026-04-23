# Skill Import & Runtime Execution Plan

**Date**: 2026-04-21

## 1. Purpose

This document defines the execution plan for Yue's skill direction under the new product boundary.

It is intentionally narrow.

Yue is not trying to become a skill authoring platform.
Yue is not trying to become a vendor-compatibility layer.
Yue is not trying to become a marketplace.

Yue is trying to become a strong, standard-aligned, internal platform for:

- importing Agent Skills standard skills
- accepting or rejecting them clearly
- activating them safely
- selecting them well at runtime
- executing them reliably inside Yue

## 2. Final Goal

The final goal is:

- **Yue becomes a reliable Agent Skills import-and-runtime platform**

That means Yue can do all of the following well:

- accept skills that follow the Agent Skills open standard
- tell admins clearly whether a skill is valid and whether it is Yue-compatible
- let admins activate and replace skills without ambiguity
- let runtime components discover and select the right skill
- inject and execute selected skills safely and predictably

## 3. Core Goal

The core goal for the next major cycle is smaller than the final goal:

- **build a strong Skill Import Gate and improve runtime routing**

This is the shortest path to delivering real value without reopening the old “skill platform” scope.

## 4. Current Delivery Position (2026-04-23)

- Delivery estimate (current): Stage 1 ~98% | Stage 2 ~97% | Stage 3-Lite ~95% | Stage 4-Lite ~95% | Stage 5-Lite ~25% (deferred, minimal externalization artifact landed).
- Stage 1/2 are functionally landed: import models/store/service, `/api/skill-imports`, lifecycle transitions, restart restore and runtime refresh smoke checks are green.
- Stage 3-Lite is largely landed: deterministic visibility-scoped routing and default minimal API response contract are guarded by tests.
- Stage 4-Lite is partially landed: runtime seams/boundary harness plus context-path and routing-visibility seam upgrades are in place; chat compatibility patch points are now migrated to runtime-context patch paths, and `skill_service` now has provider/container seams for `registry/router/action/import_store`; global singleton coupling is reduced but not fully closed.
- Stage 5 remains deferred as planned for full extraction; a minimal machine-readable externalization artifact is now maintained via Stage 5 harness.
- Remaining closeout focus in this cycle:
  - reduce `skill_service.py` global singleton dependency in runtime critical paths,
  - continue reducing Yue adapter residue around routing visibility/group resolution,
  - keep hybrid runtime mode risk bounded and observable while preserving import-gate default behavior.
- Current evidence update (2026-04-23):
  - `POST /api/skill-imports` now rejects invalid `source_type` with stable `invalid_request` detail.
  - `/api/skills/reload` now rejects in import-gate mode with `skill_reload_unavailable_in_import_gate_mode`.
  - compatibility evaluator now uses builtin registry as default supported tool set; unknown tools fail compatibility.
  - `api/chat` prompt runtime helpers are now explicitly bound to per-request runtime context in stream path.
  - `skill_service` now exposes set/reset hooks for Stage4 runtime context factory (default behavior preserved).
  - `api/chat` tests now patch runtime context instead of module-level `skill_router/skill_registry` seams.
  - `skill_service` now exposes `Stage4LiteRuntimeProviders` with set/get/reset hooks and builds runtime seams from runtime-context providers by default.
  - `api/skills` and `api/skill-imports` now resolve runtime deps from context seams; module-level singleton seam exposure is reduced.
  - convergence guard is introduced: `YUE_SKILL_RUNTIME_CONVERGENCE_STRATEGY=import-gate-strict` gates import mutations in legacy mode.
  - hybrid guardrail tests are added (import-gate reload short-circuit, legacy refresh no-op).
  - hybrid behavior matrix now covers `legacy/import-gate + reload/import/activate/deactivate` combinations in API/lifespan paths.
  - regression command set covering API/import/lifespan/seams/harness/compatibility is green (`77 passed`).
  - expanded regression set covering chat + runtime catalog + context seam tests is green (`146 passed`).

## 5. Product Position

### 5.1 What Yue Is

Yue is:

- a skill consumer
- a skill acceptance platform
- a skill activation platform
- a skill runtime platform

### 5.2 What Yue Is Not

Yue is not:

- a skill editor
- a skill creation studio
- a skill marketplace
- a multi-standard translation layer
- a release/signing/governance system in this phase

## 6. Architecture Direction

The code direction should follow one principle:

- **high cohesion inside the skill subsystem, low coupling to the rest of Yue**

That means the skill subsystem should increasingly look like:

1. a self-contained package for:
   - skill models
   - parsing
   - validation
   - registry
   - compatibility checking
   - routing
   - runtime action policy
2. a thin Yue integration layer for:
   - app startup wiring
   - API exposure
   - tool registry bridging
   - agent/runtime-specific prompt assembly

## 7. Target Module Split

### 7.1 Core Skill Module

This should contain the logic that could be reusable outside Yue:

- skill package models
- Agent Skills parsing
- structural validation
- package/resource discovery
- registry/indexing
- compatibility evaluation contract
- routing primitives
- action invocation validation

### 7.2 Yue Adapter Layer

This should contain Yue-specific integration:

- FastAPI endpoints
- startup lifecycle wiring
- `agent_store` integration
- `tool_registry` integration
- chat prompt assembly
- Yue-specific activation persistence

### 7.3 Why This Split Matters

If we do this well, the core skill module becomes much easier to:

- test in isolation
- evolve without breaking unrelated runtime code
- extract later as a small open-source library

## 8. Stage Plan

## Stage 1: Define the Acceptance Boundary

### Goal

Turn the current “skill loader” into a clearly defined **Skill Import Gate** boundary.

### Scope

- define import states
- define validation states
- define compatibility states
- define activation states

### Deliverables

- explicit lifecycle model:
  - active
  - inactive
  - rejected
  - superseded
- explicit response schema for import results
- clear separation between:
  - structural validation
  - Yue compatibility evaluation
  - activation eligibility

### Acceptance Criteria

- admins can distinguish “standard-valid but Yue-incompatible” from “fully activatable”
- runtime no longer treats raw loading and accepted import as the same concept
- the minimal lifecycle is documented and reflected in code contracts

## Stage 2: Implement the Skill Import Gate

### Goal

Add the minimum product surface so standard skills can run quickly with near-zero extra configuration.

### Scope

- import endpoint or import service
- static validation
- runtime compatibility check
- preview payload
- lightweight activation management:
  - keep directory-based loading available
  - default auto-activate when import/compatibility checks pass
  - keep explicit deactivate/replace controls for runtime safety

### Deliverables

- import service for Agent Skills package input
- package preview model
- compatibility report model
- activation state persistence (restart-safe)
- replacement flow for updated skill package

### Acceptance Criteria

- a valid Agent Skills package can be imported explicitly
- a standard skill placed in configured loading directories can be discovered and used with minimal setup
- the system returns clear validation and compatibility results
- incompatible skills cannot enter active runtime set silently
- compatible imports/directories can auto-enter active runtime set by default policy
- admins can deactivate and replace skills without editing files manually

### Current P0 Delivery Bar

- small number of skills can run stably with clear user value
- users can drop standard skills into loading directories and use them with near-zero extra configuration
- missing dependencies are surfaced clearly (what to install/configure)
- restart does not lose active runtime state

## Stage 3: Routing Lite (Current Plan)

### Goal

Deliver stable skill switching for small visible-skill sets with a fixed deterministic routing path.

### Scope

- keep runtime routing simple for current low-skill-count assumption
- enforce visibility-first candidate set (user/agent specific visible skills only)
- use lightweight deterministic scoring for selection
- keep routing contracts stable with minimal default response for current deterministic flow

### Non-Goals (This Stage)

- no vector retrieval or embedding-based recall
- no LLM-based rerank
- no multi-source candidate federation
- no new pluggable routing abstraction layer in this phase

### Deliverables

- routing pipeline with:
  - scope filtering
  - full scan of visible skills
  - lightweight lexical scoring
  - fallback
- routing API default response fields:
  - `selected_skill`
  - `reason_code`
  - `fallback_used`
- routing debug/diagnostics-only extension fields:
  - `selected`
  - `candidates`
  - `scores`
  - `reason`
  - `stage_trace`
  - `selection_mode`
  - `effective_tools`
- routing quality test cases for low-skill-count scenarios

### Acceptance Criteria

- with small visible skill sets, routing is stable and deterministic
- candidate set is strictly visibility-scoped per user/agent
- fallback behavior is deterministic and testable
- API default response remains minimal/stable; debug fields are optional diagnostics only
- API tests keep default contract narrow (`selected_skill`, `reason_code`, `fallback_used`) and prevent debug-only fields from becoming default payload surface

## Stage 4: Decouple Lite (Current Plan)

### Goal

Reduce coupling through interface seams and local isolation first, without large-scale file moves or behavior rewrites.

### Scope

- add minimal adapter/protocol seams around core integration points
- isolate global compatibility seams behind a small facade/container boundary
- keep current runtime behavior stable while making internals replaceable

### Non-Goals (This Stage)

- no large module split or package relocation
- no full dependency injection migration across the whole backend
- no behavior-changing refactor in routing/import/runtime paths

### Deliverables

- Stage 4-Lite interface contracts (reserved for future replacement):
  - `ToolCapabilityProvider`
  - `ActivationStateStore`
  - `RuntimeCatalogProjector`
  - `PromptInjectionAdapter`
  - `VisibilityResolver`
- a thin composition/facade seam that centralizes current global instances
- focused tests proving core flows can run without full FastAPI app startup

### Acceptance Criteria

- critical core logic paths are testable without full app startup
- Yue-specific concerns are accessed through interfaces/facades instead of scattered direct dependencies
- no functional regression in current import-gate and runtime behavior

## Stage 5: Externalization Prep Lite (Deferred for Full Extraction)

### Goal

Stage 5 full externalization tasks remain deferred in the current MVP cycle.

### Scope (lite)

- keep full extraction/repository split out of scope
- keep a minimal machine-readable boundary deliverable for validation/export

### Deliverables (minimal, landed)

- runtime boundary harness JSON report
- exportable boundary manifest (`stage5-lite-boundary-manifest/v1`) with deterministic fields and stable boundary ordering

Current implementation entrypoint:

- `backend/scripts/skill_runtime_boundary_harness.py`
  - verifies `ToolCapabilityProvider` / `ActivationStateStore` / `RuntimeCatalogProjector` / `PromptInjectionAdapter` / `VisibilityResolver`
  - emits machine-readable JSON report for CI-friendly checks
  - can export boundary manifest artifact via `--manifest-out`

### Non-Goals (This Stage)

- no separate repository creation
- no open-source release/publishing work
- no backwards-compatibility commitment for external consumers yet

### Acceptance Criteria

- current delivery cadence is not blocked by extraction work
- minimal externalization artifact is present and test-validated
- full extraction tasks remain documented but out of active scope

## 9. Concrete Work Breakdown

### Phase A: Contracts

- define import result models
- define compatibility result models
- define activation state models
- define routing outcome models

### Phase B: Product Surface

- add import service
- add activation/deactivation flow
- add replacement flow

### Phase C: Runtime Quality

- implement Stage 3 Routing Lite (small visible-skill set first)
- add selection explanation/result fields and smoke verification path

### Phase D: Decoupling

- implement Stage 4 Decouple Lite:
  - add reserved interfaces/adapters
  - centralize global seams behind a composition boundary
  - keep behavior unchanged

### Phase E: Extraction Spike (Deferred)

- keep full extraction artifacts as backlog
- keep only Stage 5-lite boundary manifest/harness active in current cycle

## 10. Technical Design Principles

### 10.1 High Cohesion

Each skill module should change for one primary reason.

Examples:

- parsing changes should not require chat runtime changes
- routing changes should not require startup lifecycle changes
- compatibility changes should not require API contract rewrites everywhere

### 10.2 Low Coupling

The skill core should not depend directly on:

- FastAPI request/response types
- app startup lifecycle details
- Yue chat stream implementation details
- agent persistence details

It should depend on small abstracted inputs and outputs instead.

### 10.3 Compatibility Facade, Not Compatibility Spread

If backward compatibility is needed, keep it at the edges.

Do not spread old Yue assumptions through the new skill core.

### 10.4 Extraction-Ready Packaging

When introducing new code, prefer shapes that could later live in a package like:

- `skill_core.models`
- `skill_core.parsing`
- `skill_core.registry`
- `skill_core.validation`
- `skill_core.routing`
- `skill_core.runtime_policy`

## 11. Feasibility of Extracting Skill as a Small Open-Source Project

## 11.1 Short Answer

This idea is **feasible**, and more than that, it is technically sensible.

The current codebase already has a useful starting point:

- `backend/app/services/skills/` already exists as a package
- major responsibilities are already partially extracted
- `skill_service.py` is already treated as a compatibility facade

That is a strong sign that this is not a speculative idea.

## 11.2 Why It Is Feasible

The following pieces are already close to extraction-friendly:

- models
- parsing
- registry
- routing
- policy validation

These are mostly domain logic, not application UI logic.

## 11.3 What Still Blocks Easy Extraction

The main blockers are:

1. **global instance seams**
   - `skill_registry`
   - `skill_router`
   - compatibility wrappers

2. **Yue runtime coupling**
   - prompt assembly
   - tool registry lookups
   - agent config dependence

3. **mixed product assumptions**
   - some current code still assumes Yue-specific runtime behavior and historical UX choices

## 11.4 Realistic Extraction Shape

The right extraction target is not “all skill behavior”.

The right extraction target is:

- **a small skill core library**

That library should provide:

- package parsing
- validation
- registry
- compatibility evaluation contracts
- routing helpers
- action invocation validation

Yue would keep:

- API endpoints
- UI
- activation persistence
- runtime injection wiring
- tool execution bridging

## 11.5 Recommendation

Do not try to extract it immediately.

Instead:

1. first make the internal boundaries real
2. then run an extraction spike
3. only extract after the core API is stable

That is much safer than trying to publish the current shape too early.

## 12. Risks

### Risk 1: Product Scope Drift

If the team re-expands into authoring, marketplace, or multi-standard compatibility, the architecture will drift again and the extraction boundary will blur.

### Risk 2: Hidden Yue Coupling

If too much runtime logic stays mixed into skill internals, the extraction story will remain theoretical.

### Risk 3: Premature Externalization

If we try to open-source too early, we may freeze a messy public API and slow down product progress.

## 13. Recommended Next Moves

### Immediate

1. formalize the Skill Import Gate lifecycle
2. implement explicit import / compatibility / activation models
3. improve routing quality

### Near-Term

1. isolate Yue-specific adapters from reusable skill logic
2. reduce the role of `skill_service.py` to a compatibility shell only
3. prepare an extraction readiness checklist

### After That

1. run a small extraction spike
2. test the extracted core in a minimal host application
3. decide whether to publish

## 14. Bottom Line

The idea is good.

It is feasible to shape Yue's skill subsystem so that the reusable core can later become a small open-source project.

But the correct order is:

- **first strengthen the product boundary**
- **then strengthen the code boundary**
- **then extract**

Not the other way around.
