# Pydantic AI V2 Upgrade Development and Test Plan

Date: 2026-09-03  
Status: Proposed  
Target: `pydantic-ai-slim[openai,google]==2.37.0`

## 1. Objective

Move Yue from the locked Pydantic AI V1 line (`1.63.0`) to the current stable V2 line (`2.37.0`) while preserving:

- OpenAI-compatible provider behavior, including custom base URLs.
- Google/Gemini provider behavior.
- MCP and builtin tool discovery, schema generation, execution, retry, and error reporting.
- Streaming text, tool-call, usage, and replay behavior.
- Smart Paste structured output parsing.
- Existing persisted message history and operational metrics.

This is a major-version migration. The dependency update must not be merged until the migration and test gates in this document pass.

## 2. Baseline and constraints

Current dependency state:

- `backend/pyproject.toml` declares `pydantic-ai-slim[openai,google]` without a version.
- `backend/uv.lock` resolves `pydantic-ai-slim==1.63.0` and `pydantic-graph==1.63.0`.
- The lockfile contains `pydantic==2.12.5`, `httpx==0.28.1`, `fastmcp==3.0.2`, and `mcp==1.26.0`.
- The project supports Python `>=3.10`; Pydantic AI V2 also supports Python `>=3.10`.

Relevant current code surfaces:

- Agent construction and streaming: `backend/app/api/chat_stream_deps.py`, `backend/app/api/chat_stream_runner.py`, `backend/app/api/chat_stream_runner_preparation.py`.
- Agent generation and metadata: `backend/app/api/agents.py`, `backend/app/services/session_meta_service.py`.
- Provider factories: `backend/app/services/llm/providers/*.py` and `backend/app/services/llm/utils.py`.
- Tool adapter and schemas: `backend/app/mcp/base.py`, `backend/app/mcp/registry.py`, `backend/app/mcp/manager.py`, `backend/app/mcp/builtin/*.py`.
- Smart Paste: `backend/app/mcp/smart_paste_service.py`.
- Usage mapping: `backend/app/services/usage_service.py`.
- Tests: `backend/tests/test_*provider*.py`, `test_*tool*.py`, `test_mcp_*.py`, `test_chat_stream_*.py`, and `test_comprehensive_api.py`.

## 3. Expected V2 changes

The implementation must explicitly account for these upstream changes:

- `Agent(..., result_type=...)` becomes `output_type`.
- V2 introduces the stable capabilities architecture and removes or relocates several V1 configuration arguments.
- `OpenAIModel` becomes `OpenAIChatModel`; existing code already uses the latter, but provider semantics still require verification.
- Provider-prefixed model names and OpenAI API selection have changed. `openai:` selects the Responses API; use `openai-chat:` when Chat Completions semantics are required.
- `ModelProfile` changes from dataclasses to `TypedDict`s.
- `Usage` becomes `RunUsage`; usage fields change from `request_tokens`/`response_tokens` to `input_tokens`/`output_tokens`.
- Streaming event and result accessors have been reorganized.
- The default `end_strategy` changes from `early` to `graceful`, which may execute function tools that previously were skipped beside a successful output tool.
- Instrumentation defaults to version 5 and run-span usage uses `gen_ai.aggregated_usage.*`.
- V2 uses `httpx2` for compatible HTTP clients. Custom clients and integrations must be checked during lockfile resolution.
- V2 retains deserialization compatibility for message history serialized through `ModelMessagesTypeAdapter`.
- The latest V2 line supports MCP SDK v2 and FastMCP 4 alongside FastMCP 3, but this project must still validate its direct MCP client usage.

Authoritative references:

