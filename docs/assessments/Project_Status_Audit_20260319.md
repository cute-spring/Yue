# 项目状态审核与进度分析报告 (2026-03-19)

## 1. 审核概览 (Audit Overview)

本报告是对 2026 年 3 月中旬项目增强计划执行情况的审计与偏差分析。
审计基线：[planned_enhancement_execution_order_20260314_zh.md](file://./docs/plans/planned_enhancement_execution_order_20260314_zh.md)

### 核心结论
- **Skills 架构升级**：超前完成。后端核心逻辑（三层目录、热重载、Legacy 清理）已 100% 落地。
- **分层记忆 (STM MVP)**：尚未启动。基于当前技术成熟度和独立性，已决定延后。
- **优先级调整**：将 **多模态增强 (Multimodal QA)** 的优先级提升，紧接在 Skills 闭环之后。

---

## 2. 计划执行审计 (Audit of Planned Goals)

| 计划项 | 状态 | 审计说明 |
| :--- | :--- | :--- |
| **P0-1 Unified Contract Gate** | 🟡 Partial | Phase 1 已上线；Phase 2/3 (重连/兼容性) 仍是关键安全垫。 |
| **P0-2 Release Readiness Gate** | ✅ Completed | CI/Pre-push 自动化门禁已强制执行。 |
| **P0-5 Hierarchical Memory** | ❌ Pending | 计划已起草 (03-15)，但执行被推迟，以优先处理 Skills 稳定性和多模态 Bug。 |
| **Skills 长期架构升级** | ✅ Completed | 后端已完成，脚本已就绪，前端 UI 已接入来源展示。 |
| **Reasoning + Tools 增强** | 🟡 Partial | Phase 1 已落地；Phase 1.5/2 需基于稳定的 SSE 契约继续。 |

---

## 3. 偏差与调整分析 (Deviation & Adjustment Analysis)

### 3.1 关于 Skills 架构的超前完成
- **现状**：[skill_service.py](file://./backend/app/services/skill_service.py) 已完全支持三层目录覆盖逻辑。
- **影响**：这为自定义 Skill 开发提供了坚实底座，用户可以安全地在 `user` 层扩展功能而无需改动内核。

### 3.2 延后分层记忆 (STM MVP) 的合理性
- **技术解耦**：Memory 属于会话运行时 (Session Runtime)，不影响 Skills 架构。
- **风险权衡**：目前长对话 Context 丢失虽有痛点，但多模态图片发送的 Bug 是显性功能缺失，优先级更高。

---

## 4. 下一步优先级执行计划 (Next Priorities)

### **Priority 1: 多模态图片问答增强 (Multimodal Image QA)**
- **核心目标**：支持“仅图片发送”、建立 Vision 模型门禁、补齐图片校验。
- **首要任务**：实现 `multimodal_service.py` 并接入 `chat.py` 路由。

### **Priority 2: Unified Contract Gate (Phase 2/3)**
- **核心目标**：针对即将到来的多模态 SSE 事件，补齐重连 (Replay) 和向后兼容性 (Backward Compatibility) 的 CI 验证。
- **首要任务**：在 CI 中增加对旧版本客户端的 Payload 模拟测试。

---

## 5. 决策记录 (Decision Log)

- **2026-03-18**: 确认延后分层记忆 (STM MVP) 实现。
- **2026-03-18**: 确认在 Skills 架构完全闭环后，立即启动多模态治理内核开发。
