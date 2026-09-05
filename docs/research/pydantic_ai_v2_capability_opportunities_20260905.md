# Pydantic AI V2 能力机会与 Yue 应用建议

日期：2026-09-05  
评估版本：`pydantic-ai-slim==2.37.0`  
范围：Yue（用户问题中的 “UE” 按 Yue 理解）

## 结论先行

Yue 当前已经完成的是 V2 兼容迁移，不是一次框架能力重构。最值得继续挖掘的不是把 Yue 的 Tool runtime 替换成 Pydantic AI 的 MCP/capability 层，而是利用 V2 的几个能力增强现有产品边界：

1. **延迟工具调用与人工审批**：最贴合 Yue 已有的 `approval_token`、skill approval 和副作用工具策略，可把“需要用户确认”的执行变成可恢复的类型化状态机。
2. **Capabilities/Hooks 作为内部策略插件**：用于统一审计、预算、工具过滤、模型选择和错误拦截；先只挂在 Yue 边界，不改变现有授权模型。
3. **Toolset/Tool Search 的按需暴露**：Yue 已有较多 builtin/MCP 工具，可减少每次请求发送的工具 schema 和提示词长度；应先做只读、可观测的试验。
4. **Durable execution**：适合长时间文档处理、Excel、MCP 和多步骤工作流，但需要幂等、恢复、取消和状态持久化设计，不能作为本次发布后的即插即用开关。

这些能力应在 V2 发布稳定后分阶段引入。当前迁移规格明确禁止把 Yue Tool runtime 替换为 `MCPToolset`、Capabilities 或新授权模型，也明确将 durable execution、Responses API、realtime 和 Harness 列为本次迁移范围之外的架构决策（见 `.scratch/pydantic-ai-v2-migration/spec.md` 的 Out of Scope）。

## 版本校准

Yue 工作区和虚拟环境实际解析的是：

```text
pydantic-ai-slim = 2.37.0
pydantic-ai      = 2.37.0
```

Pydantic AI 的公开 API 在该版本中包含 `Agent.run`、`run_stream`、`run_stream_events`、`iter`、`toolset`、`toolsets`、`capabilities`、`instrument_all`、`to_web` 和 `realtime` 等入口。当前没有一个可与 Yue 迁移直接对应的 “Pydantic AI 8.0” 版本号；“8.0”如果指另一个依赖（例如 Pydantic、OpenAI SDK 或模型服务），需要给出包名和完整版本号才能单独评估。

## V2 已有能力与 Yue 适配性

| 能力 | 2.37.0 中的形态 | 对 Yue 的价值 | 建议 |
| --- | --- | --- | --- |
| 新输出 API | `output_type`、多种 output tool、校验与重试 | Smart Paste、结构化图表/动作结果更稳定 | 已采用；新 agent 必须显式选择 `end_strategy` |
| 输出完成策略 | `early`、`graceful`、`exhaustive` 等策略语义 | 防止结构化输出成功后仍执行副作用工具 | 已采用 `early` 回归；按 agent policy 逐个声明 |
| V2 message history | `ModelMessagesTypeAdapter`、typed message parts | 旧聊天、工具调用/返回、多模态内容的重放 | 已采用；继续增加持久化兼容 fixture |
| 流式事件 | `run_stream`、`run_stream_events`、类型化事件流 | 更细粒度的工具/模型事件与调试 | 内部可用；外部仍保持 Yue SSE contract |
| Toolset | 可组合 `AgentToolset`/`Toolset` | 把工具发现与 agent 组合解耦 | 后续试验，不替换 Yue 授权 |
| Capabilities | `PrepareTools`、`ToolSearch`、`SelectModel`、`Hooks`、`Instrumentation` 等 | 跨 agent 的策略、工具过滤和审计 | 后续低风险增量；先内部挂载 |
| 延迟工具/审批 | `DeferredToolRequests`、`DeferredToolResults`、`ToolApproved`、`ToolDenied`、`HandleDeferredToolCalls` | 把用户确认、异步外部执行变成类型化协议 | 高优先级候选，需持久化状态机 |
| Durable execution | Temporal、DBOS、Prefect 等 durability capability | 断点恢复长任务、MCP/文档工作流 | 中长期；先做单一任务原型 |
| Instrumentation | V2 默认 instrumentation version 5、aggregated usage attributes | 统一 trace、token、工具和延迟观察 | 已配置；生产 exporter/dashboard 仍需 staging 验证 |
| 模型包装/选择 | wrapper、fallback、concurrency、model selection capability | provider 故障转移和按任务选择模型 | 可与现有 provider routing 对接，避免双重重试 |
| UI/AG-UI | UI adapter、原生事件流、AG-UI 相关支持 | 快速接入标准 agent UI | 不替换 Yue SSE；可用于内部调试或独立实验 |
| Realtime/图像/搜索 | realtime providers、image generation、web search/fetch | 新产品形态 | 不是当前聊天迁移目标，需独立产品决策 |
| Evals | Pydantic 生态的评测能力与离线模型测试 | 评估工具选择、历史重放、成本和质量 | 放入 release/quality pipeline，不放运行时 |

