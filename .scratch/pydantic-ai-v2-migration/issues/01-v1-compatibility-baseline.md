# 01 - Establish the V1 compatibility baseline

**What to build:** Move Yue to the Pydantic AI 1.107.4 migration compatibility stage and create reproducible characterization evidence for the chat execution boundary before V2 changes begin.

**Blocked by:** None - can start immediately.

**Status:** resolved

- [x] The resolved dependency environment uses Pydantic AI 1.107.4 and installs reproducibly from the reviewed lockfile.
- [x] Exercised chat execution, structured output, provider adapter, tool runtime, MCP, streaming, usage, and history paths emit no unresolved Pydantic AI V1 deprecation warnings.
- [x] Deterministic fixtures capture the existing Yue-visible behavior for text streaming, a tool-backed run, Smart Paste, usage metrics, and V1 message-history replay.
- [x] The backend's offline test suite passes, or every pre-existing failure is recorded separately from migration evidence.
- [x] The baseline preserves current OpenAI-compatible Chat Completions behavior and the existing Yue usage contract.

## Answer

The reviewed lockfile and local backend environment resolve `pydantic-ai-slim==1.107.4`, the final V1 compatibility release before the separately scoped V2 migration. `httpx2` is present transitively as expected and does not replace Yue's direct `httpx` dependency.

Characterization coverage passed under `-W error::DeprecationWarning` for the chat streaming/usage boundary, Smart Paste structured output, tool registry, direct MCP manager integration, and V1 usage-field mapping:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -q -W error::DeprecationWarning \
  tests/test_pydantic_ai_migration_baseline.py \
  tests/test_smart_paste_service_unit.py \
  tests/test_tool_registry_integration.py \
  tests/test_mcp_manager_unit.py \
  tests/test_api_chat_metrics.py
```

Result: `77 passed`. The only emitted warning is an unrelated third-party `pythonjsonlogger.jsonlogger` relocation warning. No Pydantic AI V1 deprecation warnings were observed in the exercised paths.

`test_api_chat_metrics.py` was updated to patch the public dependency-construction seam (`app.api.chat_stream_deps`) after the existing chat-stream modularization moved its former `chat.py` module globals. It continues to assert the Yue SSE contract for `ttft`, duration, token fields, and TPS.

The broad offline command cannot collect the full suite because of pre-existing chat/runtime modularization test drift, recorded separately from this migration evidence:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -m "not integration"
```

- `tests/test_chat_stream_runner_unit.py` imports symbols no longer re-exported by `app.api.chat_stream_runner` (`PromptPreparation` and related helpers).
- `tests/test_skill_runtime_catalog_unit.py` imports `_resolve_runtime_skill_directories`, which no longer exists in `app.main`.
- `tests/test_api_chat_unit.py` has 62 fixture/setup errors because it patches removed `app.api.chat` runtime globals such as `get_stage4_lite_runtime_context`; those collaborators now live behind `app.api.chat_stream_deps.build_stream_runner_deps`.

These failures are not caused by the Pydantic AI 1.107.4 dependency change and should be repaired in the ongoing modularization work before the V2 release gate requires a fully green offline suite. The V2 implementation ticket must retain the Chat Completions behavior and `request_tokens`/`response_tokens` to Yue `prompt_tokens`/`completion_tokens` translation characterized here.
