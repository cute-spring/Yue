task statement
Complete Phase 2.4/2.5 backend runtime model routing integration and validation.

desired outcome
Runtime routing precedence is consistently applied across chat, agent, and skill execution paths with focused deterministic tests and no frontend work.

known facts/evidence
- Phase 1 routing config foundation already exists.
- chat_stream_runner already integrates resolve_runtime_model and has unit coverage.
- Dirty worktree includes routing-related edits in backend/app/api/agents.py, backend/app/api/chat_schemas.py, backend/app/api/chat_stream_runner.py, backend/app/services/agent_store.py, backend/app/services/config_service.py, backend/tests/test_api_agents_unit.py, backend/tests/test_chat_stream_runner_unit.py, backend/tests/test_config_service_unit.py, plus new routing files.
- Required validation commands specified by user.

constraints
- TDD: tests first.
- Minimal production-safe changes, no frontend UI work, avoid broad refactors.
- Preserve provider-only request compatibility.
- Must stop if unexpected conflicting repo changes appear.

unknowns/open questions
- Exact remaining runtime entrypoints for agent and skill execution.
- Whether chat schemas already carry model_role and provider/model override fields.
- Which existing tests best capture agent/skill routing precedence.

likely codebase touchpoints
- backend/app/api/chat.py
- backend/app/services/chat_service.py
- backend/app/services/chat_runtime.py
- backend/app/services/skill_service.py
- backend/app/services/skills/routing.py
- backend/app/api/chat_schemas.py
- backend/tests/*routing*
