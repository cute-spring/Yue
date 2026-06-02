# Source Workspace Phase 4 Priority Execution Plan

Date: 2026-06-02
Status: Draft for execution
Owner Scope: product hardening, grounded-answer trust loop, workspace UX, validation strategy

## 1. Purpose

This document extracts the highest-necessity unfinished work from the broader Source Workspace roadmap and turns it into a focused execution plan.

It does not attempt to finish every deferred Source Workspace idea. Instead, it prioritizes the work that most directly determines whether Source Workspace is merely an MVP or a trustworthy product capability.

The four priority tracks are:

1. real grounded-answer closed-loop validation
2. citation and evidence-contract productization
3. workspace usage-flow hardening
4. workspace memory review-flow design

## 2. Why These Four

Source Workspace Phase 1/2 MVP is already implemented and verified. The most important remaining gap is not basic data persistence or object association. The main remaining risk is product trust:

- Can users reliably get answers grounded in workspace sources?
- Can they understand what evidence was or was not used?
- Can they work inside a workspace without fighting the UI?
- Can future memory behavior avoid persisting unstable or weakly supported conclusions?

These four tracks address those risks directly.

## 3. Non-Goals

This plan does not include:

- global RAG/indexing across all workspaces
- OCR expansion
- full autonomous long-running research jobs
- full rich artifact editor systems
- universal parser coverage
- final implementation of workspace memory CRUD

Those may remain deferred until the trust loop and workspace UX are stable.

## 4. Priority Track A: Real Grounded-Answer Closed Loop

### 4.1 Goal

Verify that real workspace chats behave correctly across source scope, citation strictness, and mixed source readiness conditions.

This is the single highest-priority unfinished area because it validates the core Source Workspace promise: answers should be meaningfully constrained by workspace evidence when requested.

### 4.2 Problems To Solve

- The product already exposes `workspace_source_mode`, `selected_workspace_source_ids`, and `grounding_mode`, but these controls must be validated in real user flows rather than only by unit or integration assumptions.
- `require_sources` must not silently degrade into unsupported general-model answering.
- Mixed readiness workspaces must behave clearly and predictably.

### 4.3 Execution Steps

1. Define a fixed manual-QA matrix of real workspace scenarios:
- one workspace with a single ready PDF
- one workspace with ready PDF + ready CSV
- one workspace with ready + unsupported + missing sources

2. For each scenario, test all three grounding modes:
- `normal`
- `prefer_sources`
- `require_sources`

3. For each run, record:
- selected source scope
- eligible source list shown in UI
- whether citations are attached
- whether answer behavior matches source constraints
- whether failure states are explicit when evidence is insufficient

4. Validate that `require_sources` behaves correctly in all failure classes:
- no ready sources
- no citation-capable execution path
- source exists but cannot support the user request

5. Convert the validated scenarios into a durable regression pack:
- manual smoke checklist
- targeted automated tests where feasible
- seeded workspace fixtures for repeatability

### 4.4 Deliverables

- grounded-answer QA matrix document
- seeded real-workspace fixtures or equivalent test setup
- targeted regression coverage for the validated scenarios
- explicit pass/fail criteria for `require_sources`

### 4.5 Acceptance Criteria

- At least one full real-workspace validation pass covers all scenario/mode combinations.
- `require_sources` never silently behaves like unconstrained general chat in tested scenarios.
- Citation presence or absence matches the visible evidence state and actual runtime behavior.
- Mixed-readiness workspaces produce understandable, reproducible outcomes.

## 5. Priority Track B: Citation and Evidence-Contract Productization

### 5.1 Goal

Make the evidence model understandable at the message level so users can read a response and immediately understand its evidence boundary.

This track matters because technical capability alone is not enough. Users must be able to interpret what Yue did, what it relied on, and where the answer may be limited.

### 5.2 Problems To Solve

- Evidence controls and response metadata currently exist, but they must read as product language rather than internal implementation state.
- `require_sources` failure or degraded states must be clearly distinguished.
- Citation UX must avoid over-claiming truth while still signaling trustworthy evidence usage.

### 5.3 Execution Steps

1. Standardize message-level evidence contract content:
- source mode
- grounding strictness
- eligible source count or list
- citation count
- missing-evidence or tooling-warning state

2. Review and refine all related user-facing language:
- avoid wording that implies guaranteed truth
- prefer wording that communicates evidence scope and support level

3. Add explicit UI states for `require_sources` edge cases:
- no ready sources
- no compatible retrieval tool path
- no citations attached despite citation requirement

4. Ensure the message-level UI and the backend grounding metadata contract stay aligned.

