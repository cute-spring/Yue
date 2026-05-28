# Yue Session Context UI E2E Capability Report

Date: 2026-05-26

## Scope

This report captures real browser-driven UI validation against the live Yue frontend and backend using the real `deepseek/deepseek-chat` model.

Test environment:

- Frontend: `http://127.0.0.1:4173/`
- Backend: `http://127.0.0.1:8003/`
- Model: `deepseek/deepseek-chat`
- Session-context flag: enabled
- Small-window runtime used during validation:
  - `PROMPT_HISTORY_MAX_CONTEXT_TOKENS=220`
  - `PROMPT_HISTORY_MAX_SINGLE_MESSAGE_TOKENS=180`
  - `YUE_SESSION_CONTEXT_RECENT_WINDOW_TOKEN_BUDGET=120`
  - `YUE_SESSION_CONTEXT_RETRIEVAL_TOKEN_BUDGET=120`
  - `YUE_SESSION_CONTEXT_TOP_K=3`

Evidence folder:

- [session-context-e2e-20260526](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526)

## Preserved Artifacts

Summary index:

- [summary.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/summary.json)

Short-term scenario:

- [short_term_recent_followup.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/short_term_recent_followup.json)
- [short_term_recent_followup.trace-bundle.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/short_term_recent_followup.trace-bundle.json)
- [short_term_recent_followup.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/short_term_recent_followup.png)

Mid-term scenario:

- [mid_term_small_window_followup.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/mid_term_small_window_followup.json)
- [mid_term_small_window_followup.trace-bundle.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/mid_term_small_window_followup.trace-bundle.json)
- [mid_term_small_window_followup.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/session-context-e2e-20260526/mid_term_small_window_followup.png)

## Scenario A: Short-Term Context Carryover

Chat id: `54ddabb8-babd-4542-a941-faf91538984b`

Test shape:

1. User gave three options in the current chat turn:
   `方案一 Redis，方案二 SQLite，方案三 对象存储`
2. Immediate follow-up:
   `继续按刚才第二个方案展开...`

Observed user-visible result:

- The assistant correctly answered that the second plan was `SQLite`
- It then expanded that plan into concrete implementation steps

Observed trace behavior:

- `action = use_recent_artifact`
- `reason = ordinal_reference`
- `should_retrieve = false`
- Selected candidates included the recent ordinal artifacts for options 1/2/3

Assessment:

- Short-term carryover works
- Recent-window / recent-artifact integration is visibly effective in this scenario

Status: `PASS`

## Scenario B: Mid-Term Context Carryover Under Small Window Pressure

Chat id: `3679772e-48c9-4883-8e6b-cb56cea4bd9a`

Test shape:

1. Seed memory:
   `方案A 是 SQLite，方案B 是 Postgres + pgvector，方案C 是 Markdown 文件`
2. Two long filler turns were added to force raw history truncation
3. Final follow-up:
   `继续展开刚才第二个方案...`

Observed user-visible result:

- The assistant did not recover `Postgres + pgvector`
- It instead invented a different “second plan” and expanded that hallucinated plan

Observed trace behavior:

- `action = retrieve_mid_session_memory`
- `reason = recent_context_insufficient`
- `should_retrieve = true`
- `retrieved_chunk_count = 0`
- `selected_candidate_count = 0`

Observed prompt snapshot behavior:

- Raw message history no longer contained the original seed turn by the time of the final request
- This confirms the small-window stress condition was real, not simulated

Assessment:

- The integration now correctly recognizes that recent context is insufficient
- The routing layer escalates to mid-session retrieval as intended
- The live application still fails to recover the earlier content because retrieval returns no chunk evidence

Status: `PARTIAL`

## Current Capability Summary

What is already real and working:

- short-term contextual carryover inside the recent window
- ordinal reference resolution from recent structured artifacts
- browser-visible end-to-end behavior for immediate follow-ups

What is partially integrated but not yet fully working in live UX:

- mid-term recall routing is now integrated and triggers correctly
- live retrieval storage/index evidence is still missing in the tested scenario
- therefore the final user experience for true mid-term recall is not yet reliable

## Bottom Line

The UI/browser evidence shows that the integration has produced a real and visible short-term context capability.

It also shows that the mid-term integration has progressed from “not routed correctly” to “routed correctly but not yet backed by retrievable live memory chunks.”

So the current live product state is:

- short-term memory carryover: `working`
- mid-term memory recall: `partially integrated, not yet reliably effective end-to-end`
