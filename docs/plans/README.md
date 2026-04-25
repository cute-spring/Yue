# Architecture Evolution Plans - 架构演进计划

本目录是 Yue 项目架构演进与功能开发的核心计划管理中心，所有复杂的架构调整和重要功能开发都应先在这里记录为 Epic，并链接到具体的 Plan 文档。

---

## 📊 计划管理结构

```
plans/
├── INDEX.md                           # 🎯 总控看板（任务追踪中心）
├── README.md                          # 本文件：计划管理说明
├── active/                            # 进行中的 Epic（待迁移）
│   ├── Epic4-observability.md
│   ├── Epic5-multimodal.md
│   └── Epic6-quality-gates.md
├── completed/                         # 已完成的 Epic（可选）
└── archive/                           # 已归档的历史计划
    ├── Database_Evolution_Plan.md
    ├── Logging_Config_Evolution_Plan.md
    └── ...
```

---

## 🎯 总控看板 (INDEX.md)

**[INDEX.md](INDEX.md)** 是项目架构演进的**单一事实来源** (Single Source of Truth)，包含：

### 当前状态概览

| 状态 | Epic 数量 | 说明 |
|------|----------|------|
| 🟢 In Progress | 4 | Epic 4, 5, 6, 8 正在推进中 |
| 🟡 Todo | 5 | Epic 3, 7, 9, 10 等待启动 |
| ✅ Done | 6 | Epic 1, 2 等已完成 |

### Epic 追踪

#### 进行中 (In Progress)

- **Epic 4**: [可观测性与执行透明化](observability_transparency_plan.md) - 90%
- **Epic 5**: [消息交互与多模态增强](multimodal_image_qa_enhancement_plan_20260317.md) - 60%
- **Epic 6**: [发布质量与工程门禁](release_readiness_gate_execution_plan_20260314.md) - 85%
- **Epic 8**: [Skill Import Gate 与 Runtime 路由增强](INDEX.md) - 总体约96%（Stage 4-Lite 约95%）

#### 待启动 (Todo)

按优先级排序：

1. **Epic 3**: [文件管理与存储抽象层重构](File_Management_Improvement_Review.md)
2. **Epic 7**: [记忆与模型能力精细化管理](hierarchical_memory_foundation_plan_20260315.md)
3. **Epic 9**: [代码库健康与 God Object 重构](codebase_refactor_plan_20260319.md)
4. **Epic 10**: [聊天历史与用户体验优化](2026-03-26-chat-history-management-improvement-plan.md)

#### 已完成 (Done)

- ✅ **Epic 1**: 配置与日志的云端演进
- ✅ **Epic 2**: 数据库架构演进
- ✅ **Agent 种类与技能组重构**
- ✅ **内置工具架构重构**
- ✅ **Markdown 技能系统实现**
- ✅ **技能架构长线演进与清理**

---

## 📝 计划文档分类

### 按领域分类

#### 基础设施层
- [12-Factor 合规](../architecture/12_Factor_App_Guide.md) - 云原生架构
- [日志架构演进](archive/Logging_Config_Evolution_Plan.md) ✅
- [数据库演进](archive/Database_Evolution_Plan.md) ✅
- [文件存储抽象](File_Management_Improvement_Review.md) 🟡

#### 业务逻辑层
- [多模态增强](multimodal_image_qa_enhancement_plan_20260317.md) 🟢
- [消息导出](2026-03-20-message-export-plan.md) 🟢
- [记忆系统](hierarchical_memory_foundation_plan_20260315.md) 🟡

#### 架构治理层
- [可观测性](observability_transparency_plan.md) 🟢
- [发布门禁](release_readiness_gate_execution_plan_20260314.md) 🟢
- [代码重构](codebase_refactor_plan_20260319.md) 🟡

#### 技能系统
- [Yue Skill Strategy](../research/skills_gap_comparison_and_roadmap_20260421.md) ✅
- [Skill Import Runtime Execution Plan](./skill_import_runtime_execution_plan_20260421.md) 🟢
- [Skill Import Gate Implementation Design](./skill_import_gate_implementation_design_20260421.md) 🟢
- [Skill Import Gate API Contract](./skill_import_gate_api_contract_20260421.md) 🟢
- [Skill Runtime Core Externalization Plan](./skill_runtime_core_externalization_plan_20260423.md) 🟢
- 当前执行口径：最小可用优先（directory 导入 + 内部研发调试可用 + 单一路由入口）；Stage 4-Lite 已进入最后收口（provider/container seam + hybrid 门禁矩阵 + runtime context 取依赖），但 `skill_service.py` 全局兼容壳层与 legacy/import-gate 双轨运行面仍待完全收敛；Stage 5 externalization 工作 deferred。
- 最新回归证据：Epic 8 Stage 4-Lite closeout 回归已更新为 `77 passed / 146 passed`，与 `INDEX.md`、execution plan、implementation design 保持一致。