- [PyPI package metadata](https://pypi.org/pypi/pydantic-ai-slim/json)
- [Pydantic AI V2 release](https://github.com/pydantic/pydantic-ai/releases/tag/v2.0.0)
- [Pydantic AI 2.37.0 release](https://github.com/pydantic/pydantic-ai/releases/tag/v2.37.0)
- [Official upgrade guide](https://github.com/pydantic/pydantic-ai/blob/main/docs/changelog.md)
- [Official V1 to V2 migration map](https://github.com/pydantic/pydantic-ai/blob/main/docs/migration.md)

## 4. Delivery strategy

Use a short-lived upgrade branch and keep each phase independently reviewable. Do not combine unrelated feature work with this migration. Existing uncommitted work in the repository must remain untouched; resolve conflicts explicitly if an upgrade edit overlaps it.

Recommended sequence:

1. Establish a clean baseline and dependency-resolution branch.
2. Upgrade to the latest V1 security release (`1.107.4`) only to expose deprecation warnings.
3. Resolve warnings and record all changed API surfaces.
4. Upgrade to V2.37.0 and regenerate the lockfile.
5. Fix compile/import failures and migrate behavior-sensitive APIs.
6. Run deterministic tests, integration tests, and live-provider smoke tests.
7. Compare production-like telemetry and tool side effects against the baseline.
8. Release behind a rollback-ready deployment and monitor.

The V1 staging step is optional if the team needs a single migration PR, but it is strongly preferred because the official guide identifies it as the smoother path.

## 5. Development plan

### Phase 0: Baseline and inventory

Tasks:

- Record the current commit, Python version, `uv` version, and resolved dependency graph.
- Run the existing backend test suite and capture the result.
- Run a static inventory using:

  ```bash
  rg -n "from pydantic_ai|import pydantic_ai|Agent\\(|result_type|output_type|RunContext|Tool\\(|OpenAIChatModel|ModelProfile|request_tokens|response_tokens|usage\\(|end_strategy|capture_run_messages|gen_ai\\.usage" backend/app backend/tests --glob '*.py'
  ```

- Save representative traces for one text-only run, one builtin-tool run, one MCP run, one streamed run, and one Smart Paste parse.
- Identify the configured provider/model names used in each environment. Do not assume all `openai:` names have identical semantics.

Exit criteria:

- Baseline tests pass or existing failures are documented.
- Representative outputs and telemetry are available for comparison.
- Every direct Pydantic AI import has an owner and migration status.

### Phase 1: Dependency and lockfile migration

Tasks:

- Change the declaration to an explicit version range or exact version approved by the team. For the first migration use:

  ```toml
  "pydantic-ai-slim[openai,google]==2.37.0",
  ```

- Regenerate `backend/uv.lock` with the project’s normal `uv` workflow.
- Verify that `pydantic-graph` resolves to `2.37.0`.
- Review changes to `pydantic`, `httpx`, `httpx2`, OpenAI, Google, FastMCP, MCP, Logfire, and transitive provider packages.
- Confirm no removed extra is being requested indirectly. Keep `openai` and `google` explicit.
- Run an import-only smoke test before editing application code.

Exit criteria:

- Lockfile resolves reproducibly on Python 3.10 and the project’s primary Python version.
- No incompatible dependency conflict exists with FastAPI, MCP, FastMCP, or the project HTTP utilities.
- The exact lockfile diff is reviewed rather than accepted wholesale.

### Phase 2: Mechanical API migration

Tasks:

- Replace `result_type=SmartPasteLlmEnvelope` with `output_type=SmartPasteLlmEnvelope` in `backend/app/mcp/smart_paste_service.py`.
- Search for all other removed Agent constructor arguments and migrate them using the official migration map.
- Update explicit V1 names and accessors found by the inventory, including usage fields and result accessors.
- Update type annotations whose V2 generic defaults change from `None` to `object` where applicable.
- Update any `prepare` callback that returns `None` to return an empty tool list or the V2 equivalent.
- Update model profile code to use dictionary access and `merge_profile` where the project reads or mutates profiles.
- Preserve explicit provider/model selection. Add a focused test for every custom provider adapter.

Exit criteria:

- All application modules import successfully.
- No V1 deprecation warning remains in the touched execution paths.
- Static search has no unexplained V1-only symbols.

### Phase 3: Provider and HTTP-client compatibility

Tasks:

- Verify `OpenAIChatModel` construction in OpenAI, Azure, DeepSeek, LiteLLM, Ollama, Gemini, and custom-provider adapters.
- Confirm custom `base_url`, API key, proxy, SSL verification, timeout, and custom `http_client` behavior.
- Decide and document whether each model name should use Responses API or Chat Completions. Preserve existing semantics unless intentionally changed.
- Check `backend/app/services/llm/utils.py` for clients passed into Pydantic AI providers. Adapt clients to `httpx2` only where the V2 provider requires it; do not globally replace clients used by FastAPI/MCP without testing.
- Verify model discovery endpoints independently from model execution.
- Verify structured output and multimodal input for OpenAI and Google.

Exit criteria:

- Each supported provider has a construction test and a live or cassette-backed request test.
- No provider silently changes API protocol or model routing.
- HTTP-client ownership and lifecycle are explicit; no leaked async clients are observed.

### Phase 4: Tool, MCP, and streaming compatibility

Tasks:

- Verify `Tool` construction, `RunContext` annotations, dynamic schema preparation, and `parameters_json_schema` replacement in `backend/app/mcp/base.py` and `backend/app/mcp/registry.py`.
- Verify all builtin tools, including chart artifacts, docs, Excel, execution, PPT, and system tools.
- Verify MCP session initialization, stdio transport, streamable HTTP transport, reconnect, timeout, cleanup, and server status reporting in `backend/app/mcp/manager.py`.
- Check whether direct `mcp` client APIs remain compatible with the resolved MCP SDK. If not, isolate a compatibility adapter rather than spreading version checks through tools.
- Audit streamed event consumers in `backend/app/api/chat_stream_runner.py` and related parsers for renamed or removed event classes.
- Set `end_strategy` explicitly where the old `early` behavior is required for side-effect safety. Otherwise document and test the new `graceful` behavior.
- Preserve the application’s external SSE contract; Pydantic AI event changes must be translated internally.

Exit criteria:

- Tool schemas are unchanged at the API boundary unless intentionally versioned.
- Tool execution order, retries, error text, and side effects are covered by tests.
- MCP cleanup succeeds during normal shutdown and failed initialization.
- SSE event snapshots and replay remain backward-compatible.

### Phase 5: Usage, observability, and persistence

Tasks:

- Update `PydanticAIUsageAdapter` in `backend/app/services/usage_service.py` to read V2 usage fields, with a short-lived compatibility fallback if mixed-version workers are possible.
- Verify token totals, duration, TPS, finish reason, and cost calculations against provider responses.
- Audit Logfire instrumentation settings and dashboards for version 5 and `gen_ai.aggregated_usage.*`.
- Decide whether to preserve V1 instrumentation field names temporarily with an explicit setting.
- Validate message-history deserialization and stream replay from V1-generated fixtures.
- Confirm persisted chat/session/tool-call records do not depend on internal Pydantic AI class names.

Exit criteria:

- Usage metrics match the provider response within documented rounding rules.
- Existing dashboards either continue to work or have a migration note and updated queries.
- V1 message fixtures load and replay successfully.

### Phase 6: Release hardening and rollout

Tasks:

- Pin the approved version explicitly in `pyproject.toml`; do not leave the production dependency unpinned after migration.
- Update the upgrade assessment and this plan with actual compatibility findings.
- Produce a release note covering behavior changes, especially `end_strategy`, provider protocol selection, and telemetry fields.
- Deploy first to a canary or non-production environment.
- Monitor error rate, tool-call success, latency, token accounting, MCP connection failures, and stream disconnects.
- Keep the previous lockfile and deployment artifact available for rollback.

Exit criteria:

- All gates in Section 7 pass.
- No unexplained regression appears in canary metrics.
- Rollback has been exercised or verified operationally.

## 6. Test plan

### 6.1 Test environments

Maintain three layers:

- Offline unit tests: no network, deterministic fake models/clients.
- Integration tests: local fake OpenAI-compatible server, fake Google endpoint, and local MCP servers.
- Live smoke tests: real credentials in a controlled environment, never in CI logs.

Run at minimum on Python 3.10 and the project’s primary supported Python version.

### 6.2 Dependency and import tests

- Assert installed `pydantic_ai.__version__ == "2.37.0"` in the upgrade environment.
- Import every module under `backend/app`.
- Verify `pydantic-ai-slim`, `pydantic-graph`, Pydantic, HTTP clients, MCP, and FastMCP resolve without conflict.
- Run `uv lock --check` or the repository-equivalent reproducibility check.
- Verify a fresh environment can install from the lockfile without using undeclared extras.

### 6.3 Agent and structured-output tests

- Construct agents with the same system prompts and model settings as production.
- Run plain text, structured output, invalid structured output, retry, timeout, and usage-limit cases.
- Test Smart Paste with valid JSON, malformed text, invalid MCP fields, missing fields, model timeout, and retry exhaustion.
- Assert `output_type` returns the expected `SmartPasteLlmEnvelope` and no `result_type` warning/error is emitted.
- Test title and summary generation in `session_meta_service.py`.

### 6.4 Provider matrix

For every provider adapter actually enabled in the deployment, test:

- Model construction with normal and custom base URLs.
- API key absence and invalid credentials.
- Proxy and SSL verification settings.
- Non-streaming text.
- Streaming text.
- Structured output.
- Tool call and tool result.
- Multimodal input where supported.
- Provider error, timeout, cancellation, and retry.
- Model discovery and fallback list behavior.

At minimum, explicitly cover OpenAI and Google because they are declared Pydantic AI extras, plus every custom adapter shipped under `backend/app/services/llm/providers`.

### 6.5 Tool and schema matrix

For each builtin tool and one remote MCP tool, assert:

- Tool name and description.
- Required and optional parameter schema.
- Nested object, array, enum, nullable, and default handling.
- Provider-specific schema translation.
- Pydantic model argument conversion and `None` filtering.
- Single-value argument wrapping.
- Successful execution.
- Exception-to-tool-error conversion.
- Retry behavior and logging redaction.
- Correct `RunContext` dependency handling.

### 6.6 MCP matrix

- Legacy config without `transport` still defaults to stdio.
- Stdio connect, initialize, list tools, call tool, reconnect, timeout, bad command, and cleanup.
- Streamable HTTP connect, initialize, list tools, call tool, auth headers, timeout, HTTP error, reconnect, and cleanup.
- Multiple MCP servers with one unavailable server must not prevent application startup.
- Tool names and schemas remain stable across V1 and V2.
- Secrets in env/header placeholders never appear in logs, status payloads, traces, or test failure output.

### 6.7 Streaming and SSE matrix

- Text-only stream.
- Text plus builtin tool call.
- Text plus remote MCP tool call.
- Multiple tool calls and tool results.
- Tool retry and model retry.
- Cancellation while receiving text.
- Cancellation during tool execution.
- Provider timeout and reconnect.
- Malformed or unknown upstream event.
- Stream replay from persisted history.
- Client disconnect and server cleanup.
- Exact external SSE event names, ordering, terminal event, and error payload.

Capture and compare a V1 baseline fixture against V2. Internal Pydantic AI event names may differ, but the Yue contract must not change without an explicit API decision.

### 6.8 Behavior-change tests

- Explicitly test `end_strategy="early"` for tools whose side effects must not run after a successful output tool.
- Explicitly test V2 default `graceful` behavior and confirm whether side effects are desired.
- Test tool execution order when multiple tools are emitted.
- Test `prepare` callbacks that expose no tools.
- Test model names with `openai:` and `openai-chat:` and assert the intended protocol.
- Test instrumentation field names and dashboard extraction.
- Test model profile dictionary access and custom profile merging.

### 6.9 Persistence and backward-compatibility tests

- Load V1 serialized `ModelMessagesTypeAdapter` fixtures.
- Replay a V1 conversation containing text, tool calls, tool results, and multimodal parts.
- Verify database records and API responses remain unchanged.
- Verify old agent and MCP configuration files load without rewrite.
- Verify new writes use the explicit V2-compatible normalized shape.

### 6.10 Performance and reliability tests

- Compare cold-start import time and memory.
- Compare first-token latency and full-stream latency.
- Compare tool-call round-trip latency.
- Run a sustained stream with repeated tool calls to detect leaks.
- Run concurrent chats with shared provider clients.
- Run repeated MCP connect/cleanup cycles.
- Verify no unbounded retry or background task growth.

## 7. Quality gates and acceptance criteria

The upgrade is ready only when all are true:

- Full offline backend suite passes.
- Provider, tool, MCP, streaming, persistence, and usage matrices pass.
- No unexplained import errors, deprecation warnings, or dependency conflicts remain.
- OpenAI and Google live smoke tests pass with production-like configuration.
- At least one stdio and one streamable HTTP MCP smoke test pass.
- V1 message-history fixtures replay successfully.
- External SSE contract is unchanged or explicitly versioned.
- Tool side-effect behavior is documented and covered with explicit `end_strategy` tests.
- Token usage and observability dashboards are verified.
- Security review confirms no secret leakage and the known V2 web UI fixes are included.
- Canary metrics stay within agreed thresholds for error rate, latency, tool success, and token accounting.

Suggested initial thresholds, to be adjusted from the Phase 0 baseline:

- No increase in failed chat runs greater than 1 percentage point.
- No increase in failed tool calls greater than 1 percentage point.
- No unexplained first-token or full-response latency regression greater than 10 percent.
- No token-accounting discrepancy greater than 1 percent on deterministic fixtures.
- Zero confirmed secret-leak findings.

## 8. Rollback plan

Rollback is required if any of the following occurs:

- Provider requests use the wrong API protocol or fail broadly.
- Tool side effects occur unexpectedly.
- MCP sessions leak, fail to clean up, or prevent startup.
- Streaming clients receive malformed or missing terminal events.
- Usage metrics become materially inaccurate.
- Any secret appears in logs, traces, or API responses.

Rollback procedure:

1. Deploy the previous application artifact and `uv.lock`.
2. Restore the previous explicit dependency resolution.
3. Disable the V2 canary route if traffic splitting is available.
4. Preserve failed V2 traces, fixtures, and dependency diffs for diagnosis.
5. Do not delete or rewrite persisted message history during rollback.

## 9. Proposed implementation split

Keep commits small and ordered:

1. Add baseline/version diagnostic tests and fixtures.
2. Pin and regenerate dependencies.
3. Migrate agent and structured-output APIs.
4. Migrate usage and result accessors.
5. Verify provider factories and HTTP-client boundaries.
6. Verify tool/MCP adapters and explicit tool-execution semantics.
7. Verify streaming/SSE translation and replay.
8. Update observability queries and documentation.
9. Run full release gates and publish the rollout record.

No commit should mix unrelated feature changes with the migration.

