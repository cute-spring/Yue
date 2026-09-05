# 06 - Define the Deep Research evidence contract in-product

**What to build:** Deep Research has source-scope preview, evidence-state labels, missing-evidence vocabulary, and tests for unsupported versus cited claims.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** resolved

**Validation:**
- `uv run pytest tests/test_api_workspaces_unit.py -q`
- `npm run test:unit -- src/components/ChatSidebar.workspace.test.ts src/pages/chat/utils/chatCommands.test.ts`
- `python -m py_compile backend/app/api/workspaces.py`
- `npm run build`

- [x] Deep Research can preview or summarize the source scope before a run begins.
- [x] Yue has user-visible labels for source-supported, inferred, user-confirmed, unsupported, and missing-evidence claims.
- [x] The evidence contract can represent unavailable sources and citation warnings.
- [x] Tests cover cited claims, unsupported claims, and missing-evidence states.
- [x] The evidence contract does not silently convert research findings into durable memory.
