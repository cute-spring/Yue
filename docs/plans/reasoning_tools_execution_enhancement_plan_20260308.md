# Reasoning Chain 与 Tools Execution 展示增强实施方案（分阶段可落地版）

## 1. 背景与问题定义（Background）

当前系统已经具备 Reasoning Chain 与 Tools Execution 的基础能力，但在“显示策略复杂度、稳定显示、事件归属、历史回放、一致性”上仍存在可预期问题：

1. 展示顺序虽在组件层固定为“Reasoning → Tools → Content”，但事件模型仍偏“轻量字段拼接”，缺少统一事件信封（event envelope）。
2. 工具事件历史挂载粒度为 session 级，未做到 message/turn 级精准归属，容易出现历史错位或重复感知。
3. 缺少事件级去重主键与序号，重连/回放场景在工程上不可完全保证幂等（idempotent）与顺序一致。
4. 目前尚无完整的“从流式到历史回放”的统一契约（contract），前后端逻辑分叉较多。

本方案目标是在不破坏现有主链路的前提下，完成一套完整、可分阶段发布、可回滚的增强设计。

### 1.1 当前问题的具体表现（User-Visible Symptoms）

为避免问题描述停留在抽象层，下面补充“用户可见表现 + 触发条件 + 影响范围”：

| 编号 | 具体表现 | 常见触发条件 | 影响 |
| :--- | :--- | :--- | :--- |
| S1 | 历史会话中，某条 assistant 消息下出现“并非该轮触发”的工具调用卡片 | 历史加载时采用 session 级 tool_calls 聚合挂载 | 用户误判模型推理路径，排障成本上升 |
| S2 | 断线重连或重复推送后，Tools Execution 列表出现重复项 | 事件缺稳定 `event_id` 去重键 | UI 可读性下降，状态可信度下降 |
| S3 | 工具事件与正文 token 到达顺序抖动时，展示前后关系不稳定 | SSE 并发合流但缺显式 sequence 约束 | 用户感知“工具在偷跑”或“状态跳变” |
| S4 | 同一问题在“实时流式”和“历史回放”中的工具展示不一致 | 在线路径与历史路径契约不统一 | 难以复盘与审计，难做故障复现 |
| S5 | Reasoning 与 Tools 的关系弱绑定，用户看到“想法”和“动作”脱节 | 缺 assistant turn 级关联字段 | 透明化价值被削弱，解释链不闭环 |

### 1.2 最小复现场景（Minimal Reproduction Scenarios）

1. **场景 A：跨轮错挂**
   - 连续发起两轮都触发工具调用的请求。
   - 刷新页面重新加载历史。
   - 观察到第一轮 assistant 消息下混入第二轮工具调用卡片。

2. **场景 B：重连重复**
   - 在工具执行中途断网并恢复，或触发客户端重连。
   - 若后端/中间层重发已送达事件，前端缺去重时会重复渲染同一 `tool.call.started/finished`。

3. **场景 C：顺序抖动**
   - 模型正文与工具事件在并发路径中交错抵达。
   - 页面可能出现“先看到回答片段，再看到对应工具运行”或状态瞬时回跳。

### 1.3 影响评估（Impact Assessment）

1. **用户信任影响**：执行透明化的核心价值下降，用户难以确认“是否按预期调用了工具”。
2. **工程运维影响**：排障时需要人工对齐日志与界面，定位耗时增加。
3. **产品一致性影响**：同一会话在实时与历史视图不一致，影响审计与回放可信度。

---

## 2. 目标与非目标（Goals / Non-Goals）

### 2.1 目标（Goals）

1. 固化并稳定用户可见顺序：**Reasoning Chain → Tools Execution → Final Content**。
2. 建立统一事件模型：支持 `event_id`、`sequence`、`run_id`、`assistant_turn_id`。
3. 实现工具事件按 assistant turn 精准归属，消除历史回放错位。
4. 支持前端去重、重连恢复、历史回放一致性。
5. 引入完整测试门禁（unit + integration + frontend state tests）。

### 2.2 非目标（Non-Goals）

1. 不重构整套聊天 UI 风格与布局体系。
2. 不引入新的长期数据仓库或外部观测平台。
3. 不在本期做复杂 trace graph 产品化，仅保证事件契约可扩展。

