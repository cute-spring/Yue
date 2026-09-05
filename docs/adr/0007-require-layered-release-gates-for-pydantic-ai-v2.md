# Require layered release gates for the Pydantic AI V2 migration

Yue will release the Pydantic AI V2 migration only after offline regression tests, credentialed staging smoke tests for both provider and MCP paths, and a monitored canary deployment. The canary must roll back on agreed chat, tool, streaming, token-accounting, or latency regressions.

