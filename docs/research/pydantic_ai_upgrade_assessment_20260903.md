# Pydantic AI Upgrade Assessment

Date: 2026-09-03

## Current and latest versions

- The backend declares `pydantic-ai-slim[openai,google]` without a version pin in `backend/pyproject.toml`.
- The lockfile resolves `pydantic-ai-slim` and `pydantic-graph` to `1.63.0` in `backend/uv.lock`.
- PyPI currently lists `pydantic-ai-slim` `2.37.0`, released 2026-09-01. It requires Python `>=3.10` and Pydantic `>=2.12`.
- Pydantic AI V2 became stable at `2.0.0` on 2026-06-23. `2.37.0` is therefore a stable V2 release, not a beta.

Sources:

- [PyPI package metadata](https://pypi.org/pypi/pydantic-ai-slim/json)
- [Pydantic AI v2.0.0 release](https://github.com/pydantic/pydantic-ai/releases/tag/v2.0.0)
- [Official V1 to V2 upgrade guide](https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/changelog.md)

## Recommendation

Upgrade, but treat it as a planned V1-to-V2 migration rather than a lockfile refresh. The project already has Pydantic 2.12.5 and Python >=3.10, so the base runtime requirements are aligned. The upgrade should be done in a branch with the full backend test suite and a live streaming/tool-call smoke test.

## Benefits relevant to this project

- Ongoing bug fixes and provider compatibility improvements, including OpenAI, Google, MCP/FastMCP, streaming, and tool-call handling.
- V2 capabilities provide a composable way to bundle tools, hooks, instructions, and model settings if the agent architecture adopts them later.
- V2.29 adds MCP SDK v2 and FastMCP 4 support alongside FastMCP 3.
- V2.30 fixes a security issue in the local development web chat UI and adds host validation.
- V2.32 improves sync-tool timeout enforcement, cancellation behavior, and tool-result handling.
- V2.36 adds durable-operation APIs and stable instruction-part IDs; V2.37 adds fixes for Google routing, AG-UI tool-call streams, and durable operations.
- V1 message history serialized with `ModelMessagesTypeAdapter` remains deserializable in V2.

## Migration risks found locally

- `backend/app/mcp/smart_paste_service.py` uses the V1 `Agent(..., result_type=...)` argument. V2 uses `output_type`.
- The app directly imports and wraps V1-era model/provider APIs such as `OpenAIChatModel`, `RunContext`, and `Tool`; these need compile/test verification against V2.
- V2 changes the default `end_strategy` from `early` to `graceful`, which can execute function tools alongside a successful output tool. This is behaviorally important for side-effecting tools.
- V2 changes default instrumentation to version 5 and aggregated usage attribute names. Existing Logfire dashboards or token metrics may need updates.
- V2 uses `httpx2` for compatible HTTP clients. The current lockfile also contains legacy `httpx 0.28.1`, FastMCP 3.0.2, and MCP 1.26.0, so dependency resolution and custom HTTP-client integrations need validation.
- Model profile classes become `TypedDict`s in V2; code that reads profile attributes or mutates profiles must migrate to dictionary access.

## Suggested rollout

1. Upgrade the dependency explicitly to `pydantic-ai-slim[openai,google]==2.37.0` in a branch and regenerate `uv.lock`.
2. Resolve V1 deprecation warnings and migrate `result_type` to `output_type`.
3. Audit tool execution semantics, provider construction, streaming events, instrumentation attributes, and custom HTTP clients.
4. Run unit tests plus end-to-end OpenAI/Google streaming and builtin-tool scenarios before merging.

