# Unified Contract Gate（SSE + API Compatibility）执行计划

## 1. 背景与目标（Background & Goals）

### 1.1 背景（Background）

当前增强路线中，推理链路、工具调用治理、可观测与透明化都在扩展事件语义与 API 输出。若缺少统一兼容闸门，不同模块可在各自测试中通过，但在端到端链路中仍可能出现以下回归：

1. SSE 事件字段漂移导致前端渲染或解析失败。
2. 重连/回放路径中的事件顺序不稳定，造成重复渲染或缺失渲染。
3. 老版本客户端遇到新事件类型时异常中断。

因此需要将事件与 API 合同从“约定”升级为“发布前硬门禁”。

### 1.2 目标（Goals）

本计划聚焦 P0-1，建立统一 Contract Gate，确保 SSE 事件与关键 API Schema 在增量演进中保持可验证兼容性：

1. 对关键事件类型建立 Golden Contract Tests。
2. 对 replay + reconnect 建立确定性测试与去重测试。
3. 对未知事件类型建立向后兼容断言。
4. 将破坏性变更强制绑定版本升级与发布审批。

### 1.3 成功标准（Success Criteria）

1. 未显式版本升级的变更无法引入破坏性 schema 修改。
2. 每次候选发布均通过 replay 一致性、重连一致性、事件去重三类测试。
3. 老客户端面对未知事件类型可降级处理且不中断主流程。
4. 每个 release candidate 均产生可审计的 Contract Gate 报告。

### 1.4 非目标（Out of Scope）

1. 本阶段不重构业务推理策略或工具调度策略。
2. 本阶段不引入跨服务协议统一平台，仅覆盖 Yue 当前 chat stream 与相关关键 API。

---

## 2. 合同治理范围（Contract Surface）

### 2.1 SSE 事件合同范围

纳入强制治理的事件类型：

1. `meta`
2. `content`
3. `error`
4. `tool_event`
5. `trace_event`

每类事件均需明确：

1. `event kind` 与 `version`
2. required/optional 字段
3. 字段类型与枚举值约束
4. 顺序约束与幂等键
5. 客户端未知字段/未知事件的处理约定

### 2.2 API 合同范围

纳入强制治理的 API 返回面：

1. 会话启动响应中的流能力声明字段。
2. chat stream 相关关键响应结构与错误结构。
3. replay / reconnect 所依赖的分页、游标、序列位点字段。

### 2.3 合同来源（Single Source of Truth）

建立单一合同来源，推荐结构：

1. `contracts/sse/*.json`：事件 schema 定义。
2. `contracts/api/*.json`：关键 API schema 定义。
3. `contracts/compatibility/rules.yaml`：兼容规则、版本策略、弃用窗口。

所有生产者与消费者测试均从该来源生成或读取，不允许手写重复 schema。

---

## 3. 兼容策略（Compatibility Policy）

### 3.1 版本语义（Versioning）

1. **Patch**：新增 optional 字段、放宽枚举、修正文案，不破坏旧客户端。
2. **Minor**：新增事件类型且旧客户端可忽略并继续运行。
3. **Major**：删除/重命名必填字段、变更字段语义、改变关键顺序约束。

### 3.2 破坏性变更判定（Breaking Change Rules）

以下变更默认判定为 breaking：

1. 删除 required 字段。
2. required 字段类型变化（如 string -> object）。
3. 事件顺序约束改变且影响渲染时序。
4. 错误结构关键字段缺失导致前端无法恢复。

### 3.3 老客户端容错约定（Backward Compatibility）

1. 未识别事件类型必须走 ignore + log，不得中断连接。
2. 未识别字段必须忽略，不得导致反序列化失败。
3. 关键未知事件可通过 `meta.compat_notice` 提供温和提示，但不阻断内容输出。

---

## 4. 测试门禁设计（Test Gates）

## Gate A：Golden Contract Tests

目标：验证 payload shape 与字段约束不漂移。

实施项：

1. 为 `meta/content/error/tool_event/trace_event` 建立 golden 样本。
2. 每次构建比对当前输出与 golden baseline。
3. 引入 allowlist 机制，仅在版本升级且审批通过时更新 golden。

验收标准：

1. 非版本升级 PR 无法更新 breaking 相关 golden。
2. contract diff 报告可读、可追踪到字段级别。

## Gate B：Replay Determinism Tests

目标：同一输入与同一 run seed 下，事件序列稳定一致。

实施项：

1. 固定输入、固定工具响应桩、固定随机种子。
2. 对比事件序列：kind、sequence、assistant_turn_id、event_id。
3. 加入去重断言，确保回放过程无重复消费副作用。

验收标准：

1. 同 run 多次 replay 结果一致。
2. 序列一致性失败时给出首个偏差事件定位。