### 2.3 核心设计决策（Design Decision）

本次改写采用“**Reasoning 显示最小化策略**”，规则如下：

1. 仅当 **模型具备 reasoning/deep thinking 能力** 且 **用户开启 deep thinking** 时，才展示 Reasoning Chain。
2. 不满足上述条件时：
   - 前端不渲染 Reasoning Chain 区块；
   - 后端不注入 `<thought>...</thought>` 协议；
   - 系统仅展示 Tools Execution + Final Content。
3. 实时流式与历史回放遵循同一规则，避免“实时有思维链、历史无思维链”或反向不一致。

该决策的目标是：减少分支、减少误判、降低维护复杂度，优先保证可解释的一致性与稳定性。

### 2.4 Deep Thinking 能力判定规范（Capability Decision Spec）

本节定义“如何判断某个 LLM 是否支持 deep thinking / reasoning”，作为后端判定、前端展示与测试验收的统一依据。

#### 2.4.1 判定原则（Principles）

1. **配置优先（Config-First）**：以模型配置中的 `capabilities` 为唯一权威来源。
2. **保守默认（Fail-Closed）**：未声明 `reasoning` 能力时，默认不支持。
3. **开关分离（Capability vs Toggle）**：
   - `supports_reasoning` 代表模型“能力”；
   - `deep_thinking_enabled` 代表用户“意图”；
   - 最终渲染开关 `reasoning_enabled = supports_reasoning AND deep_thinking_enabled`。
4. **前后端同源（Single Source of Truth）**：以服务端判定结果为准，前端不再自行猜测模型名。

#### 2.4.2 数据来源（Data Sources）

1. **模型能力来源**：`llm.models.{provider/model}.capabilities`。
   - 示例：`["text", "function_calling", "reasoning"]`。
2. **用户开关来源**：前端 Deep Thinking Toggle 状态，随请求透传到 `/api/chat/stream`。
3. **运行时判定输出**：后端在首个 `meta` 事件返回 `reasoning_enabled` 与 `supports_reasoning`。

#### 2.4.3 判定算法（Deterministic Algorithm）

```text
Input:
  provider, model_name, deep_thinking_enabled

Step 1:
  capabilities = get_model_capabilities(provider, model_name)

Step 2:
  supports_reasoning = ("reasoning" in capabilities)

Step 3:
  reasoning_enabled = supports_reasoning AND deep_thinking_enabled

Output:
  supports_reasoning, reasoning_enabled
```

#### 2.4.4 判定矩阵（Decision Matrix）

| supports_reasoning | deep_thinking_enabled | reasoning_enabled | UI 行为 | Prompt 行为 |
| :--- | :--- | :--- | :--- | :--- |
| false | false | false | 不显示 Reasoning Chain | 不注入 reasoning 协议 |
| false | true | false | 不显示 Reasoning Chain | 不注入 reasoning 协议 |
| true | false | false | 不显示 Reasoning Chain | 不注入 reasoning 协议 |
| true | true | true | 显示 Reasoning Chain | 允许 reasoning 输出路径 |

#### 2.4.5 不推荐策略（Anti-Patterns）

以下方式不再作为主路径判定标准：

1. 通过模型名关键词推断（如 `r1`、`o1`、`reasoner`）直接决定展示。
2. 通过正文中是否出现 `<thought>` 标签反向判断“模型支持 deep thinking”。
3. 前端独立判定而不依赖后端输出，导致实时与历史不一致。

#### 2.4.6 兼容与迁移（Compatibility Plan）

在灰度期允许以下兼容策略，但需明确下线时间：

1. 若历史模型配置缺失 `capabilities`，可临时使用名称匹配作为运营兜底，仅用于告警，不直接开启 `reasoning_enabled`。
2. 对 legacy 数据，允许读取已有 `thought` 字段渲染历史内容，但新请求统一走 `reasoning_enabled` 判定。
3. 兼容窗口建议 1-2 个发布周期，随后移除名称推断主逻辑。

#### 2.4.7 观测与告警（Observability）

新增/复用指标：