5. Add frontend and backend coverage for these user-visible states.

### 5.4 Deliverables

- refined evidence-contract UI copy set
- state matrix for citation/evidence messaging
- frontend rendering updates where needed
- tests covering explicit evidence-state rendering

### 5.5 Acceptance Criteria

- A user can understand a message’s evidence boundary without reading internal implementation details.
- `require_sources` failures are distinguishable by cause.
- Citation count, eligible sources, and visible warning states are consistent with the runtime metadata contract.
- Product language avoids misleading certainty claims.

## 6. Priority Track C: Workspace Usage-Flow Hardening

### 6.1 Goal

Make the day-to-day Source Workspace flow easy to understand and repeat for both first-time and returning users.

This is necessary because a capability can be technically correct and still fail product adoption if the usage path feels scattered, overly technical, or visually noisy.

### 6.2 Problems To Solve

- Workspace entry, source awareness, and artifact awareness still need final usability hardening.
- Users should understand where they are, what sources are active, and what outputs belong to the workspace.
- Sidebar and surrounding flows must support work, not merely expose configuration.

### 6.3 Execution Steps

1. Define the canonical workspace user journeys:
- first-time workspace creation and first chat
- returning to an existing workspace
- asking a grounded question from existing sources
- reviewing a saved workspace artifact

2. Audit the current UI against those journeys:
- entry clarity
- source visibility
- artifact discoverability
- chat flow continuity

3. Hardening tasks should focus on:
- clearer workspace context presentation
- stable default expansion/collapse behavior
- readable resource summaries
- lower visual noise for secondary controls
- consistent empty and loading states

4. Create a lightweight workspace usability checklist for future regression.

5. Validate the updated flow in-browser with seeded workspaces and at least one first-time and one returning-user scenario.

### 6.4 Deliverables

- workspace user-journey checklist
- UI/UX refinement patch set
- browser validation notes or screenshots
- regression checklist for workspace usability

### 6.5 Acceptance Criteria

- A first-time user can create and use a workspace without needing hidden product knowledge.
- A returning user can quickly understand current workspace state and continue work.
- Resource summaries feel like work context rather than raw technical configuration.
- The sidebar acts as a workspace navigation surface, not just a control panel.

## 7. Priority Track D: Workspace Memory Review-Flow Design

### 7.1 Goal

Design the review and governance model for workspace memory before implementing full memory CRUD or automatic persistence.

This track is included because memory will likely become an important extension of Source Workspace, but implementing it too early risks cementing weak, unsupported, or temporary conclusions.

### 7.2 Problems To Solve

- The system needs a clear rule for what is eligible to become durable workspace memory.
- Memory should not accept unsupported research conclusions by default.
- The workspace evidence model and memory model must align before implementation expands.

### 7.3 Execution Steps

1. Define memory-eligible content classes:
- user-confirmed project facts
- stable user or project preferences
- cited conclusions with clear provenance

2. Define ineligible or review-required content classes:
- unsupported or uncited claims
- speculative synthesis
- temporary execution state
- tool failures or transient observations

3. Design a review gate:
- what the user sees before something becomes memory
- what provenance should be attached
- when human confirmation is mandatory

4. Define the relationship between workspace notes, research artifacts, and workspace memory.

5. Produce a standalone follow-on design document for future implementation.

### 7.4 Deliverables

- workspace memory eligibility rules
- workspace memory review-gate design
- provenance expectations for memory records
- follow-on implementation design stub or linked plan

### 7.5 Acceptance Criteria

- There is a documented policy for what may enter workspace memory.
- The design clearly separates notes, artifacts, and memory.
- Memory write behavior is gated by review rather than assumed safe by default.
- The design is ready for implementation planning after grounded-answer behavior is stable.

## 8. Recommended Execution Order

The tracks should be executed in this order:

1. Track A: Real grounded-answer closed loop
2. Track B: Citation and evidence-contract productization
3. Track C: Workspace usage-flow hardening
4. Track D: Workspace memory review-flow design

Reasoning:

- Track A validates the product promise.
- Track B makes that promise legible to users.
- Track C makes the validated promise easy to use.
- Track D prepares the next layer of durable intelligence without rushing implementation.

## 9. Suggested Status Model

To avoid ambiguity, progress should be tracked separately for each track:

- `not started`
- `in progress`
- `validated`
- `completed`

Initial recommended status:

- Track A: `in progress`
- Track B: `in progress`
- Track C: `validated`
- Track D: `not started`

Rationale:

