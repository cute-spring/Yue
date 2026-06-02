# Source Workspace Grounded-Answer QA Matrix

Date: 2026-06-02
Status: Ready for execution
Related Plan: [2026-06-02-source-workspace-phase4-priority-plan.md](../plans/2026-06-02-source-workspace-phase4-priority-plan.md)

## Execution Update (2026-06-02)

Automated coverage now exists for these seeded scenario families:

1. Scenario A
- single ready PDF
- browser coverage across `normal`, `prefer_sources`, and `require_sources`

2. Scenario C
- ready + unsupported + missing
- browser coverage asserts that only the ready source is eligible and unavailable sources remain visible

3. Scenario D
- selected-source restriction
- browser coverage asserts selected-source payload scope and explicit evidence-insufficient behavior

4. Scenario E
- no sources allowed
- browser coverage asserts `workspace_source_mode = none` and explicit citation-required failure messaging

5. Required failure-state coverage
- citation-required turn with no compatible retrieval tool path
- backend prompt-context mixed-readiness/source-mode matrix
- stream grounding-event summary seam

Current remaining gap:

- The seeded browser pass validates the runtime/UI evidence contract deterministically, but not yet a true tool-backed retrieval/citation path. A final Track A closure pass should still run at least one real workspace/tool-backed citation flow.

## Purpose

This matrix defines the minimum real-scenario validation loop for Source Workspace grounded-answer behavior.

It is designed to validate the product promise behind:

- `workspace_source_mode`
- `selected_workspace_source_ids`
- `grounding_mode`
- message-level evidence contract
- citation-required behavior

The goal is not broad exploratory QA. The goal is to establish a repeatable trust regression pack.

## Core Questions

For every scenario below, validate:

1. Does the answer respect the workspace source scope?
2. Does the answer behavior change correctly across `normal`, `prefer_sources`, and `require_sources`?
3. Are citations attached when evidence-backed answering succeeds?
4. When evidence is insufficient, is the failure explicit rather than silently guessed?
5. Does the UI reflect the evidence contract correctly?

## Scenario Matrix

### Scenario A: Single Ready PDF

Workspace contents:
- 1 ready PDF

Prompt style:
- ask a factual question answerable from the PDF

Expected by mode:

1. `normal`
- answer may use workspace evidence when relevant
- citations may or may not appear depending on execution path
- evidence contract should show the active workspace grounding state

2. `prefer_sources`
- answer should prefer the PDF over general model recall
- citations should normally be present when the tool path is used
- UI should show eligible source count and workspace evidence state

3. `require_sources`
- answer should cite the PDF or explicitly say evidence is insufficient
- no unsupported confident answer should appear without citations
- if citation-capable execution is unavailable, warning state must be visible

### Scenario B: Ready PDF + Ready CSV

Workspace contents:
- 1 ready PDF
- 1 ready CSV

Prompt style:
- ask a question that may require one or both sources

Expected by mode:

1. `normal`
- answer may be partial or blended, but should not claim workspace evidence it did not use

2. `prefer_sources`
- answer should prefer workspace materials
- if both sources are relevant, citations should be consistent with the actual evidence used

3. `require_sources`
- answer must cite workspace evidence or explicitly fail with evidence-insufficient language
- citations should not refer to excluded or unavailable sources

### Scenario C: Ready + Unsupported + Missing

Workspace contents:
- 1 ready PDF
- 1 unsupported source
- 1 missing source

Prompt style:
- ask a factual question only answerable from the ready source

Expected by mode:

1. `normal`
- answer may proceed if ready source is sufficient
- UI should still reflect mixed source readiness accurately

2. `prefer_sources`
- answer should prefer the ready source
- unsupported or missing sources should not appear as silently usable evidence

3. `require_sources`
- answer should cite only the ready usable source
- if the ready source is not enough, the answer should say what evidence is missing
- unsupported or missing sources should remain unavailable in both runtime behavior and UI state

### Scenario D: Selected Source Scope Restriction

Workspace contents:
- 2 or more ready sources

Prompt style:
- select only one source and ask a question answerable only by the excluded source

Expected by mode:

1. `selected + normal`
- answer should not pretend excluded sources are in scope

2. `selected + prefer_sources`
- answer should stay within selected eligible sources

3. `selected + require_sources`
- if the selected source cannot support the answer, the result should explicitly fail or state evidence is insufficient

### Scenario E: No Sources Allowed

Workspace contents:
- ready sources exist, but `workspace_source_mode = none`

Prompt style:
- ask a factual workspace question

Expected by mode:

1. `none + normal`
- workspace identity may remain active, but no workspace sources should be treated as eligible evidence

2. `none + prefer_sources`
- answer should not claim workspace evidence because none is allowed

3. `none + require_sources`
- answer should clearly state that evidence-backed answering cannot proceed under current source scope

## Per-Run Checklist

For every run, record:

- workspace scenario
- source mode
- grounding mode
- selected source ids if any
- visible eligible sources
- visible unavailable sources
- whether a tooling warning appears
- whether citations are attached
- whether answer behavior matches the requested evidence contract
- whether the answer incorrectly uses excluded, missing, or unsupported sources

## Required Failure-State Checks

These failure modes must be explicitly tested:

1. `require_sources` with no ready eligible sources
- expected: explicit evidence-insufficient state

2. `require_sources` with selected source that is unavailable
- expected: no silent fallback answer that acts fully supported

3. `require_sources` with no compatible retrieval tool path
- expected: visible tooling warning

4. mixed-readiness workspace where only one source is usable
- expected: only usable source may appear as eligible evidence

## Automation Mapping

Recommended automated coverage split:

1. backend unit/integration
- workspace prompt-context eligibility matrix
- runtime grounding metadata construction
- require-sources warning conditions

2. frontend unit
- evidence summary rendering
- citation-required warning rendering
- eligible/unavailable source display logic

3. browser/manual smoke
- one seeded workspace per scenario family
- one full pass across the scenario/mode combinations

## Minimum Exit Criteria

Track A should not be considered validated until:

1. at least Scenarios A, C, D, and E have been run end-to-end
2. `require_sources` has no silent unsupported-answer path in the tested cases
3. the visible evidence contract matches actual runtime evidence behavior
4. citations, when present, correspond to eligible in-scope workspace sources

## Execution Notes

- Use seeded workspaces whenever possible so failures are reproducible.
- When a scenario fails, record whether the failure is:
- backend grounding selection
- tool-path availability
- citation emission
- frontend evidence-contract rendering
- UX copy ambiguity

- Do not classify “the model answered something plausible” as success unless the evidence contract was honored.
