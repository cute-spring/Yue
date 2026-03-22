# Chat API Stream Simplification Plan (2026-03-22)

## 1. Background and Goal

`backend/app/api/chat.py` 当前约 857 行，`chat_stream -> event_generator` 逻辑承担了过多职责（配置解析、技能路由、工具事件持久化、流式生成、重试、usage 统计、落库、日志、异常分流）。

本计划目标：

1. 在不改变外部 API 行为和 SSE 契约的前提下，降低 `chat.py` 复杂度和维护成本。
2. 将“编排层”和“业务策略层”分离，减少单函数内状态变量和重复分支。
3. 为后续能力迭代（模型策略、重试策略、可观测性）提供稳定扩展点。

非目标：

1. 本轮不调整前端协议字段命名。
2. 本轮不重写 `chat_service` 数据模型。
3. 本轮不变更数据库 schema。

## 2. Current Problems (Observed)

## 2.1 Single Function Overloaded

`event_generator` 同时处理如下职责：

1. 会话上下文初始化
2. 技能选择与提示词装配
3. 工具事件队列和持久化
4. 模型能力判定（reasoning/vision）
5. 主流式推理
6. 错误分流与工具兼容回退
7. usage/性能指标收集与补充提示
8. assistant 落库与响应日志

## 2.2 State Explosion

函数内存在大量跨区域变量（tokens、duration、finish_reason、provider/model、turn id、error message 等），可读性和正确性风险较高。

## 2.3 Duplicate and Divergent Paths

1. `stream_result_chunks(...)` 在主流程、fallback、retry 三处重复。
2. `user_input` 构造有多套路径，未来易出现输入不一致。
3. 错误处理链存在局部 `return`/`raise` 混合，控制流复杂。

## 2.4 Thin Wrapper and Dead Code

存在仅做透传的本地 wrapper 与未使用 helper，增加噪音和阅读负担。

## 3. Design Principles

1. **Behavior Preservation First**: 不改变 API 路由、SSE 事件 key、持久化语义。
2. **Small Safe Steps**: 按阶段拆解，每阶段均可独立回滚。
3. **Single Responsibility**: 路由层只做编排，策略逻辑下沉到 service/helper。
4. **Explicit State**: 通过 dataclass 聚合运行态和指标态，消除隐式 `locals()` 依赖。
5. **Test Before/After Parity**: 以回归测试覆盖关键路径，不依赖人工点测。

## 4. Execution Plan

## Phase 0: Baseline and Safety Net

目标：建立可验证基线，避免重构引入行为漂移。

任务：

1. 补齐 `chat_stream` 关键路径测试矩阵（成功流、tool fallback、usage limit、vision reject、cancelled）。
2. 记录当前关键输出样本（SSE 事件序列、assistant 入库字段）。
3. 将现有日志字段建立对照清单（请求日志、响应日志）。

产出：

1. 回归测试集（新增/补强）。
2. 事件契约对照表（文档）。

完成标准：

1. 测试在当前主干稳定通过。
2. 能够明确比对重构前后行为是否一致。

## Phase 1: Low-Risk Internal Refactor (No Behavior Change)

目标：减少函数体长度和重复代码，保持行为不变。

任务：

1. 抽取上下文准备函数 `_prepare_stream_runtime(...)`  
   职责：agent_config、skill runtime、prompt assemble、model availability、tools、capabilities、meta payload。
2. 抽取通用执行函数 `_run_stream_once(...)`  
   职责：统一 `agent.run_stream + stream_result_chunks`，避免三处重复。
3. 抽取 `_emit_reasoning_and_vision_meta(...)`  
   职责：reasoning 开关判定、meta payload 统一发射。
4. 删除未使用 helper；将薄透传 helper 合并为直接调用（仅当不影响可测性）。
5. 显式引入 `current_exception: Exception | None`，替代 `locals()` 检查。

产出：

1. `chat.py` 代码行数显著下降（预期减少 120~180 行）。
2. 同功能代码聚合，重复路径收敛。

完成标准：

1. 所有现有和新增测试通过。
2. 对比 Phase 0 输出样本，事件序列和关键字段一致。

## Phase 2: Structured State Refactor

目标：压缩跨作用域变量，提升可维护性。

任务：

1. 新增 `StreamRunContext` dataclass  
   字段建议：`chat_id/run_id/assistant_turn_id/provider/model_name/system_prompt/tools/deps/history/feature_flags/...`
