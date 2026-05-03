# YUE Jira Operations And Project Intelligence Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve YUE from a read-oriented Jira assistant into a trusted Jira operations and project-intelligence copilot that can safely read, write, analyze, and help manage delivery work through a company-internal Jira MCP server, with default-open read access and confirmation-gated mutation access.

**Architecture:** Build Jira capability in four layers. First, establish a safe Jira read/write execution model with preview, confirmation, policy gating, and audit. Second, add a Jira analysis layer that turns issues, boards, sprints, epics, comments, transitions, and changelogs into structured progress and risk reports. Third, add a management layer that converts those insights into suggested actions, stakeholder updates, and operational guidance. Keep the built-in Jira agent as the YUE-facing orchestration contract while MCP details remain externalized behind config and runtime guards.

**Tech Stack:** FastAPI, Pydantic, existing MCP manager/registry, built-in agent YAML loading, skill runtime, frontend Settings + chat surfaces, Jira MCP server via stdio.

---

## 1. Product Intent

YUE should not stop at “can call Jira tools.” The target capability is a project-operations copilot that can:

- inspect Jira state across issues, boards, sprints, epics, and changelogs
- perform guarded Jira write actions with explicit preview and confirmation
- analyze delivery progress, blockers, execution quality, and schedule risk
- help teams manage sprint planning, backlog hygiene, release readiness, and stakeholder reporting

This plan assumes the current YUE Jira baseline already exists:

- built-in agent: `builtin-jira`
- MCP onboarding guide and token-based template
- `jira-company` template and example config
- narrow verification seams for onboarding and template behavior

The operating policy for this roadmap is:

- read operations are fully authorized by default
- analysis, reporting, and management guidance may freely use authorized read capability
- any non-read Jira action that creates, updates, comments on, transitions, links, or otherwise edits Jira state must be previewed and explicitly confirmed by the user before execution

---

## 2. Capability Model

### 2.1 Observe

YUE can read and normalize Jira state from:

- projects
- issues
- boards
- sprints
- epics
- comments
- transitions
- changelogs
- searchable fields
- versions and related metadata when needed later

Read capability should be treated as broad by default. If the connected Jira MCP server and user permissions allow it, YUE may use those read surfaces without per-action confirmation.

### 2.2 Act

YUE can perform Jira mutations only through a guarded path:

- add comment
- create issue
- update issue
- transition issue

Later phases may add:

- link issue to epic
- create issue links
- controlled sprint/version mutations

YUE may recommend any Jira-native action the connected MCP server and the user's Jira permissions allow, but it must not execute those mutations until the user confirms the previewed action.

### 2.3 Analyze

YUE should compute structured reports such as:

- sprint health
- delivery progress
- blocker and idle-work detection
- risk scan
- epic progress summary
- execution hygiene review
- trend and scope-change analysis

### 2.4 Manage

YUE should guide management workflows such as:

- sprint planning support
- backlog triage
- weekly operating review
- release readiness review
- stakeholder update drafting
- escalation suggestion

---

## 3. Non-Goals

- No unguarded Jira writes
- No silent automation that mutates Jira without preview and confirmation
- No delete or destructive cleanup flows in early versions
- No wide batch-write support in the first implementation wave
- No assumption that all company Jira MCP servers expose the same tool names or env keys
- No runtime refactor unrelated to Jira capability expansion

---

## 4. Core Principles

### 4.1 Trust Before Power

Write operations must be previewable, confirmable, auditable, and reversible at the policy level before YUE is allowed to mutate Jira.

### 4.2 Analysis Must Use Real Jira Signals

Progress and risk analysis must rely on more than current issue status. It should incorporate, where available:

- status transitions
- updated timestamps
- sprint membership
- issue type distribution
- assignee and owner gaps
- comments
- changelog history
- epic and dependency relationships

### 4.3 Safe-by-Default Scope Control

The default operating model should stay narrow:

- limited projects
- explicit action allowlists
- confirmation required
- audit enabled

This is intentionally narrow only at the mutation boundary. Read, analysis, planning, and recommendation depth should be maximized.

### 4.4 YUE Contract Stability

The built-in Jira agent remains the stable YUE-facing contract. The underlying MCP package name, env aliases, and server-specific knobs remain implementation-dependent and must stay externalized.

---

## 5. Target Architecture

### 5.1 Jira Read Layer

Purpose:
- normalize Jira reads across MCP tools
- isolate MCP-specific request/response handling
- return YUE-friendly domain objects for downstream analysis

