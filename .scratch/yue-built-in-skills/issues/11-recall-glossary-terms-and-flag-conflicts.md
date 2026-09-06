# 11 - Recall glossary terms and flag conflicts

**What to build:** Yue can surface saved workspace terms in later chats and warn when a term appears fuzzy or conflicts with existing glossary meaning.

**Blocked by:** 10 - Save confirmed workspace glossary terms.

**Status:** resolved

**Validation:**
- `uv run pytest tests/test_workspace_service_unit.py -q`
- `python -m py_compile backend/app/services/workspace_service.py`

- [x] Saved workspace glossary terms can be recalled in relevant later conversations.
- [x] Yue can show provenance or confirmation state for recalled terms.
- [x] Yue warns when a term appears to conflict with an existing glossary entry.
- [x] Yue does not overwrite existing definitions silently.
- [x] Users can reject a conflict warning or choose an explicit resolution path.
