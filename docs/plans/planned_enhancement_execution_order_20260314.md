# Planned Enhancement Execution Order (2026-03-14)

## Objective
Record the recommended execution order for current enhancement plans, based on dependency, implementation status, and rollout risk.

## Additional Higher-Priority Items (Before Current Plan Order)

These items are cross-cutting foundations and should be treated as **Priority 0**.  
Reason: they reduce regression risk across multiple plans at once and improve release safety more than any single feature plan.

### P0-1) Unified Contract Gate (SSE + API Compatibility)

- Scope: establish a mandatory compatibility gate for stream/event contracts and critical API schemas before rollout.
- Why this is higher priority:
  - Multiple planned tracks modify streaming and event semantics (reasoning/tools/transparency).
  - Without a single compatibility gate, each plan can pass local tests while still breaking reconnect/replay/front-end rendering.
  - Contract regressions directly damage user trust and are hard to hotfix safely.
- What to add:
  - Golden contract tests for `meta/content/error/tool_event/trace_event` payload shape and ordering.
  - Replay + reconnect determinism tests (same run -> same event sequence).
  - Backward-compat assertion for unknown event kinds on old clients.
- Success criteria:
  - Zero breaking schema changes enter mainline without explicit version bump.
  - Replay consistency and dedup tests remain green in CI for every release candidate.

### P0-2) Release Readiness Gate (Quality, Risk, and Rollback)

- Scope: introduce one release gate that combines quality signals, risk score, and rollback readiness.
- Why this is higher priority:
  - Existing plans are phase-heavy and feature-flag-driven; failure mode is not coding speed, but promotion without unified go/no-go criteria.
  - Manual sign-off exists in skills track; without one release gate, approvals are fragmented and easy to bypass.
  - Rollback delay is often more costly than implementation defects.
- What to add:
  - A release checklist requiring: full regression pass, migration dry-run pass, alert sanity pass, rollback drill pass.
  - Risk scoring dimensions: runtime path touched, data schema touched, UI protocol touched.
  - Hard block if rollback drill is missing for medium/high-risk changes.
- Success criteria:
  - Every promoted change has an auditable gate report.
  - Mean time to rollback is bounded with a rehearsed runbook.

### P0-3) Observability Baseline for Operations (SLO + Alerting)

- Scope: define service-level objectives and alert thresholds for chat/tooling quality before adding more feature surface.
- Why this is higher priority:
  - New features improve transparency, but without SLOs teams still cannot decide when to degrade, rollback, or scale.
  - Tool-calling reliability work needs model-level KPI operations to close the loop.
  - Prevents “metrics exist but no operational action” anti-pattern.
- What to add:
  - Core SLOs: stream success rate, first-token latency, tool-call mismatch rate, fallback rate, replay error rate.
  - Alert routing by severity with ownership (oncall target + response window).
  - Daily and weekly operational snapshots by provider/model.
- Success criteria:
  - Alert-to-action workflow is defined and exercised.
  - Model/tool degradations trigger automated or guided mitigation within target response time.

### P0-4) Data Lifecycle and Migration Safety (SQLite Focus)

- Scope: formalize schema migration, data retention, and replay data growth controls for trace/tool events.
- Why this is higher priority:
  - Transparency and replay features increase write volume; uncontrolled growth can degrade runtime and recovery.
  - Schema changes across tool_calls/run_traces require safe migration discipline.
  - Data correctness issues in traces are hard to repair retroactively.
- What to add:
  - Migration policy: forward-only migration + rollback fallback strategy + preflight checks.
  - Retention policy for high-volume event/chunk data.
  - Query/index budget checks to protect p95 read/write latency.
- Success criteria:
  - Migration failure path is validated before production promotion.
  - Database size and key query latency stay within agreed budget after rollout.

### P0-5) Hierarchical Memory Foundation (Short-Term + Long-Term)

- Scope: implement a production-safe memory baseline that combines session memory (short-term) and persistent memory (long-term) with retrieval/decay policy.
- Why this is higher priority:
  - It is explicitly planned but still pending in roadmap memory milestones.
  - Without memory, reasoning quality degrades in long sessions and cross-session continuity is weak.
  - Several planned features (skills quality, multi-agent orchestration, observability interpretation) become less effective without stable memory grounding.
- What to add:
  - **Short-term memory**: rolling summary + turn-level key facts for each active session.
  - **Long-term memory**: persistent store for durable facts/preferences with retrieval scoring and decay/importance policy.
  - **Memory write policy**: strict schema and confidence threshold to avoid storing hallucinated facts.
  - **Memory read policy**: bounded retrieval budget with citation-ready provenance fields.
- Success criteria:
  - Long-session quality improves with lower context-loss rate and fewer repeated user corrections.
  - Cross-session continuity works for durable user/project facts with measurable retrieval hit rate.
  - Memory writes are auditable and reversible, with no uncontrolled growth.

## Recommended Order

0. **Cross-Cutting Priority-0 Foundations (New)**  
   Source: This document (P0-1 ~ P0-5).  
   Priority reason: These controls prevent cross-plan regressions and create safe delivery conditions for all downstream enhancements.

1. **Reasoning + Tools Execution Enhancement**  
   Source: `reasoning_tools_execution_enhancement_plan_20260308.md`  
   Priority reason: Stabilizes event contract and turn-level attribution (`event_id`, `sequence`, `assistant_turn_id`), which is a prerequisite for reliable replay and transparency.