Probable responsibilities:
- tool lookup and invocation mapping
- issue/project/board/sprint/transition/changelog fetch helpers
- field normalization
- error shaping

### 5.2 Jira Write Layer

Purpose:
- execute Jira mutations only after policy and confirmation checks

Probable responsibilities:
- preview payload generation
- execution policy enforcement
- write operation dispatch
- success/failure normalization
- audit event production

### 5.3 Jira Analysis Layer

Purpose:
- convert Jira state into progress, risk, and quality reports

Probable report families:
- sprint health
- risk scan
- epic progress
- blocker analysis
- execution hygiene
- weekly delivery summary

### 5.4 Jira Management Layer

Purpose:
- turn analysis into operational guidance and suggested next actions

Examples:
- “which issues are likely to spill over this sprint”
- “which blockers need escalation”
- “which tickets should be split”
- “which updates should be posted to stakeholders”

---

## 6. Write Governance Model

### 6.0 Authorization Policy

The Jira authorization model for YUE is:

- Read operations: default fully authorized
- Non-read operations: always confirmation-gated

For this plan, “non-read” includes any Jira action that changes stored Jira state, including:

- create
- update
- add comment
- transition
- linking
- sprint/version/release mutation
- any other MCP-backed Jira action that edits content, workflow state, ownership, relationships, or planning metadata

YUE may freely inspect Jira, analyze Jira, and recommend any permission-allowed Jira action. YUE must not execute non-read Jira actions without explicit user confirmation.

All Jira writes should follow the same lifecycle:

1. User asks for a write-oriented outcome
2. YUE gathers Jira context
3. YUE returns a structured preview of the intended write
4. Runtime checks write policy and scope gates
5. User explicitly confirms
6. Jira write executes
7. Result is returned and audited

### 6.1 Required Write Controls

- `JIRA_WRITE_ENABLED`
- `JIRA_WRITE_ALLOWED_ACTIONS`
- `JIRA_WRITE_ALLOWED_PROJECTS`
- `JIRA_REQUIRE_CONFIRMATION`
- `JIRA_AUDIT_ENABLED`

### 6.2 Early Allowed Actions

- `add_comment`
- `create_issue`
- `update_issue`
- `transition_issue`

These are the first execution targets, not the limit of what YUE may reason about or recommend.

### 6.3 Deferred Actions

- `link_to_epic`
- `create_issue_link`
- sprint mutation
- version mutation
- batch create/update

Deferred here means “not first to implement,” not “forbidden to recommend.”

### 6.4 Early Forbidden Actions

- delete issue
- silent bulk mutation
- mutation without preview
- mutation without confirmation when confirmation is required

---

## 7. Project Intelligence Report Set

### 7.1 Sprint Health

Questions answered:

- Is the sprint on track?
- Which items are likely to spill over?
- Where are blockers concentrated?

Expected inputs:

- sprint issues
- issue status
- update timestamps
- assignee distribution
- comments/changelog when needed

Expected outputs:

- summary
- health rating
- metrics
- top risks
- recommended actions

### 7.2 Delivery Risk Scan

Questions answered:

- What is likely to slip?
- Which work is stale, blocked, or underdefined?

Expected signals:

- no recent updates
- no owner
- unclear acceptance criteria
- repeated reopen/transition churn
- high-priority issues with weak activity

### 7.3 Epic Progress Summary

Questions answered:

- How far along is each epic?
- Which epics are slipping or overloaded?

### 7.4 Execution Hygiene

Questions answered:

- Which tickets are hard to execute because they are poorly maintained?

Expected checks:

- missing owner
- missing priority
- missing due date
- weak description
- no acceptance criteria
- inconsistent status vs comments

### 7.5 Weekly Delivery Report

Questions answered:

- What changed this week?
- What did we finish?
- What is at risk next week?

---

## 8. Management Workflow Set

YUE should eventually support the following management-oriented workflows:

- sprint planning copilot
- backlog triage copilot
- weekly delivery review
- release readiness review
- stakeholder update drafting
- dependency and escalation identification

These should be layered on top of the analysis outputs rather than implemented as isolated prompts.

---

## 9. Rollout Strategy

### Phase 1: Trusted Jira Operations Foundation

Objective:
- move from read-only onboarding to trusted, guarded Jira mutation primitives

Primary outcomes:

- write preview contract
- write policy layer
- audit baseline
- first safe mutation path

Recommended first real write path:
- `add_comment`

Then:
- `create_issue`
- `update_issue`
- `transition_issue`

