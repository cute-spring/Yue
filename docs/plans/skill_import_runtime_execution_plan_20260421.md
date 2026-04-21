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

## 4. Product Position

### 4.1 What Yue Is

Yue is:

- a skill consumer
- a skill acceptance platform
- a skill activation platform
- a skill runtime platform

### 4.2 What Yue Is Not

Yue is not:

- a skill editor
- a skill creation studio
- a skill marketplace
- a multi-standard translation layer
- a release/signing/governance system in this phase

## 5. Architecture Direction

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

## 6. Target Module Split

### 6.1 Core Skill Module

This should contain the logic that could be reusable outside Yue:

- skill package models
- Agent Skills parsing
- structural validation
- package/resource discovery
- registry/indexing
- compatibility evaluation contract
- routing primitives
- action invocation validation

### 6.2 Yue Adapter Layer

This should contain Yue-specific integration:

- FastAPI endpoints
- startup lifecycle wiring
- `agent_store` integration
- `tool_registry` integration
- chat prompt assembly
- Yue-specific activation persistence

### 6.3 Why This Split Matters

If we do this well, the core skill module becomes much easier to:

- test in isolation
- evolve without breaking unrelated runtime code
- extract later as a small open-source library

## 7. Stage Plan

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
  - imported
  - parsed
  - standard-valid
  - Yue-compatible
  - active
  - rejected
- explicit response schema for import results
- clear separation between:
  - structural validation
  - Yue compatibility evaluation
  - activation eligibility

### Acceptance Criteria

- admins can distinguish “standard-valid but Yue-incompatible” from “fully activatable”
- runtime no longer treats raw loading and accepted import as the same concept
- the new lifecycle is documented and reflected in code contracts

## Stage 2: Implement the Skill Import Gate

### Goal

Add the minimum product surface for importing and accepting skills.

### Scope

- import endpoint or import service
- static validation
- runtime compatibility check
- preview payload
- activation / deactivation / replacement

### Deliverables

- import service for Agent Skills package input
- package preview model
- compatibility report model
- activation state persistence
- replacement flow for updated skill package

### Acceptance Criteria

- a valid Agent Skills package can be imported explicitly
- the system returns clear validation and compatibility results
- incompatible skills cannot be activated silently
- admins can activate, deactivate, and replace a skill without editing files manually

## Stage 3: Strengthen Routing

### Goal

Improve dynamic identification of which skill should be used.

### Scope

- better candidate recall
- better reranking
- clearer routing outcomes

### Deliverables

- routing pipeline with:
  - scope filtering
  - candidate recall
  - reranking
  - fallback
- routing explanation fields
- routing quality test cases

### Acceptance Criteria

- routing performs better than simple name/description token matching alone
- the system can explain why a skill was selected or not selected
- fallback behavior is deterministic and testable

## Stage 4: Decouple the Skill Core

### Goal

Reduce coupling between the skill subsystem and Yue runtime integration.

### Scope

- separate pure skill logic from Yue app glue
- isolate mutable globals and compatibility seams
- define a reusable package boundary

### Deliverables

- stricter internal module boundaries
- fewer Yue-specific imports in core skill code
- clear adapter interfaces for:
  - tool capability lookup
  - activation persistence
  - runtime prompt injection

### Acceptance Criteria

- core skill logic can be tested without full app startup
- Yue-specific concerns live in adapter or facade layers
- coupling to `agent_store`, `tool_registry`, and app globals is reduced

## Stage 5: Prepare for Externalization

### Goal

Make the skill core realistically extractable as a small open-source project.

### Scope

- package boundary review
- public API review
- dependency minimization
- extraction spike

### Deliverables

- extraction readiness checklist
- dependency map
- proposed package name and API surface
- proof-of-concept extraction branch or local package spike

### Acceptance Criteria

- core skill package can be imported in a small standalone test harness
- public API is narrower than the current Yue-internal surface
- extraction does not require dragging most of Yue with it

## 8. Concrete Work Breakdown

### Phase A: Contracts

- define import result models
- define compatibility result models
- define activation state models
- define routing outcome models

### Phase B: Product Surface

- add import service
- add import preview
- add activation/deactivation flow
- add replacement flow

### Phase C: Runtime Quality

- improve routing recall and reranking
- add skill selection explanation fields
- add smoke verification path

### Phase D: Decoupling

- isolate Yue-specific wiring
- reduce global compatibility seams
- split reusable core from app integration

### Phase E: Extraction Spike

- create standalone package skeleton
- move pure skill modules behind a clean API
- validate that another small host app could consume the package

## 9. Technical Design Principles

### 9.1 High Cohesion

Each skill module should change for one primary reason.

Examples:

- parsing changes should not require chat runtime changes
- routing changes should not require startup lifecycle changes
- compatibility changes should not require API contract rewrites everywhere

### 9.2 Low Coupling

The skill core should not depend directly on:

- FastAPI request/response types
- app startup lifecycle details
- Yue chat stream implementation details
- agent persistence details

It should depend on small abstracted inputs and outputs instead.

### 9.3 Compatibility Facade, Not Compatibility Spread

If backward compatibility is needed, keep it at the edges.

Do not spread old Yue assumptions through the new skill core.

### 9.4 Extraction-Ready Packaging

When introducing new code, prefer shapes that could later live in a package like:

- `skill_core.models`
- `skill_core.parsing`
- `skill_core.registry`
- `skill_core.validation`
- `skill_core.routing`
- `skill_core.runtime_policy`

## 10. Feasibility of Extracting Skill as a Small Open-Source Project

## 10.1 Short Answer

This idea is **feasible**, and more than that, it is technically sensible.

The current codebase already has a useful starting point:

- `backend/app/services/skills/` already exists as a package
- major responsibilities are already partially extracted
- `skill_service.py` is already treated as a compatibility facade

That is a strong sign that this is not a speculative idea.

## 10.2 Why It Is Feasible

The following pieces are already close to extraction-friendly:

- models
- parsing
- registry
- routing
- policy validation

These are mostly domain logic, not application UI logic.

## 10.3 What Still Blocks Easy Extraction

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

## 10.4 Realistic Extraction Shape

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

## 10.5 Recommendation

Do not try to extract it immediately.

Instead:

1. first make the internal boundaries real
2. then run an extraction spike
3. only extract after the core API is stable

That is much safer than trying to publish the current shape too early.

## 11. Risks

### Risk 1: Product Scope Drift

If the team re-expands into authoring, marketplace, or multi-standard compatibility, the architecture will drift again and the extraction boundary will blur.

### Risk 2: Hidden Yue Coupling

If too much runtime logic stays mixed into skill internals, the extraction story will remain theoretical.

### Risk 3: Premature Externalization

If we try to open-source too early, we may freeze a messy public API and slow down product progress.

## 12. Recommended Next Moves

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

## 13. Bottom Line

The idea is good.

It is feasible to shape Yue's skill subsystem so that the reusable core can later become a small open-source project.

But the correct order is:

- **first strengthen the product boundary**
- **then strengthen the code boundary**
- **then extract**

Not the other way around.