## 最值得 Yue 挖掘的四项能力

### 1. 延迟工具调用 + 人工审批（优先级：高）

Yue 已经有 skill policy、`approval_token` 和 action lifecycle。V2 的 `DeferredToolRequests` 可以让模型提出“需要执行什么”，由 Yue 持久化请求并等待用户批准，再用 `DeferredToolResults` 恢复运行。这样比在 SSE 层自定义一组隐式事件更容易保证类型、重试和恢复的一致性。

建议的边界：

- Yue 继续决定哪些工具需要审批，框架只负责传递 deferred request；
- 持久化 `run_id`、`tool_call_id`、参数摘要、授权主体、过期时间和幂等键；
- 用户批准/拒绝必须通过现有 Yue API，不能让模型或 MCP server 自己批准；
- 拒绝、超时、撤销、重复提交都要产生确定的 `ToolDenied`/失败结果；
- 将副作用工具和只读工具分开，默认只对 `workspace_write`、`destructive`、外部 API 写操作启用。

第一步可做一个单独的 `approval_toolset` 原型，只覆盖一个 builtin 写工具，不改所有 agent。验收指标是：重启后能恢复 pending request；重复批准不会重复执行；拒绝不会执行副作用；SSE 仍保持现有事件名。

### 2. Capabilities/Hooks 作为统一策略层（优先级：高）

2.37.0 的 `Hooks`/`AbstractCapability` 能在 run、node、model request、tool validate、tool execute、output validate 和 event stream 边界插入逻辑。对 Yue 最有价值的不是把所有代码搬进 capability，而是把横切策略集中起来：

- **预算策略**：在模型请求前检查 token、工具次数、时间预算；
- **工具审计**：记录 agent、用户、tool、参数摘要、批准状态和结果分类，默认脱敏；
- **工具过滤**：按 agent、workspace、skill capability 和风险等级裁剪 tool definitions；
- **provider fallback**：只在 provider 错误类别满足条件时切换，避免与现有 retry 双重执行；
- **输出安全**：在输出验证后执行敏感信息/危险动作检查；
- **事件观测**：把 V2 事件转换为 Yue 内部 telemetry，不直接改变前端 SSE。

建议先实现一个只读 `YueAuditCapability` 或等价 hook，验证不会改变 tool authorization 和 SSE。待指标稳定后再加入 `PrepareTools`/`SelectModel`。不要同时引入 MCP capability，否则授权来源会变成两套。

### 3. Toolset 与按需工具发现（优先级：中高）

Yue 的 builtin 工具、文档、Excel、图表和 MCP 工具数量会持续增加。每次把全部 JSON schema 放进 prompt 会增加 token、延迟和模型误选工具的概率。V2 的 Toolset/Tool Search 可以支持：

- 首轮只暴露工具目录或搜索工具；
- 模型根据任务加载一组工具；
- 工具 schema 按 session 或 workspace 缓存；
- 记录“发现→加载→调用”的链路，衡量 token 节省和成功率。

建议实现一个 Yue-owned adapter：输入仍来自 `ToolRegistry` 的授权结果，输出才映射成 Pydantic AI Toolset。不能让框架直接读取所有 MCP server，也不能把“工具可发现”当成“工具已授权”。先选文档/Excel 只读工具做 A/B：比较 prompt token、首 token 延迟、工具选择错误率和最终任务成功率。

### 4. Durable execution（优先级：中，长期价值高）

Durable execution 适合以下 Yue 任务：多页文档解析、Excel 大表分析、远程 MCP 不稳定连接、需要用户审批的长工作流、跨多次模型请求的研究任务。它可以记录模型请求、工具调用和恢复点，在进程重启后继续。

但它不是当前 `chat_service` 的简单替换：需要决定 workflow identity、事件日志、幂等执行、取消/超时、数据保留、错误重放和 provider 成本上限。Temporal/DBOS/Prefect 还会引入运行基础设施。

建议先不接外部 durability engine，而是做一个 Yue 内部 journal 原型：

1. 只覆盖一个可重复的文档分析任务；
2. 每个 model/tool step 写入 append-only 状态和输入哈希；
3. 工具副作用必须带 idempotency key；
4. 进程重启后从最后一个已确认 step 恢复；
5. 对比普通运行的延迟、成本和恢复成功率。