### Phase 2: Project Intelligence Foundation

Objective:
- make YUE useful for delivery analysis, risk detection, and weekly management

Primary outcomes:

- sprint health analysis
- risk scan
- epic progress summary
- weekly delivery report

### Phase 3: Management Copilot Expansion

Objective:
- add planning, triage, release, and escalation workflows on top of stable read/write + analysis foundations

Primary outcomes:

- planning recommendations
- release readiness guidance
- stakeholder reporting
- next-best-action support

---

## 10. Risks And Constraints

### 10.1 MCP Capability Variance

The company Jira MCP server may expose different tool names, payload shapes, or auth env keys than the default Atlassian skill expects.

Mitigation:
- keep tool mapping isolated
- keep env aliases documented
- avoid hardcoding production package names

### 10.2 Workflow Variance Across Projects

Transition IDs, required fields, and custom fields can vary significantly by project.

Mitigation:
- discover fields and transitions dynamically
- avoid hardcoding transition IDs
- constrain early rollout to well-known projects

### 10.3 Misleading Analysis

Progress analysis that ignores changelog, comments, or sprint context may produce shallow or misleading conclusions.

Mitigation:
- treat changelog and recent activity as first-class signals
- make uncertainty explicit in reports

### 10.4 Write Safety

The highest operational risk is unreviewed or overly broad Jira mutation.

Mitigation:
- preview
- confirmation
- allowlists
- project scope gates
- audit

---

## 11. Phase 1 Implementation Plan: Trusted Jira Operations Foundation

### Task 1: Write the Jira write contract and preview schema
**Files:**
- Create: `docs/superpowers/specs/2026-05-01-jira-write-operations-design.md`
- Modify: `backend/data/builtin/agents/builtin-jira.yaml`
- Test: contract-oriented backend tests under `backend/tests/`

- [ ] **Step 1: Define the canonical write preview payload shape**
- [ ] **Step 2: Enumerate allowed actions and per-action target/payload rules**
- [ ] **Step 3: Encode the rule that every non-read action requires explicit user confirmation**
- [ ] **Step 4: Update the built-in Jira agent prompt to require preview before mutation**
- [ ] **Step 5: Add failing tests that assert preview-first behavior**
- [ ] **Step 6: Re-run tests and commit**

### Task 2: Add Jira write policy service
**Files:**
- Create: `backend/app/services/jira_write_policy.py`
- Test: `backend/tests/test_jira_write_policy_unit.py`

- [ ] **Step 1: Write failing tests for disabled write mode**
- [ ] **Step 2: Add action allowlist checks**
- [ ] **Step 3: Add project scope checks**
- [ ] **Step 4: Add mandatory confirmation checks for every non-read action**
- [ ] **Step 5: Preserve default-open behavior for read and analysis operations**
- [ ] **Step 6: Re-run tests and commit**

### Task 3: Add Jira write executor seam
**Files:**
- Create: `backend/app/services/jira_write_executor.py`
- Test: `backend/tests/test_jira_write_executor_unit.py`

- [ ] **Step 1: Write failing tests for preview-to-execution mapping**
- [ ] **Step 2: Add executor interface for `add_comment`, `create_issue`, `update_issue`, `transition_issue`**
- [ ] **Step 3: Normalize success and failure results**
- [ ] **Step 4: Keep tool-name mapping isolated from agent logic**
- [ ] **Step 5: Re-run tests and commit**

### Task 4: Add audit event surface for Jira writes
**Files:**
- Create: `backend/app/services/jira_write_audit.py`
- Modify: existing trace/tool-event plumbing as needed
- Test: `backend/tests/test_jira_write_audit_unit.py`

- [ ] **Step 1: Write failing tests for audit record generation**
- [ ] **Step 2: Emit audit metadata on both success and failure**
- [ ] **Step 3: Ensure action, target, summary, and result are captured**
- [ ] **Step 4: Re-run tests and commit**

### Task 5: Ship first real write path with confirmation
**Files:**
- Modify: backend chat/runtime flow files that mediate tool execution
- Test: targeted backend integration tests

- [ ] **Step 1: Implement `add_comment` as the first confirmed write path**
- [ ] **Step 2: Add integration tests for preview -> confirm -> execute**
- [ ] **Step 3: Add negative tests for missing confirmation**
- [ ] **Step 4: Re-run tests and commit**

### Task 6: Expand to core write actions
**Files:**
- Modify: `backend/app/services/jira_write_executor.py`
- Test: corresponding integration tests

