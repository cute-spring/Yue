# 参考 OpenClaw 工具调用经验的落实计划（Yue）

## 1. 背景与目标（Background & Goals）

### 1.1 背景（Background）

当前系统在部分模型（例如 `stepfun/step-3.5-flash`）上出现过 `finish_reason = "tool_call"` 但没有实际 `tool.call.started` 事件的问题，导致“模型声明要调用工具”与“服务端实际执行工具”之间产生语义错位。该问题本质是**模型协议兼容性（Protocol Compatibility）**与**工具治理（Tool Governance）**不足的组合结果。

问题影响集中在三类场景：
1. 文档问答链路中，首轮工具命中率下降，用户感知为“该调工具却未调”。
2. 异常处理以提示为主，恢复动作不充分，导致重试成本与响应时延上升。
3. 指标虽可观测但缺少按模型运营闭环，难以做准入、降级与归因决策。

### 1.2 目标（Goals）

本计划在保持现有 API 行为兼容的前提下，完成以下升级：
1. 将“工具可用性”从 Prompt 约束升级为**服务端硬约束（Server-Side Enforcement）**。
2. 将“出现异常后提示用户”升级为**分级自愈（Tiered Self-Healing）**。
3. 将“事后排查”升级为**可观测驱动优化（Observability-Driven Optimization）**。

### 1.3 成功标准（Success Criteria）

1. `tool_call_mismatch_rate` 相对基线显著下降，并可按 Provider/Model 归因。
2. `zero_tool_event_rate` 进入可控阈值区间，且异常模型可自动识别。
3. `auto_retry_success_rate` 提升，并将新增时延控制在可接受范围。
4. StepFun / OpenRouter 场景下文档类请求的首轮工具命中率提升。

### 1.4 非目标（Out of Scope）

1. 本阶段不追求所有模型统一支持并行工具调用。
2. 本阶段不重构业务 Agent 语义层，仅治理工具调用协议与策略层。

---

## 2. 外部参考与可复用结论（OpenClaw Lessons）

基于 OpenClaw 官方文档与公开讨论，可提炼出以下可复用机制：

1. **双通道工具暴露（Dual-Channel Exposure）**  
   工具既通过 System Prompt 文本说明暴露，也通过 Provider API 的结构化 Tool Schema 暴露。缺任一通道，模型无法稳定调用工具。

2. **分层工具策略（Layered Tool Policy）**  
   全局（Global）→ Agent（Per-Agent）→ Provider/Model（Per-Provider/Model）逐层收敛，默认最小权限（Least Privilege）。

3. **循环与无进展检测（Loop / No-Progress Detection）**  
   识别重复调用、A/B ping-pong、无增量输出，并触发阻断或降级。

4. **模型能力显式声明（Explicit Model Capability）**  
   对模型是否支持 `tools` / `tool_choice` / 并行工具调用（parallel tool calls）进行显式建模，避免“假支持”。

### 2.1 Lessons 与 Phase A-D 映射（Traceability Map）

1. **双通道工具暴露（Dual-Channel Exposure）** → **Phase A**  
   对应动作：双通道暴露治理与一致性校验，缺失通道触发 `tool_channel_mismatch`。
2. **分层工具策略（Layered Tool Policy）** → **Phase B**  
   对应动作：`tools.profile` / `tools.by_provider` / `tools.by_model` 分层裁剪。
3. **循环与无进展检测（Loop / No-Progress Detection）** → **Phase C**  
   对应动作：重复调用识别、A/B ping-pong 识别、warn/degrade/break 熔断策略。
4. **模型能力显式声明（Explicit Model Capability）** → **Phase A**  
   对应动作：`supports_tools` / `supports_tool_choice` / `supports_parallel_tool_calls` 能力矩阵与 compat gate。

参考来源：
- OpenClaw Tools 文档：https://docs.openclaw.ai/tools
- OpenClaw 讨论（本地/兼容模型工具调用）：https://github.com/openclaw/openclaw/discussions/6922
- Step-3.5-Flash 仓库（OpenClaw 生态指引）：https://github.com/stepfun-ai/Step-3.5-Flash

