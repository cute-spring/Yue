# 05 - Implement session approval envelopes and redacted audit trail

**What to build:** Server-enforced irreversible-action approval and local-owner auditability.

**Blocked by:** 01, 02, 03, 04.

**Status:** ready-for-agent

**Scope:**
- Classify irreversible actions centrally, including submit/send/approve/pay/delete/upload/sensitive paste/security changes/cross-origin navigation and risky downloads.
- Add one-action approval and session-scoped batch envelopes limited by exact origin, action class, previewed record set or maximum count, redacted consequence, expiry, and consumed action IDs.
- Reject an envelope on any material mismatch; make it impossible to reuse after expiry, revocation, or consumption.
- Persist append-only, redacted audit events with a hash chain for policy changes, lifecycle, commands, decisions, outcomes, retained artifacts, and manual deletions.
- Provide audit filtering/export and selective deletion; retain a redacted deletion event. Keep artifacts session-scoped unless retained deliberately.
- Require a dedicated approval for sensitive paste/upload and redact likely personal/financial identifiers everywhere.

**Validation:**
- Policy matrix tests for every irreversible class and every envelope boundary/mismatch.
- Audit tests for redaction, hash-chain verification, manual retention/deletion, and no stored secrets/raw field values.
- UI tests for single and batch approval previews.

**Acceptance Criteria:**
- Similar items can be approved once per bounded session envelope.
- Different, extra, expired, or sensitive-changing work always asks again.
- A local owner can inspect/export/delete redacted records without recovering authentication secrets.
