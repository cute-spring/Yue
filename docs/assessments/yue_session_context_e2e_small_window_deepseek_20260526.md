# Yue Session Context E2E Small-Window Validation (DeepSeek Chat)

Date: 2026-05-26

## Goal

Validate real end-to-end behavior for Yue session-context under an intentionally small history window, using the real frontend, real backend, and real `deepseek/deepseek-chat` provider.

## Runtime Setup

- Frontend URL: `http://127.0.0.1:4173/`
- Backend URL: `http://127.0.0.1:8003/`
- Provider / model: `deepseek / deepseek-chat`
- Feature flag: `session_context_enabled=true`
- Prompt-history window:
  - `PROMPT_HISTORY_MAX_CONTEXT_TOKENS=220`
  - `PROMPT_HISTORY_MAX_SINGLE_MESSAGE_TOKENS=180`
- Session-context window:
  - `YUE_SESSION_CONTEXT_RECENT_WINDOW_TOKEN_BUDGET=120`
  - `YUE_SESSION_CONTEXT_RETRIEVAL_TOKEN_BUDGET=120`
  - `YUE_SESSION_CONTEXT_TOP_K=3`

## Test Shape

Chat id: `3c526adf-3701-4eb4-baeb-57b9754c437f`

Turns:

1. Seed memory:
   `我们刚才定了三个持久化方案：方案A 是 SQLite，方案B 是 Postgres + pgvector，方案C 是 Markdown 文件。你先只回复“记住了”。`
2. Long filler turn #1:
   force raw history pressure, assistant replies `收到1`
3. Long filler turn #2:
   force raw history pressure, assistant replies `收到2`
4. Referential query:
   `继续展开刚才第二个方案，给我 3 个落地步骤，并先明确说出第二个方案是什么。`

## User-Visible Result

The final answer failed.

Expected behavior:

- explicitly recover that the second plan was `Postgres + pgvector`
- then expand that plan

Actual behavior:

- the assistant said earlier conversation did not clearly define the second plan
- it hallucinated a new pair of plans about long-context handling
- it answered with `摘要 / 层级压缩` instead of `Postgres + pgvector`

This is a clear end-to-end miss from the user’s point of view.

## Trace Evidence

Saved UI/body capture:

- JSON: `/tmp/yue-e2e-session-context-20260526.json`
- Screenshot: `/tmp/yue-e2e-session-context-20260526.png`

Saved trace bundle for the final run:

- `GET /api/chat/3c526adf-3701-4eb4-baeb-57b9754c437f/trace/bundle`

Important snapshot evidence from the final trace bundle:

- `snapshot.provider = deepseek`
- `snapshot.model = deepseek-chat`
- `snapshot.user_message = 继续展开刚才第二个方案...`
- `snapshot.message_history` only kept:
  - assistant: `收到1`
  - user: long filler #2
  - assistant: `收到2`

The original seed turn containing `方案B 是 Postgres + pgvector` was no longer in raw prompt history by the time of the final request. That confirms the small-window setup worked as intended.

## Session-Context Host Evidence

Backend `SESSION_CONTEXT_RESOLVED` for the final request:

- `action = use_recent_context`
- `reason = continuation_reference`
- `should_retrieve = false`
- `matched_signals = ["刚才", "继续"]`

Selected candidates were all from `recent_window`, for example:

- `recent_window:...:7:user_message`
- `recent_window:...:2:assistant_message`
- `recent_window:...:3:user_message`

No mid-session retrieval happened on the final turn even though the original referent had already fallen out of raw prompt history.

## Diagnosis

This run shows a real E2E seam failure:

1. The reduced raw history successfully removed the original seed turn from the model prompt.
2. The final user message was an explicit continuation reference.
3. The host classified it as `use_recent_context` instead of `retrieve_mid_session_memory`.
4. The model did not receive enough grounded evidence to recover the original second plan.
5. The model hallucinated a plausible but wrong “second plan”.

## Conclusion

This validation proves two things at once:

- the small-window configuration is effective for forcing a true mid-session-memory test
- current session-context routing is not yet robust enough for this explicit continuation case in real DeepSeek Chat E2E usage

Status for this scenario: `FAIL`

## Follow-Up Implemented

This failure has now been promoted into a committed regression fixture:

- [reviewed_traffic_deepseek_small_window_second_plan_recovery.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/fixtures/session_context/reviewed_traffic_deepseek_small_window_second_plan_recovery.json)

The routing seam has also been tightened so that:

- explicit ordinal references without a grounded recent ordinal target do not fall back to a plain recent message
- continuation-style deictic references prefer grounded artifacts over arbitrary recent window messages
- unresolved cases of this shape now escalate to mid-session retrieval

Regression validation passed after the fix:

- `PYTHONPATH=backend:../midterm-session-memory/src pytest -q backend/tests/test_session_context_host_unit.py`
- `PYTHONPATH=../midterm-session-memory/src pytest -q ../midterm-session-memory/tests`

## Real Browser Rerun After Fix

The same real browser DeepSeek Chat E2E scenario was rerun after the routing fix.

Rerun artifacts:

- JSON: `/tmp/yue-e2e-session-context-rerun-20260526.json`
- Screenshot: `/tmp/yue-e2e-session-context-rerun-20260526.png`
- Chat id: `b9ef836e-3be1-4a59-949f-67554d237afd`

Observed result:

- user-visible answer still failed to recover `Postgres + pgvector`
- however, the final host routing decision changed from `use_recent_context` to `retrieve_mid_session_memory`

Important backend evidence from the final rerun turn:

- `action = retrieve_mid_session_memory`
- `reason = recent_context_insufficient`
- `should_retrieve = true`
- `retrieved_chunk_count = 0`
- `selected_candidate_count = 0`

Interpretation:

- the routing seam fix worked
- the remaining live E2E gap is now downstream of routing
- the live application did not have retrievable mid-session chunks available for that conversation, so retrieval escalated correctly but returned no evidence

Current status after rerun: `PARTIAL FIX`

- routing behavior: fixed
- live end-to-end recovery: still failing because retrieval storage/index population is not yet delivering chunks in this real scenario
