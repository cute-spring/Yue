# 🚀 Yue Project: Architecture Evolution Backlog (总控看板)

> **关于此看板：**
> 这是本项目的架构演进与核心功能重构的总控中心（Backlog）。所有的复杂架构调整都应该先在这里记录为一个 Epic，并链接到具体的 Plan 文档。
> **AI 协作指南：** 在开启新的对话时，请先让 AI 读取此文件以恢复系统演进的上下文状态。

---

## 🟢 In Progress (进行中)
*(暂无)*

---

## 🟡 Todo (待办架构演进)

*建议按照以下顺序（从易到难、从底层到上层）逐步实施：*

### Epic 1: 配置与日志的云端演进 (基础建设)
> **状态**: 待启动
> **详情文档**: [Logging_Config_Evolution_Plan.md](./Logging_Config_Evolution_Plan.md)
> **目标**: 彻底解耦本地配置和日志文件，为容器化和多实例部署扫清障碍。
- [ ] **Phase 1: 环境变量注入改造** (将硬编码和本地配置文件读取，重构为优先读取 `os.environ`)
- [ ] **Phase 2: 日志流式改造** (停止写本地 `.log` 文件，改为结构化输出到 `stdout/stderr`)

### Epic 2: 数据库架构演进 (核心数据层)
> **状态**: 待启动
> **详情文档**: [Database_Evolution_Plan.md](./Database_Evolution_Plan.md)
> **目标**: 解决 SQLite 的并发和无状态部署瓶颈，引入 ORM 实现方言解耦。
- [ ] **Phase 1: 引入 ORM 框架** (选型并集成 SQLAlchemy / Prisma)
- [ ] **Phase 2: 数据访问层 (DAO) 重构** (将原生 SQL 替换为 ORM 模型)
- [ ] **Phase 3: 引入数据库迁移工具** (集成 Alembic 等 Migration 工具)

### Epic 3: 文件管理与存储抽象层重构 (业务逻辑层)
> **状态**: 待启动
> **详情文档**: [File_Management_Improvement_Review.md](./File_Management_Improvement_Review.md)
> **目标**: 解决本地物理路径强耦合，引入 `yue://` 虚拟路径，支持 S3 等云存储。
- [ ] **Phase 1: 规范本地存储目录** (统一迁移到 `~/.yue/upload` 结构)
- [ ] **Phase 2: 建立 Storage Provider 抽象层** (实现 LocalStorage 与 S3Storage 适配器)
- [ ] **Phase 3: 数据库路径虚拟化改造** (将 DB 中的物理路径替换为 `yue://` 协议)
- [ ] **Phase 4: Agent 工具重构** (改造 CLI 工具与 Tool-use，适配虚拟路径解析)

---

## ⚪ Done (已完成)
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