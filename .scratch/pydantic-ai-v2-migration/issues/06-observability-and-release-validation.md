# 06 - Migrate observability and complete release validation

**What to build:** Complete the evidence and operational safeguards needed to release the V2 migration through staging and a monitored canary.

**Blocked by:** 05 - Protect the chat execution boundary streaming and persistence contract.

**Status:** claimed

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

It currently stops during collection on the separately tracked chat modularization imports in `test_chat_stream_runner_unit.py` and `test_skill_runtime_catalog_unit.py`. This must be green before canary approval.

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