2. **OpenClaw Tool-Calling Governance**  
   Source: `openclaw_tool_calling_reference_execution_plan_20260308.md`  
   Priority reason: Adds model capability gates and scoped tool policies to reduce tool-call mismatch and silent failures before wider rollout.

3. **Observability & Transparency**  
   Source: `observability_transparency_plan.md`  
   Priority reason: Builds on stable event semantics from items 1 and 2; avoids amplifying inconsistent or duplicated telemetry in UI.

4. **PPT Skill Gap Enhancement**  
   Source: `ppt_skill_gap_enhancement_plan_20260307.md`  
   Priority reason: Delivers direct user-facing quality improvements (design system, QA loop, template workflow) after platform stability baseline.

5. **Markdown-Defined Skills (Remaining Sign-off and Hardening)**  
   Source: `markdown_defined_skills_plan.md`  
   Priority reason: Core phases are already implemented and auto-verified; focus on pending manual UI sign-off and targeted hardening.

6. **Nanobot Skill Gap Continuation (Phase 3/4 Optional)**  
   Source: `nanobot_skill_gap_plan_20260307.md`  
   Priority reason: Major Phase 1/2 work is already landed; continue only when distribution/ecosystem demand is confirmed.

7. **Built-in Tools Refactor (Maintenance Only)**  
   Source: `builtin_tools_refactor_plan.md`  
   Priority reason: Refactor is completed; keep as maintenance/backlog only.

## Detail Breakdown Status Flag

Legend:
- ✅ **Clear**: dedicated detailed breakdown plan exists.
- 🟡 **Partial**: partially covered in existing docs/plans, but no single complete execution plan.
- ❌ **Missing**: no clear detailed breakdown plan yet.

| Item | Breakdown Status | Evidence | Gap to Close |
|---|---|---|---|
| 0. Cross-Cutting Priority-0 Foundations | ✅ Clear | Source: This document (P0-1 ~ P0-5) | Split remaining items into dedicated execution plans |
| P0-1 Unified Contract Gate | ✅ Clear | `unified_contract_gate_execution_plan_20260314.md` | Complete Phase 2 (Replay/Reconnect) and Phase 3 (Backward Compatibility) |
| P0-2 Release Readiness Gate | ❌ Missing | No dedicated plan file yet | Create release gate plan (quality checklist, risk scoring, rollback drill protocol) |
| P0-3 Observability Baseline (SLO/Alerting) | 🟡 Partial | Related content exists in `observability_transparency_plan.md` and governance plan | Add explicit SLO catalog + alert ownership + oncall runbook plan |
| P0-4 Data Lifecycle & Migration Safety | 🟡 Partial | Persistence/migration concerns are mentioned in transparency plan | Add dedicated DB lifecycle plan (retention, migration preflight, rollback strategy, budget checks) |
| P0-5 Hierarchical Memory Foundation | ❌ Missing | Roadmap-level mention only (`ROADMAP 3.5 / 6.1`) | Create full memory evolution plan (STM/LTM schema, retrieval/decay, write/read governance) |
| 1. Reasoning + Tools Execution Enhancement | ✅ Clear | `reasoning_tools_execution_enhancement_plan_20260308.md` | Continue by phase gates |
| 2. OpenClaw Tool-Calling Governance | ✅ Clear | `openclaw_tool_calling_reference_execution_plan_20260308.md` | Execute Phase A-D rollout |
| 3. Observability & Transparency | ✅ Clear | `observability_transparency_plan.md` | Continue staged rollout and hardening |
| 4. PPT Skill Gap Enhancement | ✅ Clear | `ppt_skill_gap_enhancement_plan_20260307.md` | Execute phased design/dev/test track |
| 5. Markdown-Defined Skills | ✅ Clear | `markdown_defined_skills_plan.md` | Complete pending manual sign-off and remaining gates |
| 6. Nanobot Skill Gap Continuation | ✅ Clear | `nanobot_skill_gap_plan_20260307.md` | Decide Phase 3/4 based on demand thresholds |
| 7. Built-in Tools Refactor | ✅ Clear | `builtin_tools_refactor_plan.md` | Maintenance only |

## Prioritization Principles

- **Dependency first**: Execute foundational contract/governance work before UX-heavy transparency features.
- **Risk-controlled rollout**: Prefer fail-open compatibility and phased release where core chat stream remains stable.
- **ROI-aware sequencing**: Defer mostly-completed tracks to sign-off mode; prioritize items with highest impact on reliability and trust.
- **Operate before expand**: Build SLO/alerting and release gate discipline before adding new feature surface.

## Immediate Next Actions

1. Create and enforce P0 unified contract gate in CI for stream and replay compatibility.
2. Land release readiness gate with mandatory rollback drill output for medium/high-risk changes.
3. Define operational SLOs and alert ownership for chat/tool reliability and stream quality.
4. Start Memory Foundation MVP: short-term rolling summary and long-term durable memory schema with retrieval/decay policy.
5. Add memory write/read governance: confidence threshold, provenance, reversible update path.
6. Start Phase 1.5 + Phase 2 from Reasoning/Tools enhancement to lock event and attribution consistency.
7. Implement model capability matrix and provider/model tool scoping from OpenClaw governance plan.
8. Continue observability rollout in staged mode (emit-only -> persistence -> internal UI -> gradual release).

## Notes

- This document records planning guidance and does not replace detailed phase-level implementation plans in each source file.