- Some evidence UX and workspace UX hardening work has already begun.
- Track A now has an initial grounded-answer QA matrix, mixed-readiness/source-mode prompt-context regression coverage, a stream grounding-event unit seam, and a seeded Playwright regression pack covering Scenario A (single ready PDF across grounding modes), Scenario C (mixed readiness), Scenario D (selected source restriction), Scenario E (no sources allowed), plus citation-required tooling-warning behavior. A true end-to-end retrieval/citation runtime pass with real workspace tool execution is still pending.
- Track B now has refined message-level evidence wording, distinct citation-required warning causes, unavailable-source visibility in the message contract card, updated helper coverage, and end-to-end smoke validation. Broader copy harmonization and any additional backend-state expansion remain pending.
- Track C now has a focused sidebar/workspace UX hardening pass: workspace-state summaries for first-time and returning users, deterministic per-workspace expansion defaults, clearer source/artifact empty and loading states, readable work-context summaries instead of raw config counts, helper regression coverage, and browser-validated first-time grounded-workspace guidance.
- Workspace memory review design has not yet started as a first-class execution track.

## 9.2 Track A Execution Update (2026-06-02)

Implemented progress:

1. Seeded scenario regression coverage
- Browser validation is now organized around deterministic seeded workspace scenarios instead of one-off checks.
- The current regression pack covers:
  - Scenario A: single ready PDF across `normal`, `prefer_sources`, and `require_sources`
  - Scenario C: ready + unsupported + missing sources with only the ready source eligible
  - Scenario D: selected-source restriction with explicit evidence-insufficient behavior
  - Scenario E: no-sources-allowed with explicit citation-required failure state
  - required failure state: citation-required turn with no compatible retrieval tool path

2. Runtime/UI contract verification
- The seeded browser tests verify that the visible message-level evidence contract matches the seeded runtime grounding payload for source mode, grounding mode, eligible sources, unavailable sources, and citations.
- Request payload assertions now verify that source-scope settings sent from the sidebar (`all_ready`, `selected`, `none`) match the scenario under test.

3. Mixed-readiness repeatability
- Mixed readiness is now reproducible through stable seeded source sets rather than incidental mock combinations.
- Unsupported and missing sources are explicitly asserted as unavailable in the evidence contract UI instead of only being implied in backend tests.

Remaining gap before Track A can be called fully validated:

- The regression pack still uses deterministic seeded stream payloads rather than a fully real retrieval/citation runtime path.
- A final true closed-loop pass should execute at least one real workspace/tool-backed citation flow so the actual retrieval path, citation emission, and UI contract are validated together rather than only through seeded browser events plus backend prompt-context seams.

## 9.1 Track C Execution Update (2026-06-02)

Implemented progress:

1. Workspace context visibility
- The sidebar header now summarizes the active workspace state in product language, including ready sources, sources needing attention, and saved artifacts.
- Unselected-workspace and loading states now explain how to enter the workspace flow instead of only showing empty chrome.

2. Resource summary readability
- Resource cards now summarize workspace materials as usable work context, for example ready sources for grounding, attention-needed sources, and saved artifacts.
- Source status labels are normalized for readability (`Needs permission`, `Unsupported`, `Missing`, `Processing`).

3. Stable expand/collapse defaults
- Resource panel defaults are now initialized per workspace after source/artifact loading settles, instead of drifting based on repeated rerenders.
- First-time workspace selection opens the main resources section by default and expands source details when the user most needs orientation (no sources yet, selected-source mode, or mixed readiness).

4. Clearer empty and loading states
- Empty source and artifact lists now explain what appears there and what the user can do next.
- Loading copy now frames the sections as workspace context rather than low-level fetch state.

5. Navigation feel over control-panel feel
- The sidebar now reads as “where work lives” rather than a compact configuration drawer, while preserving existing source-mode and grounding-mode controls needed for Tracks A/B.

Validation notes:

- Helper regression coverage expanded for workspace source readiness summaries and count-label formatting.
- Playwright smoke now covers a first-time empty-workspace flow plus the existing citation-required grounded-answer flows.
- Direct local-browser validation on `http://127.0.0.1:4173/` confirmed:
  - selected workspace summary visible
  - resources panel auto-opened on first use
  - first-time guidance copy visible
  - empty source-state guidance visible

## 10. Exit Criteria For Source Workspace Phase 4

Source Workspace Phase 4 should be considered substantially complete when:

1. grounded-answer behavior has been validated in real workspace scenarios
2. evidence contract and citation UX are clear and consistent
3. workspace entry and daily usage flows are hardened and browser-validated
4. workspace memory governance is designed clearly enough to support a later implementation phase

At that point, the product can reasonably claim that Source Workspace is no longer only an MVP container model, but a credible AI workbench surface for evidence-backed work.
