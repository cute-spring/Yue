# 分层记忆基础 (Short-Term + Long-Term) 执行计划

## 1. 背景与目标 (P0-5)

### 1.1 背景
目前，聊天系统依赖于固定窗口的历史记录或基本的 Token 感知截断。随着会话的增长，会出现 Context 丢失，导致“推理漂移（Reasoning Drift）”和用户重复纠正。此外，由于 Agent 在对话之间会忘记用户偏好和特定项目的 Fact，因此也缺乏跨会话的连续性。

### 1.2 目标
建立一个生产安全的 Memory 基础，结合即时的 Context 感知和持久的 Fact 保留：
1. **Short-Term Memory (STM)**：为活跃会话维护滚动摘要和关键 Fact，以保护 Token 预算并保持推理质量。
2. **Long-Term Memory (LTM)**：持久化跨会话的 Fact、偏好和项目 Context。
3. **Memory Governance**：实施严格的写/读策略，防止幻觉 Fact 污染 Memory 存储。

### 1.3 成功标准
1. **更低的 Context 丢失率**：通过减少长会话中“我不记得”的回答来衡量。
2. **跨会话连续性**：Agent 能够回忆起之前会话中的核心用户偏好。
3. **可审计的写入**：每次 Memory 写入都有 Provenance（来源消息/会话）和置信度评分（Confidence Score）。
4. **稳定的性能**：LTM 的检索延迟保持在 P95 < 100ms。

---

## 2. 记忆架构 (Memory Architecture)

### 2.1 Short-Term Memory (STM)
- **机制**：滚动摘要 (Rolling Summary) + Turn 级别关键事实 (Key Facts)。
- **触发条件**：当会话 Context 超过 20k tokens 时。
- **输出**：注入系统提示词 (System Prompt) 的结构化摘要块。

### 2.2 Long-Term Memory (LTM)
- **机制**：基于 SQLite 的事实存储，支持向量搜索 (Vector Search, 可选/未来) 或基于关键词的检索。
- **Schema**：
  - `memory_id`: UUID
  - `category`: Fact, Preference, ProjectContext
  - `content`: 文本内容
  - `confidence`: 0.0 - 1.0
  - `provenance`: message_id 或 session_id
  - `decay_score`: 重要性因子（如果不被引用，随时间衰减）
  - `last_referenced_at`: 时间戳

---

## 3. 分阶段实现 (Phased Implementation)

### Phase 1: Short-Term Rolling Summary (MVP)
- 实现 `backend/app/services/memory/stm_service.py`。
- 使用当前 Provider 的“快速”模型（如 GPT-4o-mini 或 DeepSeek-V3）添加 Summarization 逻辑。
- 将 STM 接入 `chat_service.py` 的 Context 组装流程。

### Phase 2: Long-Term Memory Schema & Persistence
- 创建 `backend/app/models/memory.py` (SQLAlchemy)。
- 实现 `backend/app/services/memory/ltm_service.py` 用于 CRUD 操作。
- 在设置中添加手动 Memory 管理 UI（查看/删除记忆）。

### Phase 3: Retrieval & Decay Policy
- 实现基于相关性的检索（评分 = Semantic Similarity * Importance * Decay）。
- 添加“遗忘”逻辑：自动归档或删除低置信度、低相关性的记忆。

### Phase 4: Memory Governance (Write/Read Policy)
- **写入策略 (Write Policy)**：仅存储置信度 > 0.8 的事实。每个存储的事实都要求提供引用 (Citation)。
- **读取策略 (Read Policy)**：每次对话限制检索 Top-3 最相关的记忆，以节省 Context Tokens。

---

## 4. 治理与安全 (Governance & Safety)

- **隐私 (Privacy)**：未经用户明确同意，LTM 中不得包含 PII (个人身份信息)。
- **可逆性 (Reversibility)**：用户可以随时清除 STM 或 LTM。
- **偏见缓解 (Bias Mitigation)**：定期审计 Memory 是否存在偏见或幻觉模式。

---

## 6. 与 Mem0 开源框架的对比 (Comparison with Mem0 Open Source Framework)

为了确保为 Yue 选择的技术路径是最佳的，我们将此分层记忆计划与领先的开源记忆框架 **Mem0** 进行了对比。

### 6.1 功能对比表 (Feature Comparison Table)

