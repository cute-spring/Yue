# Skill Kernel Library Extraction Plan (2026-03-29)

## 1. Purpose

This document is the execution plan for turning Yue's current skill system into a truly reusable Python library that can be adopted by other projects.

The target is not just "better modularization inside Yue".

The target is:

1. a host-neutral `skill_kernel` library
2. a thin Yue adapter layer that consumes that library
3. a packaging and verification story that allows another project to install and use the kernel without importing Yue app code

This plan should be read together with:

1. [`docs/plans/skill_package_contract_plan_20260327.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [`docs/plans/skill_kernel_extraction_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_kernel_extraction_plan_20260328.md)
3. [`docs/plans/skill_kernel_boundary_map_20260329.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_kernel_boundary_map_20260329.md)
4. [`docs/plans/skill_action_runtime_modularization_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_action_runtime_modularization_plan_20260328.md)
5. [`docs/plans/skill_service_modularization_plan_20260323.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md)

## 2. Current State

The current codebase already contains a strong reusable core, but it is still embedded inside the Yue application tree.

What is already close to library-shaped:

1. package contract models
2. package loading and normalization
3. registry and version-aware lookup
4. skill routing and visibility resolution
5. action descriptor models
6. action argument validation and approval gating
7. action lifecycle and event payload builders
8. browser continuity contracts and lookup interfaces

What is still Yue-bound:

1. global registry and router instances in [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. `chat_service` coupling in action execution setup
3. `skill_group_store` coupling in routing
4. `AgentConfig` coupling in the legacy adapter
5. FastAPI endpoints and SSE orchestration
6. Yue persistence and action-state projection
7. frontend trace/history UX

The practical conclusion is:

1. the kernel concept exists
2. the library boundary does not yet exist
3. the next work must be boundary extraction, not new feature breadth

## 3. Final Target Architecture

### 3.1 Reusable Library

The reusable library should live in a dedicated Python package, for example:

1. `backend/packages/skill_kernel/`
2. or `packages/skill_kernel/`

The exact directory can be chosen later, but the important rule is that the package must be installable and importable without Yue app modules.

The reusable library should expose:

1. contract models
2. loader and parser utilities
3. registry and directory resolution
4. routing and ranking utilities
5. schema validation and policy evaluation
6. action lifecycle contracts
7. browser continuity contracts
8. adapter interfaces for host integrations

The reusable library must not directly depend on:

1. FastAPI
2. Yue chat runtime
3. Yue persistence models
4. Yue frontend code
5. Yue global singleton instances

### 3.2 Yue Adapter Layer

Yue should keep a small adapter layer that wires the kernel into Yue's runtime.

That adapter layer may depend on:

1. `chat_service`
2. `skill_group_store`
3. `agent_store`
4. Yue tool registries
5. Yue persistence and SSE plumbing

But the adapter layer should only consume library contracts rather than define them.

### 3.3 Consumer Projects

A consuming project should be able to:

1. install the library
2. define its own skill directories
3. define its own registry bootstrap
4. plug in its own approval model
5. plug in its own persistence model
6. plug in its own chat or agent runtime
7. use the same skill packages without copying Yue code

## 4. Library Quality Bar

The extraction is complete only when the following are true:

1. the reusable package can be imported without any `app.services.*` dependency
2. the reusable package can be unit-tested without Yue app startup
3. the reusable package can be installed by another project as a normal Python dependency
4. the reusable package has a stable public API surface
5. the Yue adapter layer composes the library instead of being composed into it
6. no consumer needs to patch Yue globals to get the kernel behavior

## 5. Step-By-Step Plan

### Phase 0: Freeze The Contract

Goal:

1. define the exact public API the library will expose
2. define what is intentionally out of scope
3. lock the compatibility story before moving files

Deliverables:

1. a public module map for the library
2. a list of exported symbols
3. a list of Yue-only symbols that must not move into the library
4. a compatibility policy for legacy imports

Exit criteria:

1. we can say, module by module, what is kernel and what is adapter
2. we have a clear "do not import Yue app code from the library" rule
3. the first public API surface is narrow enough to be documented in one page

Concrete substeps:

1. inventory every symbol currently exported by `app.services.skill_service` and `app.services.skills`
2. label each symbol as `kernel`, `adapter`, or `Yue compatibility`
3. choose the final library package name and source layout
4. decide whether `skill_service.py` becomes a compatibility shim or a thin host adapter
5. define the compatibility policy for existing import paths and deprecation windows
6. define what must never enter the reusable library, even if it is skill-related

### Phase 1: Create The Library Skeleton

Goal:

1. create the new installable package directory
2. define the source layout
3. move no behavior yet, only structure

Recommended layout:

```text
skill_kernel/
├── pyproject.toml
├── src/skill_kernel/
│   ├── __init__.py
│   ├── contracts/
│   ├── loading/
│   ├── registry/
│   ├── policy/
│   ├── routing/
│   ├── runtime/
│   └── adapters/
└── tests/
```

Deliverables:

1. package metadata
2. importable namespace
3. public `__init__.py` re-export policy
4. initial smoke test proving the package imports cleanly

Exit criteria:

1. the new package can be installed in editable mode
2. the package imports without Yue app imports
3. a smoke test can import the package from a clean Python process

Concrete substeps:

1. create `pyproject.toml` for the new package
2. create `src/skill_kernel/` and `tests/` scaffolding
3. add a minimal `__init__.py` export surface
4. add one import-only test that proves the package starts cleanly
5. wire local editable installation for the workspace

### Phase 2: Move Pure Contracts

Goal:

1. move all host-neutral models into the library first
2. remove model duplication from Yue app modules

Move these first:

1. package specs
2. resource specs
3. overlay specs
4. action specs
5. runtime action request/result models
6. browser continuity request/result models
7. skill summaries and validation results

Rules:

1. models must not import FastAPI
2. models must not import Yue chat runtime
3. models must not import persistence services

Exit criteria:

1. app modules import models from the library
2. model tests pass in the new package location
3. no duplicate model definitions remain in Yue app modules except compatibility re-exports

Concrete substeps:

1. move `SkillPackageSpec`, `SkillResourceSpec`, `SkillActionSpec`, and related runtime request/result models first
2. move `SkillSpec`, `SkillSummary`, and `SkillValidationResult` next
3. move browser continuity request/result contracts with the rest of the runtime models
4. update Yue imports to use the library package directly where safe
5. keep temporary compatibility re-exports only when a caller migration would be too broad for one PR

### Phase 3: Move Loading And Normalization

Goal:

1. move package detection, manifest parsing, markdown parsing, and resource normalization into the library
2. keep the Yue behavior unchanged

Move these responsibilities:

1. legacy markdown parsing
2. package directory parsing
3. manifest derivation
4. references/scripts/overlays discovery
5. package validation
6. `SkillSpec` normalization

Additions needed:

1. explicit loader interfaces
2. parser error types or structured parse failures
3. a test fixture matrix for legacy markdown, basic package, and declared manifest package

Exit criteria:

1. Yue can still load the same skills through the new library code
2. a consuming project can point the loader at its own directories without Yue-specific setup
3. legacy markdown, basic package, and manifest-driven package fixtures all pass

Concrete substeps:

1. extract parser helpers and manifest helpers into focused modules
2. keep markdown parsing behavior unchanged while moving code
3. preserve package synthesis for implicit manifests
4. validate reference/script/overlay discovery against fixture packages
5. make structured parse failures explicit enough for consumer projects to handle
6. add tests for all supported package shapes before touching registry behavior

### Phase 4: Move Registry And Routing

Goal:

1. make registry and routing logic dependency-injected
2. remove reliance on Yue global stores from the reusable core

Required changes:

1. registry should accept directory resolution and validation collaborators
2. router should accept a skill-group resolver interface rather than importing Yue state
3. any default implementations should live behind optional host adapters

Specific boundary moves:

1. `skill_group_store` usage becomes adapter-owned
2. registry lifecycle stays in the library
3. route scoring stays in the library
4. visibility resolution becomes interface-based

Exit criteria:

1. the library can resolve skills without importing Yue stores
2. Yue still uses the same routing behavior through adapter wiring
3. default routing can run with an injected interface instead of a module global

Concrete substeps:

1. replace direct `skill_group_store` import usage with an injected resolver interface
2. keep a Yue adapter implementation that plugs in the existing store
3. move visibility resolution into the library while leaving policy-specific defaults outside
4. retain route scoring semantics and add regression tests for ranking parity
5. preserve legacy `resolved_visible_skills`, group, extra, and explicit skill resolution order

### Phase 5: Move Policy And Runtime Decision Logic

Goal:

1. keep the kernel responsible for generic policy and lifecycle decisions
2. keep execution side effects outside the kernel

Library-owned responsibilities:

1. schema validation
2. default filling
3. approval gating
4. invocation identity generation
5. lifecycle/status transition building
6. preflight result construction
7. browser continuity contract resolution

Adapter-owned responsibilities:

1. actual chat or tool execution
2. persistence writes
3. approval persistence
4. SSE emission

Exit criteria:

1. the kernel can compute "ready / blocked / approval required" without Yue runtime dependencies
2. the host adapter can turn those decisions into app-specific side effects
3. event payload builders remain deterministic and host-neutral

Concrete substeps:

1. split pure decision logic from side-effect orchestration
2. keep validation, approval, and lifecycle transitions in the kernel
3. move any request-to-stream integration glue into the adapter layer
4. ensure action preflight and approval messages stay identical for Yue callers
5. preserve lifecycle/status vocabulary and invocation-id generation

### Phase 6: Split Host-Neutral Runtime From Yue Runtime

Goal:

1. isolate the parts that are genuinely reusable from the parts that are app-specific
2. prevent the library from depending on Yue chat/session details

Move out of the library:

1. `chat_service` dependencies
2. action-state persistence
3. tool bridge wiring
4. stream orchestration
5. requested-action continuation logic

Keep in the library:

1. contracts
2. preflight and approval state machine
3. normalized event payload schemas
4. continuity interfaces

Exit criteria:

1. the kernel can be used in a non-Yue project with a different runtime
2. Yue-specific side effects become replaceable adapters
3. no kernel path requires `chat_service`, SSE, or persistence modules

Concrete substeps:

1. define explicit adapter interfaces for persistence, tool execution, and continuity lookup
2. keep only contracts and deterministic helpers inside the kernel
3. move execution bridging code into Yue-owned modules
4. add an external-consumer-style harness that uses a fake runtime instead of Yue services

### Phase 7: Build A Thin Yue Compatibility Layer

Goal:

1. keep Yue behavior stable while the new library takes over implementation
2. preserve old import paths for a deprecation window

Required work:

1. keep `backend/app/services/skill_service.py` as a shim or facade only
2. move global singletons behind explicit bootstrapping
3. keep compatibility exports for callers that have not migrated yet
4. update Yue app entrypoints to import from the library where possible

Exit criteria:

1. Yue still starts and behaves the same
2. the compatibility file becomes small and boring
3. no new feature work lands in the compatibility layer

Concrete substeps:

1. reduce `skill_service.py` to a facade that wires kernel objects to Yue services
2. remove any remaining inline implementations that duplicate library code
3. preserve existing import paths during the migration window
4. keep compatibility wrappers only where tests or callers still need them
5. update Yue app entrypoints to import from the library directly where possible

### Phase 8: Package For External Consumption

Goal:

1. make the kernel installable and versioned like a real library
2. define the public release surface

Required work:

1. add packaging metadata
2. define runtime dependencies explicitly
3. publish a minimal README or usage guide
4. define semantic versioning policy
5. define changelog/release notes policy

Exit criteria:

1. another project can install the library from a local path or wheel
2. the public API surface is documented
3. the library can be versioned independently of Yue

Concrete substeps:

1. add packaging metadata and dependency declarations
2. define a minimal README or usage guide for consumer projects
3. pin the public export surface in `__init__.py`
4. define semantic versioning and compatibility policy
5. confirm local wheel or editable install works in a clean virtualenv

### Phase 9: Validate With A Real Consumer

Goal:

1. prove the library works outside Yue
2. catch hidden Yue coupling before calling the extraction complete

Validation approach:

1. create a tiny external-style consumer harness in the repo
2. load a sample skill package through the library
3. route a skill request through the library
4. validate an action invocation through the library
5. verify the consumer harness does not import Yue app internals

Exit criteria:

1. the library works in an isolated consumer scenario
2. any lingering Yue coupling is surfaced and removed

Concrete substeps:

1. create a tiny standalone consumer harness in the repo
2. load a sample package through the library
3. resolve a skill selection through the library only
4. validate an action preflight/approval flow through the library only
5. confirm the consumer harness never imports Yue app modules

## 6. Recommended Migration Order

The safest order is:

1. contracts and models
2. loading and normalization
3. registry and routing
4. policy and runtime decisions
5. runtime adapters
6. Yue compatibility layer cleanup
7. packaging and consumer validation

This order reduces risk because each step moves from the most stable, least side-effectful code toward the most host-specific behavior.

## 6.1 Recommended PR Split

If this work is executed as a sequence of reviewable PRs, the cleanest split is:

1. PR 1: Phase 0 contract freeze and public surface inventory
2. PR 2: Phase 1 package skeleton and import smoke test
3. PR 3: Phase 2 contract extraction
4. PR 4: Phase 3 loader and normalization extraction
5. PR 5: Phase 4 registry and routing decoupling
6. PR 6: Phase 5 policy and runtime decision extraction
7. PR 7: Phase 6 adapter cleanup and Yue facade reduction
8. PR 8: Phase 7 packaging and external consumer harness

This split keeps each review focused on one type of boundary change.

## 6.2 File-Level Migration Map

This map is the practical bridge between the phase plan and code execution.

### Phase 0: Freeze The Contract

Primary files to review:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py)
3. [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
4. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
5. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
6. [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
7. [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
8. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)

Decision output:

1. final library module boundaries
2. final compatibility policy
3. final public export list

### Phase 1: Create The Library Skeleton

Primary files to add:

1. `packages/skill_kernel/pyproject.toml`
2. `packages/skill_kernel/src/skill_kernel/__init__.py`
3. `packages/skill_kernel/src/skill_kernel/contracts/__init__.py`
4. `packages/skill_kernel/src/skill_kernel/loading/__init__.py`
5. `packages/skill_kernel/src/skill_kernel/registry/__init__.py`
6. `packages/skill_kernel/src/skill_kernel/policy/__init__.py`
7. `packages/skill_kernel/src/skill_kernel/routing/__init__.py`
8. `packages/skill_kernel/src/skill_kernel/runtime/__init__.py`
9. `packages/skill_kernel/src/skill_kernel/adapters/__init__.py`
10. `packages/skill_kernel/tests/test_import_smoke.py`

Dependency rule:

1. this phase must not import Yue application code from the new package

### Phase 2: Move Pure Contracts

Primary files to move:

1. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
2. [`backend/app/services/skills/runtime_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_contracts.py)
3. [`backend/app/services/skills/browser_continuity_contracts.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/browser_continuity_contracts.py)

Follow-up compatibility files:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py)
3. [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
4. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)

### Phase 3: Move Loading And Normalization

Primary files to move:

1. [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
2. [`backend/app/services/skills/directories.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/directories.py)

