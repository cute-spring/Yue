# 10 - Save confirmed workspace glossary terms

**What to build:** A user can manually save a confirmed term with definition, aliases, provenance, confirmation status, and update metadata.

**Blocked by:** 09 - Establish glossary memory classes and approval preview.

**Status:** resolved

**Validation:**
- `uv run pytest tests/test_workspace_service_unit.py tests/test_api_workspaces_unit.py -q`
- `python -m py_compile backend/app/services/workspace_service.py`
- `npm run build`

- [x] A user can manually save a confirmed term to the active workspace glossary.
- [x] The saved entry includes definition, aliases, provenance, confirmation status, and update metadata.
- [x] Yue previews the durable write before saving.
- [x] Saved glossary entries can be listed or inspected in the active workspace.
- [x] Sensitive or secret values are not stored unless policy allows it and the user confirms.
