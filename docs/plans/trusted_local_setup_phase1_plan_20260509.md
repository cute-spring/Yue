# Trusted Local Setup Phase 1 Plan

Date: 2026-05-09

## Goal

Add a narrow, explicit `Trusted Local Setup` flow for copied open-source skill packages so a local user can prepare a skill for use without enabling default arbitrary third-party script execution.

Phase 1 must:

- support only manifest-declared `node` and `python` setup commands
- require explicit `Trust & Setup` approval from the user
- execute setup only inside an isolated per-skill environment
- reuse Yue's existing platform-tool boundary instead of introducing a skill-owned runner
- stop short of general chat-time arbitrary script execution

## Current Responsibilities And Existing Seams

### Parsing And Package Shape

- `SkillLoader.parse_markdown()` and `SkillLoader.parse_package()` already preserve `install` metadata from `SKILL.md`, but the runtime does not currently interpret it for setup execution.
- `SkillPackageSpec` and `SkillSpec` already include an `install` field, which is a natural contract anchor for Phase 1.

Relevant files:

- [backend/app/services/skills/models.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py:123)
- [backend/app/services/skills/parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py:563)

### Preflight And Skill Health

- preflight currently classifies skills as `available | needs_fix | unavailable`
- serialized preflight payload adds `mountable`, `visible_in_default_agent`, `status_message`, and `next_action`
- current health UX supports copying repair commands, but not trusting a skill, running setup, or surfacing setup state

Relevant files:

- [backend/app/services/skills/preflight_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/preflight_service.py:14)
- [backend/app/api/skill_preflight.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_preflight.py:48)
- [frontend/src/pages/SkillHealth.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.tsx:125)
- [frontend/src/types.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/types.ts:47)

### Runtime Action Boundary

- `SkillActionExecutionService` is intentionally `non_executing`
- current action flow exposes a stable preflight and approval contract and explicitly avoids a skill-owned runner
- this is the correct product boundary to preserve

Relevant files:

- [backend/app/services/skills/actions.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py:246)

### Shell Execution Capability

- `builtin:exec` already exists with deny patterns, optional allow patterns, workspace restriction, timeout control, and local-mode behavior
- Phase 1 should build on this rather than bypass it

Relevant files:

- [backend/app/mcp/builtin/exec.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/exec.py:57)

## Pain Points

1. copied open-source skills can be discovered and diagnosed, but not locally prepared through a trusted product flow
2. `install` metadata exists but is effectively inert
3. there is no persisted trust state, setup state, setup observability, or version/hash binding for a trusted package
4. the current UI can tell the user what to run, but cannot safely complete setup on the user's behalf
5. a direct jump to "auto-run arbitrary scripts" would violate the current platform boundary and create hidden risk

## Phase 1 Product Boundary

### In Scope

- a manifest-backed setup contract for `node` and `python`
- explicit trust approval before running setup
- isolated environment creation and reuse per skill package
- persisted setup state keyed to skill identity plus package fingerprint
- API support to inspect setup state and trigger setup
- Skill Health UI support for `Trust & Setup`
- focused tests and regression coverage

### Out Of Scope

- chat-time arbitrary third-party script execution
- auto-trusting newly copied packages
- support for shell-first freeform setup blocks
- global environment mutation
- package marketplace, signing, or remote provenance
- generalized runtime execution of all script actions

## Proposed Contract

### Package Manifest Extension

Phase 1 should standardize a narrow `install.setup` shape.

Proposed shape:

```yaml
install:
  setup:
    runtime: python | node
    commands:
      - python -m venv .yue/venv
      - .yue/venv/bin/pip install -r requirements.txt
```

Refinements for implementation:

- require `runtime`
- require non-empty `commands`
- commands must be plain strings
- commands must be validated against a setup command allow-policy before execution
- commands are executed from the skill package root

Phase 1 restriction:

- only packages with declared `install.setup.commands` are setup-capable
- setup capability is distinct from action invocation capability

### Persisted Skill Setup State

Add persisted state for each skill package, stored alongside preflight/import data.

Minimum fields:

- `skill_ref`
- `source_path`
- `manifest_path`
- `package_fingerprint`
- `trust_status`: `untrusted | trusted`
- `setup_status`: `not_needed | available | pending | running | succeeded | failed`
- `setup_runtime`
- `isolated_env_path`
- `last_setup_started_at`
- `last_setup_finished_at`
- `last_setup_error`
- `last_setup_commands`

