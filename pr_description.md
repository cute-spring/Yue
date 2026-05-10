## Summary

Close out Trusted Local Setup Phase 1 by aligning the command-policy implementation with the written contract and packaging the final verification evidence.

This changeset finishes the backend side of Phase 1 by:
- adding narrow `uv` Python setup support
- adding narrow `node <package-local-script>` support
- running Node setup from the skill root while keeping package-local isolated env paths
- supporting venv-local `python` / `pip` paths
- cleanly rejecting malformed `--prefix` / `--dir` / `--cwd` flag shapes
- adding a real setup-capable demo fixture and end-to-end API coverage
- refreshing the Phase 1 audit with final verification status

## What Changed

### Backend
- Updated `SkillSetupService` command validation to accept the intended narrow Phase 1 command shapes:
  - `uv venv ...`
  - `uv pip install --python <skill-root>/.yue/python/venv/bin/python ...`
  - `node <package-local-script>`
  - venv-local `python` / `pip` install commands
- Changed validated setup execution to run from the skill root for both runtimes.
- Added explicit rejection for malformed path-flag commands that omit a required value.
- Preserved package-local path containment and isolated env preparation.

### Tests and Fixtures
- Added a real setup-capable demo fixture under:
  - `backend/tests/fixtures/skills/trusted-local-setup-uv-demo/`
- Expanded unit coverage for:
  - `uv` positive-path execution
  - venv-local `python` / `pip` execution
  - root-based Node `cwd` behavior
  - `node <local-script>` execution
  - malformed `--prefix` / `--dir` / `--cwd` rejection
- Strengthened API happy-path coverage for:
  - trust -> setup success
  - rescan -> trust -> setup -> status using the real `uv` fixture

### Documentation
- Added a dedicated closeout audit at:
  - `docs/assessments/Project_Status_Audit_20260509_trusted_local_setup_phase1.md`
- Updated the audit to record:
  - command-policy alignment
  - root-based Node execution semantics
  - real fixture coverage
  - current focused verification results

## Verification

### Backend
- `cd backend && PYTHONPATH=. pytest tests/test_skill_setup_service_unit.py tests/test_skill_preflight_service_unit.py tests/test_api_skill_preflight.py tests/test_skill_import_store_unit.py -q`

### Frontend
- `cd frontend && npm run test -- src/pages/SkillHealth.test.ts`

### Hygiene
- `git diff --check`
- `git diff --cached --check`

## Results
- Backend focused suite: `59 passed`
- Frontend SkillHealth suite: `18 passed`
- Diff hygiene: clean

## Scope Notes
This PR intentionally does **not** add:
- chat-time arbitrary third-party script execution
- auto-trust for copied packages
- freeform shell setup blocks
- global environment mutation
- package signing / provenance / marketplace features

## Residual Risks
- Verification here is focused rather than repo-wide; no full build/lint sweep was rerun in this changeset.
- FastAPI deprecation warnings still appear in the backend test environment.
- There is unrelated untracked workspace content outside this PR scope (`data/skills/fireworks-tech-graph/`), but it is not included in this changeset.
