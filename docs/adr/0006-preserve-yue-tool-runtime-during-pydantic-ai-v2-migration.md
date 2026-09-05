# Preserve the Yue tool runtime during the Pydantic AI V2 migration

Yue will retain its direct MCP SDK integration and its own tool discovery, authorization, schema translation, and execution runtime during the V2 migration. Adopting Pydantic AI MCPToolset or capabilities is deferred to a separate architecture initiative so framework compatibility can be validated without redesigning a security-sensitive boundary.

