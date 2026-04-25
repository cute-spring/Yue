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
> **目标**: 升级图片问答体验，支持仅图片提问、视觉能力门禁、文件上传与消息导出。
- [x] **Phase 1: 后端治理内核** (图片校验、标准化与 vision 判定)
- [x] **Phase 2: 流式 meta 契约扩展** (透传 vision_enabled 状态)
- [ ] **Phase 3: 仅图片发送支持** (前端发送逻辑重构)
- [ ] **Phase 4: 消息导出功能** (见 [2026-03-20-message-export-plan.md](./2026-03-20-message-export-plan.md))
- [ ] **Phase 5: 文件上传集成** (见 [upload_file_integration_plan_20260324.md](./upload_file_integration_plan_20260324.md))
- [ ] **Phase 5A: 聊天附件上传与 Excel/PDF 可读能力落实** (见 [2026-04-19-chat-attachment-file-support-execution-plan.md](./2026-04-19-chat-attachment-file-support-execution-plan.md))

### Epic 6: 发布质量与工程门禁 (Quality & Release Gates)
> **状态**: 推进中 (约 85%)
> **详情文档**: [release_readiness_gate_execution_plan_20260314.md](./release_readiness_gate_execution_plan_20260314.md)
> **目标**: 建立标准化的 go/no-go 审计流程，包含风险评分与强制回滚演练。
- [x] **Phase 1: 手动审计基线** (完成首批 3 份 Gate Report)
- [x] **Phase 2: 自动化脚本集成** (实现 `check_gate_completeness.py`)
- [ ] **Phase 3: 统一契约门禁 (Contract Gate)** (见 [unified_contract_gate_execution_plan_20260314.md](./unified_contract_gate_execution_plan_20260314.md))

