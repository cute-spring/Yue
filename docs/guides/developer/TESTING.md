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

### 0) Full Stack Check (Recommended)
项目根目录提供了一个一键检查脚本，集成了后端测试、前端类型检查和前端单元测试：
```bash
./check.sh
```
当前 `./check.sh` 也会自动启动前端开发服务器，并执行语音输入专项 Playwright 回归：
```bash
cd frontend && npx playwright test e2e/voice-input.spec.ts
```

### Real E2E: History Date Grouping (No Mock)

This scenario runs browser + real backend + real sqlite data, and does not mock `/api/chat/history`.

```bash
cd frontend && npm run test:e2e:real-history
```

### 1) Backend Integration Suite
- **Location**: `backend/tests/test_comprehensive_api.py`
- **Command**: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_comprehensive_api.py`
- **Scope**: Models, Config, Chat History, Agents, MCP Status.

### 2) Agent Refactor Regression (Mandatory)
- **Location**: `backend/tests/test_agent_regression.py`
- **Command**: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_agent_regression.py`
- **Scope**: Specific functional cases after agent layer refactoring.
- **Mandatory Case 1**: Builtin Local Docs - Master-Sub Agent Query.
  - Payload:
    ```json
    {
      "message": "有什么讲到关于主子agent的内容？",
      "agent_id": "builtin-local-docs",
      "chat_id": "e355cd56-873c-4bba-a70a-9a4ae62685fb",
      "provider": "deepseek",
      "model": "deepseek-reasoner"
    }
    ```

### 3) Agent Kind + Skill Groups Regression (Mandatory)
- **Backend unit + API + runtime**
```bash
cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_group_store_unit.py tests/test_agent_store_unit.py tests/test_api_skill_groups.py tests/test_skill_runtime_integration.py -v
```
- **Migration script**
```bash
cd backend && PYTHONPATH=$(pwd) pytest tests/test_agent_store_persistence.py -k migrate -q
```
- **Frontend state/types**
```bash
cd frontend && npm run test -- Agents
```
- **Frontend E2E**
```bash
cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts
```
- **Release gate**
```bash
./check.sh
```

### 2) Frontend E2E Suite
- **Location**: `frontend/e2e/`
- **Command**: `cd frontend && npx playwright test`
- **Scope**: Navigation, Agent Creation, Settings, Chat Workflow, MCP Toggles.
- **Key File**: `frontend/e2e/comprehensive-workflow.spec.ts` (Validates full user journey).

### 2.1) Voice Input Regression (Mandatory)
- **Location**: `frontend/e2e/voice-input.spec.ts`
- **Command**: `cd frontend && npx playwright test e2e/voice-input.spec.ts`
- **Scope**: Browser dictation writes into composer, Azure Speech cloud STT commit, Azure failure fallback to Browser dictation.
- **Gate**: Included in root `./check.sh`.

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

### 2.1) Meta LLM 配置体感验证（Title / Summary）

- 目标：验证 `meta_use_runtime_model_for_title` 对标题生成路径的影响是否符合预期。
- 配置项：`llm.settings.meta_use_runtime_model_for_title` 或环境变量 `META_USE_RUNTIME_MODEL_FOR_TITLE`。

#### 自动化验证（后端单测）
```bash
PYTHONPATH=backend pytest backend/tests/test_config_service_unit.py::test_config_service_load_existing_redacts_secrets_in_logs \
  backend/tests/test_config_service_unit.py::test_meta_llm_config_round_trip \
  backend/tests/test_api_chat_unit.py::test_refine_title_once_forwards_runtime_provider_model \
  backend/tests/test_api_chat_unit.py::test_refine_title_once_ignores_runtime_provider_model_when_disabled -v
```

预期：
- 全部通过；
- 覆盖“日志脱敏”“开关开启时透传 runtime model”“开关关闭时忽略 runtime model”。

#### 手工验证（最有体感）
1. 在 `~/.yue/data/global_config.json` 设置：
   - `meta_provider` 与 `meta_model` 为固定值（例如 `openai/gpt-4o-mini`）；
   - 分别测试 `meta_use_runtime_model_for_title=false` 与 `true`。
2. 前端新建会话，使用同样的首轮问题，但切换不同聊天模型发送。
3. 对比自动 refinement 后的标题风格是否变化。

