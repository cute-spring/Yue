# Preserve Chat Completions semantics during the Pydantic AI V2 migration

Yue will retain its existing OpenAIChatModel-based Chat Completions behavior for OpenAI-compatible provider adapters while migrating to Pydantic AI 2.37.0. Moving to the Responses API is deferred because it would independently alter streaming, tool, and payload behavior, making regressions harder to attribute during the framework migration.

