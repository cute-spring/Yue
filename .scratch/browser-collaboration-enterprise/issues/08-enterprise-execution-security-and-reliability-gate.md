# 08 - Run enterprise execution security and reliability gate

**What to build:** A release gate covering the end-to-end browser execution, recovery, governance, and template flows.

**Blocked by:** 02, 03, 04, 05, 06, 07.

**Status:** ready-for-agent

**Scope:**
- Build an E2E matrix for extension lifecycle, trusted/SSO origins, browser restarts, reconnect/reconciliation, approval envelopes, audit retention/deletion, sensitive-data redaction, and all four templates.
- Add adversarial cases for prompt injection in page content, ambiguous semantic targets, forged/duplicate result messages, expiry, cross-origin redirect, and sensitive paste/upload.
- Document operational recovery and the intentional post-restart reauthorization behavior.
- Record performance/reliability thresholds for command delivery and reconciliation without weakening safety.

**Validation:**
- Automated unit, API, frontend, extension, and E2E suites plus a manual release checklist on representative authenticated test systems.
- Security review against the source specifications and implementation diff.

**Acceptance Criteria:**
- Every delivery gate in the execution specification is demonstrably met.
- Release evidence shows no path from page content to expanded authorization, secret capture, unapproved irreversible action, or silent duplicate execution.