1. `reasoning_capability_missing_rate`：模型配置缺失 reasoning 能力声明比例。
2. `reasoning_toggle_ignored_rate`：用户打开 deep thinking 但模型不支持导致未启用比例。
3. `reasoning_display_accuracy_rate`：展示行为与判定矩阵一致比例。
4. `reasoning_policy_fallback_count`：触发兼容兜底策略次数。

#### 2.4.8 测试用例（Test Cases）

最小覆盖集：

1. **能力缺失 + 开关开**：`reasoning_enabled=false`，UI不显示。
2. **能力存在 + 开关关**：`reasoning_enabled=false`，UI不显示。
3. **能力存在 + 开关开**：`reasoning_enabled=true`，UI显示。
4. **能力缺失 + 开关关**：`reasoning_enabled=false`，UI不显示。
5. **回放一致性**：实时与历史对于同一 turn 的 `reasoning_enabled` 判定一致。
6. **兼容路径**：legacy 消息不影响新会话的判定规则。

#### 2.4.9 API 契约补充（Stream Meta Contract）

建议在首个 `meta` 事件补充以下字段：

```json
{
  "meta": {
    "provider": "openai",
    "model": "gpt-4o",
    "supports_reasoning": true,
    "deep_thinking_enabled": true,
    "reasoning_enabled": true
  }
}
```

其中：
- `supports_reasoning`：来自模型能力配置；
- `deep_thinking_enabled`：来自用户开关；
- `reasoning_enabled`：服务端最终判定结果（前端仅消费此结果控制展示）。

---

## 3. 现状基线（Current Baseline）

### 3.1 后端流式与工具事件

- 聊天流主编排位于 `backend/app/api/chat.py`。
- 工具事件由 `backend/app/mcp/registry.py` 的 wrapper 发出 `tool.call.started/finished`。
- `chat.py` 通过队列并发合并文本流与工具事件，并以 SSE 发给前端。

### 3.2 前端解析与展示

- 流式消费位于 `frontend/src/hooks/useChatState.ts`，按字段/事件分支更新最后一条 assistant 消息。
- Reasoning 通过 `frontend/src/utils/thoughtParser.ts` 做结构化/标签兼容解析。
- 展示位于 `frontend/src/components/MessageItem.tsx` 与 `ToolCallItem.tsx`。
- 当前 Reasoning 展示为混合条件（模型名推断、thought 内容存在、流式状态），策略复杂且与 deep thinking 开关未完全统一。

### 3.3 持久化与历史回放

- `backend/app/services/chat_service.py` 已有 `tool_calls` 存储。
- 历史读取时当前策略更偏 session 聚合挂载，缺少 turn 级关联主键。

---

## 4. 关键差距（Gap Analysis）

1. **事件缺统一信封**：当前事件结构可用但不标准，缺 `event_id/sequence`。
2. **归属缺 assistant_turn_id**：工具调用记录无法准确绑定具体 assistant 回合。
3. **前端缺去重模型**：断线重连与回放容易产生重复渲染风险。
4. **契约未版本化**：流式与历史接口没有显式 version 与兼容策略。
5. **测试覆盖未形成门禁闭环**：缺少针对顺序、幂等、重放一致性的专项验证。
6. **Reasoning 展示策略过于混合**：当前包含“模型名推断 + 标签解析 + 流式状态”多分支逻辑，心智负担高、调试成本高。

---

## 5. 目标架构（Target Architecture）

采用“**事件优先（Event-First） + 回合绑定（Turn-Bound） + 前端幂等渲染（Idempotent Render） + Reasoning 条件显示（Conditional Reasoning）**”：

1. 后端所有可观察事件统一封装为 `ChatEventEnvelope`。
2. 每次 assistant 响应生成时创建 `assistant_turn_id`，所有 tool/reasoning/content 事件均挂载此 ID。
3. 前端以 `event_id` 去重、`sequence` 排序，消息按 turn 聚合后渲染。
4. 历史接口按 turn 回放，保证“在线流式”与“离线回放”一致。
5. Reasoning 只在 `reasoning_enabled=true` 时展示，且该标志由“模型能力 + deep thinking 开关”共同决定。

---

## 6. 分阶段实施方案（Phased Implementation）

