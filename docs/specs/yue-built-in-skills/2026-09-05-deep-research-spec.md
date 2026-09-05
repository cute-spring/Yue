# 2026-09-05 Deep Research Spec

## 1. Product Purpose
Deep Research turns source-backed questions into cited, durable research artifacts. It differentiates Yue from generic chat by making answers inspectable, reusable, and honest about evidence gaps.

## 2. Target User
- Knowledge workers who need grounded reports from workspace files, attachments, or trusted external sources.
- Product, research, strategy, and operations users who need evidence-backed synthesis.
- Power users who want Yue to produce reusable workspace artifacts rather than transient chat answers.

## 3. User-Facing Entry Points
- `/research` shortcut.
- "Research this" message action.
- Workspace source panel action.
- Attachment flow action after a user uploads or selects files.
- Natural-language trigger such as "research this using my workspace files."

## 4. MVP Scope
- Research job form with question, selected sources, depth, and output type.
- Source selection limited to workspace-addressable files or trusted already-configured sources.
- Required citation behavior for source-supported claims.
- Research artifact containing summary, findings, evidence, gaps, assumptions, and next actions.
- Clear state for unsupported claims and missing evidence.

## 5. Prerequisites and Dependencies
- Workspace sources and uploaded files are addressable by tools.
- Grounding modes are productized enough for the user to understand source scope.
- Citation, warning, unavailable-source, and missing-evidence states are visible.
- Artifact save path exists for research reports.
- Redaction and source permission rules are defined.

## 6. Expected Artifacts or Outputs
- Research report artifact attached to the active workspace.
- Citation list or evidence map.
- Missing-evidence section.
- Optional follow-up task brief, questionnaire seed, or next-actions list.

## 7. Safety and Approval Boundaries
- Yue must not claim unsupported findings as sourced facts.
- Yue must show when a claim is source-supported, inferred, user-confirmed, or missing evidence.
- External or connector-based source access must respect configured permissions.
- Long-running or broad-scope research should preview the source scope before execution.
- Durable workspace memory writes from research findings require separate user confirmation.

## 8. Out-of-Scope Items
- Unrestricted autonomous web-wide research in the first MVP.
- Automatic publication, email sending, or external sharing of reports.
- Silent conversion of findings into glossary or long-term memory entries.
- Full background job orchestration beyond the minimal MVP artifact flow.

## 9. Acceptance Criteria
- A user can start Deep Research from at least one visible product entry point and one shortcut.
- A user can choose or confirm the source scope before research begins.
- The output is saved as a workspace-attached research artifact.
- The artifact includes summary, findings, citations, evidence gaps, assumptions, and next actions.
- Claims without evidence are labeled as inferred or unsupported rather than presented as sourced.
- No external send or durable memory write occurs without explicit confirmation.

## 10. Suggested Implementation Phase
Phase 1 after the lower-dependency MVPs begin. Phase 0 must first define the evidence contract and source-scope rules; Phase 2 can add progress states, export, and richer missing-evidence handling.
