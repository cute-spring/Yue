# Project Status Audit

Date: 2026-05-10
Primary baselines: [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md), [docs/overview/ROADMAP.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/overview/ROADMAP.md), [docs/plans/trusted_local_setup_phase1_plan_20260509.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/trusted_local_setup_phase1_plan_20260509.md)

## Audit Overview

This audit compares the current codebase against the project’s active planning baseline, with special attention to the current skill-runtime convergence track and the newly closed Trusted Local Setup Phase 1 track.

### Core conclusion

The project is materially ahead of what the raw checkbox count suggests. The broad plan scan still reports `92/642` tasks complete across `67` plan documents, but that number is diluted by historical and still-open epics. The active execution track in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:40) is much healthier: the skill runtime program is documented at roughly `96%`, Trusted Local Setup Phase 1 is implemented and verified, and several older plan items are already landed in code even though their source plans remain unchecked.

## Planned Goals Audit

| Plan item | Status | Audit notes |
| :--- | :--- | :--- |
| Skill runtime convergence (`Stage 1-5 Lite`) | 🟡 | Current baseline says overall progress is about `96%`, with the main remaining work being Stage 4-Lite seam cleanup and deferred Stage 5 externalization in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:46). Code evidence matches that: `skill_service.py` now has provider/container seams and host adapters, but still keeps module-level compatibility exports in [backend/app/services/skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py:166). |
| Stage 5-Lite minimum externalization artifact | ✅ | The boundary harness now emits a machine-readable `stage5-lite-boundary-manifest/v1` manifest in [backend/scripts/skill_runtime_boundary_harness.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/scripts/skill_runtime_boundary_harness.py:25), matching the plan index note that the minimal artifact has landed in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:65). |
| Trusted Local Setup Phase 1 | ✅ | The Phase 1 contract, trust/setup API flow, UI entrypoint, and command-policy enforcement are implemented in [backend/app/services/skills/setup_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/setup_service.py:42), [backend/app/api/skill_preflight.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_preflight.py:188), and [frontend/src/pages/SkillHealth.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.tsx:134). |
| Model routing foundation | ✅ | Older implementation breakdown docs still contain many unchecked items, but the backend foundation is already present: routing defaults and role inheritance in [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:56), resolution logic in [backend/app/services/llm/routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/llm/routing.py:8), and runtime integration in [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py:621). |
| Chat attachment upload and persistence | ✅ | This appears super-achieved relative to older planning. Upload policy and file acceptance are implemented in [backend/app/api/files.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/files.py:17), frontend upload + stream payload wiring exists in [frontend/src/hooks/chat/chatSubmission.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatSubmission.ts:83), and message attachment persistence exists in [backend/app/services/chat_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py:581). |
| Chat edit-history question flow | ✅ | The April plan remains unchecked, but the edit flow is already implemented in [frontend/src/hooks/useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts:486), passed through [frontend/src/pages/Chat.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/Chat.tsx:816), and guarded by component/UI tests in [frontend/src/components/MessageItem.edit.test.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/MessageItem.edit.test.tsx:4). |
| File/storage abstraction epic | ❌ | The plan index still lists storage normalization, provider abstraction, and `yue://` path virtualization as not started in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:80). The current upload path code still writes dated local files under the existing uploads root in [backend/app/api/files.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/files.py:126), so this gap is real. |
| Release readiness governance | 🟡 | Quality evidence exists, but it is fragmented. There is no current `docs/release_readiness_gate/` directory in the repo root; instead, older gate materials live under [docs/release/phase1/](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/release/phase1). This makes present-day shipping status harder to audit consistently. |

## Deviation And Adjustment Analysis

### 1. Raw completion percentage understates active-track progress

- The automated scan reports only `14.33%` overall completion because it aggregates every open checkbox across a large historical plan set.
- That conflicts with the project’s own active baseline, which records the current skill runtime track at about `96%` in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:40).
- Assessment: the portfolio-wide percentage is useful as backlog pressure, but not as the primary executive status metric for the current delivery wave.

### 2. Several plans are stale relative to shipped code

- Model routing, chat edit-history, and attachment upload all have concrete implementation and passing tests, yet older plan documents still show many unchecked items.
- Evidence:
  - model routing defaults and resolution: [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:125), [backend/app/services/llm/routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/llm/routing.py:121)
  - edit flow: [frontend/src/hooks/useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts:486), [frontend/src/components/MessageItem.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/MessageItem.tsx:184)
  - attachments: [backend/app/api/files.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/files.py:112), [frontend/src/hooks/chat/chatSubmission.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatSubmission.ts:151)
- Assessment: documentation drift is now large enough to distort prioritization unless the active plan index is refreshed.

### 3. The real remaining engineering risk is architectural convergence, not feature absence

- The current baseline explicitly calls out three remaining runtime issues:
  - residual module-level globals in `skill_service.py`
  - continued `legacy/import-gate` hybrid runtime
  - deferred full externalization
- Those exact issues are visible in code and docs:
  - compatibility globals remain in [backend/app/services/skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py:168)
  - transitional host-wiring seam is still described as transitional in [backend/app/services/skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py:285)
  - Stage 5 is still explicitly deferred in [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md:67)
- Assessment: this is a healthy deviation. The project has moved from feature construction into cleanup, seam removal, and product-surface normalization.

## Verification

Focused checks run locally on 2026-05-10:

- `cd backend && PYTHONPATH=. pytest -q tests/test_skill_service_runtime_context_unit.py tests/test_stage5_runtime_boundary_harness.py tests/test_skill_setup_service_unit.py` -> `50 passed`
- `cd backend && PYTHONPATH=. pytest -q tests/test_llm_routing_unit.py tests/test_api_files_unit.py` -> `18 passed`
- `cd frontend && npm run test -- src/components/MessageItem.edit.test.tsx src/hooks/chat/chatSubmission.test.ts src/hooks/useChatState.events.test.ts` -> `17 passed`

Notes:

- An initial backend test attempt from the repo root failed during collection with `ModuleNotFoundError: app`; rerunning from [backend/](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend) resolved this, so that was an execution-context issue rather than a product regression.

## Recommended Next Priorities

### Priority 1: Finish skill runtime convergence closeout

- Core goal: remove remaining module-level compatibility shims and shrink the `legacy/import-gate` hybrid surface.
- First action: convert the remaining `skill_service.py` consumers that still rely on compatibility exports to runtime-context or host-adapter entrypoints, then rerun the existing convergence gate suite.

### Priority 2: Refresh planning artifacts to match shipped reality

- Core goal: eliminate status distortion from stale checklists.
- First action: update [docs/plans/INDEX.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/INDEX.md) and the older plan docs for model routing, attachments, and edit-history to mark landed slices and isolate true remaining work.

### Priority 3: Start the storage abstraction epic

- Core goal: reduce path coupling before more attachment and document features accrete around today’s local storage shape.
- First action: land Phase 1 local storage normalization and define the `yue://` path contract before adding more file-facing behavior.

## Decision Summary

- Current assessment: the project is in late-cycle convergence, not broad feature build-out.
- Delivery reality: the active runtime/skill platform work is largely landed, and multiple older feature plans have already been overtaken by implementation.
- Main risk: governance drift between code, plan checklists, and release-readiness artifacts.
- Best next move: finish runtime seam closeout, then immediately reconcile the plan index so future audits track the real frontier instead of historical backlog noise.
