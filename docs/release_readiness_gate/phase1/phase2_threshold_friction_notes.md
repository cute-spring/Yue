# P0-2 Phase 2 Automation Input: Threshold and Friction Notes

## 1) Scope

- source_phase: `P0-2 Phase 1 Manual Enforcement`
- date: `2026-03-14`
- based_on_reports:
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-001.md`
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-002.md`
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-003.md`
- rollback_evidence:
  - `docs/release_readiness_gate/phase1/rollback_drills/RBD-20260314-001.md`

## 2) Threshold Recommendations for Phase 2

1. Risk tier threshold
   - keep `low: 0-1`, `medium: 2-3`, `high: 4-6`
   - require rollback evidence for `medium/high`
2. Quality gate threshold
   - block promotion if any required quality field is missing
   - required fields: backend unit, frontend typecheck, frontend unit, decision metadata
3. Rollback SLO threshold
   - medium rollback drill must be `<= 15 min`
   - high rollback drill must be `<= 30 min`

## 3) Friction Observed in Phase 1

1. Verification command ambiguity
   - `npm run build -- --noEmit` can fail due Vite arg handling
   - practical fallback needed: `npx tsc --noEmit`
2. Memory pressure in stream tests
   - full response buffering assertions are expensive for local regression
   - streaming assertions with early-exit are safer and faster
3. False confidence from aggregate script output
   - project-level scripts may continue after backend failures
   - release gate must rely on explicit command-level pass/fail evidence

## 4) False-Positive/False-Negative Risk

1. False positive risk
   - tool-level script exits can hide individual command failures if not parsed
2. False negative risk
   - strict full-suite gating may fail due unrelated environment dependencies
3. Mitigation
   - separate mandatory targeted regression bundle for release candidate scope
   - store exact command output summary in gate report

## 5) Phase 2 Automation Sequence Advice

1. Step A: schema validation
   - validate gate report structure and required fields
2. Step B: command evidence validation
   - check each required command has explicit pass/fail and timestamp
3. Step C: risk-policy enforcement
   - if tier in `medium/high`, verify rollback evidence path exists
4. Step D: promotion hard block
   - reject promotion when required evidence is missing
5. Step E: archive and reporting
   - auto-store gate report + rollback drill linkage in release records

## 6) Memory-Safe Automation Constraint

1. enforce stream-test assertion policy in CI checks:
   - disallow new `response.content.decode("utf-8")` patterns in stream test files
2. enforce payload-size policy for non-stress test suites:
   - reject oversized synthetic payload additions outside dedicated benchmark files