## Phase 0：基线冻结与特性开关（1 天）

### 目标
- 在不改行为的前提下，为后续改造建立可回滚护栏。

### 改动
1. 增加特性开关：
   - `transparency_event_v2_enabled`
   - `transparency_turn_binding_enabled`
   - `reasoning_display_gated_enabled`
2. 记录基线指标：
   - `tool_call_mismatch_rate`
   - `duplicate_tool_render_rate`
   - `history_misalignment_rate`
   - `reasoning_unexpected_render_rate`

### 验收
- 开关关闭时，行为与当前线上一致。

---

## Phase 1：事件契约标准化（2-3 天）

### 目标
- 将现有 SSE payload 升级为标准事件信封，不破坏现有字段兼容。

### 后端改动
1. 在 `backend/app/api/chat.py` 增加事件构造器：
   - `build_event_envelope(event_type, payload, run_id, assistant_turn_id, sequence)`
2. `tool.call.started` 与 `tool.call.finished` 增补字段：
   - `event_id`, `sequence`, `run_id`, `assistant_turn_id`, `ts`
3. 在首个 `meta` 事件中增加 `reasoning_enabled` 字段（布尔值）。
4. 保留旧字段以兼容旧前端分支（灰度阶段）。

### 前端改动
1. `frontend/src/types.ts` 新增 `ChatEventEnvelope` 类型。
2. `useChatState.ts` 优先消费 envelope，旧分支作为 fallback。
3. 将 `reasoning_enabled` 存入当前 assistant turn 上下文。

### 测试
1. 后端单测：事件字段完整性与 sequence 单调性。
2. 前端单测：envelope/legacy 双路径兼容。
3. 单测校验 `reasoning_enabled` 有无对显示分支的影响。

### 验收
- 新旧前端都能正确显示工具状态与文本流。
- `reasoning_enabled=false` 时，不渲染 Reasoning Chain。

---

## Phase 1.5：Reasoning 显示简化改造（2 天）

### 目标
- 将 Reasoning 从“混合推断显示”改为“显式条件显示”，显著降低实现复杂度。

### 后端改动
1. 调整 `build_system_prompt` 触发条件：
   - 仅当模型 capability 包含 reasoning 且 deep thinking 开启时，允许 reasoning 协议或结构化思维输出。
2. deep thinking 关闭时，不注入 `<thought>...</thought>` 协议。
3. 将开关状态与模型能力判定结果统一映射为 `reasoning_enabled`。

### 前端改动
1. `MessageItem.tsx` 改为基于 `reasoning_enabled` 决定是否渲染 Reasoning 区块。
2. 保留 `thoughtParser` 作为兼容兜底，但默认路径不依赖正文标签推断。
3. 将“Reasoning 展示条件”从多分支收敛为单分支布尔决策。

### 测试
1. 组合用例覆盖：
   - 支持 reasoning + deep thinking 开启 → 显示；
   - 支持 reasoning + deep thinking 关闭 → 不显示；
   - 不支持 reasoning + deep thinking 开启/关闭 → 不显示。
2. 回放一致性测试：实时与历史都遵循同一显示规则。

### 验收
- Reasoning 展示行为可预测且规则单一，前后端一致。

---

## Phase 2：assistant turn 精准绑定与持久化升级（3-4 天）

### 目标
- 实现工具调用按消息回合精准归属，解决历史错位问题。

### 数据模型改动
1. `tool_calls` 增加字段：
   - `assistant_turn_id TEXT`
   - `run_id TEXT`
   - `event_id_started TEXT`
   - `event_id_finished TEXT`
2. 索引建议：
   - `idx_tool_calls_session_turn_created(session_id, assistant_turn_id, created_at)`
   - `idx_tool_calls_run_sequence(run_id, created_at)`

### 后端改动
1. 在 `chat.py` 每轮 assistant 响应开始即生成 `assistant_turn_id`。
2. `chat_service.add_tool_call/update_tool_call` 增补 turn/run/event 字段写入。
3. `chat_service.get_chat` 按 assistant_turn_id 关联 tool_calls，而非 session 全量挂载。

### 测试
1. 数据迁移测试：旧数据可读、字段缺失可降级。
2. API 单测：多轮对话下工具事件归属正确。

