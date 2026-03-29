# Agent Browser New Thread Handoff Package (2026-03-28)

## 1. Purpose

This document is the top-level entrypoint for opening a brand new thread and continuing Yue's current `agent-browser` work without losing scope, boundary, or implementation status.

Use this file as the starting index for handoff.

## 2. Recommended Reading Order

Read in this order:

1. [docs/plans/skill_package_contract_plan_20260327.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [docs/plans/skill_package_contract_handoff_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md)
3. [docs/plans/agent_browser_phase2_completion_summary_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_phase2_completion_summary_20260328.md)
4. [docs/plans/agent_browser_mutation_continuity_plan_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_mutation_continuity_plan_20260328.md)
5. [docs/plans/agent_browser_continuity_handoff_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_handoff_20260328.md)
6. [docs/plans/agent_browser_continuity_resolver_plan_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_resolver_plan_20260328.md)

## 3. Current State In One Screen

Current branch status:

1. package-first skill/action runtime foundation is complete
2. browser builtin family is complete
3. browser skill package wiring is complete
4. requested-action lifecycle integration is complete
5. real minimal browser execution exists for:
   - `open`
   - `snapshot`
   - `screenshot`
   - `press`
   - `click`
   - `type`
6. authoritative target path exists
7. continuity metadata exists
8. continuity-resolution metadata exists
9. continuity resolver seam exists
10. explicit-context resolver exists
11. default no-op resolver still exists
12. `resolved_context` metadata is live
13. requested-action tool args can be hydrated from `resolved_context`
14. builtin mutation tools are continuity-aware at the rejection boundary
15. lookup backend seam exists with a default no-op implementation

What is not complete:

1. storage-backed lookup backend
2. browser process/tab restore
3. resumed tab/session lookup execution
4. resumed continuity runtime engine

## 4. Immediate Recommended Next Goal

The next thread should not revisit foundation work.

It should start from:

1. the existing `BrowserContinuityLookupBackend` seam
2. the already-live `resolved_context` metadata contract
3. a minimal adapter-owned lookup implementation and tests

## 5. Companion Files For Actual Execution

When opening a new thread, use:

1. [docs/plans/agent_browser_new_thread_prompt_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_new_thread_prompt_20260328.md)
2. [docs/plans/agent_browser_new_thread_checklist_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_new_thread_checklist_20260328.md)

## 6. Recommendation

For a brand new thread:

1. read this file first
2. open the prompt document
3. copy it as-is into the new thread
4. use the checklist to verify the new thread stays on-scope
