# 04 - Persist recoverable execution state and chat events

**What to build:** A redacted execution state machine and chat event contract that accurately represents asynchronous browser work.

**Blocked by:** 02, 03.

**Status:** ready-for-agent

**Scope:**
- Introduce execution/action state transitions: planned, awaiting_approval, queued, leased, running, succeeded, failed, blocked, needs_reconciliation, cancelled, expired.
- Correlate commands, snapshots, approvals, and outcomes to chat runs and stream durable events to the frontend.
- Restore execution history after a browser-page/chat refresh and render appropriate resume/reconcile/stop affordances.
- Require terminal command result plus required fresh evidence before displaying completion.
- Preserve the existing ephemeral browser authority boundary.

**Validation:**
- API/service/frontend tests for state transitions, refresh recovery, stale event ordering, cancelled work, and uncertain command reconciliation.
- Contract tests for chat tool responses that must not claim a queued action has completed.

**Acceptance Criteria:**
- A user can understand and recover every non-terminal action after UI or transport interruption.
- Chat never reports success merely because an action was queued or dispatched.