### 验收
- 历史页面中每条 assistant 仅显示其自身工具调用。

---

## Phase 3：前端幂等状态机与稳定排序（3 天）

### 目标
- 前端在流式、重连、回放场景保持一致渲染。

### 前端改动
1. `useChatState.ts` 引入内存事件仓：
   - `seenEventIds: Set<string>`
   - `eventsByTurn: Map<assistant_turn_id, Event[]>`
2. 更新合并规则：
   - 去重：`event_id`
   - 排序：`sequence`（缺失则 `ts` 兜底）
3. UI 固化显示顺序：
   - Reasoning block
   - Tools Execution block
   - Content block

### 测试
1. 状态测试：重复事件不重复渲染。
2. 顺序测试：乱序到达后仍按 sequence 展示。
3. 回放测试：实时结果与历史加载一致。

### 验收
- 强制模拟重连后，页面无重复 tool 卡片、顺序一致。

---

## Phase 4：历史回放接口与一致性闭环（2-3 天）

### 目标
- 在线与离线完全同构，支持可靠复盘。

### 后端改动
1. 新增回放接口（建议）：
   - `GET /api/chat/{chat_id}/events`
   - 可选参数：`assistant_turn_id`, `after_sequence`
2. 返回统一 envelope 序列。

### 前端改动
1. 进入会话时先拉取 `events` 再 hydration message。
2. 若接口不可用，自动降级旧历史逻辑。

### 测试
1. 集成测试：同一会话“流式结果”与“回放结果”一致。

### 验收
- 回放与实时同一 turn 的工具状态、耗时、顺序一致。

---

## Phase 5：强化与灰度发布（2 天）

### 目标
- 以最小风险上线并可快速回滚。

### 发布策略
1. Stage A：内部环境启用 `event_v2`。
2. Stage B：10% 灰度用户启用 turn binding + reasoning gated display。
3. Stage C：全量发布并保留 legacy 兼容 1-2 个版本周期。

### 监控指标
1. `event_parse_error_rate`
2. `duplicate_tool_render_rate`
3. `history_alignment_success_rate`
4. `tool_call_success_rate_by_model`
5. `reasoning_display_accuracy_rate`

### 回滚策略
1. 关闭 `transparency_event_v2_enabled` 即刻回到 legacy payload。
2. 关闭 `transparency_turn_binding_enabled` 回到 session 级挂载策略。
3. 关闭 `reasoning_display_gated_enabled` 回到现有混合展示策略。

---

## 7. 文件级实施清单（File-Level Map）

### Backend
1. `backend/app/api/chat.py`
   - 事件信封构造
   - sequence/run_id/assistant_turn_id 注入
2. `backend/app/mcp/registry.py`
   - started/finished 事件扩展字段透传
3. `backend/app/services/chat_service.py`
   - tool_calls 写入/读取模型升级
   - 按 turn 归属查询
4. `backend/app/services/config_service.py`
   - 新增特性开关配置读取
5. `backend/app/services/prompt_service.py`
   - 仅在条件满足时注入 reasoning 协议

### Frontend
1. `frontend/src/types.ts`
   - 增加 `ChatEventEnvelope` 与 turn 级结构
2. `frontend/src/hooks/useChatState.ts`
   - 事件去重、排序、turn 聚合、reasoning_enabled 透传
3. `frontend/src/components/MessageItem.tsx`
   - 固化 Reasoning / Tools / Content 顺序策略与条件显示
4. `frontend/src/components/ToolCallItem.tsx`
   - 可选增加 sequence 与回放标识显示

### Tests
1. `backend/tests/test_api_chat_unit.py`
2. `backend/tests/test_tool_registry_integration.py`
3. `frontend` 对应 hook/component 测试文件

---

## 8. 质量门禁（Quality Gates）

1. 事件契约门禁：每个工具调用必须成对出现 `started/finished` 或可解释失败事件。
2. 顺序门禁：同一 turn 内 sequence 单调非降。
3. 幂等门禁：重复输入事件集，渲染结果不变。
4. 回放门禁：实时与历史输出一致。
5. 兼容门禁：legacy 客户端可正常工作。
6. Reasoning 门禁：仅在 `reasoning_enabled=true` 时展示思维链。

