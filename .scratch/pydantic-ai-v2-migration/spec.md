# Pydantic AI V2 Migration

Status: ready-for-agent

## Problem Statement

Yue's chat execution boundary is locked to Pydantic AI 1.63.0. It therefore misses the maintained V2 line's provider compatibility, security fixes, MCP improvements, and runtime fixes. A direct dependency bump would be unsafe because Yue owns provider adapters, the tool runtime, SSE translation, usage mapping, and persisted chat history around the framework.

The migration must upgrade Pydantic AI without changing established user behavior: OpenAI-compatible chat requests must retain Chat Completions semantics, tool authorization and execution must remain owned by Yue, SSE consumers must keep their contract, and token fields exposed by Yue must remain stable.

## Solution

Deliver a staged, evidence-driven framework migration.

First move from Pydantic AI 1.63.0 to the latest V1 compatibility stage, 1.107.4, and eliminate deprecation warnings in exercised paths. Then migrate to exactly pinned Pydantic AI 2.37.0, update affected adapters, and validate the chat execution boundary through offline regression tests, credentialed staging smoke tests, and a monitored canary rollout.

The migration uses the existing chat execution boundary as its principal compatibility seam. Provider adapters continue to own provider-specific configuration. The Yue tool runtime continues to own builtin and MCP tool discovery, authorization, schemas, execution, and application events. Framework-specific changes are translated at those boundaries rather than propagated into user-facing contracts.

## User Stories

1. As a Yue chat user, I want existing chat conversations to continue working after the framework upgrade, so that a maintenance release does not disrupt my work.
2. As a Yue chat user, I want streamed text to arrive with the same SSE contract and terminal behavior, so that the frontend remains compatible.
3. As a Yue chat user, I want my prior conversation history to remain readable, so that upgrading does not orphan existing chats.
4. As a Yue chat user, I want builtin tools to retain their names, schemas, validation, and error messages, so that existing prompts and workflows behave consistently.
5. As a Yue chat user, I want MCP tools to remain authorized only when enabled for my agent, so that the upgrade does not broaden tool access.
6. As a Yue chat user, I want MCP servers to keep reconnecting, timing out, and cleaning up predictably, so that chat remains available when an integration is unhealthy.
7. As a Yue chat user, I want tool execution events to remain visible in streaming responses, so that I can understand what the agent did.
8. As a Yue chat user, I want token usage displayed with the same Yue field names, so that my usage views and integrations remain stable.
9. As a Yue chat user, I want image and multimodal messages to remain accepted where they work today, so that the upgrade does not remove supported input modes.
10. As a Yue chat user, I want Smart Paste to continue returning validated MCP configurations, so that I can configure integrations without manual reconstruction.
11. As a provider administrator, I want OpenAI-compatible configurations to preserve Chat Completions semantics, so that model routing and tool behavior do not change unexpectedly.
12. As a provider administrator, I want custom base URLs, API keys, proxies, SSL verification, and timeouts to remain supported, so that self-hosted and compatible endpoints continue to work.
13. As a provider administrator, I want Google and Gemini configurations to remain functional, so that the declared provider extras remain usable.
14. As a provider administrator, I want model discovery to remain independent from model execution, so that listing failures do not incorrectly imply execution failures.
15. As an operator, I want framework-specific HTTP client changes isolated to provider adapters, so that the rest of Yue's HTTP and MCP behavior remains stable.
16. As an operator, I want token usage and observability data to remain accurate, so that cost, performance, and capacity decisions remain trustworthy.
17. As an operator, I want dashboards to account for V2 instrumentation attributes, so that a framework upgrade does not create silent telemetry gaps.
18. As an operator, I want staging smoke tests with real provider and MCP credentials, so that behavior unavailable to mocks is verified before release.
19. As an operator, I want a canary rollout with explicit rollback thresholds, so that failures can be contained before they affect all users.
20. As a security reviewer, I want tool access, secret redaction, and persisted message behavior to remain unchanged, so that the migration does not weaken safety boundaries.
21. As a security reviewer, I want the V2 security fixes included without enabling unrelated web UI features, so that the dependency upgrade improves posture without widening scope.
22. As a maintainer, I want V1 deprecations resolved before V2 removals are introduced, so that migration failures are attributable and actionable.
23. As a maintainer, I want the production framework version pinned during rollout, so that dependency resolution cannot silently change behavior.
24. As a maintainer, I want the tool runtime preserved as the compatibility seam, so that a framework upgrade is not conflated with a tool architecture redesign.
25. As a maintainer, I want structured-output agents with side-effecting tools to declare output-completion behavior explicitly, so that future changes cannot silently execute unintended side effects.
26. As a maintainer, I want deterministic test fixtures for V1 history, usage, streaming, and tool activity, so that regressions can be reproduced without provider access.
27. As a maintainer, I want the prior lockfile and deployable artifact retained through canary validation, so that rollback is fast and does not alter user data.
28. As a future framework adopter, I want Responses API adoption, capabilities, and MCPToolset considered separately, so that each behavior-changing architecture decision is independently evaluated.

