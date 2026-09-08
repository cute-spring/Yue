# 03 - Add frontend Understanding types and hook

**What to build:** Frontend state loading for Workspace Understanding without further bloating `useChatWorkspace`.

**Blocked by:** 02 - Add Workspace Understanding API contract.

**Status:** resolved

**Scope:**
- Add `WorkspaceUnderstandingSummary`, `WorkspaceUnderstandingGroup`, and `WorkspaceUnderstandingItem` types to `frontend/src/types.ts`.
- Add `frontend/src/pages/chat/hooks/useWorkspaceUnderstanding.ts`.
- Load `/api/workspaces/{workspace_id}/understanding`.
- Reset summary state when no workspace is selected.
- Expose loading and error states.
- Provide a refresh function for later memory approval flows.

**Validation:**
- Add focused hook or helper tests where the existing test setup makes that practical.
- Run `npm run build`.

**Acceptance Criteria:**
- Workspace Understanding loading is isolated behind a small hook interface.
- `useChatWorkspace` does not become responsible for product grouping behavior.
- The frontend has typed access to groups, counts, representative items, and applied user memory preview.