---

## 9. 验收标准（Acceptance Criteria）

1. 用户可稳定看到“Reasoning Chain（条件满足时）→ Tools Execution → Final Content”。
2. 多轮会话历史中，工具调用不会跨轮错挂。
3. 断线重连后不出现重复工具卡片。
4. Reasoning 显示只由“模型能力 + deep thinking 开关”决定，不再依赖混合推断。
5. 支持按 turn 回放并与实时一致。
6. 出现异常时可通过开关分钟级回滚。

---

## 10. 执行排期建议（Suggested Timeline）

1. Week 1：Phase 0 + Phase 1 + Phase 1.5
2. Week 2：Phase 2 + Phase 3
3. Week 3：Phase 4 + Phase 5 + 灰度观测

如果资源紧张，可优先实施 Phase 1.5 + Phase 2，这两步可优先收敛复杂度并提升稳定性。

---

## 11. 当前代码差距映射（Code Gap Mapping）

为减少实施阶段二次理解成本，以下给出“现状代码证据 → 目标改造”的一一映射。

| 主题 | 现状代码证据 | 差距结论 | 目标改造 |
| :--- | :--- | :--- | :--- |
| Deep Thinking 开关透传 | `frontend/src/hooks/useChatState.ts` 发送 `/api/chat/stream` 时未携带 deep thinking 字段 | 用户意图无法进入后端判定 | 在 ChatRequest 增加 `deep_thinking_enabled` 并前端透传 |
| Reasoning 判定来源 | `backend/app/services/prompt_service.py` 仍包含模型名关键词兜底逻辑 | 判定路径混合，不利于一致性 | 以 `capabilities.reasoning` 为主，关键词仅灰度告警兜底 |
| Reasoning 展示条件 | `frontend/src/components/MessageItem.tsx` 仍依赖模型名/内容/流式混合条件 | UI 条件分支过多 | 改为仅消费后端 `meta.reasoning_enabled` |
| 工具事件顺序与幂等 | `backend/app/api/chat.py` 与 `frontend/src/hooks/useChatState.ts` 当前无完整 envelope 去重主键 | 重连与回放场景可重复/乱序 | 引入 `event_id + sequence + assistant_turn_id` |
| 历史工具归属 | `backend/app/services/chat_service.py` 目前为 session 聚合挂载 | 跨轮错挂风险高 | 按 `assistant_turn_id` 精准归属 |

---

## 12. API 变更清单（Contract Delta）

本节明确接口字段变化，避免前后端联调时口径不一致。

### 12.1 请求体变更（`POST /api/chat/stream`）

新增字段：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `deep_thinking_enabled` | boolean | 否 | `false` | 用户是否主动开启 deep thinking |

兼容策略：
1. 旧客户端不传该字段时，后端按 `false` 处理。
2. 新客户端必须显式传递，避免服务端猜测。

### 12.2 SSE `meta` 事件变更

新增字段：

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `supports_reasoning` | boolean | 模型 capability 判定结果 |
| `deep_thinking_enabled` | boolean | 用户开关状态 |
| `reasoning_enabled` | boolean | 最终渲染判定（前端仅消费该字段） |

兼容策略：
1. 旧前端忽略未知字段，不影响主流程。
2. 新前端优先使用 `reasoning_enabled` 控制渲染。

### 12.3 废弃计划（Deprecation）

1. `MessageItem` 基于模型名关键字判断 reasoning 的主路径进入废弃状态。
2. 计划在 1-2 个发布周期后移除关键词主逻辑，仅保留监控告警用途。

---

## 13. 测试执行清单（Step-by-Step Test Plan）

本节提供可执行的测试分步，确保“写了方案就能按步骤验证”。

### 13.1 本地前置条件

1. 后端依赖已安装，且可运行 `pytest`。
2. 使用测试配置文件，避免污染生产数据。
3. 准备至少 1 个 `capabilities` 含 `reasoning` 的模型和 1 个不含 `reasoning` 的模型。

### 13.2 后端测试步骤

1. 运行单测（事件契约、判定逻辑、历史归属）：
   - `PYTHONPATH=backend pytest backend/tests/test_api_chat_unit.py`
   - `PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py`
