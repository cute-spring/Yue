# 02 - Add Workspace Understanding API contract

**What to build:** A thin API endpoint that exposes the Workspace Understanding summary to the frontend.

**Blocked by:** 01 - Build Workspace Understanding summary service.

**Status:** resolved

**Scope:**
- Add `GET /api/workspaces/{workspace_id}/understanding`.
- Return `workspace_id`, fixed groups, representative items, summary counts, and an empty or stubbed `applied_user_memory_preview` field for the first slice.
- Return 404 when the workspace does not exist.
- Keep the route wrapper thin; business logic stays in the summary service.

**Validation:**
- Add API unit tests in `backend/tests/test_api_workspaces_unit.py`.
- Add a service-backed integration-style test where practical.
- Run the focused workspace tests.

**Acceptance Criteria:**
- Frontend can load the full Workspace Understanding first-screen model with one request.
- The endpoint preserves the fixed group order.
- The API response shape is stable enough for frontend types.
