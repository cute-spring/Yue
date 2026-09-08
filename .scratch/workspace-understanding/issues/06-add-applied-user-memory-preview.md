# 06 - Add applied User Memory preview

**What to build:** Show relevant `About You` memory inside Workspace without mixing it into Workspace Understanding groups.

**Blocked by:** 04 - Implement two-layer Workspace first screen.

**Status:** ready

**Scope:**
- Add a small backend interface for user-level memory preview.
- For the first slice, reuse existing memory storage with `scope_type = user` if available.
- Populate `applied_user_memory_preview` in `/understanding`.
- Render the preview in the selected two-layer layout.
- Ensure user-level memories do not appear in workspace groups.

**Validation:**
- Backend tests for user memory preview separation.
- Frontend tests for rendering empty and populated preview states.
- Run focused workspace tests and `npm run build`.

**Acceptance Criteria:**
- Workspace clearly shows which cross-workspace preferences are active.
- User Memory is not duplicated into Workspace Memory.
- The implementation can later swap storage behind the user-memory interface.

