# Yue Project Documentation Hub

本文档中心是 Yue AI 助手项目的完整知识库，提供架构设计、使用指南、执行计划、API 参考等全方位文档支持。

---

## 📚 文档分类导航

### 🌟 快速开始 (Start Here)

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [FEATURES.md](overview/FEATURES.md) | 功能特性概览 | 所有用户 |
| [PROJECT_REQUIREMENTS.md](overview/PROJECT_REQUIREMENTS.md) | 项目需求说明 | 开发者、决策者 |
| [ROADMAP.md](overview/ROADMAP.md) | 发展路线图 | 所有参与者 |
| [CONFIGURATION.md](guides/developer/CONFIGURATION.md) | 配置指南 | 开发者、运维 |

---

## 📂 文档目录结构

### 1. 📋 项目概览 ([overview/](overview/))
项目核心文档，快速了解 Yue 是什么、能做什么。

- **[FEATURES.md](overview/FEATURES.md)** - 功能特性全景图
- **[PROJECT_REQUIREMENTS.md](overview/PROJECT_REQUIREMENTS.md)** - 需求规格说明
- **[ROADMAP.md](overview/ROADMAP.md)** - 发展阶段与里程碑
- **[Quick Start](guides/developer/CONFIGURATION.md)** - 快速开始指南（待创建）

### 2. 📘 使用指南 ([guides/](guides/))
分角色的详细使用与开发指南。

#### 👤 最终用户指南 ([guides/user/](guides/user/))
- **[Agent Skills User Guide](guides/user/Agent_Skills_User_Guide.md)** - 智能体技能使用手册
- **Chat Usage Guide** - 聊天交互指南（待创建）
- **MCP Usage Guide** - MCP 工具使用指南（待创建）

#### 👨‍💻 开发者指南 ([guides/developer/](guides/developer/))
- **[CONFIGURATION.md](guides/developer/CONFIGURATION.md)** - 开发环境配置
- **[TESTING.md](guides/developer/TESTING.md)** - 测试框架与执行指南
- **[Azure OpenAI Intranet Config](guides/developer/Azure_OpenAI_Intranet_Config.md)** - 企业内网配置
- **Deployment Guide** - 部署指南（待创建）

#### 🔧 管理员指南 ([guides/admin/](guides/admin/))
- **Document Access Control** - 文档访问控制（待创建）
- **User Management** - 用户管理（待创建）
- **Backup & Recovery** - 备份与恢复（待创建）

### 3. 🏗️ 架构设计 ([architecture/](architecture/))
核心技术架构与设计决策。

- **[12-Factor App Guide](architecture/12_Factor_App_Guide.md)** - 云原生架构规范
- **[LLM Capability Inference](architecture/LLM_Capability_Inference_Architecture.md)** - 模型能力推理架构
- **[Skill Architecture Analysis](architecture/Skill_Architecture_Analysis_Report.md)** - 技能系统架构分析
- **[Architecture Decisions](architecture/decisions/)** - 架构决策记录 (ADR)

### 4. 📝 执行计划 ([plans/](plans/))
架构演进与功能开发的详细执行计划。

- **[INDEX.md](plans/INDEX.md)** - 🎯 **总控看板**（任务追踪中心）
- **[Active Plans](plans/active/)** - 进行中的 Epic（待迁移）
- **[Archive](plans/archive/)** - 已归档的历史计划

#### 核心 Epic 追踪
- Epic 4: [可观测性与执行透明化](plans/observability_transparency_plan.md)
- Epic 5: [消息交互与多模态增强](plans/multimodal_image_qa_enhancement_plan_20260317.md)
- Epic 6: [发布质量与工程门禁](plans/release_readiness_gate_execution_plan_20260314.md)
- Epic 7: [记忆与模型能力精细化管理](plans/hierarchical_memory_foundation_plan_20260315.md)
- Epic 8: [技能系统深度增强](plans/skill_creator_implementation_plan_20260319.md)
- Epic 9: [代码库健康与 God Object 重构](plans/codebase_refactor_plan_20260319.md)

### 5. 🔬 战略评估 ([assessments/](assessments/))
项目状态审计与战略调整报告。

- **[README](assessments/README.md)** - 评估文档说明
- **[Project Status Audit](assessments/Project_Status_Audit_20260319.md)** - 最新进度审计报告

### 6. 🐛 根本原因分析 ([rca/](rca/))
技术问题根因分析与最佳实践。

- **[RCA-001](rca/RCA-001-deepseek-reasoner-truncation.md)** - DeepSeek Reasoner 流式输出截断修复
- **[RCA-002](rca/RCA-002-streaming-parser-prefix-collision.md)** - 流式解析器前缀冲突问题
- **[Parsing Best Practices](rca/PARSING-BEST-PRACTICES.md)** - 解析最佳实践

### 7. 📊 调研报告 ([research/](research/))
技术选型与竞品分析报告。

- **[ADK vs PydanticAI](research/ADK_vs_PydanticAI_Comparison.md)** - Agent 框架对比
- **[Obsidian 2025 Features](research/Obsidian_2025_Features_Analysis_Report.md)** - Obsidian 功能分析
- **[Multi-Source Multi-Audience Framework](research/MultiSource_MultiAudience_Framework_Comparison_Report.md)** - 多源多受众框架对比
- **[Model Providers Race RCA](research/Model_Providers_500_Startup_Race_RCA.md)** - 模型供应商竞争分析

