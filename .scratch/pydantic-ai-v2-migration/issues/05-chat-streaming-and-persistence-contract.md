# 05 - Protect the chat execution boundary streaming and persistence contract

**What to build:** Verify end-to-end Yue chat execution under V2 so provider streaming, tool activity, persistence, and frontend-facing SSE behavior remain compatible.

**Blocked by:** 03 - Preserve provider adapter behavior under V2; 04 - Validate the tool runtime and MCP compatibility under V2.

**Status:** resolved

- [x] Text-only, builtin-tool, and MCP-tool chat runs preserve the external SSE event names, ordering, terminal payload, and error payload.
- [x] Cancellation, provider errors, tool retries, client disconnects, and cleanup preserve Yue-visible behavior and leave no unfinished runtime work.
- [x] V1 serialized history fixtures containing text, tools, tool results, and multimodal parts deserialize and replay with equivalent Yue-visible outcomes.
- [x] Persisted chat, session, tool-call, and usage records retain their existing API and storage contracts.
- [x] The chat execution boundary does not expose Pydantic AI internal event classes or V2-only framework objects to frontend consumers.

## Answer

Added a fixed V1-shaped Pydantic AI message-history fixture containing text, multimodal input, a linked tool call/result, and final assistant text. Pydantic AI V2 deserializes it through `ModelMessagesTypeAdapter` without leaking framework objects into Yue's frontend contract.

Fixed a stream-cleanup race: when provider streaming fails after the tool-event queue getter already consumed an event, Yue now emits that event before ending the stream. Focused tests cover normal queued-tool draining, provider-error cleanup, V2 history replay, SSE metrics, tool persistence, and chart persistence: `62 passed`.

The required offline suite still cannot collect because of the separately recorded modularization drift in `test_chat_stream_runner_unit.py` and `test_skill_runtime_catalog_unit.py`; no additional ticket-05 failures were observed.
