# 03 - Session Handoff creates a continuation artifact

**What to build:** A user can generate a redacted handoff from the current chat, saved to the workspace with decisions, sources, artifacts, blockers, open questions, and a continuation prompt.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** resolved

**Validation:**
- `npm run test:unit -- src/pages/chat/utils/chatCommands.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts`
- `npm run build`

- [x] A user can invoke Session Handoff from the current conversation.
- [x] The generated handoff includes objective, current state, decisions, sources, artifacts, blockers, open questions, next actions, and a continuation prompt.
- [x] The handoff is saved as a workspace-attached artifact.
- [x] Sensitive values are redacted or excluded according to the defined policy.
- [x] The artifact distinguishes completed work, decisions, assumptions, and proposed next steps.
- [x] No external task, ticket, or notification is created automatically.