### Epic 8: Skill Import Gate 与 Runtime 路由增强
> **状态**: 推进中 (总体约 96%)
> **策略文档**: [../research/skills_gap_comparison_and_roadmap_20260421.md](../research/skills_gap_comparison_and_roadmap_20260421.md)
> **执行计划**: [skill_import_runtime_execution_plan_20260421.md](./skill_import_runtime_execution_plan_20260421.md)
> **实施设计包**: [skill_import_gate_implementation_design_20260421.md](./skill_import_gate_implementation_design_20260421.md)
> **API 契约**: [skill_import_gate_api_contract_20260421.md](./skill_import_gate_api_contract_20260421.md)
> **目标**: 将 Yue 收敛为 Agent Skills 标准 skill 的导入、验收、激活、选择和运行平台；当前坚持最小可用优先（internal dev first）。
> **子项进度**: Stage 1 约 98% | Stage 2 约 97% | Stage 3-Lite 约 95% | Stage 4-Lite 约 95% | Stage 5-Lite 约 25%（full extraction deferred，已落地最小 boundary manifest）
> **当前下一步**: 继续推进 Stage 4-Lite 收口（聚焦 `skill_service.py` provider/container 边界进一步收敛与剩余全局兼容 seam 退场），并维持 hybrid 运行面收敛门禁回归。
- [x] **Phase 1: Skill Import Gate** (约 98%；`import_models/import_store/import_service`、`/api/skill-imports`、重启恢复 smoke 已落地)
- [x] **Phase 2: Runtime 路由 Lite** (约 96%；默认最小响应契约稳定，debug 字段仅在诊断开关下返回)
- [x] **Phase 3: 标准对齐清理** (约 95%；旧细粒度 runtime flag 叙事清理完成，保留 `test_config_service_unit.py` 负向断言白名单)
- [x] **本轮收口结果（2026-04-23）**
- [x] `POST /api/skill-imports` 已增加 `source_type` 非法值拒绝（`invalid_request`）
- [x] `/api/skills/reload` 在 `import-gate` 运行模式下已降级拒绝（`skill_reload_unavailable_in_import_gate_mode`）
- [x] `SkillCompatibilityEvaluator` 默认支持工具集已接入 builtin registry，unknown tool 会进入不兼容报告
- [x] `SkillRouter` 已支持注入 `visibility_resolver`，将 Yue 可见性解析从纯路由评分逻辑中进一步隔离
- [x] `api/skills.py` 关键读取路径已切换 runtime context 访问，减少对模块级全局实例的直接耦合
- [x] `api/chat.py` 已新增 runtime prompt helper 绑定（按会话 runtime context 绑定 resolve/assemble，减少隐式全局读取）
- [x] `skill_service.py` 已新增 Stage4 runtime context factory set/reset seam，支持可注入上下文边界（兼容默认行为）
- [x] 增补 hybrid 护栏测试：import-gate 模式 `reload` 短路且不触发 runtime context；legacy 模式 refresh 严格 no-op
- [x] `api/chat.py` 兼容 patch 点已迁移到 runtime context patch 路径（测试不再依赖 `app.api.chat.skill_router/skill_registry` 模块级 seam）
- [x] `skill_service.py` 已补 `Stage4LiteRuntimeProviders`（registry/router/action/import_store）及 set/get/reset seam，`build_stage4_lite_runtime_seams()` 默认跟随 runtime context providers
- [x] hybrid 行为矩阵已覆盖 `legacy/import-gate + reload/import/activate/deactivate` 组合，并在 API + lifespan smoke 路径落地
- [x] `api/skills.py` / `api/skill_imports.py` 已改为 runtime context 取依赖，不再暴露模块级 `skill_registry/skill_router/skill_import_store/skill_import_service` 单例 seam
- [x] 新增 hybrid 收敛门禁：`YUE_SKILL_RUNTIME_CONVERGENCE_STRATEGY=import-gate-strict` 时，legacy 模式拒绝 import mutation（`skill_import_mutation_unavailable_in_legacy_mode`）
- [x] Stage 5-Lite 已补最小 externalization 交付：`skill_runtime_boundary_harness.py` 产出可导出 machine-readable `externalization_manifest`（`stage5-lite-boundary-manifest/v1`）并由测试校验结构
- [ ] **未完成项清单（跨 Phase）**
- [ ] Stage 4-Lite 仍未完全收口：`skill_service.py` 虽已落 provider/container seam，但仍保留模块级全局导出与兼容壳层
- [ ] Runtime 仍为 legacy/import-gate 双轨 hybrid，尚未形成单一清晰运行面
- [ ] Stage 5-Lite 仍 deferred：当前已具备最小 boundary manifest 交付，但完整 externalization（提取/发布）仍未进入执行
- [x] **回归结果（2026-04-23）**
- [x] `cd backend && PYTHONPATH=. pytest -q tests/test_api_skills.py tests/test_api_skill_imports.py tests/test_skill_import_gate_unit.py tests/test_import_gate_lifespan_smoke.py tests/test_skill_runtime_seams_unit.py tests/test_stage5_runtime_boundary_harness.py tests/test_skill_compatibility_unit.py` -> `77 passed`
- [x] `cd backend && PYTHONPATH=. pytest -q tests/test_api_chat_unit.py tests/test_api_skills.py tests/test_api_skill_imports.py tests/test_import_gate_lifespan_smoke.py tests/test_skill_runtime_catalog_unit.py tests/test_skill_runtime_seams_unit.py tests/test_stage5_runtime_boundary_harness.py tests/test_skill_compatibility_unit.py tests/test_skill_service_runtime_context_unit.py` -> `146 passed`

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
- [ ] **Phase 3: Providers API 重构** (合并 [llm_providers_api_refactoring_plan.md](./llm_providers_api_refactoring_plan.md))

### Epic 9: 代码库健康与 God Object 重构 (Refactoring)
> **状态**: 推进中 (约 10%)
> **详情文档**: [codebase_refactor_plan_20260319.md](./codebase_refactor_plan_20260319.md)
> **子计划（chat.py 专项）**: [chat_api_stream_simplification_plan_20260322.md](./chat_api_stream_simplification_plan_20260322.md)
> **子计划（Settings.tsx 专项）**: [settings_tsx_modularization_plan_20260323.md](./settings_tsx_modularization_plan_20260323.md)
> **子计划（Chat 前端专项）**: [chat_frontend_modularization_plan_20260326.md](./chat_frontend_modularization_plan_20260326.md)
> **目标**: 拆解 `chat.py` 和 `Settings.tsx` 等超过 500 行的庞大组件。
- [ ] **Phase 1: 后端重构 (chat/doc)** (模块化拆解核心服务)
- [ ] **Phase 2a: 前端重构 (Settings.tsx 专项)** (拆解 settings 页面 tabs、modals、hooks)
- [ ] **Phase 2b: 前端重构 (MessageItem 专项)** (消息项组件解耦)
- [ ] **Phase 2c: 前端重构 (Chat 组件专项)** (合并 [chat_frontend_modularization_plan_20260326.md](./chat_frontend_modularization_plan_20260326.md))