---

## 🔄 计划生命周期

### 1. 提案阶段 (Proposal)

当识别到需要架构演进或重要功能开发时：

1. 创建计划文档：`<主题>-plan-<日期>.md`
2. 在 [INDEX.md](INDEX.md) 的 Todo 区域添加 Epic 条目
3. 描述背景、目标、范围和预期收益

### 2. 审批阶段 (Review)

1. 与决策者 review 计划文档
2. 确定优先级和排期
3. 在 [assessments/](../assessments/) 中记录决策

### 3. 执行阶段 (In Progress)

1. 将 Epic 移至 INDEX.md 的 In Progress 区域
2. 按 Phase 逐步实施
3. 更新完成度百分比

### 4. 完成阶段 (Done)

1. 所有 Phase 完成后，标记 Epic 为✅ Done
2. 可选：移至 `completed/` 目录
3. 在 [assessments/](../assessments/) 中记录完成审计

### 5. 归档阶段 (Archive)

对于不再执行或已过时的计划：
1. 移至 `archive/` 目录
2. 在 INDEX.md 中更新状态为"已归档"
3. 添加归档原因说明

---

## 📋 计划文档模板

```markdown
# Epic X: 计划标题

## 背景 (Context)
为什么需要这个演进？解决什么问题？

## 目标 (Goals)
- 目标 1
- 目标 2

## 范围 (Scope)
### 包含
- 功能 1
- 功能 2

### 不包含
- 明确排除的内容

## 技术方案 (Technical Approach)
### 架构设计
架构图、组件说明等。

### 实施步骤
1. Phase 1: ...
2. Phase 2: ...
3. Phase 3: ...

## 依赖关系 (Dependencies)
- 依赖的 Epic 或外部因素

## 风险与缓解 (Risks & Mitigation)
| 风险 | 严重程度 | 缓解措施 |
|------|----------|----------|

## 验收标准 (Acceptance Criteria)
- [ ] 标准 1
- [ ] 标准 2

## 测试计划 (Testing Plan)
- 单元测试
- 集成测试
- E2E 测试

## 文档更新 (Documentation Updates)
- [ ] FEATURES.md
- [ ] API 文档
- [ ] 用户指南

## 参考资源 (References)
- 相关链接、文档、RFC 等
```

---

## 🤖 AI 协作指南

### 开始执行 Epic

复制以下 Prompt 发送给 AI 即可开始工作：

```
请阅读 `docs/plans/INDEX.md` 和对应的 `[Plan_Name].md`，
我们将开始执行 `[Epic Name]` 下的 `[Phase X]` 任务。
请先分析代码现状，然后给出你的修改方案，确认后直接改代码。
```

### 示例

**执行多模态增强 Phase 1**:
```
请阅读 `docs/plans/INDEX.md` 和 `multimodal_image_qa_enhancement_plan_20260317.md`，
我们将开始执行 Epic 5 下的 Phase 1: 后端治理内核 任务。
请先分析代码现状，然后给出你的修改方案，确认后直接改代码。
```

**执行代码重构**:
```
请阅读 `docs/plans/INDEX.md` 和 `codebase_refactor_plan_20260319.md`，
我们将开始执行 Epic 9 下的 Phase 1: 后端重构 (chat/doc) 任务。
```

---

## 📊 执行顺序建议

INDEX.md 中建议的执行顺序（从易到难、从底层到上层）：

```
1. Epic 3: 文件存储抽象（基础层）
   ↓
2. Epic 7: 记忆系统（业务层）
   ↓
3. Epic 8: 技能增强（应用层）
   ↓
4. Epic 9: 代码重构（健康度）
```

**理由**:
- 先解决底层存储问题，避免后续返工
- 记忆系统独立性强，可并行开发
- 技能系统依赖底层稳定性
- 代码重构是持续性工作

---

## 📈 进度追踪

### 更新频率

- **每日**: 更新进行中的 Phase 完成度
- **每周**: 更新 Epic 整体状态
- **每月**: 在 [assessments/](../assessments/) 中生成审计报告

### 状态标识

| 标识 | 含义 | 使用场景 |
|------|------|----------|
| 🟢 | 进行中 | 当前正在执行的 Epic |
| 🟡 | 待启动 | 已规划但未开始的 Epic |
| ✅ | 已完成 | 所有 Phase 已完成的 Epic |
| ⏸️ | 已暂停 | 因优先级调整暂时搁置 |
| 🗄️ | 已归档 | 不再执行或已过时 |

---

## 🔗 相关链接

- [项目总览](../README.md)
- [战略评估](../assessments/) - 优先级决策
- [架构设计](../architecture/) - 技术参考
- [使用指南](../guides/) - 开发规范

---

**最后更新**: 2026-04-23  
**维护者**: Yue Project Team
