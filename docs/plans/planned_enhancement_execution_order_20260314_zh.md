# 计划中的增强功能执行顺序 (2026-03-14)

## Objective
记录当前增强计划的推荐执行顺序，基于依赖关系、实现状态和 Rollout 风险。

## Additional Higher-Priority Items (在当前计划顺序之前)

这些项是横向的基础设施，应被视为 **Priority 0**。  
原因：它们能同时降低多个计划的 Regression 风险，并比任何单一功能计划更能提升 Release 安全性。

### P0-1) Unified Contract Gate (SSE + API 兼容性)

- Scope：在 Rollout 之前，为 stream/event Contract 和关键 API Schema 建立强制兼容性 Gate。
- 为什么这是更高优先级：
  - 多个计划中的 Track 都会修改 Streaming 和 Event 语义（Reasoning/Tools/Transparency）。
  - 如果没有统一的兼容性 Gate，每个计划可能通过本地测试，但在重连、重放或前端渲染时仍会中断。
  - Contract Regressions 会直接损害用户信任，且难以安全地进行 Hotfix。
- 增加内容：
  - 针对 `meta/content/error/tool_event/trace_event` 的 Payload 形状和排序的 Golden Contract 测试。
  - Replay + Reconnect 确定性测试（同一次运行 -> 相同的 Event 序列）。
  - 针对旧 Client 上未知 Event 类型的向后兼容性断言。
- 成功标准：
  - 零破坏性 Schema 变更进入 Mainline，除非有明确的版本升级。
  - Replay 一致性和 Dedup 测试在每个 Release Candidate 的 CI 中保持绿色。

### P0-2) Release Readiness Gate (质量、风险与 Rollback)

- Scope：引入一个结合了质量信号、风险评分和 Rollback 就绪状态的 Release Gate。
- 为什么这是更高优先级：
  - 现有计划侧重于 Phase 和 Feature-flag 驱动；失败模式不是编码速度，而是在没有统一 Go/No-go 标准的情况下进行推广。
  - Skills Track 中存在 Manual Sign-off；如果没有统一的 Release Gate，审批会变得碎片化且容易被绕过。
  - Rollback 延迟通常比实现缺陷成本更高。
- 增加内容：
  - Release Checklist，要求：全量 Regression 通过、Migration Dry-run 通过、Alert 连通性通过、Rollback Drill 通过。
  - 风险评分维度：触及的 Runtime 路径、触及的 Data Schema、触及的 UI Protocol。
  - 对于中/高风险变更，如果缺失 Rollback Drill 则强制拦截（Hard Block）。
- 成功标准：
  - 每个推广的变更都有可审计的 Gate Report。
  - 平均回滚时间（MTTRb）在经过演练的 Runbook 范围内。

### P0-3) Observability 运维基线 (SLO + Alerting)

- Scope：在增加更多功能表面之前，为 Chat/Tooling 质量定义 Service-level Objectives 和 Alert 阈值。
- 为什么这是更高优先级：
  - 新功能提升了 Transparency，但如果没有 SLO，团队仍无法决定何时降级、Rollback 或扩容。
  - Tool-calling 可靠性工作需要 Model 级别的 KPI 运营来闭环。
  - 防止出现“指标存在但无运维动作”的 Anti-pattern。
- 增加内容：
  - 核心 SLO：Stream 成功率、First-token Latency、Tool-call Mismatch Rate、Fallback Rate、Replay Error Rate。
  - 按严重程度进行 Alert 路由并明确责任（Oncall 目标 + 响应窗口）。
  - 按 Provider/Model 划分的每日和每周运维快照。
- 成功标准：
  - 定义并演练了 Alert-to-action 工作流。
  - Model/Tool 降级在目标响应时间内触发自动化或引导式缓解。

### P0-4) 数据生命周期与 Migration 安全 (以 SQLite 为中心)

- Scope：为 Trace/Tool Events 规范 Schema Migration、数据保留（Retention）以及重放数据增长控制。
- 为什么这是更高优先级：
  - Transparency 和 Replay 功能增加了写入量；失控的增长会降低 Runtime 和恢复速度。
  - 跨 tool_calls/run_traces 的 Schema 变更需要安全的 Migration 纪律。
  - Trace 中的数据正确性问题很难在事后修复。
- 增加内容：
  - Migration 策略：仅向前迁移 + Rollback 回退策略 + Preflight 检查。
  - 高频 Event/Chunk 数据的数据保留策略。
  - Query/Index 预算检查，以保护 p95 读写延迟。
- 成功标准：
  - Migration 失败路径在生产推广前经过验证。
  - Rollout 后，数据库大小和关键查询延迟保持在约定的预算内。

