# Yue

Yue is an AI chat-agent platform that combines provider-backed agents, MCP tools, skills, and streaming chat into one user-facing runtime.

## Language

**Chat execution boundary**:
The backend boundary that converts an incoming chat request into provider execution, tool activity, streamed events, and persisted chat state.
_Avoid_: Chat pipeline, agent loop

**Provider adapter**:
The Yue-owned component that configures a specific LLM provider or OpenAI-compatible endpoint for the chat execution boundary.
_Avoid_: Model factory, LLM client

**Tool runtime**:
The Yue-owned layer that discovers, authorizes, schemas, and executes builtin and MCP tools for an agent run.
_Avoid_: MCP layer, tool registry

**Migration compatibility stage**:
The interim release on the previous major Pydantic AI line used to expose and resolve deprecations before the V2 upgrade.
_Avoid_: Partial upgrade, temporary version

**OpenAI execution protocol**:
The API semantics used by Yue provider adapters when executing an OpenAI-compatible chat request. Existing adapters preserve Chat Completions behavior during the Pydantic AI V2 migration.
_Avoid_: OpenAI model name, provider transport

**Provider HTTP boundary**:
The boundary at which a Yue provider adapter supplies an HTTP client required by a provider SDK or Pydantic AI. Pydantic AI V2-specific `httpx2` use remains confined here.
_Avoid_: Global HTTP migration, shared HTTP stack

**Usage contract**:
The Yue-facing token and completion metrics exposed by chat execution and persistence. It keeps `prompt_tokens` and `completion_tokens` stable while framework-specific usage fields are translated internally.
_Avoid_: Provider usage object, raw telemetry fields

**Side-effecting tool policy**:
The rule governing function tools that can change user-visible or external state. An agent combining them with structured output must declare its output-completion behavior explicitly.
_Avoid_: Default tool behavior, implicit tool ordering

**Tool runtime**:
The Yue-owned component that discovers, authorizes, schemas, and executes builtin and MCP tools for the chat execution boundary. It remains the integration seam during the Pydantic AI V2 migration.
_Avoid_: Pydantic AI MCPToolset, framework tool layer

**Migration release gate**:
The required evidence before a framework migration reaches production: offline regression coverage, credentialed staging smoke tests, and monitored canary rollout with rollback thresholds.
_Avoid_: Single test-suite pass, direct production upgrade
