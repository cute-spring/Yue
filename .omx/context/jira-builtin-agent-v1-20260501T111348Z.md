Task statement:
- Implement the first vertical slice of Jira integration for YUE as a built-in agent, keeping v1 read-oriented and low risk.

Desired outcome:
- A loadable `builtin-jira` agent definition in the built-in catalog.
- A production-ready Jira MCP example template for YUE.
- A YUE-specific design/spec document for the Jira built-in agent.
- Verification proving the new built-in agent loads correctly.

Known facts/evidence:
- Built-in agents load from `backend/data/builtin/agents/*.yaml` via `BuiltinAgentCatalog`.
- Existing built-in agent coverage lives in `backend/tests/test_builtin_agent_catalog.py` and `backend/tests/test_agent_store_unit.py`.
- `backend/data/mcp_configs.json.example` already includes a simple Jira example entry.
- User requires no Jira write automation in v1.

Constraints:
- Reuse the existing built-in loading path and patterns.
- Prefer manual or tightly constrained skill exposure.
- Keep prompt/configuration YUE-specific.
- Avoid unrelated refactors.
- Verify changes with tests and report blockers if any.

Unknowns/open questions:
- Exact Jira skill ref/version to expose inside YUE before the external skill package is installed.
- Whether any MCP template API tests assert on the example config shape.

Likely codebase touchpoints:
- `backend/data/builtin/agents/`
- `backend/tests/test_builtin_agent_catalog.py`
- `backend/tests/test_agent_store_unit.py`
- `backend/data/mcp_configs.json.example`
- `docs/superpowers/specs/`
