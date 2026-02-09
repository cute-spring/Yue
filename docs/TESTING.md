# Yue Phase 2 Verification Guide

## Scope & Goals
- Validate Phase 2 capabilities: LLM config security, provider health tests, MCP status and tool identity, Agents tool configuration, Chat interactions (@mention + slash commands), and Custom Models CRUD.
- Execute per feature: backend API → frontend UI → acceptance criteria → edge cases.
- Environments: Backend http://127.0.0.1:8003, Frontend http://localhost:3000.

## Prerequisites
- Backend server running with hot reload. MCP filesystem server connected by default.
  - Code refs: [mcp.py](../backend/app/api/mcp.py), [manager.py](../backend/app/mcp/manager.py), [main.py](../backend/app/main.py)
- Frontend dev server running, or production build available.
  - Code refs: [package.json](../frontend/package.json), [Dockerfile](../Dockerfile)

## Backend API Tests (curl)
...
(Previous curl commands omitted for brevity)
...

## Automated Integration Testing

### 1) Backend Integration Suite
- **Location**: `backend/tests/test_comprehensive_api.py`
- **Command**: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_comprehensive_api.py`
- **Scope**: Models, Config, Chat History, Agents, MCP Status.

### 2) Frontend E2E Suite
- **Location**: `frontend/e2e/`
- **Command**: `cd frontend && npx playwright test`
- **Scope**: Navigation, Agent Creation, Settings, Chat Workflow, MCP Toggles.
- **Key File**: `frontend/e2e/comprehensive-workflow.spec.ts` (Validates full user journey).

## Phase 3 Verification Results (2026-02-09)

| Test Category | Suite | Result | Note |
|---------------|-------|--------|------|
| Backend API | Pytest | PASSED | 6/6 tests passed. Covers all major service modules. |
| Frontend E2E | Playwright | PASSED | 5/5 tests passed. Validated core UI workflows. |
| Refactoring | Manual | PASSED | Modular LLM factory verified for streaming and compatibility. |

### 1) LLM Config Security
- Expect: GET returns redacted keys (empty strings for *_api_key).

```bash
curl -s http://127.0.0.1:8003/api/config/llm
```

Code refs: [config.py](../backend/app/api/config.py#L9-L17), [config_service.py](../backend/app/services/config_service.py#L33-L50)

### 2) Provider Health Test
- Expect: {"provider":"openai","ok":true} when configured.

```bash
curl -s -X POST http://127.0.0.1:8003/api/models/test/openai -H "Content-Type: application/json" -d '{}'
```

Code refs: [models.py](../backend/app/api/models.py#L20-L39), [model_factory.py](../backend/app/services/model_factory.py)

### 3) MCP Tools & Status
- Tools must include stable id "server:name".
- Status must show enabled/connected/last_error per server.
- Responses should include `X-Request-Id` for traceability (echo if provided).

```bash
curl -s http://127.0.0.1:8003/api/mcp/tools
curl -s http://127.0.0.1:8003/api/mcp/status
curl -s -D - http://127.0.0.1:8003/api/mcp/status -o /dev/null | head -n 20
curl -s -D - http://127.0.0.1:8003/api/mcp/status -H "X-Request-Id: test-trace-id-123" -o /dev/null | head -n 20
```

Toggle enabled and reload:
```bash
curl -s -X POST http://127.0.0.1:8003/api/mcp/ -H "Content-Type: application/json" \
  -d '[{"name":"filesystem","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","${PROJECT_ROOT}"],"enabled":false}]'
curl -s -X POST http://127.0.0.1:8003/api/mcp/reload
curl -s http://127.0.0.1:8003/api/mcp/status
```

Code refs: [mcp.py](../backend/app/api/mcp.py), [manager.py:get_available_tools](../backend/app/mcp/manager.py#L100-L123), [manager.py:get_status](../backend/app/mcp/manager.py#L146-L159)

### 4) Agents Tool ID Normalization
- Expect: create/update normalizes legacy names to composite IDs when unambiguous.

```bash
curl -s -X POST http://127.0.0.1:8003/api/agents/ -H "Content-Type: application/json" \
  -d '{"name":"Verifier","system_prompt":"You verify configs.","provider":"openai","model":"gpt-4o","enabled_tools":["filesystem:list"]}'
