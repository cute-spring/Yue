# Yue Session Context Reference Host Status (2026-05-23)

## Scope

This note records the current completion status for Yue as the first reference host validating the generic host integration seams for `midterm-session-memory`.

This is a controlled validation pass only.

Out of scope for this step:

- broad rollout
- default-on enablement
- moving Yue-specific code into `midterm-session-memory`
- redesigning Yue's request or prompt pipeline

## Current Completion Status

Status: `COMPLETE FOR REFERENCE-HOST VALIDATION PASS`

The following Yue-side behaviors are now verified:

- Yue host integration shape was audited from code, including the adapter, `SessionContextManager.resolve(...)` call site, prompt append path, and feature-flag gating.
- Yue-native `message` and `tool` records map into ordered `ContextEvent` values with normalized event types.
- With `session_context_enabled=True`, Yue reaches `SessionContextManager.resolve(...)` through the existing thin integration.
- Exported prompt context is consumed by Yue and appended into the existing prompt assembly flow.
- Yue-side prompt context consumption preserves traceability fields including block names, sections, selected candidate ids, and source chunk ids.
- With `session_context_enabled=False`, Yue keeps prior behavior and does not inject session context blocks.
- The integration remains scoped to session-context seams and does not introduce cross-session or external retrieval through this path.

## Local Validation Included

The current Yue-local deterministic validation covers:

- adapter mapping and event ordering
- thin integration happy path
- feature-flag OFF path
- traceability preservation
- retrieval boundary expectations at the Yue host seam
- prompt append ordering inside Yue's existing assembly flow

Validation was kept local and deterministic:

- no network calls
- no model calls
- no external services

## Remaining Gaps Before Broader Rollout

The current pass is sufficient for Yue as a first reference host, but not yet sufficient for broader rollout.

Remaining gaps:

- The committed reviewed traffic-derived replay corpus is still small and only covers the first conservative promotion pass.
- The rollout gate is now documented, but it has not yet been exercised as part of a broader promotion workflow.
- The local validation set is now stronger, but only a small reviewed subset of the exported traffic-derived candidates has been promoted so far, so the current result should still be treated as controlled validation rather than default-on readiness.

## Rollout Gate Checklist

## Gate Decision

Decision: `REFERENCE_HOST_VALIDATED`

Broader rollout recommendation: `NOT YET`

Default-on recommendation: `NO`

This gate means Yue is a valid first reference host for the existing generic seams, but the evidence is not yet strong enough for broader host expansion or default enablement.

## Gate Scope

This checklist applies before either of the following:

- enabling `session_context_enabled` for a wider Yue lane
- using Yue validation as the basis for enabling the same integration pattern in additional hosts

## Mandatory Checklist

### Gate A: Host Seam Correctness

Required:

- Yue host records map to ordered normalized `ContextEvent` values.
- Yue reaches `SessionContextManager.resolve(...)` only through the feature-flagged path.
- Yue consumes exported prompt context without losing block names, sections, selected candidate ids, or source chunk ids.
- Yue appends session context into the existing prompt assembly path without redesigning prompt construction.

Current status: `PASS`

### Gate B: Feature-Flag Safety

Required:

- `session_context_enabled=False` preserves prior behavior.
- Feature-flag OFF path does not call the Yue session context integration seam.
- Feature-flag OFF path does not inject session context prompt blocks.

Current status: `PASS`

### Gate C: Retrieval Boundary Safety

Required:

- Yue-side host integration keeps retrieval scoped to session-context behavior only.
- The seam does not introduce cross-session retrieval.
- The seam does not introduce external knowledge, internet, or host-level document retrieval through `midterm-session-memory`.

Current status: `PASS`

### Gate D: Deterministic Local Validation

Required:

- validation remains local and deterministic
- no network calls
- no model calls
- no external services
- focused Yue-local test coverage exists for the touched seam

Current status: `PASS`

### Gate E: Higher-Level Host Integration Confidence

Required before broader rollout:

- at least one Yue-local higher-level integration test covering persisted chat history, tool calls, feature-flag ON/OFF behavior, and final prompt assembly
- at least one transcript-shaped validation case that exercises a denser multi-turn host timeline

Current status: `PASS`

### Gate F: Prompt Mode Validation

Required before broader rollout:

- explicit Yue-side comparison of compatibility mode versus strict evidence behavior, if strict mode is considered for future rollout
- confirmation that selected evidence behavior is not regressed by Yue prompt consumption

Current status: `PASS`

### Gate G: Rollout Criteria and Observability

Required before broader rollout:

- a documented rollout gate for host expansion or wider traffic exposure
- a minimal host-side debug or inspection contract sufficient to diagnose seam failures locally

Current status: `PASS`

Current note:

- rollout criteria are documented in this note
- Yue now exposes a minimal host-side inspection payload through [session_context_host.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/memory/session_context_host.py), including event counts, action/reason, retrieval intent, signal strength, selected candidate ids, source chunk ids, and prompt block/section traceability
- the broader promotion workflow itself still has not been exercised, but that is a rollout-readiness gap rather than a missing local observability contract

## Hard Blocks

Broader rollout should remain blocked if any of the following are true:

- the feature-flag OFF path no longer preserves prior Yue behavior
- traceability fields are dropped during Yue-side prompt context consumption
- the integration seam expands beyond session-scoped behavior
- higher-level Yue-local integration coverage is still missing
- the Yue-local replay corpus stops expanding while rollout scope grows
- strict-versus-compatibility behavior remains unreviewed while rollout planning depends on that choice

