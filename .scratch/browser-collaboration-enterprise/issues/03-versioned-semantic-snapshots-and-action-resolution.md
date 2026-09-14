# 03 - Add versioned semantic snapshots and safe action resolution

**What to build:** A semantic page contract that replaces fragile text-only targeting as the execution basis.

**Blocked by:** 01.

**Status:** ready-for-agent

**Scope:**
- Capture versioned, redacted semantic snapshots with exact origin, page generation, accessible landmarks/controls, labels, roles, business row keys, validation messages, and field classification.
- Resolve actions against a snapshot version and verify a declared postcondition using a fresh snapshot.
- Define bounded, explainable locator fallback; ambiguous/missing targets block and request reconciliation.
- Exclude SSO-handoff pages and sensitive input values from snapshots.
- Evolve the extension action payload and backend browser tool contract without exposing arbitrary scripts/selectors.

**Validation:**
- Unit/integration tests for stable semantic resolution, stale snapshot rejection, ambiguity, DOM reload, validation error, and sensitive/SSO redaction.
- Representative dynamic table and labeled-form fixtures.

**Acceptance Criteria:**
- Every dispatched action identifies the snapshot version and semantic target it used.
- A changed page cannot silently redirect an action to a different control or record.
