# 🚀 Yue Project: Architecture Evolution Backlog (总控看板)

> **关于此看板：**
> 这是本项目的架构演进与核心功能重构的总控中心（Backlog）。所有的复杂架构调整都应该先在这里记录为一个 Epic，并链接到具体的 Plan 文档。
> **AI 协作指南：** 在开启新的对话时，请先让 AI 读取此文件以恢复系统演进的上下文状态。

---

## 🟢 In Progress (进行中)

### Epic 4: 可观测性与执行透明化 (Observability & Transparency)
> **状态**: 推进中 (约 90%)
> **详情文档**: [observability_transparency_plan.md](./observability_transparency_plan.md)
> **目标**: 建立工具调用面板、任务思维链可视化和实时耗时统计，提升 Agent 执行的可信度。
- [x] **Phase 1: 事件契约标准化** (建立统一的 Event Envelope)
- [x] **Phase 2: 助手回合 (Turn) 绑定** (解决历史回放错位问题)
- [ ] **Phase 3: 前端幂等状态机** (重连场景去重与稳定排序)
- [ ] **Phase 4: 历史回放接口闭环** (流式与回放完全同构)

### Epic 5: 消息交互与多模态增强 (Interaction & Multimodal)
> **状态**: 推进中 (约 60%)
> **详情文档**: [multimodal_image_qa_enhancement_plan_20260317.md](./multimodal_image_qa_enhancement_plan_20260317.md)
> **目标**: 升级图片问答体验，支持仅图片提问、视觉能力门禁与消息导出。
- [x] **Phase 1: 后端治理内核** (图片校验、标准化与 vision 判定)
- [x] **Phase 2: 流式 meta 契约扩展** (透传 vision_enabled 状态)
- [ ] **Phase 3: 仅图片发送支持** (前端发送逻辑重构)
- [ ] **Phase 4: 消息导出功能** (见 [2026-03-20-message-export-plan.md](./2026-03-20-message-export-plan.md))

### Epic 6: 发布质量与工程门禁 (Quality & Release Gates)
> **状态**: 推进中 (约 85%)
> **详情文档**: [release_readiness_gate_execution_plan_20260314.md](./release_readiness_gate_execution_plan_20260314.md)
> **目标**: 建立标准化的 go/no-go 审计流程，包含风险评分与强制回滚演练。
- [x] **Phase 1: 手动审计基线** (完成首批 3 份 Gate Report)
- [x] **Phase 2: 自动化脚本集成** (实现 `check_gate_completeness.py`)
- [ ] **Phase 3: 统一契约门禁 (Contract Gate)** (见 [unified_contract_gate_execution_plan_20260314.md](./unified_contract_gate_execution_plan_20260314.md))

---

## 🟡 Todo (待办架构演进)

*建议按照以下顺序（从易到难、从底层到上层）逐步实施：*

### Epic 3: 文件管理与存储抽象层重构 (业务逻辑层)
> **状态**: 待启动
> **详情文档**: [File_Management_Improvement_Review.md](./File_Management_Improvement_Review.md)
> **目标**: 解决本地物理路径强耦合，引入 `yue://` 虚拟路径，支持 S3 等云存储。
- [ ] **Phase 1: 规范本地存储目录** (统一迁移到 `~/.yue/upload` 结构)
- [ ] **Phase 2: 建立 Storage Provider 抽象层** (实现 LocalStorage 与 S3Storage 适配器)
- [ ] **Phase 3: 数据库路径虚拟化改造** (将 DB 中的物理路径替换为 `yue://` 协议)
- [ ] **Phase 4: Agent 工具重构** (改造 CLI 工具与 Tool-use，适配虚拟路径解析)

### Epic 7: 记忆与模型能力精细化管理 (Memory & Capabilities)
> **状态**: 待启动
> **详情文档**: [hierarchical_memory_foundation_plan_20260315.md](./hierarchical_memory_foundation_plan_20260315.md)
> **目标**: 建立层级记忆系统 (STM/LTM)，并优化模型能力判定与 UI 展示。
- [ ] **Phase 1: 短期滚动摘要 (STM) MVP** (缓解长会话上下文丢失)
- [ ] **Phase 2: 模型能力精细化管理 (UI)** (见 [ui_capability_management_plan_plan.md](./ui_capability_management_plan_plan.md))
- [ ] **Phase 3: Providers API 重构** (见 [llm_providers_api_refactoring_plan.md](./llm_providers_api_refactoring_plan.md))

### Epic 8: 技能系统深度增强 (Skills Deep Dive)
> **状态**: 待启动
> **详情文档**: [skill_creator_implementation_plan_20260319.md](./skill_creator_implementation_plan_20260319.md)
> **目标**: 建立 Skill Creator 内置 Agent，并补齐 PPT/Nanobot 等领域技能差距。
- [ ] **Phase 1: Skill Creator 实现** (AI 驱动的技能生成工作流)
- [ ] **Phase 2: PPT 技能加固** (见 [ppt_skill_gap_enhancement_plan_20260307.md](./ppt_skill_gap_enhancement_plan_20260307.md))
- [ ] **Phase 3: Nanobot 技能演进** (见 [nanobot_skill_gap_plan_20260307.md](./nanobot_skill_gap_plan_20260307.md))

### Epic 9: 代码库健康与 God Object 重构 (Refactoring)
> **状态**: 待启动
> **详情文档**: [codebase_refactor_plan_20260319.md](./codebase_refactor_plan_20260319.md)
> **目标**: 拆解 `chat.py` 和 `Settings.tsx` 等超过 500 行的庞大组件。
- [ ] **Phase 1: 后端重构 (chat/doc)** (模块化拆解核心服务)
- [ ] **Phase 2: 前端重构 (Settings/MessageItem)** (组件级解耦)

---

## ⚪ Done (已完成)
- [x] **Epic 2: 数据库架构演进 (核心数据层)** (见 [archive/Database_Evolution_Plan.md](./archive/Database_Evolution_Plan.md))
- [x] **Epic 1: 配置与日志的云端演进** (见 [archive/Logging_Config_Evolution_Plan.md](./archive/Logging_Config_Evolution_Plan.md))
- [x] **架构演进可行性与依赖关系分析** (完成了日志、数据库、文件管理的拆解与评估)
- [x] **建立 AI 驱动的工程管理最佳实践** (见 [archive/AI_Driven_Project_Management_Best_Practices.md](./archive/AI_Driven_Project_Management_Best_Practices.md))
- [x] **Agent 种类与技能组重构** (见 [archive/agent_classification_and_skill_group_plan_20260319.md](./archive/agent_classification_and_skill_group_plan_20260319.md))
- [x] **内置工具架构重构** (见 [archive/builtin_tools_refactor_plan.md](./archive/builtin_tools_refactor_plan.md))
- [x] **Markdown 技能系统实现 (Phase 6.2)** (见 [archive/markdown_defined_skills_plan.md](./archive/markdown_defined_skills_plan.md))
- [x] **技能架构长线演进与清理** (见 [archive/skills_long_term_architecture_and_legacy_removal_plan_20260317.md](./archive/skills_long_term_architecture_and_legacy_removal_plan_20260317.md))

---

## 💡 How to use (如何驱动 AI 推进工作)
复制以下 Prompt 发送给 AI 即可开始工作：
> "请阅读 `docs/plans/INDEX.md` 和对应的 `[Plan_Name].md`，我们将开始执行 `[Epic Name]` 下的 `[Phase X]` 任务。请先分析代码现状，然后给出你的修改方案，确认后直接改代码。"