- [ ] **Step 1: Add `create_issue` execution path**
- [ ] **Step 2: Add `update_issue` execution path with restricted field policy**
- [ ] **Step 3: Add `transition_issue` execution path with transition discovery**
- [ ] **Step 4: Re-run tests and commit**

---

## 12. Phase 2 Implementation Plan: Project Intelligence Foundation

### Task 1: Add Jira analysis domain models
**Files:**
- Create: `backend/app/services/jira_analysis_models.py`
- Test: `backend/tests/test_jira_analysis_models_unit.py`

- [ ] **Step 1: Define report schemas for sprint health, risk scan, epic progress, and weekly delivery**
- [ ] **Step 2: Add severity, evidence, metrics, and recommended-action fields**
- [ ] **Step 3: Re-run tests and commit**

### Task 2: Build sprint health analyzer
**Files:**
- Create: `backend/app/services/jira_sprint_health_service.py`
- Test: `backend/tests/test_jira_sprint_health_service_unit.py`

- [ ] **Step 1: Write failing tests for health-score and risk classification**
- [ ] **Step 2: Use sprint issues, status mix, and stale-work signals**
- [ ] **Step 3: Return a structured sprint health report**
- [ ] **Step 4: Re-run tests and commit**

### Task 3: Build delivery risk scanner
**Files:**
- Create: `backend/app/services/jira_risk_analysis_service.py`
- Test: `backend/tests/test_jira_risk_analysis_service_unit.py`

- [ ] **Step 1: Write failing tests for stale, blocked, underdefined, and churn risks**
- [ ] **Step 2: Incorporate comments/changelog signals when available**
- [ ] **Step 3: Return ranked risks with concrete evidence**
- [ ] **Step 4: Re-run tests and commit**

### Task 4: Build epic progress summary
**Files:**
- Create: `backend/app/services/jira_epic_progress_service.py`
- Test: `backend/tests/test_jira_epic_progress_service_unit.py`

- [ ] **Step 1: Write failing tests for progress rollup by epic**
- [ ] **Step 2: Add completion, in-progress, blocked, and risk metrics**
- [ ] **Step 3: Re-run tests and commit**

### Task 5: Build weekly delivery report generator
**Files:**
- Create: `backend/app/services/jira_weekly_report_service.py`
- Test: `backend/tests/test_jira_weekly_report_service_unit.py`

- [ ] **Step 1: Write failing tests for weekly delta and summary composition**
- [ ] **Step 2: Produce summary, wins, risks, and next actions**
- [ ] **Step 3: Re-run tests and commit**

### Task 6: Expose analysis workflows through the built-in Jira agent
**Files:**
- Modify: `backend/data/builtin/agents/builtin-jira.yaml`
- Modify: backend routing/prompt orchestration files as needed
- Test: targeted agent/runtime tests

- [ ] **Step 1: Add supported analysis workflow language to the built-in agent contract**
- [ ] **Step 2: Ensure the agent can request structured analysis outputs**
- [ ] **Step 3: Add tests for sprint health, risk scan, and epic summary request handling**
- [ ] **Step 4: Re-run tests and commit**

---

## 13. Verification Strategy

### Backend

- policy unit tests
- executor unit tests
- audit unit tests
- analysis service unit tests
- built-in agent contract tests
- targeted integration tests for preview -> confirm -> execute

### Frontend

- Settings template/default-value tests
- modal logic tests for onboarding guidance
- future chat/UI tests for preview and confirmation rendering

### End-to-End

- Settings Marketplace onboarding remains visible for Jira MCP template
- write-disabled path rejects mutation attempts
- confirmed write path succeeds for allowed action
- project-intelligence flows produce structured reports

---

## 14. Acceptance Criteria

- YUE can use authorized Jira read capability broadly without per-read confirmation
- YUE can safely preview and confirm Jira writes for the initial allowed action set
- Every non-read Jira action requires explicit user confirmation before execution
- Jira writes are policy-gated, scope-limited, and auditable
- YUE can generate structured sprint health and delivery risk reports from Jira data
- YUE can summarize epic progress and weekly delivery state
- The built-in Jira agent contract remains stable while company MCP details stay configurable
- Existing Jira onboarding/template/docs/tests remain aligned with the expanded roadmap

---

## 15. Recommended Immediate Next Step

Begin with Phase 1, Task 1 and Task 2 together:

- define the write preview contract
- add the write policy service

That sequence creates the minimum safe foundation for all later Jira mutation and project-intelligence work.
