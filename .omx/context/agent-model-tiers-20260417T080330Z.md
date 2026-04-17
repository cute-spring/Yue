task statement
- Use Ralph as the primary controller for the current Yue project and combine ultrawork, tdd, and build-fix to finish the agent model tiering feature with speed-first parallel execution.

desired outcome
- Settings can configure `light` / `balanced` / `heavy` provider+model mappings.
- Agent form defaults to tier mode, supports direct override, and persists the correct fields.
- Reloading settings shows saved tier configuration.
- Runtime tier mode resolves to the correct provider/model at execution time with correct precedence.
- Targeted backend/frontend tests pass and final integration is verified.

known facts/evidence
- Worktree is dirty and already contains in-flight changes in backend and frontend files related to model routing and agent configuration.
- New file `backend/app/services/llm/routing.py` and tests for routing already exist in progress.
- `docs/shared/agent-tiers.md` was requested by skill docs but is not present in this repo.
- User asked for four explicit lanes:
  - Lane A: backend config persistence
  - Lane B: runtime routing
  - Lane C: frontend settings + agent form
  - Lane D: frontend tests + acceptance baseline

constraints
- Do not overwrite unrelated dirty worktree changes.
- Speed first, parallel first.
- Core logic must still follow red -> green.
- Final answer must include stage judgment, lane plan/results, red-green process, modified files, verification commands/results, and remaining risks.
- Must pause and report if direct conflicts with current uncommitted changes block safe progress.

unknowns/open questions
- Whether all lane work already exists but is incomplete versus needing additional implementation.
- Exact targeted test commands for backend/frontend in this repo.
- Whether any missing types or API serialization gaps remain between backend and frontend.

likely codebase touchpoints
- backend/app/services/config_service.py
- backend/app/api/config.py
- backend/app/services/llm/routing.py
- backend/app/api/chat_stream_runner.py
- backend/tests/test_config_service_unit.py
- backend/tests/test_api_config_unit.py
- backend/tests/test_llm_routing_unit.py
- backend/tests/test_chat_stream_runner_unit.py
- frontend/src/pages/settings/components/LlmSettingsTab.tsx
- frontend/src/pages/settings/useSettingsData.ts
- frontend/src/pages/settings/types.ts
- frontend/src/components/AgentForm.tsx
- frontend/src/hooks/useAgentsState.ts
- frontend/src/types.ts
- frontend/src/components/AgentForm.test.tsx
- frontend/src/hooks/useAgentsState.Agents.test.ts
