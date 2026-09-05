# 03 - Session Handoff creates a continuation artifact

**What to build:** A user can generate a redacted handoff from the current chat, saved to the workspace with decisions, sources, artifacts, blockers, open questions, and a continuation prompt.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** ready-for-agent

- [ ] A user can invoke Session Handoff from the current conversation.
- [ ] The generated handoff includes objective, current state, decisions, sources, artifacts, blockers, open questions, next actions, and a continuation prompt.
- [ ] The handoff is saved as a workspace-attached artifact.
- [ ] Sensitive values are redacted or excluded according to the defined policy.
- [ ] The artifact distinguishes completed work, decisions, assumptions, and proposed next steps.
- [ ] No external task, ticket, or notification is created automatically.
