# Yue Browser Validation (2026-05-24)

## Scope

This note records a browser-level local validation run for the Yue host project after the session-context reference-host validation work.

The goal of this run was not to exercise live model traffic. It was to confirm, through a real browser flow, that:

- Yue can load preserved historical chats from a local seeded environment
- seeded session-context-style history is visible in the chat UI
- the trace inspector can display saved historical request and tool-trace data
- the seeded validation chats remain available for later manual reference

## Validation Environment

- Frontend URL: `http://127.0.0.1:3010`
- Backend URL: `http://127.0.0.1:8013`
- Isolated data dir: `/tmp/yue-browser-validation-20260524`
- Browser automation: Playwright using the local Google Chrome executable

Feature flags seeded in the isolated environment:

- `session_context_enabled=true`
- `chat_trace_ui_enabled=true`
- `chat_trace_raw_enabled=false`

## Seeded Historical Chats

The following chats were seeded and preserved in the isolated environment:

1. `Browser Validation - Session Context Flow`
   Chat id: `b45d2e41-152f-455b-b121-6b38507390d4`
   Key preserved turns:
   - user: `给我三个持久化方案`
   - assistant: `方案一 Redis，方案二 SQLite 持久化，方案三 对象存储。`
   - tool result trace: `backend/app/services/memory/session_context_host.py`
   - user: `继续按刚才第二个方案展开，并保留刚才查到的文件路径。`

2. `Browser Validation - Mixed Language Doc Ref`
   Chat id: `7f7990e3-c0ae-447a-af29-1679527b9c8f`
   Key preserved turns:
   - user: `文档命名要怎么定？`
   - assistant: `Spec 在 docs/specs/api_naming_convention.md，里面约定了 endpoint 和 field naming。`
   - user: `按那个 doc 里的 naming convention 来。`

3. `Browser Validation - Standalone Negative`
   Chat id: `b84a6a13-4fcb-45c3-903d-ac7f5bbb79c6`
   Key preserved turns:
   - assistant: `Get-EXOMailbox -Identity Alice | Export-Csv mailbox.csv`
   - assistant: `文档在 docs/specs/session_context_api_spec_20260522.md`
   - user: `另外写个 pytest fixture`

## Browser Validation Flow

The browser validation executed this flow:

1. Open Yue at `http://127.0.0.1:3010`
2. Confirm the history sidebar shows the three seeded chats
3. Open `Browser Validation - Session Context Flow`
4. Confirm the preserved chat messages are visible
5. Open the trace inspector
6. Confirm the trace inspector shows:
   - `Latest Historical Run`
   - `Request History`
   - `Tool Trace`
   - the seeded `exec` trace with `call_ctx_1`
7. Close the trace inspector
8. Open `Browser Validation - Mixed Language Doc Ref`
9. Confirm the mixed-language preserved document reference is visible
10. Open `Browser Validation - Standalone Negative`
11. Confirm the standalone negative preserved follow-up is visible

## Validation Result

Decision: `PASS`

Executed browser checks:

- `history_sidebar_shows_seeded_sessions`
- `session_context_chat_history_visible`
- `trace_inspector_shows_request_history`
- `trace_inspector_shows_tool_trace`
- `mixed_language_chat_history_visible`
- `standalone_negative_chat_history_visible`

All checks passed.

## Evidence Files

Screenshots:

- [01-home.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/01-home.png)
- [02-session-context-chat.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/02-session-context-chat.png)
- [03-trace-panel.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/03-trace-panel.png)
- [03-trace-panel-debug.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/03-trace-panel-debug.png)
- [04-mixed-language-chat.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/04-mixed-language-chat.png)
- [05-standalone-negative-chat.png](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/05-standalone-negative-chat.png)

Saved API snapshots:

- [chat-history.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/chat-history.json)
- [chat-session-context-flow.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/chat-session-context-flow.json)
- [chat-session-context-flow-trace-summary.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/chat-session-context-flow-trace-summary.json)
- [validation-summary.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/test-results/browser-validation/validation-summary.json)

## Notes

- This run used seeded local data instead of live model traffic, so the validation remained deterministic and locally inspectable.
- The preserved chats remain in the isolated data dir and can be reopened in the browser environment above for manual follow-up.