2. 新增/补充用例：
   - `deep_thinking_enabled` 透传到服务端；
   - `meta.reasoning_enabled` 组合判定；
   - `assistant_turn_id` 归属正确；
   - `event_id/sequence` 单调与不重复。
3. 通过标准：
   - 关键测试 100% 通过；
   - 不引入既有回归失败。

### 13.3 前端测试步骤

1. 状态层测试：
   - 重复事件输入不重复渲染；
   - 乱序事件输入按 `sequence` 收敛。
2. 展示层测试：
   - `reasoning_enabled=false`：不显示 Reasoning；
   - `reasoning_enabled=true`：显示 Reasoning；
   - Tools Execution 在两种情况下均正常。
3. 手动联调检查：
   - 切换 deep thinking 开关后，下一轮请求的 `meta` 字段变化符合预期。

### 13.4 回放一致性测试

1. 触发一轮包含工具调用的会话并记录实时界面结果。
2. 刷新后通过历史回放加载同一会话。
3. 对比以下维度是否一致：
   - Reasoning 是否显示；
   - 工具调用数量、顺序、状态；
   - 关键耗时字段。

### 13.5 验收打勾表（Checklist）

- [ ] 判定矩阵 4 组合全部通过。
- [ ] 重连场景无重复工具卡片。
- [ ] 历史与实时展示一致。
- [ ] legacy 客户端可继续使用。
- [ ] 关键指标达到门槛（见第 8 节）。

---

## 14. 回滚 Runbook（Operational Rollback）

### 14.1 触发条件

满足任一条件即触发回滚评估：

1. `event_parse_error_rate` 在 15 分钟窗口内显著升高。
2. `reasoning_display_accuracy_rate` 低于阈值。
3. 线上出现大面积“历史错挂/重复渲染”用户反馈。

### 14.2 回滚顺序

1. 关闭 `reasoning_display_gated_enabled`，恢复原展示逻辑。
2. 若问题仍在，关闭 `transparency_turn_binding_enabled`。
3. 若仍异常，关闭 `transparency_event_v2_enabled` 回到 legacy payload。

### 14.3 回滚后验证

1. 监控 15-30 分钟关键指标是否回归。
2. 快速人工验证：
   - 发起 1 轮工具调用会话；
   - 刷新回放；
   - 确认主流程可用。

---

## 15. 风险优先级矩阵（Risk Priority）

| 风险 | 概率 | 影响 | 优先级 | 缓解措施 |
| :--- | :--- | :--- | :--- | :--- |
| 事件乱序导致 UI 跳变 | 中 | 高 | P0 | 强制 `event_id + sequence` 与前端幂等合并 |
| 历史工具跨轮错挂 | 高 | 高 | P0 | `assistant_turn_id` 绑定与回放一致性测试 |
| 判定规则迁移导致展示异常 | 中 | 中 | P1 | 灰度开关 + 判定矩阵测试 |
| legacy 兼容退化 | 低 | 高 | P1 | 双路径兼容与发布前回归 |
| 指标不可观测导致问题发现滞后 | 中 | 中 | P2 | 提前埋点并设置告警阈值 |

---

## 16. 分阶段 DoD（Definition of Done）

### Phase 0 DoD
- [ ] 三个特性开关已接入配置。
- [ ] 基线指标可查询。

### Phase 1 DoD
- [ ] SSE envelope 字段上线并兼容旧字段。
- [ ] `meta.reasoning_enabled` 可稳定输出。

### Phase 1.5 DoD
- [ ] 前端展示仅消费 `reasoning_enabled` 主路径。
- [ ] 后端不再默认注入 `<thought>` 到非启用场景。

### Phase 2 DoD
- [ ] `assistant_turn_id` 写入与查询链路完成。
- [ ] 历史工具归属不再 session 混挂。

### Phase 3 DoD
- [ ] 前端去重与排序逻辑通过压测样例。
- [ ] 重连场景无重复渲染。

### Phase 4 DoD
- [ ] 回放接口可用，实时与回放一致。

### Phase 5 DoD
- [ ] 灰度数据达标后全量发布。
- [ ] 回滚演练完成并记录结果。
