# 01 - Establish local-owner policy and trusted-origin contract

**What to build:** A durable local policy model and management surface for exact business and SSO-handoff origins.

**Blocked by:** none.

**Status:** ready-for-agent

**Scope:**
- Define one local-owner policy store with a migration, service boundary, API, and settings UI.
- Support only canonical exact `https://host[:port]` origins; reject wildcard, path, credential-bearing, and implicit-subdomain entries.
- Add a request-and-approve flow that previews an origin before adding it, plus list/revoke operations.
- Distinguish `business` from `sso_handoff`; SSO pages must suppress text, screenshots, semantic controls, commands, and audit payloads.
- Make new-origin navigation block auto execution and create an approval/reconciliation requirement.
- Keep extension/session tokens, cookies, credentials, MFA, and raw IdP content out of persistence and logs.

**Validation:**
- Focused backend unit/API tests for canonicalization, rejection, add/revoke, SSO redaction, and navigation downgrade.
- Frontend tests for origin add/review/revoke states.
- Verify a backend restart restores policy but not live browser authority.

**Acceptance Criteria:**
- A local owner can easily add and revoke one exact origin.
- No policy operation expands trust to a subdomain or arbitrary destination.
- An SSO-handoff origin can support browser traversal without Yue receiving usable page content or actions.