### Epic 10: 聊天历史与用户体验优化 (Chat History & UX)
> **状态**: 待启动
> **详情文档**: [2026-03-26-chat-history-management-improvement-plan.md](./2026-03-26-chat-history-management-improvement-plan.md)
> **2026-04 设计交付**: [2026-04-10-chat-history-date-tag-execution-plan.md](./2026-04-10-chat-history-date-tag-execution-plan.md), [2026-04-10-chat-history-date-tag-ui-ux-detail-design.md](./2026-04-10-chat-history-date-tag-ui-ux-detail-design.md), [2026-04-10-chat-history-date-tag-visual-direction.md](./2026-04-10-chat-history-date-tag-visual-direction.md)
> **目标**: 实现用户隔离、搜索过滤、虚拟滚动等体验优化，提升历史会话查找与管理效率。
- [ ] **Phase 1: 用户隔离基础** (Session owner 字段、API 过滤参数)
- [ ] **Phase 2: 前端搜索与过滤** (虚拟滚动、日期分组、搜索栏)
- [ ] **Phase 3: 高级功能** (收藏、标签、快速定位)

## ⚪ Done (已完成)
- [x] **Epic 11: 历史请求与工具调用追踪调试 (Request & Tool Trace Inspection)** (见 [2026-04-03-chat-request-payload-inspection-plan.md](./2026-04-03-chat-request-payload-inspection-plan.md), [2026-04-03-chat-trace-inspection-release-checklist.md](./2026-04-03-chat-trace-inspection-release-checklist.md), [2026-04-03-chat-trace-delivery-summary.md](./2026-04-03-chat-trace-delivery-summary.md), [2026-04-03-chat-trace-user-guide.md](./2026-04-03-chat-trace-user-guide.md)) - 已完成，待发布
- [x] **Epic 2: 数据库架构演进 (核心数据层)** (见 [archive/Database_Evolution_Plan.md](./archive/Database_Evolution_Plan.md))
- [x] **Epic 1: 配置与日志的云端演进** (见 [archive/Logging_Config_Evolution_Plan.md](./archive/Logging_Config_Evolution_Plan.md))
- [x] **架构演进可行性与依赖关系分析** (完成了日志、数据库、文件管理的拆解与评估)
- [x] **建立 AI 驱动的工程管理最佳实践** (见 [archive/AI_Driven_Project_Management_Best_Practices.md](./archive/AI_Driven_Project_Management_Best_Practices.md))
- [x] **内置工具架构重构** (见 [archive/builtin_tools_refactor_plan.md](./archive/builtin_tools_refactor_plan.md))
- [x] **语音合成与自动朗读功能** (见 [archive/2026-03-24-auto-speech-synthesis.md](./archive/2026-03-24-auto-speech-synthesis.md))
- [x] **语音输入功能（Azure Speech + Browser Fallback）** (见 [Voice_Input_Feature_Design.md](./Voice_Input_Feature_Design.md), [Voice_Input_Implementation_Plan.md](./Voice_Input_Implementation_Plan.md), [Voice_Input_Release_Checklist.md](./Voice_Input_Release_Checklist.md))

> **归档说明**: 以下历史计划文档已归档至 `archive/` 目录，供参考查阅：
> - 工具架构重构相关：`agent_tooling_refactor_plan.md`, `builtin_tools_refactor_plan.md`
> - 已完成功能计划：`PDF_BUILTIN_TOOLS_HIGH_ROI.md`, `MS_EXCEL_SUPPORT_PLAN.md`, `2026-03-24-auto-speech-synthesis.md`
> - 已被替代计划：`reasoning_tools_execution_enhancement_plan_20260308.md` (已被 Epic 4 替代)
> - 分析参考文档：`REASONING_CHAIN_OPTIMIZATION.md`, `SMART_DOC_PROCESSING_PLAN.md`, `Docs_Tooling_Enhancement_Plan.md`, `MCP_DOC_AGENT_PLAN.md`

---

## 💡 How to use (如何驱动 AI 推进工作)
复制以下 Prompt 发送给 AI 即可开始工作：
> "请阅读 `docs/plans/INDEX.md` 和对应的 `[Plan_Name].md`，我们将开始执行 `[Epic Name]` 下的 `[Phase X]` 任务。请先分析代码现状，然后给出你的修改方案，确认后直接改代码。"