| 功能 | Mem0 (开源版) | Yue 分层记忆 (本地计划) |
| :--- | :--- | :--- |
| **复杂度** | 高 (完整框架，多组件) | 低到中 (基于服务，集成式) |
| **架构** | Client-Server / SDK, 混合架构 (Vector + SQL) | 集成服务, 以 SQLite 为中心 |
| **记忆提取** | 基于 LLM，内置冲突解决 | 基于 LLM，置信度与引用驱动 |
| **短期记忆** | 基础滚动 Context | 滚动摘要 + 关键事实 (Token 感知触发) |
| **长期记忆** | 语义/向量 + 图 (Mem0-G) | 关键词/向量 (未来) + SQLite 事实存储 |
| **治理** | Metadata, 多用户作用域 | 置信度评分, Provenance, 衰减, PII 规则 |
| **基础设施** | 需要向量数据库 (Qdrant/LanceDB) | 零额外基础设施 (复用项目 SQLite) |
| **性能** | 可扩展, 默认异步 | 集成式, 目标 P95 延迟 < 100ms |

### 6.2 为什么 Yue 选择本地计划而非 Mem0

1. **基础设施简单性**：Mem0 通常需要一个独立的向量数据库（如 Qdrant 或 LanceDB）才能完全发挥功能。Yue 的本地计划利用现有的 SQLite 基础设施，降低了自托管用户的运维开销。
2. **治理与安全**：本地计划优先考虑“可审计的写入”，对存储的每个事实都有明确的置信度评分 (>0.8) 和强制引用要求。这种级别的严格治理在定制化服务中比包装通用框架更容易实施。
3. **Token 效率**：Yue 的 STM (短期记忆) 特别包含了 Token 感知的滚动摘要（在 20k tokens 时触发），这针对项目的特定聊天 Context 管理需求进行了高度优化。
4. **集成深度**：通过直接在 `backend/app/services/memory/` 包中构建 `stm_service.py` 和 `ltm_service.py`，我们确保了与现有 `chat_service.py` 和 `model_factory.py` 的无缝集成，而无需引入外部 API 依赖。

### 6.3 潜在的未来集成
虽然 MVP 将遵循本地计划，但如果记忆之间的复杂关系推理成为核心需求，我们仍对在 Phase 4 集成 Mem0 的 **图记忆 (Mem0-G)** 概念持开放态度。

### 6.4 使用 Mem0 的典型场景
- **长期陪伴式助手**：与用户跨天或跨周交互的助手，必须记住稳定的偏好、重复出现的目标和历史决策。
- **客户支持代理**：受益于回忆之前的工单、故障排除步骤和特定账户 Context 的服务机器人，以减少重复提问。
- **销售与成功副驾驶**：维护客户画像、沟通偏好和跟进里程碑的代理，以提高连续性和转化结果。
- **企业知识助手**：跨会话持久保留团队术语、项目惯例和工作流模式的内部副驾驶。
- **多代理协作系统**：多个代理需要共享长期记忆以协调任务，而无需反复从零开始构建 Context 的架构。

### 6.5 Mem0 在这些场景中通常带来的收益
- **跨会话连续性**：保留超出单一聊天窗口的重要用户和项目 Context。
- **降低 Token 成本**：用记忆检索取代全量历史提示词填充，提高长对话的 Token 效率。
- **更高的个性化质量**：通过保留持久偏好，改进推荐和响应风格的对齐。
- **更好的响应一致性**：通过将响应植根于持久记忆，减少矛盾的回答。
- **可扩展的记忆分层**：随着产品需求演进，支持逐步升级（重排序 Rerank、图记忆 Graph Memory、高级检索）。

### 6.6 Yue 落地建议：哪些优先采用 Mem0，哪些保留本地
- **优先采用 Mem0 (高 ROI 模块)**：
  - 跨会话用户偏好记忆（语气/风格、重复偏好、持久的个人设置）。
  - 在会话和代理之间共享的客户/项目画像记忆。
  - 多代理共享记忆检索，其中协作价值高且重复构建 Context 成本高。
- **优先保留本地策略 (当前 Yue 的优势)**：
  - 已与 `chat_service.py` 集成的会话内 STM 滚动摘要流水线及 Token 预算控制。
  - 在持久化之前需要严格置信度阈值和引用门禁的治理关键性写入。
  - 优先考虑极简基础设施和 SQLite 优先操作的本地或合规敏感型部署。
- **当前阶段推荐的混合路径**：
  - Phase A: 保持 STM 本地化，仅在一个受限的工作流中针对非敏感偏好记忆试点 Mem0。
  - Phase B: 增加检索质量监控（记忆命中率的精确度/召回率、矛盾率、延迟 P95），并与本地基线进行对比。
  - Phase C: 如果质量和延迟目标持续达成，将 Mem0 范围扩大到共享项目记忆。
  - Phase D: 为故障期间的 Fail-open 行为保留显式的本地检索回退开关。

---

## 7. 立即执行的后续行动
1. 初始化 `backend/app/services/memory/` 包。
2. 为 LTM 定义 SQLite Schema。
3. 在 `chat_service.py` 中实现第一版滚动摘要触发器。
