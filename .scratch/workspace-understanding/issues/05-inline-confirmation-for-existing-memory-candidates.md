# 05 - Inline confirmation for existing memory candidates

**What to build:** Convert the existing explicit memory candidate flow into the new inline confirmation experience.

**Blocked by:** 04 - Implement two-layer Workspace first screen.

**Status:** resolved

**Scope:**
- Add `InlineMemoryConfirmation` UI for candidates created from the existing `Review as memory` actions.
- Show proposed memory in plain language.
- Show recommended destination, initially `This Workspace`.
- Allow actions equivalent to approve, keep session-only/reject, and edit before save.
- Refresh Workspace Understanding after approval or rejection.
- Preserve existing memory candidate governance behavior.

**Validation:**
- Add frontend tests for Remember, Just this time, and Edit paths.
- Add/update backend tests only if metadata contract changes.
- Add Playwright coverage for chat -> create candidate -> inline confirm -> summary refresh.

**Acceptance Criteria:**
- Explicit memory review no longer feels like a separate management workflow.
- Durable memory still requires user confirmation.
- Approving a candidate updates the Workspace Understanding summary.
