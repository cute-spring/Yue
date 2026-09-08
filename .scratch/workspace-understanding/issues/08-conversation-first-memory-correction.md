# 08 - Conversation-first memory correction

**What to build:** Treat user corrections as candidates to update, replace, or archive stale memory.

**Blocked by:** 07 - High-signal memory capture MVP.

**Status:** ready

**Scope:**
- Detect correction language in user messages.
- Match corrections to existing User Memory or Workspace Memory when possible.
- Propose `update`, `replace`, or `archive` actions inline.
- Expose a `View conflict` affordance when an existing memory is implicated.
- Ensure superseded or archived memory is not loaded into future prompt context.

**Validation:**
- Backend tests for correction matching and replacement metadata.
- Prompt-context tests proving superseded memory is excluded.
- Playwright test for correction -> inline confirmation -> future summary update.

**Acceptance Criteria:**
- Users can correct Yue naturally in chat.
- Yue proposes the right memory lifecycle action instead of keeping stale memory active.
- Workspace management remains a review surface, not the only correction path.

