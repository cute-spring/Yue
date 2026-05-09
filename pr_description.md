## Summary 

Implement Trusted Local Setup Phase 1 for copied open-source skills. 

This adds a narrow, explicit trust-and-setup flow that: 
- only accepts manifest-declared `install.setup` 
- only supports `python` and `node` 
- requires explicit Trust before Setup 
- persists trust/setup state and binds it to package fingerprint 
- keeps setup execution constrained to isolated paths under the skill root 
- keeps Mount separate from Trust & Setup 
- exposes trust/setup state in the preflight API and SkillHealth UI 

## What Changed 

### Backend 
- Added setup contract/state models and setup orchestration service 
- Changed package parsing so Phase 1 setup capability comes only from `manifest.yaml` 
- Extended preflight records with trust/setup fields 
- Derived setup capability, status, runtime, commands, fingerprint, and isolated env path during preflight 
- Added: 
  - `POST /api/skill-preflight/{skill_ref}/trust` 
  - `POST /api/skill-preflight/{skill_ref}/setup` 
  - `GET /api/skill-preflight/{skill_ref}/setup` 
- Added package drift protection between preflight, trust, and setup 
- Reused `builtin.exec` argv execution helper for safer non-shell command execution 

### Frontend 
- Extended `SkillPreflightRecord` types with trust/setup fields 
- Updated SkillHealth to show: 
  - trusted setup support 
  - trust status 
  - setup status 
  - last setup failure 
  - setup next action 
- Added separate `Trust & Setup` / `Retry Setup` actions without changing Mount semantics 

### Tests 
- Added focused backend coverage for: 
  - preflight/store contract 
  - manifest-only setup parsing 
  - trust-first setup flow 
  - command rejection policy 
  - fingerprint drift handling 
  - API trust/setup endpoints 
- Added frontend SkillHealth tests for: 
  - trust/setup helper state 
  - error/status messaging 
  - trust-then-setup request flow 

## Verification 

### Backend 
- `PYTHONPATH=. pytest tests/test_skill_foundation_unit.py -q -k 'install_setup or minimal_manifest_for_package_without_manifest'` 
- `PYTHONPATH=. pytest tests/test_skill_import_store_unit.py tests/test_skill_setup_service_unit.py tests/test_skill_preflight_service_unit.py tests/test_api_skill_preflight.py -q` 
- `PYTHONPATH=. pytest tests/test_skill_runtime_bootstrap_unit.py -q` 
- `python -m compileall app` 

### Frontend 
- `npm test` 
- `npm run build` 

### Hygiene 
- `git diff --check` 

## Results 
- Backend targeted foundation: passed 
- Backend focused suite: passed 
- Backend bootstrap regression: passed 
- Frontend full unit suite: passed 
- Frontend build: passed 
- Python compile check: passed 
- Diff hygiene: clean 

## Scope Notes 
This PR intentionally does **not** add: 
- chat-time arbitrary third-party script execution 
- auto-trust for copied packages 
- freeform shell setup blocks 
- global environment mutation 
- package signing / provenance / marketplace features 

## Residual Risks 
- `run_exec_argv` is aligned with the setup boundary but does not yet fully mirror all `ExecTool` policy knobs such as generic `allow_patterns` / `restrict_to_workspace` 
- FastAPI deprecation warnings still exist in the test environment 
- SkillHealth does not yet have browser-level visual regression coverage 
