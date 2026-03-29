# Agent Browser New Thread Checklist (2026-03-28)

## 1. Before Opening The New Thread

Confirm these files exist and are current:

1. [docs/plans/agent_browser_phase2_completion_summary_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_phase2_completion_summary_20260328.md)
2. [docs/plans/agent_browser_continuity_handoff_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_handoff_20260328.md)
3. [docs/plans/agent_browser_continuity_resolver_plan_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_resolver_plan_20260328.md)
4. [docs/plans/agent_browser_new_thread_prompt_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_new_thread_prompt_20260328.md)

## 2. When Creating The New Thread

1. open a brand new thread manually
2. copy the full prompt from:
   - [docs/plans/agent_browser_new_thread_prompt_20260328.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_new_thread_prompt_20260328.md)
3. paste it without trimming key sections

Do not remove:

1. the “not a redesign” instruction
2. the hard constraints
3. the must-read document list
4. the single round goal
5. the completion reporting requirements

## 3. First Response Sanity Check

The new thread should:

1. acknowledge it is continuing the current branch, not redesigning
2. state the exact next goal:
   - `ExplicitContextBrowserContinuityResolver`
3. reference the required documents
4. stay inside resolver/contract/test scope

If it instead starts:

1. broad re-analysis
2. session persistence design
3. browser subsystem redesign
4. autonomous workflow ideas

Then stop and restate the prompt more strictly.

## 4. During The New Thread

Require each work round to include:

1. what files changed
2. what contract/runtime changed
3. what tests ran
4. what remains risky

## 5. End-Of-Round Gate

Before accepting the round, check:

1. no skill-owned browser runner was added
2. no selector fallback was introduced
3. no browser persistence backend was added
4. requested-action lifecycle still works
5. tests passed

## 6. After The Next Round

Repeat the same packaging flow:

1. update summary
2. update handoff
3. update next plan
4. refresh the new-thread prompt if the target changed

This keeps future thread transitions low-risk and consistent.