curl -s http://127.0.0.1:8003/api/agents/
```

Code refs: [agents.py](../backend/app/api/agents.py), [agent_store.py](../backend/app/services/agent_store.py)

### 5) Notebook API (for /note)
- Expect: create/list OK.

```bash
curl -s -X POST http://127.0.0.1:8003/api/notebook/ -H "Content-Type: application/json" \
  -d '{"title":"From Test","content":"Saved content"}'
curl -s http://127.0.0.1:8003/api/notebook/
```

Code refs: [notebook.py](../backend/app/api/notebook.py), [notebook_service.py](../backend/app/services/notebook_service.py)

### 6) Custom Models CRUD
- Full loop: add → list → update → test → delete → list. Keys always redacted in GET.

```bash
curl -s http://127.0.0.1:8003/api/models/custom
curl -s -X POST http://127.0.0.1:8003/api/models/custom -H "Content-Type: application/json" \
  -d '{"name":"my-custom","base_url":"https://api.example.com/v1","api_key":"****masked****","model":"x-large"}'
curl -s http://127.0.0.1:8003/api/models/custom
curl -s -X PUT http://127.0.0.1:8003/api/models/custom/my-custom -H "Content-Type: application/json" \
  -d '{"api_key":"real_key_123"}'
curl -s http://127.0.0.1:8003/api/models/custom
curl -s -X POST http://127.0.0.1:8003/api/models/test/custom -H "Content-Type: application/json" \
  -d '{"base_url":"https://api.example.com/v1","api_key":"real_key_123","model":"x-large"}'
curl -s -X DELETE http://127.0.0.1:8003/api/models/custom/my-custom
curl -s http://127.0.0.1:8003/api/models/custom
```

Code refs: [config_service.py (custom models)](../backend/app/services/config_service.py#L52-L90), [models.py (custom endpoints)](../backend/app/api/models.py#L40-L93)

## Frontend Manual Verification

### Settings → LLM
- Provider cards: click Test Connection. Success shows Connected; failure shows error text.
- Custom Models: add/update/delete; Test displays result. Keys hidden in list.
- Save All LLM Settings: reload and confirm values persist.
Code refs: [Settings.tsx](../frontend/src/pages/Settings.tsx)

### Settings → MCP
- Status cards: Online/Offline and last_error visible, toggle Enabled updates state; Save JSON then Reload.
Code refs: [Settings.tsx](../frontend/src/pages/Settings.tsx)

### Agents
- Create/edit agent, select MCP tools (from server). Saved tools reappear; composite IDs consistent.
Code refs: [Agents.tsx](../frontend/src/pages/Agents.tsx)

### Chat
- @mention: type @ to open agent list; choose one; token removed; selectedAgent applied.
- Slash commands: /help shows list; /note saves last assistant message to Notebook; /clear resets session.
Code refs: [Chat.tsx](../frontend/src/pages/Chat.tsx)

## Build & Tests

### Frontend Build
```bash
cd frontend && npm run build
```

### Backend Unit Tests
```bash
python3 -m unittest discover backend/tests -v
```
Code refs: [test_mcp_and_models.py](../backend/tests/test_mcp_and_models.py), [test_chat_service.py](../backend/tests/test_chat_service.py)

## Acceptance Criteria
- LLM: GET redacts, POST ignores empty/masked, health tests accurate.
- MCP: Status and toggles consistent; reload recovers; tools include stable IDs.
- Agents: Tool selection persists; normalization stable; legacy names compatible.
- Chat: @mention and slash commands usable; Notebook saves visible.
- Custom Models: Full CRUD and test; keys redacted; errors clear.
- Build & tests: production build succeeds; backend tests pass.

## Edge Cases & Regression
- API Key handling: GET redacts; POST ignores empty/****masked**** values.
- Multi-server tool name conflicts: prefer composite ID; prompt choice when ambiguous.
- MCP reload transient errors: retry /reload; state should recover.
- Provider connectivity: enforce timeouts; clear error messages.

## Troubleshooting
- Backend logs: check hot reload and MCP connection info; rerun /reload after config changes.
- Frontend: refresh or restart dev server if UI stale; confirm production assets in backend/static for Docker.
- Provider failures: verify API Key/Base URL correctness; ensure https and network reachability.
