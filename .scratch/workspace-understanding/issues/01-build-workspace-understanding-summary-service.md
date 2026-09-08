# 01 - Build Workspace Understanding summary service

**What to build:** A backend module that maps existing workspace memories and memory candidates into fixed Workspace Understanding groups.

**Blocked by:** none.

**Status:** resolved

**Scope:**
- Add `backend/app/services/workspace_understanding_service.py`.
- Define the fixed group taxonomy: Background, Goals, Decisions, Constraints, Preferences, Terms, Open Questions, Current State.
- Map existing `memory_type` values into those groups.
- Respect an optional metadata override such as `understanding_group`.
- Include active memory counts, pending candidate counts, and representative items.
- Keep raw Sources, Notes, and Artifacts out of the grouping logic.

**Validation:**
- Add focused unit tests in `backend/tests/test_workspace_understanding_service_unit.py`.
- Verify every group is present even when empty.
- Verify pending candidates contribute to pending counts.
- Verify `scope_type = user` memories are not mixed into workspace groups.
- `backend/.venv/bin/python -m pytest tests/test_workspace_understanding_service_unit.py -q`

**Acceptance Criteria:**
- A caller can ask for one workspace summary through one small service interface.
- The response always contains the fixed 8 groups in stable order.
- Existing workspace memory records require no migration to appear in the summary.
- Grouping logic is not duplicated in route handlers or frontend code.
