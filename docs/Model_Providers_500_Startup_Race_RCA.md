# `/api/models/providers` 启动期 500 问题专题复盘（Startup Race RCA）

## 1. 问题概述

- **现象**：前端页面初始化时，请求 `GET /api/models/providers` 偶发返回 `500 Internal Server Error`。
- **影响范围**：主要发生在本地开发环境冷启动阶段（`start.sh` 同时拉起前后端时）。
- **业务影响**：模型列表加载失败，导致初次进入页面出现错误提示，影响可用性与用户信心。

---

## 2. 具体现象与证据

### 2.1 浏览器网络层表现

- 请求 URL：`http://localhost:3000/api/models/providers`
- Method：`GET`
- 状态码：`500`

### 2.2 前端代理日志证据（核心）

`frontend.log` 里出现多次代理报错：

```text
[vite] http proxy error: /api/models/providers
Error: connect ECONNREFUSED 127.0.0.1:8003
```

该错误说明：**前端 3000 端口的 Vite 代理在转发到后端 8003 时，后端端口尚未可连通**。

### 2.3 后端日志证据（对照）

`backend.log` 显示后端稍后启动成功并可返回 200：

```text
INFO:     Uvicorn running on http://127.0.0.1:8003
INFO:     127.0.0.1:53943 - "GET /api/models/providers HTTP/1.1" 200 OK
```

该对照证明：不是接口逻辑持续性故障，而是**启动时序窗口导致的瞬时失败**。

---

## 3. 根因分析（Root Cause）

根因是**前后端启动竞态（Startup Race Condition）**，不是 `/api/models/providers` 业务逻辑本身异常。

### 3.1 启动脚本时序问题

历史启动逻辑中，`start.sh` 启动后端后立即启动前端，没有等待后端健康可达；前端启动更快，页面 `onMount` 立刻发起请求，导致代理转发时后端尚未监听完成。

### 3.2 前端首屏请求缺乏启动期容错

历史 `useLLMProviders` 首次请求为“单次尝试”；遇到代理 500（底层是连接拒绝）即直接报错，未针对“服务冷启动窗口”进行重试缓冲。

---

## 4. 当前已落地解决方案

已采用“双层防护”（启动时序防护 + 客户端容错）：

### 4.1 前端层：请求重试与响应校验

文件：`frontend/src/hooks/useLLMProviders.ts`

已实现：

- `loadProviders(refresh = false, retries = 3)` 增加重试参数。
- 对 `res.ok` 做显式判断，非 2xx 直接抛错。
- 对返回值做 `Array` 结构校验，避免异常载荷污染状态。
- 失败后进行延迟重试（1s 间隔），最终失败才 toast 报错。

### 4.2 启动层：后端健康探测后再启动前端

文件：`start.sh`

已实现：

- 增加 `BACKEND_HEALTH_URL=http://127.0.0.1:8003/api/health`。
- 启动后端后执行循环探测（`curl -sSf`）等待可达。
- 增加最大等待时间（60s）与后端进程异常退出检测。
- 仅在后端可达后再启动前端，减少竞态窗口。

---

## 5. 当前方案有效性结论

结论：**已有效解决本次 500 问题的主要根因，达到开发环境“稳定可用”目标。**

验证结果：

- `bash -n start.sh` 通过（脚本语法正确）。
- `npm run build` 通过（前端类型检查与构建通过）。
- 接口在后端就绪后稳定返回 200。

---

## 6. 为什么这不是“绝对终局方案”

当前方案在开发阶段性价比很高，但生产级还可进一步提升：

- 前端重试为固定间隔，尚可升级为指数退避（Exponential Backoff）+ 抖动（Jitter）。
- 目前主要依赖启动脚本串联；在容器/编排环境中应迁移为平台级就绪探针策略。
- 观测链路可继续强化（错误分类、SLO、报警闭环）。

---

## 7. 生产级增强方案（Roadmap）

### P1（短期，低成本高收益）

1. **前端退避升级**  
   将固定 1s 重试升级为指数退避 + 随机抖动，降低冷启动并发风暴风险。

2. **错误类型分层**  
   区分“启动中不可达（可重试）”与“真实 5xx 业务故障（不可盲重试）”，避免误导告警。

3. **可观测增强**  
   在前端请求与后端日志按 `X-Request-Id` 串联，快速定位失败链路。

### P2（中期，架构级）

1. **Readiness / Liveness 分离**  
   把 `/api/health` 细分为：
   - `liveness`：进程存活
   - `readiness`：依赖可用（LLM provider、MCP、配置加载等）

2. **编排层就绪门禁**  
   在 Docker Compose / Kubernetes 使用 `healthcheck` + `depends_on: condition: service_healthy`（或 probe）替代脚本轮询。

3. **网关级熔断与重试策略**  
   在反向代理层定义有限重试、超时、熔断阈值，避免故障扩散。

### P3（长期，质量门禁）

1. **启动竞态自动化测试**  
   增加 e2e 场景：模拟后端慢启动，断言 UI 能在重试后自动恢复。

2. **SLO 与告警**  
   建立 `/api/models/providers` 成功率与 P95 延迟指标，设置启动期与稳态不同告警阈值。

3. **RCA 模板化**  
   将此类问题纳入标准 RCA 模板（现象-证据-根因-修复-预防）并要求每次事故沉淀。

---

## 8. 关键代码证据索引

- 前端模型加载重试：[useLLMProviders.ts](../frontend/src/hooks/useLLMProviders.ts)
- 启动等待后端就绪：[start.sh](../start.sh)
- API 路由入口：[models.py](../backend/app/api/models.py)
- 前端代理配置：[vite.config.ts](../frontend/vite.config.ts)
- 健康检查接口：[health.py](../backend/app/api/health.py)

---

## 9. 最终结论

本问题本质为**启动时序竞态**。当前已实施的“双层防护”方案在开发环境下已明显提升稳定性并消除主要痛点；后续按 P1/P2/P3 路线推进，可将其升级为生产级韧性方案。
