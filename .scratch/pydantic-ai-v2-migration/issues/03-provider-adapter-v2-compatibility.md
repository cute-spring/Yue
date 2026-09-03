# 03 - Preserve provider adapter behavior under V2

**What to build:** Keep every Yue provider adapter's existing execution behavior working on Pydantic AI V2, including Chat Completions semantics for OpenAI-compatible endpoints and targeted HTTP-client compatibility.

**Blocked by:** 02 - Migrate the core agent and usage contract to Pydantic AI V2.

**Status:** resolved

- [x] OpenAI-compatible adapters retain Chat Completions semantics and do not silently move to the Responses API.
- [x] OpenAI, Azure, custom-compatible, DeepSeek, LiteLLM, Ollama, and Google/Gemini adapters preserve supported construction, model discovery, streaming, structured output, and tool-call behavior.
- [x] Custom base URLs, credentials, proxy settings, SSL verification, and timeouts remain effective at the provider HTTP boundary.
- [x] Any V2-required `httpx2` client is isolated to the provider adapter that needs it; application-owned HTTP and MCP behavior remains on its existing boundary.
- [x] Provider adapter failures remain actionable and do not expose credentials or configuration secrets.

## Answer

Pydantic AI V2's OpenAI-compatible providers require `httpx2` clients. Yue now has a dedicated `get_pydantic_ai_http_client()` factory that creates an `httpx2.AsyncClient` only when proxy or custom-CA settings need application control. It applies the existing timeout, CA verification, proxy, connection-limit, and HTTP/2 policies.

Only model-execution adapters use this factory: OpenAI, Azure OpenAI, custom OpenAI-compatible, DeepSeek, LiteLLM, Ollama, and Gemini. Model discovery deliberately remains on the application-owned `httpx` factory, and direct MCP transport is untouched. The adapters continue to construct `OpenAIChatModel`, preserving Chat Completions behavior; no Responses API migration was introduced.

Validation command:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -q -W error::DeprecationWarning \
  tests/test_llm_providers_unit.py \
  tests/test_llm_utils_unit.py \
  tests/test_litellm_provider.py
```

Result: `26 passed`. The new boundary test proves configured provider transport creates `httpx2.AsyncClient`; existing provider tests cover construction, model discovery, base URLs, credentials, Azure deployment aliases, proxy/SSL helpers, timeout behavior, and actionable error paths without using credentials.

Credentialed staging smoke tests remain a release-gate task: local tests cannot validate actual provider streaming/tool calls, provider-specific structured output, or remote proxy behavior without the approved staging endpoints and secrets.