### P0-5) Hierarchical Memory Foundation (Short-Term + Long-Term)

- Scope：实现一个生产级的 Memory 基线，结合 Session Memory (Short-Term) 和 Persistent Memory (Long-Term)，并配有检索/衰减策略。
- 为什么这是更高优先级：
  - 它是明确规划但在 Roadmap Memory 里程碑中仍处于 Pending 状态。
  - 如果没有 Memory，Reasoning 质量在长会话中会下降，且跨会话连续性较弱。
  - 如果没有稳定的 Memory 支撑，多个计划中的功能（Skills 质量、Multi-agent 编排、Observability 解释）效果会打折扣。
- 增加内容：
  - **Short-term memory**：每个活跃会话的滚动摘要（Rolling Summary）+ Turn 级别的关键事实。
  - **Long-term memory**：用于存储持久事实/偏好的持久化存储，具有检索评分和衰减/重要性策略。
  - **Memory 写入策略**：严格的 Schema 和置信度阈值，以避免存储幻觉事实。
  - **Memory 读取策略**：受限的检索预算，并带有可引用的 Provenance 字段。
- 成功标准：
  - 长会话质量提升，Context-loss 比例降低，用户重复纠正次数减少。
  - 跨会话连续性在持久的用户/项目事实方面生效，且具有可衡量的检索命中率。
  - Memory 写入可审计且可撤销，无失控增长。

## 推荐顺序

0. **横向 Priority-0 基础 (新增)**  
   来源：本文档 (P0-1 ~ P0-5)。  
   优先级原因：这些控制措施可防止跨计划的 Regression，并为所有下游增强功能创造安全的交付条件。

1. **Reasoning + Tools 执行增强**  
   来源：`reasoning_tools_execution_enhancement_plan_20260308.md`  
   优先级原因：稳定 Event Contract 和 Turn 级别的归因（`event_id`, `sequence`, `assistant_turn_id`），这是可靠 Replay 和 Transparency 的前提。

2. **OpenClaw Tool-Calling 治理**  
   来源：`openclaw_tool_calling_reference_execution_plan_20260308.md`  
   优先级原因：在更广泛的 Rollout 之前，增加 Model 能力 Gate 和作用域限定的 Tool 策略，以减少 Tool-call Mismatch 和静默失败。

3. **Observability & Transparency**  
   来源：`observability_transparency_plan.md`  
   优先级原因：基于项 1 和 2 的稳定 Event 语义；避免在 UI 中放大不一致或重复的 Telemetry。

4. **PPT Skill Gap 增强**  
   来源：`ppt_skill_gap_enhancement_plan_20260307.md`  
   优先级原因：在平台稳定性基线建立后，交付直接面向用户的质量改进（Design System, QA Loop, Template 工作流）。

5. **Markdown 定义的 Skills (剩余的 Sign-off 和加固)**  
   来源：`markdown_defined_skills_plan.md`  
   优先级原因：核心 Phase 已实现并自动验证；重点在于 Pending 的手动 UI Sign-off 和针对性的加固。

6. **Nanobot Skill Gap 延续 (Phase 3/4 可选)**  
   来源：`nanobot_skill_gap_plan_20260307.md`  
   优先级原因：主要的 Phase 1/2 工作已落地；仅在分发/生态需求确认后继续。

7. **内置 Tools 重构 (仅维护)**  
   来源：`builtin_tools_refactor_plan.md`  
   优先级原因：重构已完成；仅作为维护/Backlog 保留。

## 详细拆解状态 Flag

图例：
- ✅ **Clear**：存在专门的详细拆解计划。
- 🟡 **Partial**：在现有文档/计划中部分覆盖，但没有单一完整的执行计划。
- ❌ **Missing**：尚无明确的详细拆解计划。