---

## 3. Yue 当前基线（Current Baseline）

### 已具备

1. **工具事件流（Tool Events Streaming）**  
   已有 `tool.call.started` / `tool.call.finished` 的 SSE 事件与持久化路径。

2. **异常观测（Mismatch Detection）**  
   已在 `chat_stream` 中检测 `finish_reason == "tool_call"` 但无工具事件，并发出 `tool_call_mismatch`。

3. **自动重试（Auto Retry）**  
   已加入 `TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED` 和 fallback model 机制。

### 仍存在差距

1. 缺少**模型能力矩阵（Model Capability Matrix）**作为下发工具的硬前置条件。
2. 缺少**按 Provider/Model 的工具裁剪（Provider/Model Scoped Toolset）**。
3. 缺少**无进展循环护栏（No-Progress Guardrail）**与统一熔断策略。
4. 缺少**工具调用质量指标（Tool Calling Quality KPIs）**的完整聚合看板。
5. 缺少**双通道工具暴露一致性校验（Dual-Channel Consistency Check）**，尚未将 Prompt 暴露与结构化 Tool Schema 暴露绑定治理。

---

## 4. 落地原则（Design Principles）

1. **安全优先（Security First）**：权限只减不增，默认拒绝超范围工具。
2. **兼容优先（Compatibility First）**：保持当前 API 行为兼容，通过 Feature Flags 渐进上线。
3. **观测先行（Observability First）**：没有指标不发布；关键路径必须有事件与统计。
4. **失败可恢复（Recoverable Failure）**：优先自动修复，修复失败再透明提示。

---

## 5. 分阶段实施计划（Phased Execution Plan）

## Phase A：模型能力矩阵（Model Capability Matrix）

目标：在工具下发前做能力判定，避免将工具交给不兼容模型。

实施项：
1. 在配置层引入能力声明：
   - `supports_tools: bool`
   - `supports_tool_choice: bool`
   - `supports_parallel_tool_calls: bool`
2. 为 `openai/*`、`stepfun/*`、`openrouter/*` 建立默认能力表。
3. 在工具注册前执行 `compat gate`：
   - 不支持 tools：直接下发空工具集并附带解释事件。
   - 支持 tools 但不支持 `tool_choice`：降级参数策略。
4. 增加双通道暴露治理：
   - 保证 System Prompt 中工具说明与 Provider API 下发的 Tool Schema 同步来源。
   - 在请求发送前执行一致性校验，发现缺失通道时发出 `tool_channel_mismatch` 事件并触发降级策略。

验收标准：
1. 不支持 tools 的模型，`meta.tools` 为 `[]` 且有 `tool_compat_filtered` 事件。
2. 无“假 tool_call”造成的 silent failure。
3. 抽样会话中 Prompt 工具声明与 `meta.tools` 一致，且无单通道下发导致的调用失败。

---

## Phase B：Provider/Model 工具裁剪（Scoped Toolset）

目标：减少噪声和协议漂移，提高首轮工具命中率。

实施项：
1. 新增配置结构（示例）：
   - `tools.profile`（minimal / docs / full）
   - `tools.by_provider`
   - `tools.by_model`
2. 为 `stepfun/step-3.5-flash` 设默认 docs profile（优先 `docs_list/docs_search/docs_read`）。
3. 在 `tool_registry.get_pydantic_ai_tools_for_agent(...)` 前增加裁剪层。

验收标准：
1. `stepfun/step-3.5-flash` 的默认工具集显著缩小且满足文档问答场景。
2. `tool_call_mismatch_rate` 相比基线下降。

---

## Phase C：无进展护栏与熔断（No-Progress Guardrail）

目标：阻断重复空转，提升稳定性与成本可控性。

实施项：
1. 检测模式：
   - 相同工具 + 相同参数连续调用
   - A/B ping-pong 调用
   - 工具输出无增量（无新证据）
2. 策略：
   - warn（发告警事件）
   - degrade（切换更小工具集）
   - break（提前停止并给明确建议）

验收标准：
1. 相同无进展调用在阈值内被阻断。
2. 用户可见解释与下一步建议稳定输出。

