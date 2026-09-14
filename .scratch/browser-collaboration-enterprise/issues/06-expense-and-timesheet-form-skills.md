# 06 - Deliver expense-report and timesheet form skill templates

**What to build:** Versioned, parameterized enterprise form templates for expense reports and timesheets.

**Blocked by:** 03, 04, 05.

**Status:** ready-for-agent

**Scope:**
- Define the reusable form-skill schema: origin scope, parameters, page contract, preconditions, validation, draft/save/submit boundary, approval class, evidence, and recovery instructions.
- Implement an expense-report template with line-item validation, totals/policy warnings, draft population, receipt boundary, and submit envelope.
- Implement a timesheet template with date/project/hour rows, conflict detection, save-draft behavior where available, and bounded batch submission.
- Version templates and ensure sensitive fields are user-entered or separately approved.

**Validation:**
- Fixture-driven E2E tests for happy path, validation failure, stale page, duplicate row, session batch approval, disconnect, and recovery.

**Acceptance Criteria:**
- Both templates produce a reviewable draft and evidence before any submission.
- A failed run identifies the field/record that needs reconciliation and can resume safely.
