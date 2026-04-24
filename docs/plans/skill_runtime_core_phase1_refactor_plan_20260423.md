# Skill Runtime Core Phase 1 Refactor Plan

**Date**: 2026-04-23

## Context

Yue now has:

1. a documented future-state plan for `Skill Runtime Core`
2. a migration guide for reuse in another same-stack project
3. a current-state runtime operations document

The next step is to begin the first implementation phase that reduces coupling without destabilizing current Yue behavior.

## Current Pain Points

The highest-value remaining issues in the current backend path are:

1. runtime construction is still centered around `skill_service.py` module-level globals
2. runtime configuration is still mostly implicit and environment-driven
3. API entrypoints still depend directly on Yue-specific host services on critical paths
4. startup wiring still resolves runtime config in `main.py` instead of through a runtime-facing config boundary

## Phase 1 Goal

Introduce a small but real `Skill Runtime Core` boundary by:

1. extracting a host-facing runtime config object
2. extracting host adapter protocols/interfaces for agent lookup, feature flags, and skill-group resolution
3. making runtime context/build paths more explicit
4. reducing direct host-service coupling in critical API paths

This phase must preserve existing external behavior.

## Write Scope

This phase may modify:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
2. [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py)
3. new `backend/app/services/skills/bootstrap.py`
4. new `backend/app/services/skills/host_adapters.py`
5. [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py)
6. [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
7. [`backend/app/api/skill_imports.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_imports.py)
8. focused backend tests only

This phase must not modify:

1. frontend files
2. broad chat runtime behavior
3. route names or public API shapes unless required for bug-fix compatibility

## Proposed Structure

### New runtime-facing boundary

Add:

1. `SkillRuntimeConfig`
2. env-to-config resolver helpers
3. explicit runtime singleton builder
4. host adapter protocols and Yue-backed default implementations

### Existing compatibility shell

Keep:

1. `skill_service.py` global exports
2. current router compatibility wrapper
3. current route handlers and response contracts

But change the shell so it delegates more clearly to the new runtime-facing boundary.

## Test Strategy

Tests must be added before implementation for:

1. env-to-runtime-config resolution
2. runtime singleton construction through an explicit builder
3. host adapter override/reset behavior
4. existing API paths continuing to work through adapter indirection

Focused regression commands after implementation:

```bash
pytest -q \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

## Risks

### Risk 1: Breaking compatibility tests that patch module-level globals

Mitigation:

1. preserve global exports
2. keep default provider behavior stable
3. add new override hooks rather than replacing old seams outright

### Risk 2: Moving too much host logic at once

Mitigation:

1. only extract config and adapter boundaries in this phase
2. do not move chat-path prompt assembly yet

### Risk 3: Startup regressions

Mitigation:

1. keep current `main.py` lifecycle shape
2. only replace env parsing and directory resolution entry helpers

## Expected Outcome

At the end of this phase:

1. the runtime has an explicit config object
2. the runtime exposes host adapter interfaces
3. `main.py` and core API entrypoints depend less directly on Yue-specific globals
4. future extraction work can move more code without first reopening runtime creation and host-coupling questions

## Execution Update

### What actually changed

1. Added [`backend/app/services/skills/bootstrap.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py) with:
   - `SkillRuntimeConfig`
   - env-to-config resolution
   - explicit runtime singleton builder
   - runtime directory resolution helper
2. Added [`backend/app/services/skills/host_adapters.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/host_adapters.py) with host-facing protocols/interfaces and simple store-backed implementations.
3. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export the new config/bootstrap/adapter symbols.
4. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) so default runtime singleton construction now delegates to the new bootstrap path and host adapters can be overridden/reset through an explicit seam.
5. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py) so runtime mode, watch config, and directory resolution now flow through `SkillRuntimeConfig` and `resolve_runtime_skill_directories(...)`.
6. Updated [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py) and [`backend/app/api/skill_imports.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_imports.py) to depend on host adapter seams rather than hardwiring host services in the main code path.
7. Added tests:
   - [`backend/tests/test_skill_runtime_bootstrap_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py)
   - new host-adapter override coverage in [`backend/tests/test_skill_service_runtime_context_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_service_runtime_context_unit.py)

### Behavior compatibility handling

1. Preserved module-level runtime globals in `skill_service.py`.
2. Preserved the API surface and route names.
3. Restored the historical `skill_group_store` patch seam in the compatibility `SkillRouter` after a regression surfaced in integration coverage.
4. Kept lightweight compatibility shims in API modules so existing tests patching `config_service` and `agent_store` still work.

### Deviation from the original phase scope

1. The new host adapter interfaces were introduced and used in API/runtime construction paths, but skill-group routing was not yet fully moved onto those interfaces.
2. To avoid broad churn, compatibility shims were retained in API modules instead of removing all legacy patch points in one step.
3. Chat-path extraction was intentionally left untouched.

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `93 passed`
2. no test failures after restoring the `skill_group_store` compatibility seam

## Phase 2 Continuation Update (Routing Visibility Decoupling)

### Additional goal

Reduce Yue-specific default coupling in routing visibility resolution while keeping compatibility behavior stable.

### What changed

1. Updated [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py):
   - removed direct dependency on module-level default `skill_group_store`
   - changed default visibility behavior to resolver-injected mode
   - kept `skill_group_store` compatibility property and setter for existing callers
2. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py):
   - `set_stage4_lite_host_adapters(...)` now updates the singleton router's group resolver
   - `reset_stage4_lite_host_adapters()` restores default resolver binding
   - default host adapters are now bound to the singleton router at initialization
3. Added regression coverage in [`backend/tests/test_skill_service_runtime_context_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_service_runtime_context_unit.py) for host-adapter-driven router visibility binding.

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `94 passed`
2. routing visibility regression coverage remains green
3. API/import/lifespan paths remain stable