## Gate C：Reconnect Compatibility Tests

目标：验证断流重连后续传事件衔接正确。

实施项：

1. 模拟不同断流点（早期、中段、尾段）重连。
2. 验证 `last_seen_sequence` / cursor 恢复后无丢失无重复。
3. 验证老客户端在重连时遇到未知事件不崩溃。

验收标准：

1. 重连后事件序列连续、可去重。
2. 老客户端兼容断言全部通过。

---

## 5. CI/CD 集成策略（Pipeline Integration）

### 5.1 PR 级别门禁

1. `contract-lint`：schema 语法与规则检查。
2. `contract-diff`：与主干基线比较并标注 breaking 风险。
3. `compat-tests`：运行 Gate A/B/C 的快速集。

PR 阻断规则：

1. breaking diff 且无版本升级说明 -> 阻断。
2. replay/reconnect 任一失败 -> 阻断。

### 5.2 Release Candidate 门禁

1. 全量 replay/reconnect 回归。
2. 多客户端版本兼容回归。
3. 产出 Contract Gate 报告并归档至发布记录。

### 5.3 紧急回滚策略

1. 保留 `CONTRACT_GATE_ENFORCE=false` 紧急开关，仅限事故恢复窗口使用。
2. 触发紧急开关后必须在 24 小时内补齐事故复盘与修复计划。

---

## 6. 实施阶段（Phased Rollout）

## Phase 0：盘点与建模 (✅ Completed)

1. 盘点现有 SSE/API 输出面与消费者解析路径。
2. 固化 schema 文件结构与版本字段规范。

交付物：

1. 合同目录骨架 (`backend/contracts/`)。
2. 初始 schema 清单 (`sse/*.json`, `api/*.json`)。

## Phase 1：Golden + Diff Gate (✅ Completed)

1. 建立 Golden Contract Tests。
2. 在 CI 接入 contract-diff 阻断。
3. 实现基础校验服务 `contract_gate.py` 并集成至 `chat.py`。

交付物：

1. Golden baseline。
2. `backend/app/services/contract_gate.py`。
3. 单元测试 `backend/tests/test_contract_gate_unit.py`。

## Phase 2：Replay/Reconnect 确定性门禁 (🟡 In Progress)

1. 实现 replay determinism 测试。
2. 实现 reconnect continuity 测试。

交付物：

1. Gate B/C 自动化测试。
2. 序列偏差定位日志。

## Phase 3：老客户端兼容与发布治理 (pending)

1. 增加 unknown event backward-compat 断言。
2. 接入 RC 级 Contract Gate 报告归档。

交付物：

1. 兼容回归报告。
2. 发布审批清单中的 Contract Gate 项。

---

## 7. 代码落点建议（File-Level Map）

以下为推荐落点，具体路径以当前仓库实际结构为准：

1. `backend/app/api/chat.py`  
   - 规范化事件封装与版本字段填充。
2. `backend/app/services/*stream*`  
   - 统一 sequence/event_id 生成与恢复逻辑。
3. `backend/tests/test_api_chat_unit.py`  
   - 加入事件 schema 与顺序断言。
4. `backend/tests/test_*replay*`  
   - 加入 replay determinism 回归。
5. `backend/tests/test_*reconnect*`  
   - 加入断流重连 continuity 与 dedup 回归。
6. `backend/contracts/`  
   - 存放合同定义与兼容规则。

---

## 8. 运营与审计（Operations & Audit）

### 8.1 指标（KPIs）

1. `contract_gate_block_count`
2. `replay_determinism_failure_rate`
3. `reconnect_dedup_failure_rate`
4. `unknown_event_client_failure_rate`

### 8.2 审计要求

1. 每次阻断需保留 diff 报告与责任人。
2. 每次版本升级需记录 breaking 说明、迁移指引、回滚路径。

---

## 9. 风险与缓解（Risks & Mitigations）

1. **风险：测试脆弱导致误报**  
   缓解：固定种子与工具桩，区分协议变化与模型随机性变化。

2. **风险：门禁过严影响迭代速度**  
   缓解：PR 快速集 + RC 全量集分层执行。

3. **风险：多端版本长期并存导致策略复杂**  
   缓解：设定客户端兼容窗口与强制升级阈值。

---

## 10. 完成定义（Definition of Done）

满足以下条件即视为 P0-1 落地完成：

1. SSE 与关键 API 均纳入统一合同来源并版本化管理。
2. Gate A/B/C 在 CI 与 RC 流程中强制执行。
3. breaking change 必须版本升级且有审计记录。
4. 老客户端未知事件兼容测试稳定通过。
5. 发布记录中可追溯每次 Contract Gate 结果与处置动作。
