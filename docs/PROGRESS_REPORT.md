# 进度报告（Progress Report）

## 2026-02-04 — Phase 2.5：TaskTool（主子 Agent 委派）+ 子任务进度 SSE + 结构化结果

### 已完成（与 ROADMAP 对齐）

- 新增子任务编排服务：`backend/app/services/task_service.py`
  - 结构化 schema：`TaskSpec / TaskEvent / TaskOutcome / TaskToolResult`
  - 子任务执行：为每个 task 创建子会话 `child_chat_id`，并写入 `parent_id=parent_chat_id`
  - 子任务输出：串行执行，支持增量回传 `content_delta`，最终回写到子会话 messages
- 新增内置工具 `builtin:task_tool`：`backend/app/mcp/manager.py`
  - 从 `deps.chat_id` 或显式 `parent_chat_id` 解析父会话
  - 将进度事件写入 `deps.task_event_queue`（若存在），并返回结构化结果 JSON
- 新增后端 API：
  - `POST /api/tasks/run`：同步返回结构化结果（JSON）
  - `POST /api/tasks/stream`：以 SSE 回传 `task_event` 与最终 `task_result`
  - 路由挂载：`backend/app/main.py`
- Chat SSE 合流（不影响原有文本流）：`backend/app/api/chat.py`
  - 在 `deps` 注入 `chat_id` 与 `task_event_queue`
  - 合并输出：同一条 SSE 连接中同时输出模型文本增量与 `task_event`

### 新增/更新测试（覆盖增强目标 + 回归门禁）

#### 后端（直连 API 集成测试）

- `backend/tests/test_tasks_api.py`
  - 正常路径：
    - `/api/tasks/run`：创建子会话 + `parent_id` 写入 + `output` 返回
    - `/api/tasks/stream`：出现 `task_event.started/running/completed` + 最终 `task_result`
  - 异常路径：
    - `parent_chat_id` 不存在时 `/api/tasks/run` 返回 404
    - `parent_chat_id` 不存在时 `/api/tasks/stream` SSE 返回 `type=task_error` 且 `error=parent_chat_not_found`

#### 前端（Playwright e2e）

- `frontend/e2e/tasks-sse.spec.ts`
  - 在浏览器侧直接调用 `/api/tasks/stream` 并解析 SSE
  - 断言出现 `task_event`（started/running/completed）与最终 `task_result`，并校验输出包含 `OK`（通过 `__guard__` provider 保证确定性）

### 验证结果（本地）

- 后端单测回归：`python3 -m unittest discover backend/tests -v` 全量通过（36/36）
- 前端构建：`npm run build` 通过
- 前端 e2e：`npm run test:e2e` 全量通过（4/4，包含新增 tasks SSE 用例）

### 后续补齐（已完成）

- 已新增确定性“必调用工具”内部 Provider：`__toolcall__`（用于稳定复现 Chat 工具调用）
  - 行为：首次响应固定调用 `builtin:task_tool`，待收到 tool-return 后输出最终文本 `OK`
  - 位置：`backend/app/services/model_factory.py`
- 已新增 Chat SSE 合流集成测试：`backend/tests/test_chat_stream_api.py`
  - 断言：SSE 中同时出现 `task_event`（started/running/completed）与最终文本输出（包含 `OK`）
  - 断言：可通过 `child_chat_id` 回查子会话，且 `parent_id == chat_id`
- 最新回归结果：后端单测回归全量通过（37/37）

### 下一步建议（推荐优先级）

- 多 task 顺序与稳定性：补一条 2~3 tasks 的用例，断言 `result.tasks` 顺序与请求一致、每个 task 都有独立 `task_id/child_chat_id`，并验证子会话 `parent_id` 正确
- 任务取消/中断：定义“父会话 stop”向子任务传播的语义与 API（避免长任务无法停止）
- 前端 Chat UI 展示 `task_event`：按 `task_id` 聚合呈现 started/running/completed，支持折叠子输出，补对应 Playwright 用例

### 风险点复盘（已覆盖/仍需关注）

- 已覆盖：
  - 父会话不存在：tasks API 不会静默失败（JSON 404 / SSE task_error 均覆盖）
  - 本次改动未破坏既有功能：后端/前端回归测试全通过
- 仍需关注（建议下一步补齐）：
  - 多 task 顺序与稳定性：建议补一条 2~3 tasks 的用例，断言 `result.tasks` 顺序与请求一致、每个 task 都有独立 `task_id/child_chat_id`
