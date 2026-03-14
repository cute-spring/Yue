# Release Readiness Gate (Quality, Risk, and Rollback) Execution Plan

## 1. Background and Goals

### 1.1 Background

Current enhancement tracks are phase-heavy and feature-flag-driven. The dominant failure mode is no longer implementation speed; it is inconsistent promotion criteria across tracks:

1. Quality checks are fragmented across unit/integration/manual flows.
2. Risk is discussed qualitatively, but not scored consistently.
3. Rollback is often documented but not rehearsed before promotion.

As a result, different plans can appear “ready” while carrying very different release risk.

### 1.2 Goals

This plan establishes one mandatory release gate (P0-2) for all medium/high-impact changes:

1. Define a single go/no-go checklist for release candidates.
2. Standardize risk scoring with explicit dimensions and thresholds.
3. Enforce rollback drill evidence before promotion for medium/high-risk changes.
4. Produce auditable gate reports for every promoted release.

### 1.3 Success Criteria

1. Every promoted release has a gate report attached.
2. Medium/high-risk releases cannot be promoted without rollback drill evidence.
3. Mean time to rollback (MTTRb) is measured and bounded by agreed targets.
4. Promotion decisions become reproducible across teams and release windows.

### 1.4 Out of Scope

1. This plan does not redesign feature implementation architecture.
2. This plan does not replace service-specific test strategy documents.
3. This plan does not introduce a new external release platform in Phase 0/1.

---

## 2. Gate Scope and Applicability

### 2.1 Gate Coverage

The gate applies to:

1. Backend API/schema changes.
2. Stream contract/event semantics changes.
3. Persistence/migration related changes.
4. Frontend protocol/rendering behavior changes.
5. Tool-calling governance and runtime policy changes.

### 2.2 Exemptions

Only low-risk changes can request expedited path:

1. Copy/text-only UI updates with no logic change.
2. Non-runtime docs updates.
3. Internal refactors with proven no-behavior-change evidence.

Exemptions still require a minimal gate record with rationale.

---

## 3. Gate Model

## Gate A: Quality Readiness

Mandatory checks:

1. Unit tests pass for touched modules.
2. Integration tests pass for impacted APIs/flows.
3. Lint/type checks pass.
4. Contract/regression suites pass where applicable.

Fail condition: any mandatory check red.

## Gate B: Risk Scoring

Each release candidate receives a risk score from three dimensions:

1. Runtime Path Touched (R): none=0, minor=1, critical path=2.
2. Data Schema Touched (D): none=0, additive=1, migration/semantic change=2.
3. UI/API Protocol Touched (P): none=0, backward-compatible=1, compatibility-sensitive=2.

Score formula:

`risk_score = R + D + P`

Risk tiers:

1. Low: 0-1
2. Medium: 2-3
3. High: 4-6

## Gate C: Rollback Readiness

Requirements by tier:

1. Low: rollback path documented.
2. Medium: rollback dry-run evidence required.
3. High: full rollback drill evidence + owner sign-off required.

Hard block:

1. Medium/high changes without required rollback evidence cannot be promoted.

---

## 4. Checklist Template (Release Candidate)

Each release candidate must include:

1. Release metadata:
   - release_id
   - owner
   - change summary
2. Quality evidence:
   - unit/integration/lint/typecheck results
   - contract/regression summary
3. Risk scoring:
   - R/D/P values
   - total score and tier
   - rationale per dimension
4. Rollback readiness:
   - rollback strategy type
   - drill output/log links
   - max expected rollback duration
5. Decision:
   - go/no-go
   - approver and timestamp

---

## 5. Rollback Drill Protocol

### 5.1 Drill Scenarios

At least one scenario per medium/high release:

1. Service degradation after deployment.
2. Contract incompatibility discovered post-promotion.
3. Migration-induced error requiring restore/fallback.

### 5.2 Minimum Evidence

1. Trigger condition and observed symptom.
2. Rollback command/procedure used.
3. Time markers: detect/start-complete.
4. Service recovery verification result.
5. Follow-up risk notes.

### 5.3 Target SLO for Rollback

Initial targets (to be tuned after two release cycles):

1. Medium-risk rollback complete within 15 minutes.
2. High-risk rollback complete within 30 minutes.

---

## 6. CI/CD and Release Workflow Integration

### 6.1 PR Stage

1. Compute preliminary risk score from labels/changed surfaces.
2. Require release gate checklist stub for medium/high candidates.
3. Block merge if required checks fail.

### 6.2 Release Candidate Stage

1. Execute full gate checklist.
2. Attach all evidence artifacts.
3. Enforce rollback evidence policy.

### 6.3 Promotion Stage

1. Publish gate report.
2. Record approver identity and rationale.
3. Archive report in release records.

---

## 7. Data Model for Gate Report

Recommended report schema:

```json
{
  "release_id": "string",
  "owner": "string",
  "risk": {
    "runtime_path": 0,
    "data_schema": 0,
    "ui_api_protocol": 0,
    "total": 0,
    "tier": "low|medium|high"
  },
  "quality": {
    "unit": "pass|fail",
    "integration": "pass|fail",
    "lint": "pass|fail",
    "typecheck": "pass|fail",
    "contract_regression": "pass|fail|na"
  },
  "rollback": {
    "required": true,
    "evidence_attached": true,
    "drill_duration_minutes": 0
  },
  "decision": {
    "result": "go|no-go",
    "approver": "string",
    "timestamp": "ISO-8601"
  }
}
```

