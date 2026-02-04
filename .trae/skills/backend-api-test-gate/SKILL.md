---
name: "backend-api-test-gate"
description: "为后端 API 变更自动补齐单测与直连 API 集成测试并跑回归。Invoke when 修改/新增 FastAPI 路由、请求/响应模型、或后端服务影响 API 行为。"
---

# Backend API Test Gate

## 适用场景（何时调用）

- 新增/修改任何 FastAPI 路由（`backend/app/api/*.py`、`backend/app/main.py`）。
- 修改请求/响应模型（Pydantic Model）或其校验规则，可能影响接口返回。
- 修改后端 service/manager（如 `chat_service`/`mcp_manager`/`config_service`）并可能改变 API 行为。
- 修复 bug 后需要保证不回归。

## 交付标准（必须同时满足）

- 对受影响的 API：新增或更新对应的单元测试（优先复用已有测试文件）。
- 对关键路径：新增或更新“直连后端 API”的集成测试（使用 `requests` 调用 HTTP 接口）。
- 测试失败：先定位与修复，再重新跑全量测试直到通过。

## 推荐工作流（按顺序执行）

### 1) 识别影响面

- 找到变更涉及的 API 路由/请求体/响应体/依赖服务。
- 列出需要覆盖的接口路径（例如 `/api/mcp/*`、`/api/chat/*`）。

### 2) 单元测试（优先）

- 对纯函数/服务层逻辑：写 service 单元测试（不依赖运行中的服务）。
- 对数据迁移/边界条件：补回归用例（重复字段、空值、非法输入、分页边界等）。

### 3) 直连 API 集成测试（必须）

目标：用真实 HTTP 请求验证“系统整体行为”，但避免依赖外部 LLM/第三方网络。

- 使用 `requests` 调用后端（默认 `http://127.0.0.1:8003`）。
- 若测试涉及 `/api/chat/stream`：
  - 必须使用内部测试模型 `provider="__guard__"` 来保证确定性与可重复。
  - 校验 SSE 流里必须有最终内容，避免出现“只输出思考没有答案”。
- 对新增 endpoint：至少覆盖
  - 正常路径（200）
  - 参数校验失败（400/422）
  - 资源不存在（404）
  - 安全策略（deny/allow）与边界（limit/offset/size）行为

### 4) 全量回归门禁

- 运行后端全量单测：
  - `python3 -m unittest discover backend/tests -v`
- 若改动影响前端交互：追加前端构建门禁
  - `cd frontend && npm run build`

## 测试文件模板建议

- 单元测试：`backend/tests/test_<module>.py`
- 集成测试：`backend/tests/test_<area>_api.py`
  - SSE/流式接口：实现一个 `_collect_sse()` helper 解析 `data: {...}` 行。
  - 常规 JSON 接口：直接 `requests.get/post/put/delete` 断言 status_code 与返回字段。

## 常见失败与处理

- 422/400 变化：优先确认 Pydantic 校验与前端传参一致，再补齐测试断言。
- SSE 不稳定：确保使用 `__guard__`，并为 `requests` 设置合理 timeout。
- 集成测试依赖外部资源：改为 mock/provider 内部 guard 或使用内置工具（避免网络不确定性）。
