# 07 - Deep Research creates a cited workspace report

**What to build:** A user can run source-scoped research from workspace sources and save a cited report with findings, assumptions, gaps, and next actions.

**Blocked by:** 06 - Define the Deep Research evidence contract in-product.

**Status:** resolved

**Validation:**
- `uv run pytest tests/test_api_workspaces_unit.py -q`
- `npm run test:unit -- src/pages/chat/utils/chatCommands.test.ts src/components/ChatSidebar.workspace.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts`
- `python -m py_compile backend/app/api/workspaces.py`
- `npm run build`

- [x] A user can start Deep Research from a visible product entry point or shortcut.
- [x] The user can choose or confirm workspace source scope before research begins.
- [x] The output is saved as a workspace-attached research artifact.
- [x] The report includes summary, findings, citations, evidence gaps, assumptions, and next actions.
- [x] Unsupported claims are labeled instead of presented as sourced facts.
- [x] No external send or durable memory write occurs without explicit confirmation.