---

## Phase D：指标聚合与运营看板（Metrics & Operations）

目标：将工具调用从“可见”升级到“可运营”。

核心指标：
1. `tool_call_mismatch_rate`
2. `auto_retry_success_rate`
3. `zero_tool_event_rate`
4. `first_tool_latency_p95`
5. `tool_call_success_rate_by_model`

实施项：
1. 扩展 `skill_effectiveness` 与工具事件聚合口径。
2. 输出按 Provider/Model 的日报与周报。
3. 建立模型准入/降级策略（SLO Gate）。

验收标准：
1. 可按模型查看工具调用质量排名。
2. 支持自动触发“降级模型/降级工具集”策略。

---

## 6. 文件级改动建议（File-Level Map）

1. `backend/app/services/config_service.py`  
   - 新增模型能力矩阵读取与默认策略。

2. `backend/app/mcp/registry.py`  
   - 增加 Provider/Model 工具裁剪层与 compatibility gate。

3. `backend/app/api/chat.py`  
   - 接入 `tool_compat_filtered`、`tool_call_retry`、`tool_call_mismatch`、`tool_channel_mismatch` 等事件统一规范。

4. `backend/tests/test_api_chat_unit.py`  
   - 新增模型能力 gate、工具裁剪、无进展熔断、自动重试链路测试。

5. `backend/tests/test_tool_registry_integration.py`（如存在）  
   - 增加 Provider/Model 维度工具集快照回归。

---

## 7. 风险与回滚（Risk & Rollback）

主要风险：
1. 过度裁剪导致可用工具不足，回答质量下降。
2. 能力矩阵配置错误导致误判（False Negative）。
3. 自动重试引入额外成本与时延。

回滚策略：
1. Feature Flags 全量控制：
   - `TOOL_COMPAT_GATE_ENABLED`
   - `TOOL_SCOPED_POLICY_ENABLED`
   - `TOOL_LOOP_GUARD_ENABLED`
2. 任一阶段异常可 1 分钟内切回 legacy 行为（仅保留当前 mismatch 提示链路）。

---

## 8. 里程碑与时间建议（Milestones）

1. M1（1-2 天）：完成 Phase A，接入模型能力矩阵与 gate。
2. M2（2-3 天）：完成 Phase B，按模型工具裁剪与灰度发布。
3. M3（2 天）：完成 Phase C，无进展护栏与熔断。
4. M4（1-2 天）：完成 Phase D，指标聚合与运营看板。

---

## 9. 预期结果（Expected Outcomes）

1. `tool_call_mismatch_rate` 与 `zero_tool_event_rate` 持续下降，并可按模型归因。
2. `auto_retry_success_rate` 提升，且首工具时延波动可控。
3. StepFun / OpenRouter 场景下文档类请求成功率与首轮工具命中率提升。
4. 工具调用链路具备“可控、可观测、可回滚”的生产级属性。

---

## 10. 线上问题复盘（Incident Record: Tool-Call Mismatch）

### 10.1 问题现象（Symptoms）

在 Excel/PDF 等强工具依赖场景中，用户多次遇到以下可见现象：

1. 模型先输出“将调用工具”的自然语言承诺。
2. 同轮结束时 `finish_reason = "tool_call"`，但没有任何 `tool.call.started` 事件。
3. 返回统一提示：`模型返回了 tool_call 结束信号，但未产生可执行工具调用`。
4. 配置了 `TOOL_CALL_MISMATCH_FALLBACK_MODEL` 后，仍可能直接进入 mismatch 提示。

对应链路证据：
- `backend/app/api/chat.py`：`finish_reason == "tool_call"` 且 `tool_call_started_count == 0` 时进入 mismatch 处理分支。
- `backend/app/api/chat.py`：`tool_call_retry`/`tool_call_retry_success`/`tool_call_retry_failed` 事件发射逻辑。

### 10.2 产生原因（Root Causes）

1. **协议兼容性问题（Protocol Compatibility Gap）**  
   部分模型会返回“工具调用结束信号”，但未返回可执行工具调用体，导致服务端观测到“声明调用工具”与“实际未调用工具”不一致。