Primary test files to extend or split:

1. existing skill foundation tests
2. manifest/package fixture tests
3. legacy markdown compatibility tests

### Phase 4: Move Registry And Routing

Primary files to move:

1. [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)
2. [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py)

Primary adapter file to keep:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)

### Phase 5: Move Policy And Runtime Decision Logic

Primary files to move:

1. [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
2. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
3. [`backend/app/services/skills/runtime_planning.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_planning.py)

### Phase 6: Split Host-Neutral Runtime From Yue Runtime

Primary files to review:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/services/chat_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)
3. [`backend/app/services/browser_continuity.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/browser_continuity.py)
4. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
5. [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

### Phase 7: Build A Thin Yue Compatibility Layer

Primary files to simplify:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
3. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)

### Phase 8: Package For External Consumption

Primary files to add:

1. `packages/skill_kernel/README.md`
2. `packages/skill_kernel/CHANGELOG.md`
3. `packages/skill_kernel/pyproject.toml`
4. `packages/skill_kernel/src/skill_kernel/__init__.py`

### Phase 9: Validate With A Real Consumer

Primary files to add:

1. `packages/skill_kernel/tests/test_external_consumer_harness.py`
2. `packages/skill_kernel/tests/fixtures/`
3. one minimal standalone consumer example inside the repo

## 6.3 Proposed Target Module Map

This is the suggested destination layout for the reusable library itself.

```text
packages/skill_kernel/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── src/
│   └── skill_kernel/
│       ├── __init__.py
│       ├── contracts/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── runtime.py
│       │   └── browser_continuity.py
│       ├── loading/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── manifest.py
│       │   └── resources.py
│       ├── registry/
│       │   ├── __init__.py
│       │   └── registry.py
│       ├── routing/
│       │   ├── __init__.py
│       │   └── router.py
│       ├── policy/
│       │   ├── __init__.py
│       │   └── policy.py
│       ├── runtime/
│       │   ├── __init__.py
│       │   ├── actions.py
│       │   ├── planning.py
│       │   └── events.py
│       └── adapters/
│           ├── __init__.py
│           ├── interfaces.py
│           └── compatibility.py
└── tests/
    ├── test_import_smoke.py
    ├── test_contracts.py
    ├── test_loader.py
    ├── test_registry.py
    ├── test_policy.py
    └── test_runtime.py
```

### Destination Rules

1. `contracts/` holds host-neutral pydantic models and normalization-friendly types.
2. `loading/` holds filesystem discovery, manifest parsing, package synthesis, and resource normalization.
3. `registry/` holds package registration, version lookup, and lifecycle state that remains kernel-owned.
4. `routing/` holds visibility resolution and scoring logic.
5. `policy/` holds argument validation, approval gates, and decision helpers.
6. `runtime/` holds lifecycle result building, events, and non-side-effectful orchestration helpers.
7. `adapters/` holds host interface definitions and optional compatibility helpers for consumer apps.

## 6.4 Suggested Migration Sequence Inside Each Phase

To reduce churn, each phase should follow the same internal order:

1. add the new library module
2. move pure helpers first
3. move model or contract types next
4. add or update tests in the new location
5. switch Yue imports to the new module
6. keep a compatibility re-export only if a current caller still depends on it
7. delete the old implementation only after the new path is verified

This sequencing is especially important for Phases 2 through 6, because those phases involve moving code that is already exercised by the current Yue runtime.

## 6.5 Dependency Cut Lines

These are the most important "do not cross" boundaries during extraction.

1. `contracts/` must not import Yue app modules.
2. `loading/` must not import FastAPI, chat runtime, or persistence.
3. `registry/` may depend on `loading/`, `contracts/`, and host-provided interfaces, but not on Yue globals.
4. `routing/` may depend on a skill lookup interface, but not on `skill_group_store` directly.
5. `policy/` must remain pure and deterministic.
6. `runtime/` may build events and results, but must not emit SSE or persist state.
7. `adapters/` may know about Yue or another host, but only behind explicit interface seams.

## 7. What Should Stay Out Of The Library

These concerns should remain in Yue or in another host application's own adapter layer:

1. FastAPI route handlers
2. SSE serialization
3. chat/session persistence
4. action-state storage
5. request streaming orchestration
6. UI rendering
7. host-specific tool registries
8. host-specific approval workflows
9. host-specific runtime globals

If a feature cannot be used by another project without Yue app context, it should not be in the reusable kernel.

## 8. Testing Strategy

The extraction should be gated by tests at each phase.

Recommended tests:

1. contract smoke tests
2. loader/manifest fixture tests
3. registry/routing unit tests
4. policy and validation unit tests
5. runtime lifecycle contract tests
6. adapter boundary tests
7. external consumer harness tests

Recommended test rule:

1. new library code must have tests in the library package itself
2. Yue tests should only verify integration with the library, not duplicate library behavior

## 9. Risk Register

### High Risk

1. moving too much logic out of Yue at once
2. breaking import compatibility for current app code
3. leaving hidden global state in the library
4. accidentally keeping Yue-specific dependencies in the public API

### Medium Risk

1. manifest normalization behavior changes
2. subtle differences in routing ranking
3. regression in legacy markdown compatibility
4. approval/status vocabulary drift

### Low Risk

1. pure model extraction
2. public re-export cleanup
3. packaging metadata addition

## 10. Rollout Policy

The extraction should be delivered as a sequence of small, reviewable PRs or commit groups.

Recommended rollout shape:

1. PR 1: library skeleton and model extraction
2. PR 2: loader and manifest normalization
3. PR 3: registry and routing
4. PR 4: policy and runtime contract builders
5. PR 5: Yue adapter cleanup
6. PR 6: packaging and consumer harness

Do not combine the library boundary change with feature changes.

## 11. Definition Of Done

The library extraction is done only when all of the following are true:

1. the reusable skill kernel is installable as a standalone Python package
2. no kernel module imports Yue app internals
3. Yue uses the library through a thin adapter layer
4. legacy skills still load and route correctly
5. package skills still support manifest/resource/overlay/action normalization
6. a non-Yue consumer can load and route skills with its own adapters
7. the public API is documented and versioned

## 12. Recommendation

The recommended next move is to execute this plan in the order above, starting with the library skeleton and pure contract extraction.

That is the fastest path to a true reusable library because it separates "what the skill system is" from "how Yue hosts it".
