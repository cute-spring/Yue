# 2026-09-05 Yue Built-In Skills Roadmap Spec

## 1. Overview
Define six built-in skill capabilities as Yue-native workbench modes:

- Deep Research
- Clarify Mode
- Workspace Glossary / Domain Modeling
- Session Handoff
- Discovery Questionnaire
- Agent Instruction Review

This spec set is based on `docs/plans/2026-09-05-yue-built-in-skills-roadmap.html`.

## 2. Product Positioning
Yue is a trusted AI workbench and skill runtime platform. It is not just a coding agent, and it is not a skill authoring IDE.

The built-in skill roadmap should therefore expose reusable work primitives rather than raw command mechanics:

- Research with inspectable evidence.
- Clarification with explicit decisions.
- Durable workspace language.
- Continuation-ready session handoff.
- Human discovery through questionnaires.
- Instruction quality review for skills and agents.

Slash commands may remain as expert shortcuts, but the primary user model should be visible workflows, message actions, workspace panels, artifact creation, and safe runtime routing.

## 3. Goals
- Productize the six skills as first-party Yue capabilities.
- Make skill outputs durable, inspectable, and reusable across workspace sessions.
- Preserve Yue's trust model through evidence state, provenance, redaction, and explicit approval boundaries.
- Keep early MVPs small enough to split into implementation tickets.
- Support later `/to-tickets` decomposition by separating each child capability into its own spec.

## 4. Non-Goals
- Do not make Yue a general-purpose skill authoring IDE.
- Do not auto-write durable workspace memory without user review.
- Do not begin with unrestricted autonomous web-wide research.
- Do not require every user to understand slash commands.
- Do not merge coding-agent implementation workflows such as TDD or code review into this global built-in skill set.
- Do not let skill activation bypass Yue's import gate, compatibility checks, or tool policy.

## 5. Capability Specs
- [Deep Research](./2026-09-05-deep-research-spec.md)
- [Clarify Mode](./2026-09-05-clarify-mode-spec.md)
- [Workspace Glossary / Domain Modeling](./2026-09-05-workspace-glossary-domain-modeling-spec.md)
- [Session Handoff](./2026-09-05-session-handoff-spec.md)
- [Discovery Questionnaire](./2026-09-05-discovery-questionnaire-spec.md)
- [Agent Instruction Review](./2026-09-05-agent-instruction-review-spec.md)

## 6. Shared Product Principles
- Evidence first: Yue should distinguish source-supported claims, inferred claims, missing evidence, and user-confirmed facts.
- Workspace native: Outputs should attach to workspaces as reports, artifacts, notes, glossary entries, or future runbook seeds.
- Approval gated: External sends, durable memory writes, and other state changes require preview, provenance, and explicit user confirmation.
- Low friction: Yue should ask only the decisions that materially change the result, preferably with recommended defaults.

## 7. Shared User Journey
1. Clarify: If intent is vague, Yue asks the smallest useful decision round.
2. Gather: If evidence or outside knowledge is needed, Yue uses workspace sources, connector sources, or a questionnaire.
3. Ground: Yue makes the evidence boundary visible.
4. Produce: Yue creates a report, plan, brief, questionnaire, handoff, glossary entry, or review artifact.
5. Preserve: Yue saves useful context into workspace-attached artifacts only when appropriate.
6. Reuse: Future chats, agents, and runbooks can use the artifacts and shared language.

## 8. Shared Dependencies
- Workspace artifact or note save path.
- Skill runtime routing and prompt-level skill injection.
- Workspace source selection and attachment addressing.
- Evidence, citation, warning, and missing-evidence display conventions.
- Explicit approval UX for durable writes and external actions.
- Redaction policy for secrets, credentials, and sensitive personal or business information.
- Skill import gate, Skill Health, and tool policy metadata for admin-facing review flows.

## 9. Phased Roadmap
### Phase 0: Define
- Clarify Mode: Trigger criteria and question format.
- Session Handoff: Handoff schema and redaction policy.
- Discovery Questionnaire: Recipient and information-gap model.
- Deep Research: Evidence contract and source-scope rules.
- Workspace Glossary / Domain Modeling: Memory classes and confirmation policy.
- Agent Instruction Review: Review rubric for triggers, safety, examples, context load, and tool fit.

### Phase 1: MVP
- Clarify Mode: Manual `/clarify` plus one-round decision brief.
- Session Handoff: Generate a handoff artifact from current chat.
- Discovery Questionnaire: Generate a Markdown artifact with answer stubs.
- Deep Research: Workspace-source research artifact with citations.
- Workspace Glossary / Domain Modeling: Manual save of confirmed terms to glossary.
- Agent Instruction Review: Admin report for one selected skill or agent.

### Phase 2: Productize
- Clarify Mode: Auto-suggest when tasks are vague or high-cost.
- Session Handoff: Attach to workspace and start a new chat from handoff.
- Discovery Questionnaire: Import responses back into workspace.
- Deep Research: Add progress states, export, and missing-evidence handling.
- Workspace Glossary / Domain Modeling: Add term conflict detection and provenance UI.
- Agent Instruction Review: Integrate with import preview and Skill Health.

### Phase 3: Automate
- Clarify Mode: Feed Research, Runbook, and Questionnaire setup.
- Session Handoff: Use handoffs as runbook seeds and multi-agent continuation input.
- Discovery Questionnaire: Add connector-assisted send and follow-up tracking.
- Deep Research: Add long-running research jobs and connector sources.
- Workspace Glossary / Domain Modeling: Add memory review queue and recall governance.
- Agent Instruction Review: Add quality score trends and pre-activation recommendations.

## 10. Cross-Capability Acceptance Criteria
- Each capability has a visible user-facing or admin-facing entry point beyond a raw slash command.
- Each capability has a clearly named artifact or output.
- Each capability defines safety and approval boundaries before implementation begins.
- Durable workspace state is never modified silently.
- The roadmap can be split into tickets capability-by-capability without requiring implementation code in this spec set.
