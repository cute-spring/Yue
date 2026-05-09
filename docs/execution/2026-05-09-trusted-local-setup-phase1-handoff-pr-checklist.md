# Trusted Local Setup Phase 1 Handoff / PR Checklist

Date: 2026-05-09

Source plan:
- [trusted_local_setup_phase1_plan_20260509.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/trusted_local_setup_phase1_plan_20260509.md)

## Scope Summary

This document captures:
- what Phase 1 goals are implemented
- what was verified
- what is intentionally not part of Phase 1
- what remains as post-Phase-1 backlog

## Implemented In This Scope

- [x] Support only manifest-declared `install.setup`
- [x] Support only `python` and `node` setup runtimes
- [x] Require explicit Trust before Setup
- [x] Persist trust/setup state on preflight records
- [x] Bind trust/setup state to package fingerprint
- [x] Reject setup when package contents drift after preflight/trust
- [x] Keep setup execution inside per-skill isolated paths under skill root
- [x] Keep Mount separate from Trust & Setup
- [x] Expose trust/setup fields in skill preflight API payloads
- [x] Add `POST /trust`, `POST /setup`, and `GET /setup` endpoints
- [x] Surface trusted setup state and actions in SkillHealth UI
- [x] Add focused backend and frontend regression coverage

## Verified

- [x] Backend focused tests for store/setup/preflight/API are passing
- [x] Backend bootstrap regression suite is passing
- [x] Frontend SkillHealth tests are passing
- [x] Frontend full unit suite is passing
- [x] Frontend build is passing
- [x] Python compile check is passing
- [x] `git diff --check` is clean
- [x] Final read-only review found no remaining P0/P1 blockers in trust-gate scope

## Explicitly Out Of Scope For Phase 1

- [x] Chat-time arbitrary third-party script execution
- [x] Auto-trusting copied packages
- [x] Freeform shell setup blocks
- [x] Global environment mutation
- [x] Marketplace / signing / provenance features
- [x] General runtime execution of package actions

## Remaining Backlog

### Near-Term Hardening

- [ ] Align `run_exec_argv` more fully with `ExecTool` policy behavior, especially `allow_patterns` and `restrict_to_workspace`
- [ ] Add richer setup observability if desired, such as per-command audit details
- [ ] Add more positive-path node setup coverage across supported package managers
- [ ] Add browser-level visual regression coverage for SkillHealth

### Nice-To-Have Follow-Up

- [ ] Document operator-facing trusted setup workflow in user/developer docs
- [ ] Add PR/commit hygiene around selecting only this feature's files because the worktree also contains unrelated untracked files

## Known Non-Blocking Notes

- Existing FastAPI deprecation warnings are still present in test runs
- A broader backend test collection issue exists in `tests/test_skill_runtime_catalog_unit.py` importing `_resolve_runtime_skill_directories` from `app.main`; this does not appear introduced by this Phase 1 work

## PR Readiness Checklist

- [x] Scope remains inside Trusted Local Setup Phase 1 boundary
- [x] Mount and Trust & Setup are still separated
- [x] Backend contract is covered by tests
- [x] Frontend contract is covered by tests
- [x] No new blocker found in final review
- [ ] Stage only Phase 1 related files
- [ ] Write commit message
- [ ] Prepare PR summary with implemented scope, verification, and residual risks
