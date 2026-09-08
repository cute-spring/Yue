# 04 - Implement two-layer Workspace first screen

**What to build:** Replace the resource-list-first Workspace panel with the selected `B - Two-Layer Context` direction.

**Blocked by:** 03 - Add frontend Understanding types and hook.

**Status:** ready

**Scope:**
- Add production components inspired by the prototype, not copied wholesale:
  - `WorkspaceUnderstandingPanel`
  - `WorkspaceUnderstandingGroupCard`
  - `AppliedUserMemoryPreview`
- Show `About You` as a lightweight left rail or top section depending on available width.
- Show `About This Workspace` as the main canvas with the fixed 8 groups.
- Keep Sources, Notes, Artifacts, and raw Memory management available as secondary sections or tabs.
- Add compact status metrics borrowed from Variant A.
- Preserve existing workspace selection, source mode, grounding mode, and resource management behavior.

**Validation:**
- Add/update frontend tests around Workspace rendering.
- Run `npm run build`.
- Browser-check a populated workspace and an empty workspace.

**Acceptance Criteria:**
- A selected Workspace opens to Understanding first, not Sources first.
- The user can still reach existing Sources, Notes, Artifacts, and Memory management.
- `About You` is visible but visually separate from workspace-level understanding.
- The layout remains usable on desktop and mobile.

