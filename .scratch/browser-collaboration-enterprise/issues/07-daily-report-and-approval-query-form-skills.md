# 07 - Deliver daily-report and approval-query form skill templates

**What to build:** A safe daily-report draft/submit template and a strictly read-only approval-query template.

**Blocked by:** 03, 04, 05.

**Status:** ready-for-agent

**Scope:**
- Implement daily-report parameters, rendered-draft preview, validation, redacted evidence, and approved submission boundary.
- Implement approval-query search/filter/result schema with stable business row keys and a hard prohibition on approve/reject/write actions.
- Expose template capabilities and recovery guidance in the user-facing skill UI.

**Validation:**
- Fixture-driven E2E tests for query filtering, empty/error states, daily-report preview/submit, policy boundary, and recovery after reload.

**Acceptance Criteria:**
- Approval query can never mutate an approval item.
- Daily report cannot submit until the user approves its reviewed consequence.