This state should be decoupled from mount state. A skill may be mountable from a compatibility standpoint but still require trusted setup before the best local experience is available.

## Proposed Target Structure

### Backend

Keep the existing module layout, but add one narrow service rather than spreading logic through preflight API code.

Candidate additions:

- `backend/app/services/skills/setup_models.py`
- `backend/app/services/skills/setup_service.py`

Likely touched files:

- `backend/app/services/skills/import_models.py`
- `backend/app/services/skills/import_store.py`
- `backend/app/services/skills/parsing.py`
- `backend/app/services/skills/preflight_service.py`
- `backend/app/api/skill_preflight.py`
- `backend/app/services/skills/policy.py`

Service responsibilities:

- derive setup capability from package manifest
- compute package fingerprint
- resolve isolated environment directory
- validate setup commands against Phase 1 allow-policy
- orchestrate setup through platform execution boundary
- persist trust and setup results

### Frontend

Keep the current `SkillHealth` page as the Phase 1 entrypoint.

Likely touched files:

- `frontend/src/types.ts`
- `frontend/src/pages/SkillHealth.tsx`
- `frontend/src/pages/SkillHealth.test.ts`

UI responsibilities:

- show whether a skill supports trusted setup
- show whether the skill is trusted
- show setup status and last failure if any
- offer `Trust & Setup` only when supported and appropriate
- keep `Mount` separate from `Trust & Setup`

## Command Policy For Phase 1

Phase 1 must not accept arbitrary shell.

Recommended policy:

- allow only manifest-declared commands
- allow only `python`, `.venv/bin/python`, `pip`, `.venv/bin/pip`, `uv`, `node`, `npm`, `pnpm`, `yarn`
- reject shell metacharacter chaining such as `;`, `&&`, `||`, pipe-based download/install patterns, command substitution, and redirection outside isolated env paths
- require execution from the skill root
- require all generated env paths to stay under the skill package directory, for example:
  - `<skill-root>/.yue/python/`
  - `<skill-root>/.yue/node/`

Implementation note:

The existing `ExecTool` denylist and workspace guard remain useful but are not sufficient by themselves. Phase 1 needs an additional stricter setup-specific command validator.

## Isolated Environment Strategy

### Python

- create a per-skill venv under `<skill-root>/.yue/python/venv`
- install dependencies only into that venv
- execute later setup-related python commands through that venv path

### Node

- create a per-skill workspace under `<skill-root>/.yue/node/`
- install package dependencies locally there or inside the skill root only when the install target remains package-local
- do not install globally

### Shared Rules

- no writes outside the skill root
- no mutation of Yue backend/frontend dependency roots
- no use of user-global site packages or global npm prefix as the main install target

## Preflight And API Evolution

Preflight should expose setup readiness without conflating it with generic compatibility.

Recommended additions to serialized preflight payload:

- `setup_capable: boolean`
- `trust_status`
- `setup_status`
- `setup_required`
- `setup_supported_runtimes`
- `setup_status_message`
- `setup_next_action`
- `setup_last_error`

Suggested new endpoints:

- `POST /api/skill-preflight/{skill_ref}/trust`
- `POST /api/skill-preflight/{skill_ref}/setup`
- `GET /api/skill-preflight/{skill_ref}/setup`

Phase 1 behavior:

- `trust` records explicit approval
- `setup` is rejected if the package is not trust-approved
- `setup` is rejected if manifest setup contract is missing or invalid
- `setup` returns structured state/result, not raw shell output as the primary API contract

## TDD-First Execution Plan

### Step 1: Store And Model Contract

Write failing tests first for:

- persisted trust/setup record shape
- save/load/replace semantics
- default states for packages without setup metadata

Target tests:

- `backend/tests/test_skill_import_store_unit.py`
- new `backend/tests/test_skill_setup_state_unit.py` if separation improves clarity

### Step 2: Parse And Validate Setup Contract

Write failing tests first for:

- package parse includes `install.setup`
- invalid setup manifests are surfaced as warnings or `needs_fix`
- only `python` and `node` runtimes are accepted in Phase 1

Target tests:

