# Skill Runtime Core Orchestrator Status

## Objective

Lock execution to the Yue Skill Runtime Core externalization line, with immediate focus on `Stage D`.

## Locked Scope

- `Stage D: Normalize Configuration and Storage`

## Source Docs

- `docs/plans/skill_runtime_core_externalization_plan_20260423.md`
- `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- `docs/architecture/Skill_Runtime_Current_Operation.md`

## Current Stage

Stage D config/storage normalization

## Current Batch

- Status: completed
- Primary: `Stage D` minimal extraction-boundary draft for `skill-runtime-core` + `skill-tool-runtime`
- Sidecar:
  - host-layer ownership clarification (what must stay host-local)
  - migration sequence for next executable decoupling step
- Checkpoint condition:
  - file-level split is documented (`core` vs `tool-runtime` vs host)
  - bridge contract between packages is explicit
  - next minimal code step is concrete (`compatibility.py` decoupling)
  - status updated
  - verification recorded

## Completed

- Documented externalization direction and task list
- Documented reuse guide and current-operation guide
- `A1` established a first-pass core boundary inventory in `boundary_manifest.py`
- `A3` landed a machine-readable boundary manifest covering core, transitional, and Yue-only files
- `A4` added boundary regression coverage for file existence and known Yue-only import drift
- `A2` labeled key runtime files and misunderstood entrypoints with boundary-role comments
- `B1` aligned the compatibility singleton builder to the public `build_skill_runtime(...)` entry and documented the active runtime construction inventory
- `B2` removed additional implicit-center behavior from `skill_service.py` by trimming unused provider override state and keeping it focused on compatibility/runtime-access seams
- `B4` shifted API regression coverage away from module-level `config_service` / `agent_store` shims and toward runtime-context / host-adapter helper paths
- narrow `B3` sidecar: `skills.py` and `skill_imports.py` no longer expose module-level config/agent shims and now resolve host-owned request dependencies through helper functions backed by runtime host adapters
- `Stage C` moved group-aware visibility resolution out of core routing defaults and into host adapters via `GroupAwareAgentVisibilityResolver`
- updated compatibility wiring so Yue's singleton router binds host visibility resolvers instead of relying on router-owned group-store semantics
- updated boundary/doc assets so `routing.py` is now classified as `reusable_now`
- Stage D batch: added `YUE_SKILL_RUNTIME_STATIC_READONLY` support in runtime catalog/bootstrapping, force-disabled `skill-imports` + `skill-groups` route mounting under readonly, blocked `/api/skills/reload` in readonly mode, and added targeted regression tests
- Stage D batch: drafted minimal extraction boundary for splitting `skill-runtime-core` and `skill-tool-runtime`, including file-level ownership, bridge contract, and migration sequence in `docs/plans/skill_runtime_core_tool_runtime_minimal_extraction_boundary_20260424.md`

## Pending

- Stage D remaining: decouple `backend/app/services/skills/compatibility.py` from direct `app.mcp.builtin` import via injected supported-tool provider/list
- Stage D remaining: normalize compatibility error/detail code naming for readonly-specific mutation failures
- Stage D remaining: doc alignment for readonly env/behavior + boundary draft linkage in architecture/reuse guide

## Parallelizable Candidates

- Stage D docs sync (`Skill_Runtime_Current_Operation.md` + `SKILL_RUNTIME_CORE_REUSE_GUIDE.md`) to reference the new extraction boundary draft
- Stage D regression pass for readonly/detail-code consistency across `skills` and `skill_imports` APIs
- Stage D low-risk tests for injected supported-tool provider path in `SkillCompatibilityEvaluator`

## Blockers

- None recorded

## Latest Verification

- `python /Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/scripts/validate_status.py /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/execution/skill-runtime-core-orchestrator-status.md`
- `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q tests/test_skill_runtime_bootstrap_unit.py tests/test_api_skills.py tests/test_api_skill_imports.py`
- note: `tests/test_skill_runtime_catalog_unit.py` currently has an existing collection error in this workspace (`from app.main import _resolve_runtime_skill_directories` import target missing), so the full four-file batch could not be executed as one run
- `python -m compileall backend/app/services/skill_service.py backend/app/api/skills.py backend/app/api/skill_imports.py`
- `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q backend/tests/test_skill_service_runtime_context_unit.py backend/tests/test_api_skills.py backend/tests/test_api_skill_imports.py backend/tests/test_skill_runtime_bootstrap_unit.py backend/tests/test_skill_runtime_seams_unit.py backend/tests/test_import_gate_lifespan_smoke.py`
- `python -m compileall backend/app/services/skills/host_adapters.py backend/app/services/skills/routing.py backend/app/services/skill_service.py`
- `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest -q backend/tests/test_skill_runtime_seams_unit.py backend/tests/test_skill_service_runtime_context_unit.py backend/tests/test_skill_foundation_unit.py backend/tests/test_skill_runtime_integration.py backend/tests/test_skill_runtime_boundary_manifest_unit.py`

## Scope Drift Check

- 2026-04-24: User explicitly requested continuing the current mainline after `Stage A + B` completion, so the orchestrator advanced to `Stage C` on the same externalization line without changing plans.
- 2026-04-24: User confirmed no online dynamic import, no runtime-phase mutation, and no user-level dynamic visibility change; this batch stayed within Stage D by adding a static readonly runtime baseline instead of expanding scope.

## Recommended Next Batch

- Stage D follow-up: implement `SkillCompatibilityEvaluator` decoupling from `app.mcp.builtin` (inject tool-id provider/list), add targeted unit tests, and keep runtime behavior backward-compatible

## Decision Log

- 2026-04-24: Initialized orchestrator status for Skill Runtime Core Stage A + B execution.
- 2026-04-24: Completed `A1 + A3` with `A4` sidecar by landing `boundary_manifest.py` and boundary regression coverage.
- 2026-04-24: Completed `A2` with `B1` sidecar by labeling key files/entrypoints, routing compatibility singleton construction through `build_skill_runtime(...)`, and documenting the runtime construction inventory.
- 2026-04-24: Completed `B2 + B4` with a narrow `B3` sidecar by shrinking `skill_service.py` further, removing API module shim exports, and centering regression coverage on runtime-context / host-adapter paths.
- 2026-04-24: Advanced the mainline to `Stage C` after explicit user continuation, moved group-aware visibility semantics into host adapters, and reclassified `routing.py` as `reusable_now`.
- 2026-04-24: Completed a bounded Stage D static-readonly batch covering runtime flag parsing, readonly route gating, reload blocking, and focused regression coverage.
- 2026-04-24: Completed a bounded Stage D planning batch that drafts the minimal extraction boundary for `skill-runtime-core` vs `skill-tool-runtime` and locks the next concrete decoupling step.