| 项 | 拆解状态 | 证据 | 需弥合的差距 |
|---|---|---|---|
| 0. 横向 Priority-0 基础 | ✅ Clear | 来源：本文档 (P0-1 ~ P0-5) | 将剩余项拆分为专门的执行计划 |
| P0-1 Unified Contract Gate | ✅ Clear | `unified_contract_gate_execution_plan_20260314.md`; `backend/services/contract_gate.py`; `backend/tests/test_contract_gate_unit.py` | 完成 Phase 2 (Replay/Reconnect) 和 Phase 3 (向后兼容性) |
| P0-2 Release Readiness Gate | ✅ 自动化 (CI/Pre-push) | `release_readiness_gate_execution_plan_20260314.md`; `.github/workflows/release-gate.yml`; `scripts/pre-push`; `scripts/check_gate_completeness.py` | 继续 Phase 3 阈值调优和 MTTRb 优化 |
| P0-3 Observability 基线 (SLO/Alerting) | 🟡 Partial | 相关内容见于 `observability_transparency_plan.md` | 增加明确的 SLO 目录 + Alert 责任划分 + Oncall Runbook 计划 |
| P0-4 数据生命周期 & Migration 安全 | 🟡 Partial | Transparency 计划中提到了持久化/迁移关注点 | 增加专门的数据库生命周期计划 |
| P0-5 Hierarchical Memory Foundation | ✅ 计划已起草 | `docs/plans/hierarchical_memory_foundation_plan_20260315.md` | 实现 STM 滚动摘要 (MVP) |
| 1. Reasoning + Tools 执行增强 | ✅ Clear | `reasoning_tools_execution_enhancement_plan_20260308.md` | 按 Phase Gate 继续 |
| 2. OpenClaw Tool-Calling 治理 | ✅ Clear | `openclaw_tool_calling_reference_execution_plan_20260308.md` | 执行 Phase A-D Rollout |
| 3. Observability & Transparency | ✅ Clear | `observability_transparency_plan.md` | 继续分阶段 Rollout 和加固 |
| 4. PPT Skill Gap 增强 | ✅ Clear | `ppt_skill_gap_enhancement_plan_20260307.md` | 执行分阶段的 Design/Dev/Test Track |
| 5. Markdown 定义的 Skills | ✅ Clear | `markdown_defined_skills_plan.md` | 完成 Pending 的手动 Sign-off 和剩余 Gate |
| 6. Nanobot Skill Gap 延续 | ✅ Clear | `nanobot_skill_gap_plan_20260307.md` | 根据需求阈值决定 Phase 3/4 |
| 7. 内置 Tools 重构 | ✅ Clear | `builtin_tools_refactor_plan.md` | 仅维护 |

## 优先级原则

- **依赖优先**：在进行以 UX 为主的 Transparency 功能之前，先执行基础的 Contract/Governance 工作。
- **风险受控的 Rollout**：优先选择 Fail-open 兼容性和分阶段 Release，保持核心 Chat Stream 稳定。
- **ROI 感知的排序**：将基本完成的 Track 推迟到 Sign-off 模式；优先处理对可靠性和信任影响最大的项。
- **运维先于扩展**：在增加新功能表面之前，建立 SLO/Alerting 和 Release Gate 纪律。

## 立即执行的后续行动

1. 在 CI 中为 Stream 和 Replay 兼容性创建并强制执行 P0 统一 Contract Gate。
2. 将 P0-2 Phase 1 的手动证据集作为审计基线（3 份 Gate Report + Rollback Drill + Phase 2 阈值/摩擦说明）。
3. Phase 2 自动化已实现并验证（`scripts/check_gate_completeness.py` + `backend/tests/test_check_gate_completeness.py`）；将此脚本集成到 CI/Release 工作流中，作为强制性的拦截步骤。
4. 为 Chat/Tool 可靠性和 Stream 质量定义运维 SLO 和 Alert 责任划分。
5. 启动 Memory Foundation MVP：实现 Short-term 滚动摘要和带有检索/衰减策略的 Long-term 持久 Memory Schema。
6. 增加 Memory 读写治理：置信度阈值、Provenance、可撤销的更新路径。
7. 从 Reasoning/Tools 增强计划开始执行 Phase 1.5 + Phase 2，以锁定 Event 和归因的一致性。
8. 根据 OpenClaw 治理计划实现 Model 能力矩阵和 Provider/Model Tool 作用域限定。
9. 以分阶段模式继续进行 Observability Rollout（Emit-only -> Persistence -> Internal UI -> 渐进式 Release）。

## P0-2 内存安全执行说明

- 保持 P0-2 验证运行为内存安全：优先使用带有 Early Exit 的 Streaming 断言 (`iter_lines`)，避免在 Chat Stream 测试中进行全量响应缓冲，且除非有专门的压力测试需求，否则避免使用超大的合成测试 Payload。

## P0-2 Phase 1 证据快照

- gate_reports:
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-001.md`
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-002.md`
  - `docs/release_readiness_gate/phase1/gate_reports/RRG-20260314-003.md`
- rollback_drill:
  - `docs/release_readiness_gate/phase1/rollback_drills/RBD-20260314-001.md`
- phase2_input:
  - `docs/release_readiness_gate/phase1/phase2_threshold_friction_notes.md`

## 备注

- 本文档记录了规划指南，不取代各源文件中详细的 Phase 级别实现计划。