- `backend/tests/test_skill_foundation_unit.py`
- `backend/tests/test_skill_preflight_service_unit.py`

### Step 3: Setup Service

Write failing tests first for:

- trust required before setup
- package fingerprint mismatch invalidates previous trust/setup state
- command allow-policy rejects dangerous or unsupported commands
- isolated env path resolution stays under skill root
- successful setup writes observability and state

Target tests:

- new `backend/tests/test_skill_setup_service_unit.py`

### Step 4: API Layer

Write failing tests first for:

- trust endpoint happy path
- setup endpoint rejects untrusted skill
- setup endpoint returns actionable structured errors
- list/detail endpoints surface trust/setup fields

Target tests:

- `backend/tests/test_api_skill_preflight.py`

### Step 5: Frontend Skill Health

Write failing tests first for:

- setup state rendering
- `Trust & Setup` button visibility rules
- new error/status mapping helpers
- trust/setup success and failure notices

Target tests:

- `frontend/src/pages/SkillHealth.test.ts`

### Step 6: Minimal Cleanup

After focused tests are green, run build/type checks and apply only minimal cleanup needed to keep the project green.

## Phased Migration Plan

### Phase 1A: Contract And Persistence

- add setup/trust models
- persist setup state
- expose setup metadata in preflight payload

### Phase 1B: Backend Orchestration

- implement setup policy validation
- implement trust endpoint
- implement setup endpoint
- wire isolated env handling

### Phase 1C: UI Entry Point

- add setup state rendering to Skill Health
- add `Trust & Setup`
- keep `Mount` behavior unchanged

### Phase 1D: Verification And Cleanup

- run focused backend tests
- run frontend tests
- run targeted build checks
- document residual risks

## Risk Assessment

### Primary Risks

1. trust state keyed too loosely
   - risk: modified package contents continue to run under stale trust
   - mitigation: persist package fingerprint and invalidate trust on mismatch

2. command policy too permissive
   - risk: Phase 1 becomes disguised arbitrary shell execution
   - mitigation: runtime allow-policy plus command-shape validation plus isolated cwd

3. isolated env writes escape skill root
   - risk: accidental mutation of Yue project or user-global environment
   - mitigation: canonical path checks for every derived path before execution

4. preflight status becomes overloaded
   - risk: confusing `available` versus `setup-ready`
   - mitigation: keep compatibility status separate from setup status in API and UI

5. long-running setup blocks request lifecycle
   - risk: poor UX or timeout mismatch
   - mitigation: Phase 1 may keep execution synchronous for simplicity only if bounded; otherwise return structured running state and store progress for polling

### Coupling Risks

- avoid embedding setup orchestration directly in `skill_preflight.py`
- avoid making `SkillActionExecutionService` the generic setup runner
- avoid changing chat runtime behavior in Phase 1

## Regression Strategy

Backend focused checks:

- `PYTHONPATH=. pytest tests/test_api_skill_preflight.py -q`
- `PYTHONPATH=. pytest tests/test_skill_preflight_service_unit.py -q`
- `PYTHONPATH=. pytest tests/test_skill_import_store_unit.py -q`
- `PYTHONPATH=. pytest tests/test_skill_foundation_unit.py -q -k "setup or install or exec"`

Frontend focused checks:

- `npm run test -- src/pages/SkillHealth.test.ts`

Build-fix cleanup if needed:

- `npm run build`

## Rollout Recommendation

Single narrow PR is acceptable for Phase 1 if kept tightly scoped to:

- setup/trust persistence
- setup service
- skill preflight API additions
- skill health UI
- tests

If the backend contract grows during implementation, split into:

1. backend setup state plus API
2. frontend health UI wiring

## What Should Not Change In Phase 1

- no change to ordinary skill mount semantics
- no general execution of package actions from chat
- no expansion of supported setup runtimes beyond `python` and `node`
- no marketplace, signing, or remote package governance

## Expected Implementation Recommendation

Proceed with a narrow TDD sequence:

1. persist trust/setup state
2. parse and validate `install.setup`
3. add trust/setup service
4. add preflight API support
5. add Skill Health UI entrypoint
6. run focused regression and minimal build-fix cleanup

That sequence gives the smallest effective vertical slice while preserving Yue's current "platform-tool-bounded" execution philosophy.
