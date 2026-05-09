# Trusted Local Setup Phase 1 Status Audit

Date: 2026-05-10
Plan baseline: [trusted_local_setup_phase1_plan_20260509.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/trusted_local_setup_phase1_plan_20260509.md)

## Audit Overview

This audit compares the current implementation against the Phase 1 plan for Trusted Local Setup.

### Core conclusion

Phase 1 is implemented and closeout-verified. The backend persistence, preflight enrichment, trust/setup API flow, Skill Health UI entrypoint, stricter command-policy alignment, and a real setup-capable demo fixture are all present and covered by focused tests.

## Planned Goals Audit

| Plan item | Status | Audit notes |
| :--- | :--- | :--- |
| Store and model contract | ✅ | `SkillPreflightRecord` now persists trust/setup state, timestamps, commands, fingerprint, isolated env path, and audit entries in [backend/app/services/skills/import_models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/import_models.py:150) and [backend/app/services/skills/import_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/import_store.py:170). |
| Parse and validate `install.setup` | ✅ | `SkillSetupService.parse_install_setup()` validates runtime and command list, and preflight surfaces invalid setup metadata as issues in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:42) and [backend/app/services/skills/preflight_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/preflight_service.py:86). |
| Setup orchestration service | ✅ | Trust approval, fingerprint invalidation, isolated env derivation, command validation, execution, and setup observability are implemented in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:60). |
| API support for trust/setup inspection and execution | ✅ | `GET /setup`, `POST /trust`, and `POST /setup` are implemented with structured actionable errors in [backend/app/api/skill_preflight.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_preflight.py:247). |
| Skill Health UI support for `Trust & Setup` | ✅ | Trusted setup status, next action, failure display, and `Trust & Setup`/retry affordances are present in [frontend/src/pages/SkillHealth.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.tsx:134) and typed in [frontend/src/types.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/types.ts:80). |
| Preserve platform-tool boundary | ✅ | Setup runs through the existing exec boundary via `build_exec_tool_config()` and `run_exec_argv()` in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:12), while `SkillActionExecutionService` still explicitly avoids becoming a skill-owned runner in [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py:246). |
| Command-policy alignment | ✅ | Phase 1 now accepts the intended narrow `uv` Python setup shapes and a narrow `node <local-script>` shape while keeping package-local path validation in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:118). |
| Root-based node execution semantics | ✅ | Validated node setup commands now execute from the skill root, matching the plan, while `.yue/node` is still prepared as an isolated package-local workspace in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:239). |
| Real setup-capable package coverage | ✅ | A real demo fixture with `install.setup` now exists at [trusted-local-setup-uv-demo](</Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/fixtures/skills/trusted-local-setup-uv-demo>) and is exercised through rescan -> trust -> setup -> status retrieval in [backend/tests/test_api_skill_preflight.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skill_preflight.py:369). |
| Focused regression coverage | ✅ | Focused backend and frontend checks passed on 2026-05-10 with the aligned command-policy and fixture coverage: `59` backend tests and `18` frontend Skill Health tests. |

## Status Notes

### 1. Setup command policy now matches the intended narrow Phase 1 contract

- Accepted Python shapes now include:
  - `python -m venv ...`
  - venv `python -m pip install ...`
  - venv `pip install ...`
  - `uv venv ...`
  - `uv pip install --python <skill-root>/.yue/python/venv/bin/python ...`
- Accepted Node shapes now include:
  - `npm install --prefix .yue/node`
  - `pnpm install --dir .yue/node`
  - `yarn install --cwd .yue/node`
  - `node <package-local-script>`
- Evidence:
  - executable allow sets: [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:20)
  - Python validation: [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:160)
  - Node validation: [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:203)
  - edge-case coverage for missing path-flag values and venv-local executable paths: [backend/tests/test_skill_setup_service_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_setup_service_unit.py:273)

### 2. Node setup now runs from the skill package root

- Command validation now returns the skill root as execution `cwd` for both runtimes:
  - [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:239)
- Focused tests lock this behavior down for `npm`, `pnpm`, `yarn`, and `node` script execution:
  - [backend/tests/test_skill_setup_service_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_setup_service_unit.py:196)

### 3. Real end-to-end fixture coverage now exists

- The repo now includes a checked-in demo fixture with a real `install.setup` block:
  - [SKILL.md](</Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/fixtures/skills/trusted-local-setup-uv-demo/SKILL.md>)
  - [manifest.yaml](</Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/fixtures/skills/trusted-local-setup-uv-demo/manifest.yaml>)
- API coverage proves the realistic flow with actual `uv` execution:
  - [backend/tests/test_api_skill_preflight.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skill_preflight.py:369)

## Verification

The following focused checks passed locally on 2026-05-10:

- `cd backend && PYTHONPATH=. pytest tests/test_skill_setup_service_unit.py tests/test_skill_preflight_service_unit.py tests/test_api_skill_preflight.py tests/test_skill_import_store_unit.py -q`
- `cd frontend && npm run test -- src/pages/SkillHealth.test.ts`

Results:

- Backend: `59 passed`
- Frontend: `18 passed`

## Recommended Next Priorities

### Priority 1: Final review and packaging

- Do a short read-only safety review of the command-policy boundary and residual plan alignment.
- Package the backend/service/test/doc changes into the Phase 1 completion changeset.

### Priority 2: Optional product polish

- Surface `setup_audit_summary` or command history in the UI if we want better operator visibility during failures.
- Consider whether synchronous setup is sufficient for expected package sizes before broadening rollout.

## Decision Summary

- Current assessment: Phase 1 is functionally complete and aligned with the written command-policy and execution-semantics contract.
- Shipping readiness: commit-ready. The read-only review found no blocking issues after edge-case coverage for malformed node path flags and venv-local executable paths was tightened.
- Best next move: finish the final review pass and package this as the Phase 1 completion changeset.
