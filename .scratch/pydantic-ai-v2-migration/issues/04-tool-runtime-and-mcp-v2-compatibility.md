# 04 - Validate the tool runtime and MCP compatibility under V2

**What to build:** Keep Yue's tool runtime as the tool integration seam while proving builtin and MCP tools behave safely and consistently on Pydantic AI V2.

**Blocked by:** 02 - Migrate the core agent and usage contract to Pydantic AI V2.

**Status:** resolved

- [x] Builtin and MCP tool authorization, names, schemas, validation, provider-specific schema translation, error classification, and Yue tool events remain stable.
- [x] Tool execution retains expected retries, cancellation behavior, and cleanup without adopting Pydantic AI MCPToolset or capabilities.
- [x] Stdio and streamable HTTP MCP servers connect, initialize, call tools, reconnect, time out, report status, and clean up correctly.
- [x] Environment placeholders and request headers continue to be redacted from logs, status, traces, and failure output.
- [x] Any future structured-output agent that combines side-effecting function tools declares and tests its output-completion strategy explicitly.

## Answer

Yue's custom `BaseTool`/`ToolRegistry` boundary remains intact on Pydantic AI V2. It continues to use `Tool` and `RunContext`; no `MCPToolset`, capabilities API, or framework-managed authorization model was introduced. The only structured-output agent is Smart Paste and it has no side-effecting tools, so no `end_strategy` override is appropriate. Future structured-output agents that add side-effecting function tools must declare and test their strategy before release.

Validation command:

```bash
PYTHONPATH=.:../../session-context-manager/src .venv/bin/python -m pytest -q -W error::DeprecationWarning \
  tests/test_base_tool_unit.py tests/test_tool_registry_integration.py \
  tests/test_mcp_manager_unit.py tests/test_mcp_builtin_registry.py \
  tests/test_docs_builtin.py tests/test_excel_builtin.py
```

Result: `81 passed`, with one unrelated existing docs-tool contract failure: `test_docs_list_fails_closed_when_allow_roots_empty` expects an error object but the current `DocsListTool` returns a list. This does not involve Pydantic AI, tool conversion, MCP connection lifecycle, or secret handling and is recorded separately for the docs-tool work.
