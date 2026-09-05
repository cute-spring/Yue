# Isolate Pydantic AI V2 httpx2 use at the provider boundary

Yue will keep its existing `httpx` clients for application-owned provider discovery, proxy/SSL handling, and MCP transport. Where Pydantic AI V2 requires `httpx2`, the provider adapter will own the narrow compatibility boundary rather than triggering a repository-wide HTTP-client migration.