## Implementation Decisions

- The migration proceeds in two stages: first the V1 compatibility stage at 1.107.4, then the V2 target at exactly 2.37.0. The V2 dependency remains exactly pinned for the initial release.
- The package resolution must be regenerated and reviewed as a whole. The review includes the Pydantic AI graph package, Pydantic, provider SDKs, MCP, FastMCP, Logfire, legacy `httpx`, and V2 `httpx2` dependencies.
- The chat execution boundary is the primary compatibility seam. It owns request preparation, provider execution, tool binding, stream translation, usage collection, and persistence-facing outcomes.
- Existing provider adapters preserve Chat Completions semantics for OpenAI-compatible endpoints. Responses API adoption is explicitly deferred.
- Provider adapters remain responsible for custom base URLs, credentials, proxy settings, SSL verification, timeouts, and provider-specific HTTP clients.
- `httpx2` is permitted only where a Pydantic AI V2 provider requires it. Application-owned discovery, proxy/SSL handling, and MCP transport continue using the existing HTTP client boundary unless compatibility testing proves a targeted change is necessary.
- Pydantic AI V1 structured-output configuration is migrated to the V2 output API. Smart Paste remains a structured-output use case and must preserve its validation, retry, timeout, and sanitation outcomes.
- The Yue tool runtime remains the sole application integration seam for builtin and MCP tools. The migration does not adopt Pydantic AI MCPToolset, capabilities, or a new tool-authorization model.
- Existing tool schemas, provider-specific schema translation, authorization checks, error classification, and emitted application tool events are preserved at the Yue boundary.
- The V2 default output-completion behavior is not globally overridden. Any future agent that combines structured output with side-effecting function tools must choose and test `end_strategy` explicitly; `early` is the default policy unless post-output tool execution is intentional.
- Yue continues to expose its stable usage contract using `prompt_tokens`, `completion_tokens`, `total_tokens`, and derived TPS. The internal adapter translates V2 input/output token fields and may support V1 field names only during the compatibility stage.
- Observability configuration and dashboards are updated for V2 instrumentation version 5 and aggregated run-usage attributes. Application metrics and framework telemetry are treated as separate contracts.
- V1 serialized message-history fixtures are retained and must deserialize and replay through V2. No migration rewrites user message history or tool-call persistence records.
- The external SSE contract remains unchanged. Pydantic AI event reorganizations are translated within the chat execution boundary rather than exposed to frontend consumers.
- The implementation is split into dependency, API migration, provider compatibility, tool/MCP compatibility, streaming and persistence compatibility, observability, and rollout work. Runtime code changes begin only after the V1 warning baseline is captured.

## Testing Decisions

A good migration test verifies Yue-observable behavior at the chat execution boundary: returned content, tool authorization and effects, SSE payloads and ordering, usage fields, persisted history, and cleanup outcomes. Tests must not assert private Pydantic AI object layout or internal event-class names.