2. 新增 `StreamRunMetrics` dataclass  
   字段建议：`ttft/total_duration/thought_duration/prompt_tokens/completion_tokens/total_tokens/finish_reason/tool_call_started/tool_call_finished/stream_error_message`
3. 抽离 `ToolEventTracker`（类或闭包工厂）  
   职责：统一处理 `tool.call.started/finished` + DB 持久化 + 计数。
4. `event_generator` 转为“编排式流程”：prepare -> run -> postprocess -> persist/log。

产出：

1. 控制流清晰、状态聚合明确。
2. 后续功能新增时不再扩散局部变量。

完成标准：

1. 重构后 cyclomatic complexity 下降。
2. 关键函数参数列表可读、职责单一。

## Phase 3: Strategy Extraction

目标：把高变动策略从路由层下沉，形成独立可测单元。

任务：

1. 提取 `tool_call mismatch` 自动重试策略到独立 service（例如 `chat_retry_service.py`）。
2. 提取 postprocess pipeline（usage emit、continue hint、citation append）到独立模块。
3. 提取错误映射策略（ollama 502、TLS/proxy、tool unsupported）到统一异常策略函数。

产出：

1. `chat.py` 仅保留编排入口和路由定义。
2. 策略逻辑可单测、可复用。

完成标准：

1. 关键策略模块具备独立测试。
2. 新增策略无需修改主路由核心流程。

## 5. Proposed File-Level Changes

首轮（Phase 1）建议涉及：

1. `backend/app/api/chat.py`（主重构）
2. 可选新增：
   - `backend/app/services/chat_stream_runtime.py`
   - `backend/app/services/chat_retry_service.py`
   - `backend/app/services/chat_postprocess_pipeline.py`

说明：是否新增文件取决于团队偏好；若希望最小改动，可先仅在 `chat.py` 内部抽函数，再逐步外移。

## 6. Risk Assessment and Mitigation

主要风险：

1. SSE 事件顺序变化导致前端透明度面板回归。
2. fallback/retry 行为变化导致工具调用率波动。
3. 异常分支遗漏导致 assistant 消息未落库。

缓解措施：

1. 建立“事件序列快照测试”（至少覆盖 5 条典型路径）。
2. 重构后对比 `tool_call_started/finished` 计数分布。
3. 在 finally 阶段落库逻辑加回归断言（异常与取消场景）。

## 7. Test Plan

单元测试：

1. reasoning/vision 判定逻辑（feature flag on/off，capability on/off）。
2. tool mismatch retry 目标解析逻辑（`provider/model` 字符串分解、去重）。
3. usage 解析适配逻辑（同步/异步 usage 对象）。

集成测试：

1. `/chat/stream` 正常路径：事件完整性、assistant 落库、usage 字段。
2. tool unsupported fallback 路径：是否切换 no-tools agent 并继续产出内容。
3. usage limit 路径：`run.limited` 与友好提示落地。
4. cancelled 路径：取消后日志与落库状态合理。

人工验收：

1. 前端会话页流式展示无明显倒退。
2. 透明度事件（tool/reasoning/meta）可正常消费。

## 8. Rollout and Rollback

发布策略：

1. 分阶段 PR：Phase 1 -> Phase 2 -> Phase 3，避免超大变更。
2. 每阶段合并后观察 24h 日志指标（错误率、tool_call mismatch 率、平均响应时长）。

回滚策略：

1. 每个阶段保持独立提交，可按 commit/PR 级别回退。
2. 如发现协议风险，优先回滚策略提取（Phase 3），保留低风险结构优化（Phase 1/2）。

## 9. Acceptance Criteria (Definition of Done)

1. `chat_stream` 行为与现网契约一致，关键 SSE 事件字段无破坏性变化。
2. `chat.py` 主函数复杂度显著降低，职责边界清晰。
3. 核心路径（success/fallback/retry/limit/cancel）均有自动化覆盖。
4. 观测指标无明显退化（错误率、响应时长、工具调用成功率）。

## 10. Suggested Execution Order and Estimate

1. Phase 0: 0.5 ~ 1 天
2. Phase 1: 0.5 ~ 1 天
3. Phase 2: 1 ~ 1.5 天
4. Phase 3: 1 天

总计：约 3 ~ 4.5 天（含测试与回归）。

