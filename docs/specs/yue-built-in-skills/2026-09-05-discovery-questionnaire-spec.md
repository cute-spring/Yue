# 2026-09-05 Discovery Questionnaire Spec

## 1. Product Purpose
Discovery Questionnaire converts missing human knowledge into a targeted questionnaire. It helps Yue continue useful work when the missing source is a stakeholder, expert, teammate, customer, or decision owner rather than a document.

## 2. Target User
- Product managers, operators, consultants, researchers, and founders gathering requirements.
- Users who need to ask someone else for decisions, facts, constraints, or preferences.
- Yue users blocked by missing human context during planning, research, or execution.

## 3. User-Facing Entry Points
- `/questionnaire` shortcut.
- Natural-language trigger such as "we need to ask the PM" or "make questions for the stakeholder."
- Follow-up from Research missing-info sections.
- Follow-up from Clarify Mode when the current user cannot answer required decisions.
- Workspace artifact creation menu.

## 4. MVP Scope
- Ask who the questionnaire is for and what must be learned.
- Generate a concise Markdown questionnaire with answer stubs.
- Include context, objective, prioritized questions, and optional decision fields.
- Save the questionnaire as a workspace artifact.
- Keep send/export separate from generation in the MVP.

## 5. Prerequisites and Dependencies
- Artifact export or note creation.
- Basic information-gap model distinguishing document research gaps from human decision gaps.
- Optional connector support can be deferred.
- Clear artifact format for answer stubs and response import preparation.

## 6. Expected Artifacts or Outputs
- Discovery questionnaire artifact.
- Answer stubs or response fields.
- Context preamble suitable for the recipient.
- Optional response-import checklist in later phases.

## 7. Safety and Approval Boundaries
- Yue must not send questionnaires externally without explicit user approval.
- Yue should avoid asking for unnecessary sensitive personal data.
- Yue should make the recipient and intended use clear.
- Yue should separate questions that require facts from questions that require decisions or preferences.
- Connector-assisted send and follow-up tracking require separate confirmation.

## 8. Out-of-Scope Items
- Automatic email, chat, or ticket sending in MVP.
- Survey analytics or form platform integration in MVP.
- Large-scale customer research operations.
- Treating unreviewed responses as durable workspace facts without user confirmation.

## 9. Acceptance Criteria
- A user can generate a questionnaire from a stated information gap.
- Yue asks only the minimal setup questions needed for recipient, goal, and missing knowledge.
- The questionnaire is saved as a workspace artifact.
- The artifact includes context, questions, answer stubs, and decision prompts where useful.
- No external send occurs without explicit user approval.
- The questionnaire can be linked from a Research, Clarify, or Handoff output.

## 10. Suggested Implementation Phase
Phase 1. Phase 0 defines recipient and information-gap model; Phase 2 imports responses back into workspace; Phase 3 adds connector-assisted send and follow-up tracking.
