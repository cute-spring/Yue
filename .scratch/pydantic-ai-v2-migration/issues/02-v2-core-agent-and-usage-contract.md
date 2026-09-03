# 02 - Migrate the core agent and usage contract to Pydantic AI V2

**What to build:** Upgrade the characterized Yue core to pinned Pydantic AI 2.37.0 while keeping structured output and the Yue-facing token-usage contract stable.

**Blocked by:** 01 - Establish the V1 compatibility baseline.

**Status:** resolved

- [x] The resolved environment pins Pydantic AI and its graph package to 2.37.0 and has a reviewed, reproducible lockfile.
- [x] Yue structured-output behavior uses the V2 API and Smart Paste preserves successful, rejected, timeout, retry, and sanitized-configuration outcomes.
- [x] Yue continues to expose `prompt_tokens`, `completion_tokens`, `total_tokens`, and TPS even though V2 supplies input/output token fields.
- [x] The usage translation accepts V2 fields and retains the V1 fallback only for the compatibility-stage evidence where required.
- [x] Application imports and characterization tests are green without relying on removed V1 APIs.

## Answer

The production lock now pins `pydantic-ai-slim==2.37.0` and the corresponding `pydantic-graph==2.37.0`. `uv lock` and `uv sync` completed successfully, preserving the deliberate coexistence of application-owned `httpx` and the V2 provider dependency `httpx2`.

V2 API migrations completed at the current core call sites:

- Smart Paste now configures structured output with `Agent(..., output_type=SmartPasteLlmEnvelope)`. Existing success, retry, failure, timeout, validation, and secret-sanitization tests remain green; the successful structured-output test asserts the V2 argument explicitly.
- Session metadata now uses `UsageLimits(output_tokens_limit=...)`, replacing the removed V1 `response_tokens_limit` argument.
- `PydanticAIUsageAdapter` translates V2 `input_tokens` and `output_tokens` to the unchanged Yue contract: `prompt_tokens`, `completion_tokens`, `total_tokens`, and TPS. It retains V1 `request_tokens` and `response_tokens` only as a fallback for historical baseline evidence.
- The streaming metrics fixture now models V2 usage fields and still verifies the SSE output contract.

Validation command:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -q -W error::DeprecationWarning \
  tests/test_pydantic_ai_migration_baseline.py \
  tests/test_smart_paste_service_unit.py \
  tests/test_session_meta_service_unit.py \
  tests/test_tool_registry_integration.py \
  tests/test_mcp_manager_unit.py \
  tests/test_api_chat_metrics.py
```

Result: `81 passed`. The only warning remains the unrelated `pythonjsonlogger.jsonlogger` relocation warning. A direct package/import check confirms `pydantic-ai-slim` resolves to `2.37.0`.

The broader offline-suite collection failures recorded in ticket 01 remain unrelated chat/runtime modularization drift and are unchanged by this V2 core migration. Provider-specific construction and client compatibility are intentionally handled by ticket 03; tool/MCP runtime semantics remain ticket 04.