- Add dependency and import checks that prove the resolved V1 and V2 environments are reproducible and that application modules load.
- Extend structured-output tests for Smart Paste to assert the V2 output API produces the same accepted, rejected, timeout, retry, and sanitized-configuration outcomes.
- Extend provider-adapter tests for OpenAI, Azure, custom OpenAI-compatible, DeepSeek, LiteLLM, Ollama, and Google/Gemini adapters. Cover construction, custom base URL, credentials, proxy/SSL settings, model discovery, streaming, structured output, tool calls, and provider errors where supported.
- Extend usage-adapter tests using V2 input/output tokens and V1 fallback fixtures. Assert Yue-facing token field names, totals, TPS, and missing-value behavior.
- Preserve and extend the existing chat-stream runner, chat API, and API metrics tests. Assert SSE event names, sequence, final payload, error payload, tool activity, cancellation, and usage output rather than framework event types.
- Preserve and extend existing tool registry and builtin-tool tests. Cover authorization, schema translation, required and optional arguments, enum/array/object/nullable schemas, error conversion, and tool event emission.
- Preserve and extend existing MCP manager tests. Cover stdio and streamable HTTP connection, headers and environment placeholders, initialization failure isolation, reconnect, timeout, exit-stack cleanup, status reporting, and redaction.
- Add tests for the explicit output-completion policy using a controlled agent that combines structured output and a side-effecting tool. Assert that such an agent declares its strategy and that unintended work is not performed.
- Add V1 message-history fixtures containing text, tool calls, tool results, and multimodal parts. Assert V2 deserialization and replay preserve the Yue-visible result.
- Add instrumentation contract tests or integration assertions for the configured Logfire data format and usage attributes. Dashboard-query validation belongs in staging release evidence if dashboards are external.
- Run a sustained concurrency and cleanup check across streaming runs and MCP connections to detect leaked clients, unfinished tasks, and accumulated retry state.
- Reuse the established provider, tool registry, MCP manager, stream runner, session metadata, Smart Paste, multimodal, and chat metrics test patterns already present in the backend suite.
- Execute three test layers before production: offline deterministic tests, credentialed staging smoke tests, and canary monitoring.
- Staging smoke tests cover an OpenAI-compatible Chat Completions provider, Google/Gemini, one stdio MCP server, and one streamable HTTP MCP server. They must not reveal credentials in logs or artifacts.
- Canary release gates are measured against the V1 baseline. Roll back for agreed regressions in chat errors, tool errors, stream disconnects, token accounting, latency, or secret exposure.

## Out of Scope

- Moving existing providers from Chat Completions to the OpenAI Responses API.
- Replacing the Yue tool runtime with Pydantic AI MCPToolset, capabilities, or a new authorization system.
- A repository-wide migration from `httpx` to `httpx2`.
- Redesigning chat APIs, frontend SSE consumers, persisted chat schemas, or agent configuration UX.
- Introducing new providers, realtime features, durable execution, UI adapters, or Pydantic AI Harness capabilities.
- Changing user-facing tool permissions, side-effect policies, or MCP server configuration semantics.
- Reprocessing or rewriting stored conversations solely for the dependency upgrade.
- Implementing the migration in this specification; implementation is split into follow-up local issues.

## Further Notes

This specification is governed by the migration ADRs for staged versioning, Chat Completions preservation, provider HTTP isolation, stable usage contracts, explicit side-effecting tool behavior, preservation of the Yue tool runtime, and layered release gates.

The work is intentionally multi-session. Follow-up issues should be dependency-ordered, small enough to validate independently, and begin with baseline fixtures and the V1 compatibility stage. The production target remains pinned to 2.37.0 until post-release evidence supports a broader update policy.

The two operational values not fixed in this specification are the exact staging endpoints and the numeric canary thresholds. Establish both from the V1 baseline before deployment; they are release inputs, not reasons to defer implementation planning.