2. **单一回退模型策略过脆（Single Fallback Fragility）**  
   旧策略仅支持一个 `fallback_model`，当其与当前模型相同或不可用时，自动恢复能力不足。

3. **回退目标缺少 Provider 维度（Provider Blind Retry）**  
   旧策略默认沿用当前 provider 构建回退模型，无法表达“跨 provider 回退”，导致回退链路可用性受限。

### 10.3 已实施解决方案（Implemented Fixes）

已完成以下修复并落地：

1. **多候选回退链（Fallback Chain）**  
   新增 `fallback_models` 概念，支持按顺序配置多个候选模型（逗号分隔）。

2. **跨 Provider 回退（Cross-Provider Retry）**  
   候选支持 `provider/model` 格式（如 `deepseek/deepseek-chat`），重试时按目标 provider 构建模型。

3. **同模型跳过与去重（Skip Same Target + Dedup）**  
   自动跳过与当前 `provider/model` 相同的候选，并对候选目标去重，避免无效重试。

4. **事件可观测增强（Observability Upgrade）**  
   `tool_call_retry` 事件新增 `from_provider/from_model/to_provider/to_model`，失败事件也包含 provider/model，便于运营归因。

关键代码变更：
- `backend/app/services/config_service.py`：`get_tool_call_mismatch_config()` 新增 `fallback_models` 解析与环境变量覆盖逻辑。
- `backend/app/api/chat.py`：mismatch 分支改为“候选链遍历重试”，支持 `provider/model` 解析。

### 10.4 配置规范（Configuration Standard）

建议统一使用：

```env
TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED=true
TOOL_CALL_MISMATCH_FALLBACK_MODELS=minimax/minimax-m2.5,openai/gpt-4o-mini,deepseek/deepseek-chat
```

兼容说明：
- `TOOL_CALL_MISMATCH_FALLBACK_MODEL` 仍可保留用于向后兼容。
- 当 `TOOL_CALL_MISMATCH_FALLBACK_MODELS` 存在时，以其为准。

### 10.5 维护人员排障手册（Runbook）

1. 检查 SSE 是否出现 `tool_call_mismatch` 事件。  
2. 若存在，检查是否出现 `tool_call_retry` 与后续 `tool_call_retry_success`。  
3. 若无 retry 事件，重点核查：
   - `TOOL_CALL_MISMATCH_AUTO_RETRY_ENABLED` 是否为 `true`
   - `TOOL_CALL_MISMATCH_FALLBACK_MODELS` 是否为空
4. 若只有 `tool_call_retry_failed`，按失败事件中的 `provider/model/error` 做逐一剔除或降级。
5. 若连续出现 mismatch，优先将问题模型下沉到候选链后位，或从链路中暂时移除。

### 10.6 验证记录（Validation Evidence）

已补充并通过与本问题直接相关的定向测试：

- `backend/tests/test_config_service_unit.py::test_tool_call_mismatch_config_defaults`
- `backend/tests/test_config_service_unit.py::test_tool_call_mismatch_config_merged_with_env_override`
- `backend/tests/test_api_chat_unit.py::test_chat_stream_auto_retry_after_tool_call_mismatch`
- `backend/tests/test_api_chat_unit.py::test_chat_stream_skip_same_model_retry_and_use_next_candidate`

测试目标覆盖：
- 新配置解析正确性；
- 同模型跳过；
- 跨 provider 回退；
- 回退成功后不落入 mismatch 提示。

### 10.7 后续建议（Next Hardening）

1. 引入模型能力矩阵（`supports_tools` / `supports_tool_choice`）作为工具下发前置 gate。  
2. 建立按模型聚合的 `tool_call_mismatch_rate` 与 `auto_retry_success_rate` 指标看板。  
3. 对高失败模型执行自动降级策略（SLO Gate）。  

---

*文档版本：v1.2*  
*创建时间：2026-03-08*  
*最近更新时间：2026-03-08*  
*适用范围：Yue Backend Tool Calling Pipeline*
