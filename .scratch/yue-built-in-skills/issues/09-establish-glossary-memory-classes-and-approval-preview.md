# 09 - Establish glossary memory classes and approval preview

**What to build:** Yue distinguishes terms, facts, preferences, conclusions, and temporary state, and previews durable glossary writes before approval.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** resolved

**Validation:**
- `uv run pytest tests/test_workspace_service_unit.py -q`
- `npm run test:unit -- src/components/ChatSidebar.workspace.test.ts`
- `python -m py_compile backend/app/services/workspace_service.py`
- `npm run build`

- [x] Yue can classify glossary and memory candidates as term, fact, preference, conclusion, or temporary state.
- [x] Durable glossary writes show a preview before saving.
- [x] The preview includes definition, aliases, provenance, confirmation status, and intended workspace scope when available.
- [x] Users can approve, reject, or keep a proposed entry as session-only context.
- [x] Tests prove research findings and temporary assumptions are not saved silently as durable workspace facts.
