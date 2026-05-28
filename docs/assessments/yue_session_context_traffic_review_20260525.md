# Yue Session Context Traffic Review (2026-05-25)

## Scope

This note records the first manual review pass over the redacted local traffic-derived candidate export produced from `~/.yue/data/yue.db`.

The export itself remained local and redacted. Only manually reviewed conclusions and selected sanitized fixtures are committed.

## Input

- Source db: `~/.yue/data/yue.db`
- Export path: `/tmp/yue-session-context-traffic-candidates-20260525.json`
- Sessions scanned: `355`
- Eligible candidates exported: `8`

## Review Outcome

Summary:

- manually reviewed candidates: `8`
- accepted reviewed fixtures promoted into repo: `2`
- known-gap cases retained only in review ledger: `6`

## Accepted Reviewed Fixtures

1. `reviewed_traffic_json_canvas_preview`
   - Verdict: `accepted_current_behavior`
   - Why it matters: explicit deictic follow-up referencing earlier generated JSON Canvas content
   - Expected resolution: `retrieve_mid_session_memory`

2. `reviewed_traffic_explicit_path_access`
   - Verdict: `accepted_current_behavior`
   - Why it matters: traffic-derived negative control where the current input already carries the explicit path
   - Expected resolution: `no_context_needed`

## Known-Gap Ledger

The following candidate ids were manually reviewed but not promoted into the committed pass lane because current behavior appears weak, ambiguous, or product-sensitive:

- `traffic_candidate_001`
  - Manual note: semantically depends on prior topic, but no strong explicit reference signal; keep for future adjudication work.
- `traffic_candidate_002`
  - Manual note: `Sheet1` HTML conversion appears to depend on prior workbook context; current `no_context_needed` result looks weak.
- `traffic_candidate_005`
  - Manual note: same family as candidate 002; likely workbook-context carryover gap.
- `traffic_candidate_006`
  - Manual note: same family as candidate 002 with heavier tool noise; useful later for robustness review.
- `traffic_candidate_007`
  - Manual note: bare `yes` depends almost entirely on prior turn intent and should not be treated as a strong standalone negative.
- `traffic_candidate_008`
  - Manual note: “same action flow one more time” looks like a real continuation reference; current `greeting_or_smalltalk` classification is a plausible bug.

## Result

Decision: `PARTIAL_PROMOTION_COMPLETE`

Interpretation:

- Yue now has a committed reviewed traffic-derived fixture layer.
- The first promotion pass is intentionally conservative and only includes manually accepted cases.
- The remaining six reviewed candidates should be treated as a realistic future-improvement pool, not as committed correctness assertions yet.