预期：
- `false`：标题更稳定，主要受 `meta_provider/meta_model` 影响。
- `true`：标题更容易跟随当前对话使用的 runtime model 风格变化。

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

## Multimodal QA 闭环测试（Chunk 1-3）

### 测试目标
- 验证“仅图片发送、图片校验、Vision 门禁、流式 meta 契约、回放稳定性”形成端到端闭环。
- 覆盖后端单测、后端集成、前端单测、前端 E2E 与 UI 手工验收。

### 自动化测试矩阵

#### Backend - Service Unit
```bash
PYTHONPATH=backend pytest backend/tests/test_multimodal_service_unit.py -v
```
- 覆盖：大小/格式校验、非法 payload、vision 判定矩阵、仅图片输入组装。
- 对应文件：`backend/tests/test_multimodal_service_unit.py`

#### Backend - API Contract Unit
```bash
PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py -k vision_meta -v
```
- 覆盖：SSE `meta` 中 `supports_vision`、`vision_enabled`、`image_count`、`vision_fallback_mode`。
- 对应文件：`backend/tests/test_api_chat_unit.py`

#### Backend - Multimodal Integration
```bash
PYTHONPATH=backend pytest backend/tests/test_multimodal_integration.py -v
```
- 覆盖：历史消息携带图片回放、缺失图片回退不崩溃。
- 对应文件：`backend/tests/test_multimodal_integration.py`

#### Frontend - Unit
```bash
cd frontend && npm run test -- src/hooks/useChatState.multimodal.test.ts src/components/ChatInput.multimodal.test.tsx src/components/LLMSelector.vision.test.tsx
```
- 覆盖：仅图片发送规则、附件数量与大小策略、Vision 徽标显示。
- 对应文件：
  - `frontend/src/hooks/useChatState.multimodal.test.ts`
  - `frontend/src/components/ChatInput.multimodal.test.tsx`
  - `frontend/src/components/LLMSelector.vision.test.tsx`

#### Frontend - E2E
```bash
cd frontend && npx playwright test e2e/multimodal-image-chat.spec.ts
```
- 覆盖：聊天输入区图片上传能力可见性（MVP）。
- 对应文件：`frontend/e2e/multimodal-image-chat.spec.ts`

### UI 手工验收清单

#### Case A：仅图片发送
- 步骤：输入框留空，仅上传 1 张图片并发送。
- 预期：请求成功进入流式响应；会话可继续。

#### Case B：图文混发
- 步骤：输入文本并上传 1 张图片发送。
- 预期：正常返回；`meta.image_count >= 1`。

#### Case C：模型不支持 Vision（严格模式）
- 前置：`multimodal_vision_fallback_enabled=false`，切换到不支持视觉模型。
- 预期：返回 `MODEL_VISION_UNSUPPORTED`，并给出切换模型建议。

#### Case D：模型不支持 Vision（降级模式）
- 前置：`multimodal_vision_fallback_enabled=true`。
- 预期：不中断请求；`meta.vision_fallback_mode = text_only`。

#### Case E：图片格式/大小失败
- 步骤：上传不支持格式或超大图片。
- 预期：返回结构化错误码（`IMAGE_FORMAT_UNSUPPORTED` / `IMAGE_TOO_LARGE`）。

#### Case F：历史回放稳定性
- 步骤：先发仅图片，再在同一 `chat_id` 连续追问。
- 预期：无历史拼接异常；流式正常。

### 闭环完成定义（Multimodal）
- 自动化测试矩阵全部通过。
- UI 手工 Case A-F 全部通过并保留截图/录屏证据。
- 回归后 `./check.sh` 通过。
- 如启用灰度：至少完成 10% 灰度窗口观测，错误率无显著异常。

### 证据归档建议
- 自动化日志：保存 pytest/vitest/playwright 输出。
- 手工证据：每个 Case 至少 1 张截图，命名为 `multimodal_case_<A-F>.png`。
- 汇总记录：在发布记录中附“通过日期、执行人、环境、模型组合”。

## Troubleshooting
- Backend logs: check hot reload and MCP connection info; rerun /reload after config changes.
- Frontend: refresh or restart dev server if UI stale; confirm production assets in backend/static for Docker.
- Provider failures: verify API Key/Base URL correctness; ensure https and network reachability.