## Phase 3 Continuation Update (Reusable Bootstrap API)

### Additional goal

Ship reusable bootstrap APIs so same-stack hosts can mount runtime routes and build runtime containers with less copy-and-paste integration code.

### What changed

1. Updated [`backend/app/services/skills/bootstrap.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py):
   - added `build_skill_runtime(...)`
   - added `mount_skill_runtime_routes(...)`
2. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export both APIs.
3. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py) to use `mount_skill_runtime_routes(app)` instead of hand-written per-router mounting for skill runtime endpoints.
4. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py):
   - runtime catalog dependency resolution now prefers runtime context path by default
   - keeps compatibility fallback when module-level aliases are explicitly monkeypatched
5. Added/expanded tests:
   - [`backend/tests/test_skill_runtime_bootstrap_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py)
   - [`backend/tests/test_skill_service_runtime_context_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_service_runtime_context_unit.py)

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `98 passed`
2. reusable bootstrap API coverage is green
3. runtime visibility, API, import-gate, and lifespan integration paths remain green

## Phase 4 Continuation Update (Pluggable Route Strategy + Host Config Mapping)

### Additional goal

Make runtime route mounting host-pluggable and reduce Yue-specific config coupling by moving `YUE_*` dependence behind a host config adapter with neutral key aliases.

### What changed

1. Updated [`backend/app/services/skills/bootstrap.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py):
   - added `HostConfigAdapter` protocol
   - added `EnvHostConfigAdapter` with key alias mapping support
   - added neutral config aliases (`SKILL_RUNTIME_*`) with Yue fallback aliases (`YUE_*`)
   - extended `resolve_skill_runtime_config_from_env(...)` to accept host adapter/env/key alias injection while keeping backward-compatible defaults
   - added `SkillRuntimeRouteMountOptions`
   - added `SkillRuntimeRouteStrategy` protocol and `DefaultSkillRuntimeRouteStrategy`
   - extended `mount_skill_runtime_routes(...)` to support `route_strategy`, `route_options`, and host-config-driven mount options
2. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export new Phase 4 bootstrap symbols.
3. Expanded [`backend/tests/test_skill_runtime_bootstrap_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py):
   - neutral key precedence over Yue fallback
   - custom host key alias support
   - route strategy injection coverage
   - optional route disable assertion tightened to concrete mounted path forms

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `101 passed`
2. new host-config and route-strategy seams are green
3. existing API/import/lifespan/runtime integration behavior remains green

## Phase 5 Continuation Update (Bootstrap Spec Solidification)

### Additional goal

Further reduce host integration boilerplate by introducing a reusable bootstrap spec so hosts can wire runtime routes/config through one stable entry path.

### What changed

1. Updated [`backend/app/services/skills/bootstrap.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py):
   - added `RuntimeBootstrapSpec`
   - added `build_skill_runtime_bootstrap_spec_from_env(...)`
   - added `bootstrap_skill_runtime_app(...)`
   - extended `mount_skill_runtime_routes(...)` to accept `bootstrap_spec` while preserving legacy parameter behavior when spec is not provided
2. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py):
   - app startup now creates one `_skill_runtime_bootstrap_spec`
   - route mounting now uses `bootstrap_skill_runtime_app(app, bootstrap_spec=...)`
   - lifespan runtime config now reads from the same bootstrap spec to avoid duplicated env parsing paths
3. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export new bootstrap-spec APIs.
4. Expanded [`backend/tests/test_skill_runtime_bootstrap_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py):
   - added spec-from-env route option coverage
   - added bootstrap-app mount coverage via `RuntimeBootstrapSpec`

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `103 passed`
2. bootstrap spec path is green
3. existing route/config behavior remains backward-compatible

## Phase 6 Continuation Update (Unified Host Runtime Adapter Registration)

### Additional goal

Provide one host-facing registration entry that groups agent/group/feature-flag adapters together with host config mapping, and provide a minimal host integration example to reduce cross-project wiring effort.

### What changed

1. Updated [`backend/app/services/skills/host_adapters.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/host_adapters.py):
   - added `HostConfigProvider` protocol
   - added `HostRuntimeAdapterBundle`
   - added `build_default_host_runtime_adapter_bundle(...)`
2. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py):
   - added host-config adapter seam:
     - `set_stage4_lite_host_config_adapter(...)`
     - `reset_stage4_lite_host_config_adapter()`
     - `get_stage4_lite_host_config_adapter()`
   - added unified registration API:
     - `register_stage4_lite_host_runtime_adapter_bundle(...)`
   - registration API now atomically applies:
     - stage4 host adapters (agent/feature-flag/group)
     - stage4 host config adapter
3. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py):
   - bootstrap spec creation now reads optional host config adapter from skill-service seam.
4. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export the new host bundle builder/types.
5. Added minimal host integration sample:
   - [`examples/host_integration/minimal_fastapi_host.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/examples/host_integration/minimal_fastapi_host.py)
6. Expanded runtime-context tests:
   - [`backend/tests/test_skill_service_runtime_context_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_service_runtime_context_unit.py)
   - added coverage for host-config seam and unified bundle registration.

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `105 passed`
2. unified host registration path is green
3. existing runtime/API behavior remains stable

## Phase 7 Continuation Update (Reusable Lifespan Bootstrap + Host Smoke Kit)

### Additional goal

Expose a reusable runtime lifespan bootstrap API so host projects can wire startup/shutdown with one lifecycle entry, and provide a minimal host smoke kit (`.env.example` + commands).

### What changed

1. Updated [`backend/app/services/skills/bootstrap.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py):
   - added `bootstrap_skill_runtime_lifespan(...)`
   - lifecycle now encapsulates:
     - runtime directory resolution
     - layered dir registration
     - skill registry load
     - legacy-mode watch start / import-gate watch skip log
     - startup and shutdown hooks
     - watch cleanup on shutdown
2. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py):
   - replaced inline skill runtime lifespan logic with `bootstrap_skill_runtime_lifespan(...)`
   - kept MCP manager + health monitor lifecycle via startup/shutdown hooks
3. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export `bootstrap_skill_runtime_lifespan`.
4. Expanded [`backend/tests/test_skill_runtime_bootstrap_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py):
   - added lifecycle test for registry load/watch and hook execution order
   - added import-gate watch-skip test
5. Added host integration smoke kit:
   - [`examples/host_integration/.env.example`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/examples/host_integration/.env.example)
   - [`examples/host_integration/README.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/examples/host_integration/README.md)

### Validation results

Executed:

```bash
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q \
  backend/tests/test_skill_runtime_bootstrap_unit.py \
  backend/tests/test_skill_service_runtime_context_unit.py \
  backend/tests/test_skill_runtime_seams_unit.py \
  backend/tests/test_skill_runtime_integration.py \
  backend/tests/test_api_skills.py \
  backend/tests/test_api_skill_imports.py \
  backend/tests/test_import_gate_lifespan_smoke.py
```

Observed result:

1. `107 passed`
2. lifespan bootstrap path is green
3. API/import/lifespan integration remains stable
