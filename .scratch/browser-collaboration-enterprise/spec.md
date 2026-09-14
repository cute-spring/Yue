# Browser Collaboration Enterprise Execution

**Status:** ready-for-agent

## Source specifications

- `docs/specs/2026-09-09-browser-collaboration-enterprise-execution-spec.md`
- Primary-worktree baseline: `docs/specs/2026-09-08-browser-collaboration-product-spec.md`
- Current implementation: `backend/app/services/browser_session_service.py`, `backend/app/api/browser.py`, `backend/app/mcp/builtin/browser.py`, `browser-extension/`

## Product boundary

Make the browser collaboration foundation dependable for a local owner operating authenticated enterprise web applications. The first delivery sequence must establish policy, a reconnectable/idempotent execution protocol, recoverable action/chat state, auditable approvals, and four parameterized form skills. Do not add general workflow recording or scheduling before those foundations prove safe.

## Confirmed decisions

- The local Yue user is administrator by default; separate roles are out of scope.
- Exact HTTPS origins only. Local policy offers an easy request-and-approve flow to add origins.
- IdP origins are SSO-handoff-only and never yield page content or executable controls.
- Irreversible actions always need explicit confirmation, ordinarily through a bounded session approval envelope for similar items.
- Audit records are local, redacted, hash-linked, and retained until the user deletes them. Artifacts remain session-scoped unless explicitly retained.
- Authentication secrets and IdP content are never captured. Sensitive paste/upload needs dedicated confirmation.

## Ticket flow

Implement the dependency frontier in numeric order unless all declared blockers are complete. Issue 01 is the initial frontier; issues 02 and 03 may proceed in parallel after it. The form templates remain blocked until the execution, approval, audit, and semantic contracts have converged.