## Evidence Snapshot

Current evidence attached to this gate:

- Yue adapter mapping and ordering tests
- Yue host-service seam validation proving `SessionContextManager.resolve(...)` is reached
- Yue feature-flag OFF path validation
- Yue prompt append ordering validation
- Yue higher-level local integration validation using persisted chat history, tool calls, and feature flag ON/OFF behavior
- Yue replay-style host validation corpus covering 20 Yue-local traffic-shaped cases across ordinal reference, tool-result follow-up with and without assistant commentary, recent document reference, decision continuation, command carryover, same-way and batch follow-ups, implicit entity and format carryover, long topic shifts, mixed-language document reference, multi-tool result follow-up, standalone negatives, greeting/small-talk negatives, and ambiguity boundaries
- Yue transcript-derived local fixture validation covering 3 browser-seeded historical chats: session-context flow, mixed-language document reference, and standalone negative follow-up
- Yue traffic-derived candidate export path through [traffic_sample_export.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/memory/traffic_sample_export.py) and [export_session_context_traffic_samples.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/scripts/export_session_context_traffic_samples.py)
- Local read-only export run against `~/.yue/data/yue.db` on 2026-05-25, scanning 355 sessions and producing 8 redacted pending-review traffic-derived candidates in `/tmp/yue-session-context-traffic-candidates-20260525.json`
- Manual review pass recorded in [yue_session_context_traffic_review_20260525.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/assessments/yue_session_context_traffic_review_20260525.md), promoting 2 accepted reviewed traffic-derived fixtures and retaining 6 known-gap candidates in the review ledger
- Yue prompt-mode comparison validating compatibility mode versus strict selected-evidence behavior
- Yue traceability preservation validation
- Yue host-side inspection contract validation covering event counts, action/reason, retrieval intent, signal strength, selected candidate ids, source chunk ids, block names, and sections
- Yue-local deterministic pytest run for the touched validation files

## Promotion Rule

Promotion from `REFERENCE_HOST_VALIDATED` to a broader controlled rollout should require all mandatory gates to be `PASS`.

Even with all current gates passing, this integration should stay in controlled validation mode until the reviewed traffic-derived layer grows beyond the current first conservative promotion pass.

## Execution Checklist

The following table is the minimum executable checklist for moving beyond the current Yue reference-host validation pass.

| Gate | Validation command or method | Owner | Pass criteria |
| --- | --- | --- | --- |
| Gate A: Host Seam Correctness | `PYTHONPATH=backend pytest -q backend/tests/test_session_context_host_unit.py backend/tests/test_chat_stream_runner_unit.py backend/tests/test_chat_prompting_scope_summary_unit.py` | Yue host integration owner | All targeted seam tests pass and prove adapter mapping, `resolve(...)` reachability, prompt append behavior, and traceability preservation. |
| Gate B: Feature-Flag Safety | Same targeted pytest lane above | Yue host integration owner | `session_context_enabled=False` path remains unchanged, does not call the Yue session context seam, and does not inject session context prompt blocks. |
| Gate C: Retrieval Boundary Safety | Review [session_context_host.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/memory/session_context_host.py) against package boundary docs and keep Yue-local tests green | Yue host integration owner | No Yue change expands this seam into cross-session retrieval, external knowledge retrieval, or host-level retrieval routing through `midterm-session-memory`. |
| Gate D: Deterministic Local Validation | Run the same targeted pytest lane in a local environment with no network/model dependencies | Yue host integration owner | The validation lane stays deterministic and passes without network calls, model calls, or external services. |
| Gate E: Higher-Level Host Integration Confidence | Add and run one focused Yue-local integration test covering persisted chat history, tool calls, feature flag ON/OFF behavior, and final prompt assembly | Yue host integration owner | At least one higher-level Yue integration test passes and proves the seam works on a realistic local host flow, not only unit seams. |
| Gate F: Prompt Mode Validation | Add a focused Yue-local test comparing compatibility mode and strict evidence behavior if strict mode is being considered for rollout | Yue host integration owner with session-context package owner review | Yue-side prompt consumption preserves expected evidence behavior for the chosen rollout mode, and no selected-evidence regression is observed. |
| Gate G: Rollout Criteria and Observability | Update this document with the exact promotion evidence and verify a minimal local debug/inspection path exists | Yue host integration owner | Promotion requirements are explicit, and a failing seam can be inspected locally without adding external analytics or rollout dashboards. |

## Current Owners and Status

| Gate | Current status | Next action |
| --- | --- | --- |
| Gate A | `PASS` | Keep the current targeted seam tests green. |
| Gate B | `PASS` | Keep the feature-flag OFF assertions in the validation lane. |
| Gate C | `PASS` | Re-check only if retrieval-related code changes. |
| Gate D | `PASS` | Keep validation local and deterministic. |
| Gate E | `PASS` | Expand from one transcript-shaped host flow to a broader replay corpus when rollout scope grows. |
| Gate F | `PASS` | Re-check only if Yue-side prompt consumption changes or strict mode becomes a rollout candidate. |
| Gate G | `PASS` | Keep the inspection payload stable as the minimum local debug contract. |

## Recommended Next Step

Priority next step:

- iterate on the 6 known-gap traffic-derived candidates from the review ledger and convert the strongest ones into committed reviewed fixtures after targeted seam improvements

Follow-on step after that:

- exercise the documented promotion workflow with that stronger evidence set before any wider Yue enablement decision
