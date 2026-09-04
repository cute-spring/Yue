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

On 2026-09-05, the complete offline suite passed after stale test seams and
portable test-environment assumptions were repaired:

```text
1,058 passed, 17 skipped, 10 warnings in 38.15s
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

There are no remaining offline failures. The warning set is non-blocking and
consists of the existing `pythonjsonlogger` deprecation, pytest warnings for
script tests that return booleans, and PDF binding type deprecations. No
Pydantic AI migration runtime behavior was changed to clear these failures.

The local gate is ready for staging. Release approval remains blocked on the
credentialed staging scenarios below, external dashboard validation, numeric
canary thresholds from the V1 baseline, and retention/validation of the V1
deployable rollback artifact.

## Staging Evidence Template

Record each result with timestamp, deployed commit, `pydantic-ai-slim==2.37.0`, provider/model, and sanitized trace ID:

| Scenario | Required assertion | Result |
| --- | --- | --- |
| OpenAI-compatible Chat Completions | text streaming, usage fields, and tool call succeed | pending |
| Google/Gemini | text streaming and usage fields succeed | pending |
| stdio MCP | initialization, tool call, timeout, and cleanup succeed | pending |
| streamable HTTP MCP | headers, tool call, timeout, reconnect, and cleanup succeed | pending |

Never record API keys, proxy credentials, raw authorization headers, or raw prompts in this evidence.

## Canary And Rollback

Before deployment, retain the prior lockfile and a deployable V1 artifact. Establish numeric thresholds from the recorded V1 production baseline for chat errors, tool errors, disconnects, token-accounting discrepancy, and p95 latency. Roll back immediately for secret exposure, any material metric regression beyond the agreed threshold, or an unrecoverable provider/MCP compatibility failure. Preserve sanitized V2 traces and the dependency diff for diagnosis.
