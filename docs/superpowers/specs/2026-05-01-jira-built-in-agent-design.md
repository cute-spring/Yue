# 2026-05-01 Jira Built-in Agent Design

## 1. Overview
Add a YUE-specific built-in Jira agent that supports project-safe Jira discovery, status summarization, and ticket drafting through the existing built-in agent and skill runtime architecture.

## 2. Goals
- Provide a dedicated built-in Jira assistant for YUE project operations.
- Keep `v1` read-oriented and low risk.
- Reuse the existing built-in agent YAML loading path and project skill runtime.
- Prepare the platform for later Jira write actions without enabling them yet.

## 3. Non-Goals
- No automatic Jira writes in `v1`.
- No bulk transitions, assignments, or cross-project mutation flows.
- No runtime refactor of the built-in agent framework.

## 4. Agent Definition
### 4.1 Identifier
- **ID**: `builtin-jira`
- **Name**: `YUE Jira Project Assistant`

### 4.2 Execution Mode
- **Skill mode**: `manual`
- **Visible skill**: `jira:1.0.0`
- **Enabled tools**: none directly on the agent definition

This keeps the agent narrowly constrained. The Jira skill can later encapsulate MCP-aware workflows while the built-in agent remains the YUE-facing contract.

## 5. v1 Responsibilities
- Inspect Jira issues, backlog, board, or sprint context.
- Summarize delivery state, blockers, and ownership signals.
- Draft issue descriptions, comments, and ticket field suggestions.
- Highlight missing requirements such as acceptance criteria, owner, priority, or due date.

## 6. Safety Boundaries
- The agent must not perform Jira write actions in `v1`.
- The agent must not claim that a ticket was created or updated unless a future explicit write path confirms success.
- The agent should surface uncertainty rather than guessing workflow states or custom fields.
- Responses should cite Jira evidence when the underlying skill or tool provides it.

## 7. MCP Integration
The project example MCP configuration should expose a Jira server template with:
- base URL
- personal token
- optional username/email support when the company MCP implementation requires it
- project scoping
- default JQL seed for YUE

This keeps deployment reproducible while allowing teams to replace the package and credentials per environment.

## 8. Implementation Plan
1. Add `backend/data/builtin/agents/builtin-jira.yaml`.
2. Register stable ordering in `BuiltinAgentCatalog`.
3. Upgrade `backend/data/mcp_configs.json.example` with a YUE-oriented Jira MCP template.
4. Add focused tests proving the built-in catalog and agent store load `builtin-jira`.

## 9. Rollout Plan
### Phase 1
- Query issue details
- Summarize sprint/backlog state
- Draft ticket content

### Phase 2
- Add guarded write-preview workflows
- Require explicit confirmation before mutation

### Phase 3
- Add controlled create/update/transition flows after permission and audit strategy are finalized

## 10. Acceptance Criteria
- `builtin-jira` is present in the built-in catalog.
- `builtin-jira` loads through `AgentStore`.
- The built-in agent remains read-oriented in prompt and configuration.
- The Jira MCP example config documents YUE-focused environment variables without assuming the final company MCP package name.
