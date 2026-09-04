# 06 - Migrate observability and complete release validation

**What to build:** Complete the evidence and operational safeguards needed to release the V2 migration through staging and a monitored canary.

**Blocked by:** 05 - Protect the chat execution boundary streaming and persistence contract.

**Status:** ready for staging (external release gates pending)

- [ ] V2 instrumentation and Yue application metrics report accurate token usage, completion outcomes, errors, and latency without dashboard double-counting.
- [ ] Offline regression tests, credentialed staging smoke tests, and concurrency/cleanup checks pass with results recorded as release evidence.
- [ ] Staging verifies an OpenAI-compatible Chat Completions provider, Google/Gemini, one stdio MCP server, and one streamable HTTP MCP server without exposing credentials.
- [ ] Canary thresholds are established from the V1 baseline for chat failures, tool failures, stream disconnects, token-accounting discrepancies, and latency regressions.
- [ ] The previous lockfile and deployable artifact are retained, and the rollback procedure is validated before broad production rollout.

## Local Evidence

The V2 usage adapter is covered by deterministic tests and remains the source of Yue-facing metrics. It translates `input_tokens` and `output_tokens` to `prompt_tokens` and `completion_tokens`; Pydantic AI instrumentation must not be added to those application metrics, preventing dashboard double counting.

The local release command is:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -m "not integration"
```

On 2026-09-05, the complete offline suite passed after stale test seams,
portable test-environment assumptions, and the remaining release-evidence
coverage were completed:

```text
1,062 passed, 17 skipped, 10 warnings in 37.33s
```

The exact command included an isolated writable data directory:

```bash
YUE_DATA_DIR=/private/tmp/yue-pydantic-ai-tests \
  PYTHONPATH=.:../../session-context-manager/src \
  .venv/bin/python -m pytest -m "not integration" --tb=short
```

Focused release-validation evidence:

| Cluster | Command | Result |
| --- | --- | --- |
| Preflight setup | `.venv/bin/python -m pytest tests/test_api_skill_preflight.py -q` | `12 passed in 3.81s` |
| Document access and DocsList | `.venv/bin/python -m pytest tests/test_doc_access_policy.py tests/test_docs_builtin.py -q` | `14 passed in 1.08s` |
| Reasoning protocol SSE/meta | `.venv/bin/python -m pytest tests/test_reasoning_protocol.py -q` | `5 passed, 1 warning in 1.96s` |
| Skill boundary manifest | `.venv/bin/python -m pytest tests/test_skill_runtime_boundary_manifest_unit.py -q` | `4 passed in 1.13s` |
| Adjacent skill import behavior | `.venv/bin/python -m pytest tests/test_skill_import_gate_unit.py tests/test_api_skill_imports.py -q` | `51 passed in 3.57s` |
| V1 history replay and sustained cleanup seams | `.venv/bin/python -m pytest tests/test_pydantic_ai_history_replay.py -q --tb=short` | `5 passed, 1 warning in 2.14s` |
| Explicit output policy and V2 instrumentation seams | `.venv/bin/python -m pytest tests/test_pydantic_ai_migration_baseline.py -q --tb=short` | `5 passed, 1 warning in 2.66s` |
| V2 instrumentation and Yue usage contracts | `.venv/bin/python -m pytest tests/test_pydantic_ai_migration_baseline.py::test_chat_execution_emits_v5_aggregated_usage_separately_from_yue_metrics -q` | `1 passed, 1 warning in 1.97s` |
| Sustained streaming/MCP cleanup (20 concurrent streams; stdio and streamable HTTP) | `.venv/bin/python -m pytest tests/test_pydantic_ai_history_replay.py::test_repeated_streaming_and_mcp_cycles_leave_no_unfinished_runtime_work -vv --tb=short` | `1 passed, 1 warning in 2.12s` |
| Combined history, output policy, instrumentation, runner, and MCP suite | `.venv/bin/python -m pytest tests/test_pydantic_ai_history_replay.py tests/test_pydantic_ai_migration_baseline.py tests/test_chat_stream_runner_unit.py tests/test_mcp_manager_unit.py -q --tb=short` | `59 passed, 1 warning in 5.84s` |

There are no remaining offline failures. The warning set is non-blocking and
consists of the existing `pythonjsonlogger` deprecation, pytest warnings for
script tests that return booleans, and PDF binding type deprecations. No
Pydantic AI migration runtime behavior was changed to clear these failures.

The local gate is ready for staging. Release approval remains blocked on the
credentialed staging scenarios below, external dashboard validation, numeric
canary thresholds from the V1 baseline, and retention/validation of the V1
deployable rollback artifact.

The `main...HEAD` code-review follow-ups for local release evidence are now
closed:

- The retained V1 serialized history fixture is deserialized and replayed by a
  real V2 agent. Separately, Yue-persisted text, multimodal content, tool
  call/result, and final-answer history is replayed through the Yue API/SSE
  boundary using a real V2 agent and verified by its Yue-visible result.
- A controlled structured-output agent explicitly uses `end_strategy="early"`;
  a side-effecting Yue tool present after the successful output is not run.
- Pydantic AI instrumentation is explicitly configured for version 5 aggregated
  usage attributes without content capture. With an in-memory tracer provider,
  the regression keeps framework `gen_ai.aggregated_usage.*` attributes distinct
  from Yue's stable `prompt_tokens` and `completion_tokens` SSE fields. The
  repository does not configure a production exporter; staging must supply and
  evidence the deployed tracer-provider/export/dashboard path before the
  observability release checkbox is complete.
- Twenty concurrent streams plus stdio and streamable-HTTP MCP connect/cleanup
  cycles leave no queued tool events, sessions, server metadata, stale error
  state, open transport/client/session contexts, or unfinished runtime tasks.

One product-policy decision remains outside the V2 migration scope: establish
the intended `llm_request_timeout` behavior when neither a proxy nor a custom CA
is configured. Repository evidence shows the current custom-client condition
predates V2, so this migration does not silently change it. It is not an offline
or staging-readiness blocker, but must be decided separately before changing
provider timeout behavior.

## Staging Evidence Template

Record each result with timestamp, deployed commit, `pydantic-ai-slim==2.37.0`, provider/model, and sanitized trace ID:

| Scenario | Required assertion | Result |
| --- | --- | --- |
| OpenAI-compatible Chat Completions | text streaming, usage fields, and tool call succeed | pending |
| Google/Gemini | text streaming and usage fields succeed | pending |
| stdio MCP | initialization, tool call, timeout, and cleanup succeed | pending |
| streamable HTTP MCP | headers, tool call, timeout, reconnect, and cleanup succeed | pending |
| Telemetry export and dashboards | V2 version-5 aggregated usage, outcomes, errors, and latency arrive without Yue-metric double counting | pending |

Never record API keys, proxy credentials, raw authorization headers, or raw prompts in this evidence.

## Canary And Rollback

Before deployment, retain the prior lockfile and a deployable V1 artifact. Establish numeric thresholds from the recorded V1 production baseline for chat errors, tool errors, disconnects, token-accounting discrepancy, and p95 latency. Roll back immediately for secret exposure, any material metric regression beyond the agreed threshold, or an unrecoverable provider/MCP compatibility failure. Preserve sanitized V2 traces and the dependency diff for diagnosis.
