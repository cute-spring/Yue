task statement
- Implement phase 1 simplification of agent model selection by introducing `light | balanced | heavy` tiers while preserving advanced direct provider/model overrides and compatibility with existing runtime routing.

desired outcome
- Agent create/edit flows default to tier mode.
- Backend persists `model_selection_mode` and `model_tier` without breaking legacy agents.
- Global config supports `model_tiers` mappings and tier resolution.
- Runtime routing precedence becomes request direct > request role > agent direct > agent tier > agent role > auto-upgrade > fallback.
- Chat runtime metadata exposes the resolved tier-based model result.

known facts/evidence
- Working tree already contains uncommitted routing-related changes for `model_role`, `model_policy`, and runtime routing.
- `backend/app/services/llm/routing.py` is newly introduced and currently resolves request overrides, agent role, auto-upgrade, and fallbacks.
- Frontend agent form still exposes provider/model as the primary selection path.
- Tests for routing/config/chat stream already exist and can be extended.

constraints
- Follow TDD: add failing tests before production edits.
- Keep diff minimal and avoid unrelated refactors.
- Do not implement fallback model lists or complex sub-strategies in phase 1.
- Preserve compatibility for legacy agents and manual chat model overrides.
- Pause only if a direct semantic conflict with existing uncommitted work appears.

unknowns/open questions
- Exact current frontend test harness capabilities for interactive AgentForm coverage.
- Whether any hidden API consumers depend on raw config shape beyond existing tests.

likely codebase touchpoints
- `backend/app/services/agent_store.py`
- `backend/app/api/agents.py`
- `backend/app/services/config_service.py`
- `backend/app/api/config.py`
- `backend/app/services/llm/routing.py`
- `backend/app/api/chat_stream_runner.py`
- `backend/data/global_config.json.example`
- `backend/tests/test_*`
- `frontend/src/components/AgentForm.tsx`
- `frontend/src/hooks/useAgentsState.ts`
- `frontend/src/types.ts`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/settings/types.ts`
- `frontend/src/pages/settings/useSettingsData.ts`
- `frontend/src/components/AgentForm.test.tsx`
- `frontend/src/hooks/useAgentsState.Agents.test.ts`
