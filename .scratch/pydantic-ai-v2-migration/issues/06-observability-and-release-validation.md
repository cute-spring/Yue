# 06 - Migrate observability and complete release validation

**What to build:** Complete the evidence and operational safeguards needed to release the V2 migration through staging and a monitored canary.

**Blocked by:** 05 - Protect the chat execution boundary streaming and persistence contract.

**Status:** blocked (external release gates)

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

On 2026-09-04, the command collected and ran the complete offline suite after stale modularization seams were repaired. Latest result: `1,035 passed, 23 failed, 17 skipped, 0 errors`.

The remaining failures are outside this migration: an uncommitted first-message title regression in the chat-service split, unrelated agent/preflight/doc/multimodal/reasoning/phase-harness assertions, and environment scripts that still invoke a missing `python` executable. The V2 migration-focused suites pass, including `tests/test_api_chat_unit.py` (`62 passed`). The full-suite gate remains red until the owning work resolves those failures; do not treat it as V2 release approval.

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