---

## 8. Phased Delivery

## Phase 0: Policy and Template Baseline (Completed in this plan)

1. Define gate model and scoring.
2. Publish checklist and rollback protocol.

Deliverables:

1. This plan document.
2. Risk scoring rubric v1.
3. Gate report schema draft.

## Phase 1: Manual Enforcement

1. Apply gate manually to all medium/high changes.
2. Collect first-cycle metrics and friction points.

Deliverables:

1. First 3 gate reports.
2. Initial rollback drill records.
3. Threshold/friction notes for Phase 2 automation input.

### Phase 1 Execution Rules (Added for Runability)

1. Artifact root for Phase 1 records: `docs/release_readiness_gate/phase1/`.
2. Gate reports must be stored as:
   - `docs/release_readiness_gate/phase1/gate_reports/<release_id>.md`
3. Rollback drill evidence must be stored as:
   - `docs/release_readiness_gate/phase1/rollback_drills/<drill_id>.md`
4. Threshold/friction notes must be stored as:
   - `docs/release_readiness_gate/phase1/phase2_threshold_friction_notes.md`
5. Minimum quality evidence for each gate report:
   - backend unit regression command and result
   - frontend typecheck command and result
   - frontend unit test command and result
6. Minimum Phase 1 completion bar:
   - at least 3 gate reports completed
   - at least 1 medium/high release with rollback drill evidence attached
   - threshold/friction notes include blocking conditions, false-positive risk, and implementation sequencing advice for Phase 2

## Phase 2: Pipeline Enforcement

1. Integrate gate checks into CI/release workflow.
2. Enforce hard-block policy automatically.

Deliverables:

1. CI policy checks for gate completeness.
2. Automated validation for mandatory evidence fields.

## Phase 3: Continuous Optimization

1. Tune risk thresholds with real incident/rollback data.
2. Optimize drill cadence and response playbooks.

Deliverables:

1. Quarterly threshold revision.
2. Updated MTTRb targets by risk tier.

---

## 9. Roles and Ownership

1. Release owner: prepares gate report and evidence.
2. Domain reviewer: validates risk scoring rationale.
3. Oncall/operations reviewer: validates rollback readiness.
4. Final approver: grants go/no-go with auditable decision.

---

## 10. Definition of Done

P0-2 is considered complete when:

1. A dedicated execution plan exists and is referenced from master priority plan.
2. Gate checklist is used in release candidate promotion.
3. Risk scoring is applied consistently with auditable rationale.
4. Medium/high releases include rollback drill evidence before promotion.
5. At least one rollback drill has been executed and archived.
6. Every promoted release has an attached gate report.

---

## 11. Execution Progress Log

### 2026-03-14

1. Phase 1 manual enforcement started.
2. Plan patched with explicit evidence storage paths and completion bar.
3. Phase 1 outputs completed:
   - gate reports:
     - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-001.md`
     - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-002.md`
     - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-003.md`
   - rollback drill evidence:
     - `docs/release_readiness_gate/phase1/rollback_drills/RBD-20260314-001.md`
   - threshold/friction notes:
     - `docs/release_readiness_gate/phase1/phase2_threshold_friction_notes.md`
4. Verification evidence recorded for Phase 1:
   - backend: `pytest tests/test_api_chat_unit.py -q` -> `21 passed`
   - backend targeted retry path: `pytest tests/test_api_chat_unit.py::test_chat_stream_auto_retry_after_tool_call_mismatch tests/test_api_chat_unit.py::test_chat_stream_emits_tool_call_mismatch_when_no_tool_events -q` -> `2 passed`
   - frontend typecheck: `npx tsc --noEmit` -> `pass`
   - frontend unit: `npm run test` -> `14 passed`

---

## 12. Remaining Scope Checklist (Phase 1 Completion Focus)

P0-2 is not complete until all items below are finished:

1. [x] Produce first 3 gate reports under `docs/release_readiness_gate/phase1/gate_reports/`.
2. [x] Ensure at least one medium/high release includes rollback drill evidence under `docs/release_readiness_gate/phase1/rollback_drills/`.
3. [x] Publish threshold/friction notes at `docs/release_readiness_gate/phase1/phase2_threshold_friction_notes.md`.
4. [x] Update this execution plan progress log with evidence file paths and go/no-go decisions.
5. [x] Update `planned_enhancement_execution_order_20260314.md` P0-2 status from planning to execution progress with evidence links.

### 12.1 Memory-Safe Execution Guardrails (Mandatory During Phase 1)

To avoid local test memory pressure and unstable verification:

1. Do not use full-response buffering assertions in streaming tests (avoid `response.content.decode("utf-8")` for large/stream paths).
2. Prefer line-by-line streaming assertions (`iter_lines`) with early-exit checks once target evidence is found.
3. Keep test payload sizes near threshold conditions and avoid oversized synthetic fixtures unless explicitly required.
4. Run targeted verification first (`pytest tests/test_api_chat_unit.py -q`) before broader regression.
5. Keep backend verbose chat logs disabled during routine local regression unless debugging requires them.
