# 项目状态审核与进度分析报告 (2026-04-24)

## 1. 审核概览 (Audit Overview)

本报告聚焦当前 `Skill Runtime Core` 外置化主线，审计基线采用以下文档集：

- [Skill Runtime Core Externalization Plan](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_runtime_core_externalization_plan_20260423.md)
- [Skill Runtime Core Phase 1 Refactor Plan](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_runtime_core_phase1_refactor_plan_20260423.md)
- [Skill Runtime Core 复用与迁移指南](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md)
- [Skill Runtime 当前运行机制说明](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/architecture/Skill_Runtime_Current_Operation.md)
- [Skill Runtime Core Orchestrator Status](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/execution/skill-runtime-core-orchestrator-status.md)

补充基线说明：

- 通用产品路线图存在于 [ROADMAP.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/overview/ROADMAP.md)，但它并不是当前 `Skill Runtime Core` 主线的直接执行基线。
- 仓库内未发现 `docs/plans/planned_enhancement_execution_order_*.md`。
- 未发现 `docs/release_readiness_gate/`，当前仅存在 [docs/release/README.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/release/README.md) 及早期 release 资料，说明这条主线仍缺少独立的 release-quality gate 资产。

### 核心结论

- `Stage A`、`Stage B`、`Stage C` 已形成连续交付链，当前主线不是停在“设计完成”，而是已经把 boundary、runtime construction、visibility extraction 都落成了代码事实，见 [skill-runtime-core-orchestrator-status.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/execution/skill-runtime-core-orchestrator-status.md#L33)。
- 当前最关键的“超额完成”项是：`routing.py` 已从 `reusable_after_cleanup` 提前推进到 `reusable_now`，因为默认 visibility 已改成 attribute-based，group 语义已挪到 host adapter 层，见 [boundary_manifest.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/boundary_manifest.py#L80)。
- 下一优先级应切到 `Stage D`，因为剩余主要阻塞已从“运行时耦合”转为“配置/存储命名仍然 Yue 化”，尤其是 `YUE_*` env alias 和 repo-relative defaults 仍在 bootstrap/config 路径里。

---

## 2. 计划执行审计 (Audit of Planned Goals)

| 计划项 | 状态 | 审计说明 |
| :--- | :--- | :--- |
| `Stage A: Define Core Boundary` | ✅ Complete | 边界 manifest 已落地，且回归测试已锁住路径存在性和 Yue-only import 漂移，[boundary_manifest.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/boundary_manifest.py#L19) 与 [test_skill_runtime_boundary_manifest_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_boundary_manifest_unit.py) 形成完整证据链。 |
| `Stage B: Remove Global Runtime Construction From Critical Paths` | ✅ Complete | runtime construction 已明确收敛到 `build_skill_runtime(...)`、bootstrap spec、runtime context/provider 解释体系，且状态文件记录 Stage B 已收口，[Skill_Runtime_Current_Operation.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/architecture/Skill_Runtime_Current_Operation.md#L100) 与 [skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L148) 一致。 |
| `Stage C: Extract Yue-Specific Visibility and Group Resolution` | ✅ Complete | core router 默认只解析 agent-local visible refs，group-aware 语义由 host adapter 提供，[routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py#L24) 与 [host_adapters.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/host_adapters.py#L74) 已兑现计划目标。 |
| `Stage D: Normalize Configuration and Storage` | 🟡 Not started, now unblocked | `SkillRuntimeConfig` 已存在，但 neutral key normalization 仍停留在 alias 兼容层，repo-relative 默认目录与 `YUE_*` 兼容仍在 bootstrap path 内，[bootstrap.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py) 仍是后续主战场。 |
| `Stage E: Publish Bootstrap and Integration API` | 🟡 Partially achieved early | `build_skill_runtime(...)` 与 `mount_skill_runtime_routes(...)` 已经可用，这部分比原计划更早落地；但默认 route strategy 仍依赖 Yue API 模块，因此 package-first host 还不能算完全闭环。 |
| `Stage F: Build Portability Regression Harness` | 🟡 Minimal assets present | 已有最小 boundary/harness 资产，但还没有真正 host-simulator 级黑盒 portability harness。当前状态更像 “Stage F 预备资产已存在”，不是正式完成。 |

---

## 3. 偏差与调整分析 (Deviation & Adjustment Analysis)

### 3.1 `Stage C` 的推进属于合理前移，不是范围漂移

- **现状**：状态文件明确记录，用户在 `Stage A + B` 完成后显式要求继续主线，因此 orchestrator 切换到 `Stage C`，见 [skill-runtime-core-orchestrator-status.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/execution/skill-runtime-core-orchestrator-status.md#L69)。
- **技术依据**：`routing.py` 默认 resolver 已不再读取 `skill_groups`，只处理 `resolved_visible_skills`、`extra_visible_skills`、`visible_skills`，[routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py#L24)。
- **影响**：这不是无控制扩张，而是顺着主线从 Stage B 自然解锁到 Stage C；它减少了后续再次重开边界讨论的成本。

### 3.2 Host adapter 层比原计划更快承担了宿主可见性语义

- **现状**：`GroupAwareAgentVisibilityResolver` 已成为 Yue 的默认宿主 visibility adapter，[host_adapters.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/host_adapters.py#L74)。
- **技术依据**：`skill_service.py` 里 `Stage4LiteHostAdapters` 现在不仅保存 `skill_group_resolver`，还允许携带 `visibility_resolver`，并在设置宿主 adapter 时把 resolver 绑定回 singleton router，[skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L186) 与 [skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L245)。
- **影响**：这是一个“super-achieved”项。原计划里 Stage C 的目标是“move semantics behind a protocol”；当前实现已经把这件事从概念层推进到了默认运行路径。

### 3.3 计划基线和治理资产存在一个现实偏差

- **现状**：当前仓库的高层 [ROADMAP.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/overview/ROADMAP.md) 仍然是产品/平台大盘路线图，不是 `Skill Runtime Core` 外置化主线的直接执行顺序文档；与此同时，仓库内缺少 `planned_enhancement_execution_order_*.md` 与 `release_readiness_gate/`。
- **影响**：这不会阻止当前代码推进，但会降低跨线程、跨贡献者协作时的“优先级单一事实源”清晰度，也会让 release-quality evidence 更难汇总。

---

## 4. 下一步优先级执行计划 (Next Priorities)

### **Priority 1: 进入 `Stage D`，完成配置与存储中立化**

- **核心目标**：把剩余 `YUE_*` naming / repo-relative convenience 从 runtime core 主逻辑里进一步抽离，压缩成明确的 host config / storage seam。
- **首要任务**：优先清点并收敛 [bootstrap.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py) 中 neutral key、Yue alias、默认目录解析之间的职责边界，然后补对应 regression。

### **Priority 2: 为 `Stage D` 建立更明确的治理基线**

- **核心目标**：让下一阶段不再完全依赖 prose 状态文件驱动，而是有更清晰的执行清单和质量门禁入口。
- **首要任务**：新增或补一份 `Stage D` 执行任务清单，并为当前主线建立最小 release-readiness / portability gate 入口，而不是继续复用泛化的产品 roadmap。

### **Priority 3: 暂缓把 `Stage E/F` 直接拉满**

- **核心目标**：避免在配置与存储仍带 Yue 语义时，过早把 bootstrap API 和 portability harness 宣布为“完成”。
- **首要任务**：继续把 `Stage E` 视为“部分提前达成”，把 `Stage F` 视为“最小资产已存在”，直到 `Stage D` 完成后再进行 package-first host 的黑盒验证。

---

## 5. 决策记录 (Decision Log)

- **2026-04-24**：确认 `Skill Runtime Core` 主线的实际完成面已覆盖 `Stage A`、`Stage B`、`Stage C`，不再只是外置化设计阶段。
- **2026-04-24**：确认 `routing.py` 已具备 `reusable_now` 条件，这是本轮最明显的超额完成项，见 [boundary_manifest.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/boundary_manifest.py#L80)。
- **2026-04-24**：确认下一优先级应切到 `Stage D`，而不是继续在 `Stage C` 或过早宣告 `Stage E/F` 完成。
- **2026-04-24**：确认当前主线仍存在治理层缺口：缺少专用 execution-order 文档与 release-readiness gate 目录，应作为后续协作成本控制项纳入考虑。