原型证明恢复语义后，再选择 DBOS/Temporal/Prefect 中的一个，不应同时支持三套。

## 其他有价值但应谨慎使用的能力

### `Agent.iter()` 与图节点

可以把“准备上下文→检索→工具调用→校验→最终回答”拆成可检查的节点，适合 Yue 的复杂研究或 workspace-grounded workflow。收益是节点级测试、暂停和诊断；代价是会把当前简单 chat execution boundary 变成显式状态图。建议仅用于新 workflow，不重写普通聊天路径。

### Model wrapper、fallback 与并发

V2 的 model wrapper/fallback 可以提供统一的 provider 降级，但 Yue 已经有 provider routing、tool-call mismatch retry 和 usage accounting。引入前必须定义唯一的 retry owner，否则一次请求可能被 Yue 和框架各重试一次，造成重复费用和重复副作用。优先复用 Yue 的 retry policy，把框架 wrapper 限定为无副作用的 provider 连接故障切换。

### V2 事件流与 AG-UI/UI adapter

这适合内部调试、管理后台或新客户端实验。Yue 的外部 SSE 已经是稳定合同；直接切换到 AG-UI 会改变事件名、终端语义、工具事件和前端耦合，收益不足以抵消迁移风险。可做一个旁路转换器，在不改变 `/api/chat/stream` 的情况下导出标准事件。

## 明确不建议现在启用

- 用 Pydantic AI `MCP`/`MCPToolset` 替代 Yue Tool runtime：会产生第二套发现、授权、schema 和生命周期来源；
- 把 OpenAI Chat Completions 迁移到 Responses API：规格明确延期，且 provider 行为变化大；
- 全局启用 capabilities 以绕过 Yue 的 tool authorization：能力发现不等于授权；
- 直接接 Temporal/DBOS/Prefect 生产 durable runtime：当前没有工作流 identity、幂等和运维基础；
- 把 realtime、web search、image generation、Harness 当作 V2 migration 的“顺手升级”：它们是独立产品和安全评审；
- 运行时引入 Evals：评测应在离线/CI/release pipeline，不应拖慢在线请求。

## 推荐路线图

| 阶段 | 工作 | 退出条件 |
| --- | --- | --- |
| 0：V2 staging | 完成 provider/MCP smoke、telemetry dashboard、canary threshold、rollback drill | Ticket 06 外部 gate 全部有证据 |
| 1：审批原型 | 一个写工具接入 deferred request + Yue approval token | 重启恢复、拒绝安全、幂等和 SSE 不变 |
| 2：审计 hooks | run/tool/output 的脱敏审计 capability | 事件可关联、无 secret leakage、延迟增量可接受 |
| 3：按需工具 | 文档/Excel 只读 Toolset A/B | token 和误选工具率改善，授权测试全绿 |
| 4：长任务恢复 | 一个文档 workflow 的内部 journal | 重启恢复和取消语义稳定，成本可控 |
| 5：平台化 | 只选择一个 durable engine；评估 AG-UI 旁路导出 | 有运维 owner、SLO、回滚和数据保留策略 |

## 决策与验证清单

在任何能力进入生产前，至少记录：

- 功能是否改变 Yue 外部 SSE、持久化 schema、工具权限或 provider protocol；
- 是否有独立的 offline fixture、失败/取消/重试测试；
- 是否引入新的后台 task、连接池、外部服务或 secret；
- token、延迟、工具成功率、重复副作用和错误率相对 V1 的差异；
- 迁移失败时如何禁用该能力并恢复旧路径；
- capability 的 owner、数据保留、审计字段和告警阈值。

## 一手依据

- Pydantic AI 2.37.0 installed package metadata and source: `backend/.venv/lib/python3.11/site-packages/pydantic_ai/` (`Agent`, `capabilities`, `tools`, `durable_exec`, `ui`, `messages`, `models`).
- Official Agent/API documentation: <https://ai.pydantic.dev/agents/>
- Official output and tool documentation: <https://ai.pydantic.dev/output/> and <https://ai.pydantic.dev/tools/>
- Official capabilities documentation: <https://ai.pydantic.dev/capabilities/>
- Official MCP documentation: <https://ai.pydantic.dev/mcp/>
- Official durable-execution documentation: <https://ai.pydantic.dev/durable_execution/>
- Official UI/event-stream documentation: <https://ai.pydantic.dev/ui/>
- Yue migration specification: `.scratch/pydantic-ai-v2-migration/spec.md`.
- Yue V2 assessment: `docs/research/pydantic_ai_upgrade_assessment_20260903.md`.
- Yue release gate: `.scratch/pydantic-ai-v2-migration/issues/06-observability-and-release-validation.md`.
