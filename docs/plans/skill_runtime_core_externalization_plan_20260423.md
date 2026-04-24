# Skill Runtime Core Externalization Plan

**Date**: 2026-04-23

## 1. Purpose

This document defines the plan for turning Yue's current skill subsystem into a highly reusable `Skill Runtime Core` that can be copied or packaged into another project using the same technology stack with low integration effort.

The target outcome is not just "code that happens to work elsewhere".

The target outcome is:

1. a high-cohesion core with explicit boundaries
2. a thin host adapter layer
3. a stable integration contract
4. a repeatable migration guide
5. a regression harness that proves the core remains portable

## 2. Desired End State

The desired end state is:

- another FastAPI-based project can adopt the skill runtime by integrating a small set of adapters and configuration values
- the host project does not need to understand Yue-specific storage, startup, or chat internals to use the runtime
- Yue-specific behavior remains possible, but is pushed into the adapter layer instead of leaking into the core

In practical terms, the reusable form should look like:

```text
skill_runtime_core/
  models/
  parsing/
  registry/
  compatibility/
  routing/
  import_gate/
  actions/
  seams/
  bootstrap/

host_project/
  adapters/
  api/
  app_startup/
```

## 3. Current Position

Yue already has a partially extracted skill subsystem under:

- [`backend/app/services/skills`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills)
- [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
- [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
- [`backend/app/api/skill_imports.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_imports.py)
- [`backend/app/api/skill_groups.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_groups.py)

This is a strong starting point because:

1. parsing, validation, routing, import models, runtime seams, and registry logic are already grouped
2. runtime mode and import-gate semantics already exist
3. tests already cover large parts of the subsystem

This is not yet a portable core because:

1. the subsystem still imports Yue-specific modules directly
2. startup wiring still assumes Yue lifecycle and filesystem layout
3. storage and environment naming are still Yue-branded
4. compatibility wrappers and global singletons remain on critical paths

## 4. Main Gap Assessment

### 4.1 What is already close to reusable

These areas are already close to "core":

- [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
- [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)
- [`backend/app/services/skills/import_models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/import_models.py)
- [`backend/app/services/skills/import_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/import_service.py)
- [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
- parts of [`backend/app/services/skills/runtime_seams.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_seams.py)

### 4.2 What still blocks low-effort reuse

The main blockers are:

1. direct imports from `app.services.*`
2. global singleton runtime construction in `skill_service.py`
3. Yue-specific visibility and group semantics inside routing adapters
4. Yue-specific env names such as `YUE_DATA_DIR` and `YUE_SKILL_RUNTIME_MODE`
5. startup and API wiring that assumes Yue app layout
6. lack of a single documented bootstrap API for host projects

## 5. Reuse Design Principles

To reach high portability, the extracted core should follow these principles:

### 5.1 Package-first

The core should be importable as one package with explicit public exports.

### 5.2 Dependency inversion

The core must depend on interfaces, not on Yue service implementations.

### 5.3 Stable contracts

The host project should integrate against a small set of typed contracts:

1. `AgentProvider`
2. `FeatureFlagProvider`
3. `SkillGroupResolver`
4. `ToolCapabilityProvider`
5. `RuntimeStorageProvider`
6. `PromptInjectionAdapter`

### 5.4 Explicit bootstrap

A host should initialize the runtime with something like:

```python
runtime = build_skill_runtime(config=...)
register_host_runtime_adapters(runtime, adapters=...)
mount_skill_runtime_routes(app, runtime=runtime, route_strategy=...)
```

Important note:

- this is the **target integration shape**, not the exact final API that exists today
- today the runtime already has `build_skill_runtime(...)`, `bootstrap_skill_runtime_lifespan(...)`, and `mount_skill_runtime_routes(...)`
- today host adapter registration still flows through the Stage4 compatibility shell in `skill_service.py`
- the externalization work must close that gap instead of pretending it is already gone

### 5.5 Separate core from host adapters

The core should know nothing about:

- Yue chat sessions
- Yue agent store
- Yue config service
- Yue frontend pages

Those remain in the host adapter layer.

## 5.6 Two adoption profiles

To keep the plan executable, we should explicitly support two adoption profiles.

### Profile A: Copy-first adoption

This is the near-term path.

The host project copies:

1. the runtime core candidate package under `backend/app/services/skills`
2. the transitional compatibility shell in `skill_service.py`
3. the Yue route handlers or host-local equivalents

This profile is acceptable during Stage A-E because it minimizes rewrite risk.

### Profile B: Package-first adoption

This is the end-state path.

The host project installs or vendors a dedicated `skill_runtime_core` package and only writes:

1. host adapters
2. host route strategy
3. startup/bootstrap wiring

The plan should treat Profile A as the migration path and Profile B as the final reusable state.

## 6. Delivery Plan

### Stage A: Define Core Boundary

Goal:

- stop treating the current `skills` package plus `skill_service.py` as one mixed unit

Changes:

1. define a formal `skill_runtime_core` public surface
2. document which files are core vs adapter
3. add a boundary manifest listing allowed imports

Current checkpoint artifact:

- [`backend/app/services/skills/boundary_manifest.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/boundary_manifest.py)

Acceptance:

- every file in the future core package is either pure domain logic or depends only on core contracts
- boundary violations are detectable in CI
- the plan explicitly labels which files are:
  - reusable now
  - transitional but still required for copy-first adoption
  - Yue-only and must not be copied into the future core package

### Stage B: Remove Global Runtime Construction From Critical Paths

Goal:

- make runtime creation explicit and host-controlled

Changes:

1. replace module-level default singleton usage with runtime factories
2. preserve a compatibility shim for Yue during migration
3. move `Stage4LiteRuntimeProviders` from transitional seam to primary runtime construction path

Acceptance:

- API and startup paths can resolve runtime dependencies from one explicit runtime container
- tests no longer need to patch module-level globals in most cases

### Stage C: Extract Yue-Specific Visibility and Group Resolution

Goal:

- keep routing reusable while moving Yue visibility policy outside the core

Changes:

1. move `AgentVisibilityResolver` semantics behind a protocol
2. keep lexical scoring and candidate ranking in core
3. move `skill_group_store` assumptions into a Yue adapter

Acceptance:

- routing can run in another project without importing Yue `skill_group_store`

### Stage D: Normalize Configuration and Storage

Goal:

- make the runtime portable across projects and naming conventions

Changes:

1. replace hardcoded `YUE_*` environment usage in the core with a config object
2. support host-defined data dir, user skill dir, runtime mode, and watch settings
3. move storage filenames and persistence paths behind a storage/config provider
4. require explicit directory configuration for non-Yue hosts instead of relying on Yue repository-relative defaults

Acceptance:

- a host project can rename env vars without editing core logic
- the core can run under a different data root without patching source
- the docs clearly state that repository-relative defaults are Yue conveniences, not reusable contract

### Stage E: Publish Bootstrap and Integration API

Goal:

- make adoption operationally simple

Changes:

1. provide `build_skill_runtime(...)`
2. provide `mount_skill_runtime_routes(...)`
3. provide reference adapters for FastAPI and file-based storage
4. provide a host-owned `route_strategy` example so route mounting no longer assumes Yue route modules
5. document minimal host implementation

Acceptance:

- a new same-stack project can integrate using adapter stubs and the documented bootstrap sequence
- a non-Yue host can mount routes without importing `app.api.skills`, `app.api.skill_imports`, or `app.api.skill_groups` from Yue

### Stage F: Build Portability Regression Harness

Goal:

- prove the runtime remains reusable over time

Changes:

1. create a host-simulator fixture package
2. add black-box tests against the bootstrap API
3. add import-boundary checks and contract tests

Acceptance:

- CI proves the runtime can boot and answer API calls outside Yue-specific startup

## 7. Recommended File Evolution

### 7.1 Move toward core package

Primary candidates:

- `models.py`
- `parsing.py`
- `import_models.py`
- `import_service.py`
- `policy.py`
- `compatibility.py`
- large parts of `registry.py`
- large parts of `runtime_catalog.py`
- routing scoring logic from `routing.py`
- action contracts from `actions.py`

These should be classified as:

1. reusable now
2. reusable after small interface cleanup
3. not reusable yet

### 7.2 Keep as Yue adapter

Primary candidates:

- `skill_service.py` during transition
- `main.py` startup hooks
- `api/skills.py`, `api/skill_imports.py`, `api/skill_groups.py` until route mounting is generalized
- `skill_group_store.py`
- `agent_store.py`
- `chat_prompting.py`
- frontend `Chat.tsx`, `SkillGroups.tsx`, and `types.ts`

## 7.3 Transitional copy set vs future package set

To avoid implementation confusion, the plan should distinguish these two sets explicitly.

### Transitional copy set

Files that another same-stack host may still copy during the migration era:

- `backend/app/services/skills/`
- `backend/app/services/skill_service.py`
- host-local or copied route handlers

### Future package set

Files that should remain once externalization is complete:

- pure runtime core package
- host adapters
- host route strategy
- host startup/bootstrap wiring

## 8. Definition of Done

The `Skill Runtime Core` effort is done when:

1. the reusable core no longer imports Yue-specific modules directly
2. the host project integrates the runtime through documented adapters and bootstrap helpers
3. a same-stack project can adopt the runtime with small configuration changes and no invasive rewrites
4. Yue still runs on top of the new boundary without losing behavior
5. the migration path is documented for both maintainers and adopters
6. the docs no longer require adopters to infer whether they should copy `skill_service.py`, Yue route modules, or only the core package

## 9. Companion Documents

This plan is meant to be read together with:

- [`docs/architecture/Skill_Runtime_Current_Operation.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/architecture/Skill_Runtime_Current_Operation.md)
- [`docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md)
