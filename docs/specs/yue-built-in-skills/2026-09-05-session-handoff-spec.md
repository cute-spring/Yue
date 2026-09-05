# 2026-09-05 Session Handoff Spec

## 1. Product Purpose
Session Handoff preserves useful chat context as a continuation-ready workspace artifact. It turns transient conversation into durable project memory that another session, user, agent, or runbook can pick up.

## 2. Target User
- Users ending a substantial work session who want to resume later.
- Users delegating continuation to another chat, agent, teammate, or future runbook.
- Teams that need decisions, sources, artifacts, and next actions captured cleanly.

## 3. User-Facing Entry Points
- `/handoff` shortcut.
- "Summarize where we are" message or conversation action.
- Workspace "summarize work" action.
- Pre-flight step before opening a new task from the current context.
- Completion action after Research, Clarify, or multi-step artifact workflows.

## 4. MVP Scope
- Generate a structured handoff from the current chat.
- Include objective, current state, decisions, sources, artifacts, open questions, blockers, next actions, and suggested continuation prompt.
- Attach the handoff to the active workspace.
- Redact sensitive values according to policy.
- Keep the output human-readable and usable by another Yue session.

## 5. Prerequisites and Dependencies
- Chat history is readable.
- Active skill state and generated artifact references are accessible.
- Workspace artifact or note save path is clear.
- Redaction policy is defined for secrets, credentials, private data, and sensitive business context.
- Source and artifact links can be represented in a durable way.

## 6. Expected Artifacts or Outputs
- Session handoff artifact.
- Continuation prompt.
- Decisions and open-questions list.
- Source and artifact reference list.
- Optional runbook seed in later phases.

## 7. Safety and Approval Boundaries
- Sensitive values must be redacted or excluded.
- Yue should not invent decisions that were not made.
- Yue should distinguish completed work from proposed next steps.
- Starting a new task, notifying someone, or creating external records from the handoff requires explicit user action.
- Handoff artifacts should preserve provenance where practical.

## 8. Out-of-Scope Items
- Automatic creation of new tasks or external tickets in the MVP.
- Full runbook generation.
- Multi-agent orchestration beyond producing continuation-ready context.
- Unredacted archival of raw chat transcripts.

## 9. Acceptance Criteria
- A user can generate a handoff from the current chat.
- The handoff is saved as a workspace-attached artifact.
- The handoff includes decisions, sources, artifacts, open questions, blockers, next actions, and continuation prompt.
- Sensitive values are redacted according to the defined policy.
- The artifact distinguishes facts, decisions, assumptions, and proposed next steps.
- A later Yue session can use the handoff as sufficient context to continue.

## 10. Suggested Implementation Phase
Phase 1. Phase 0 defines schema and redaction policy; Phase 2 attaches handoffs more deeply to workspace resume flows; Phase 3 uses handoffs as runbook seeds and multi-agent continuation inputs.