### 8. 🔌 API 文档 ([api/](api/))
后端 API 接口参考文档。

- **API Overview** - API 总览（待创建）
- **Endpoints** - 端点详情（待创建）
  - `POST /api/chat` - 聊天接口
  - `GET /api/agents` - 智能体管理
  - `GET /api/mcp/status` - MCP 状态
  - `POST /api/models/test/{provider}` - 模型测试
- **Schemas** - 数据结构定义（待创建）

### 9. ✅ 发布质量门禁 ([release/](release/))
发布审计与回滚演练文档。

- **[Phase 1 Gate Reports](release/phase1/gate_reports/)** - 发布审计报告
- **[Rollback Drills](release/phase1/rollback_drills/)** - 回滚演练记录
- **[Phase 2 Threshold Notes](release/phase2_threshold_friction_notes.md)** - 阈值摩擦分析

---

## 🔍 快速查找索引

### 按主题查找

**智能体 (Agents)**
- [Agent Skills User Guide](Agent_Skills_User_Guide.md) - 用户手册
- [Skill Architecture Analysis](architecture/Skill_Architecture_Analysis_Report.md) - 架构分析
- [Skill Creator Plan](plans/skill_creator_implementation_plan_20260319.md) - 实现计划
- [Agent Classification Plan](plans/archive/agent_classification_and_skill_group_plan_20260319.md) - 分类重构

**模型与 Provider**
- [LLM Capability Inference](architecture/LLM_Capability_Inference_Architecture.md) - 能力推理
- [Providers API Refactoring](plans/llm_providers_api_refactoring_plan.md) - API 重构
- [ADK vs PydanticAI](research/ADK_vs_PydanticAI_Comparison.md) - 框架对比

**MCP 工具**
- [Builtin Tools Refactor](plans/archive/builtin_tools_refactor_plan.md) - 内置工具重构
- [OpenClaw Tool Calling](plans/openclaw_tool_calling_reference_execution_plan_20260308.md) - 参考执行

**记忆系统**
- [Hierarchical Memory Plan](plans/hierarchical_memory_foundation_plan_20260315.md) - 分层记忆设计

**文件与存储**
- [File Management Improvement](plans/File_Management_Improvement_Review.md) - 文件管理重构
- [Document Access Control](plans/document_access_control_enhancement_plan_20260323.md) - 访问控制

**代码重构**
- [Codebase Refactor Plan](plans/codebase_refactor_plan_20260319.md) - 整体重构计划
- [Chat API Simplification](plans/chat_api_stream_simplification_plan_20260322.md) - 聊天 API 简化
- [Settings.tsx Modularization](plans/settings_tsx_modularization_plan_20260323.md) - 前端组件拆分

---

## 📐 文档规范

### 命名约定
- **文件名**: 使用小写 + 中划线（kebab-case），如 `multimodal-enhancement-plan.md`
- **日期格式**: `YYYY-MM-DD` 或 `YYYYMMDD`（统一使用一种格式）
- **计划文档**: `<主题>-plan-<日期>.md` 或 `<日期>-<主题>-plan.md`
- **RCA 文档**: `RCA-<序号>-<主题>.md`

### 文档元数据（推荐）
在文档顶部添加 Frontmatter 便于管理：
```yaml
---
title: 文档标题
category: guides/developer
status: active | archived | draft
last_updated: 2026-03-24
related: [plan1.md, plan2.md]
---
```

### 状态说明
- **active**: 正在进行或当前有效
- **archived**: 已归档（历史参考）
- **draft**: 草稿阶段

---

## 🤖 AI 协作指南

### 开始新任务
1. 首先阅读 [plans/INDEX.md](plans/INDEX.md) 了解整体架构演进路线
2. 选择对应的 Epic 和 Phase 计划文档
3. 使用以下 Prompt 驱动 AI：

```
请阅读 `docs/plans/INDEX.md` 和对应的 `[Plan_Name].md`，
我们将开始执行 `[Epic Name]` 下的 `[Phase X]` 任务。
请先分析代码现状，然后给出你的修改方案，确认后直接改代码。
```

### 文档更新流程
1. 修改文档后更新 [INDEX.md](plans/INDEX.md) 中的状态
2. 已完成的计划移至 `archive/` 目录
3. 在 [assessments/](assessments/) 中记录重大决策

---

## 📊 文档统计

| 分类 | 文档数量 | 状态 |
|------|---------|------|
| 概览 | 3 | ✅ 稳定 |
| 指南 | 5+ | 🔄 完善中 |
| 架构 | 3 | ✅ 稳定 |
| 计划 | 20+ | 🔄 活跃更新 |
| 评估 | 1+ | 📝 定期审计 |
| RCA | 3 | ✅ 稳定 |
| 调研 | 4 | ✅ 稳定 |
| API | 0 | ⏳ 待创建 |

---

## 🔗 相关链接

- **项目根目录**: [../](../)
- **后端代码**: [../backend/](../backend/)
- **前端代码**: [../frontend/](../frontend/)
- **测试指南**: [guides/developer/TESTING.md](guides/developer/TESTING.md)
- **配置说明**: [guides/developer/CONFIGURATION.md](guides/developer/CONFIGURATION.md)

---

**最后更新**: 2026-03-24  
**维护者**: Yue Project Team
