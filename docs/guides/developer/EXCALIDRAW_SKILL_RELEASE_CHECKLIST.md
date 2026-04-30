# Excalidraw Skill Release Checklist

## 1. Scope

适用对象：`excalidraw-diagram-generator` 及同类“文档+脚本”型 skills。  
目标：在发布前提供统一、可复跑、可审计的门禁清单，降低 action 变更引入的运行时风险。

## 2. Preflight Gate

- [ ] Skill Health 面板中 Excalidraw 相关检查项全部通过（无 blocker）
- [ ] 图标库资产状态符合预期（`reference.md` 存在且 `icons/` 非空，或明确降级为 L1）
- [ ] action 描述符可解析（`tool/resource/input_schema/output_schema/approval_policy` 完整）

## 3. Test Gate

在发布前执行并记录以下命令结果：

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skill_preflight.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_orchestrator_unit.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py -q -k list_action_states
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_skill_actions_unit.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_skill_e2e_unit.py -q

cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend
npm test -- /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.test.ts
```

必备覆盖点：

- [ ] action schema 校验（必填参数、类型校验、参数透传）
- [ ] E2E happy path（无图标流程 + 有图标流程）
- [ ] E2E failure path（图标缺失、`.edit` 冲突、非法 JSON）

## 4. Runtime Smoke Gate

- [ ] 通过 action flow 产出 `.excalidraw` 文件，`output_file_path` 可用
- [ ] `action_steps/warnings/failure_recovery/observability` 字段完整
- [ ] 失败场景可恢复，不会破坏原始 diagram 文件

## 5. Rollback Gate

若发布后出现故障，按以下顺序回滚：

1. 禁用 Excalidraw actions（停脚本执行）
2. 降级到 L1 基础图模式（禁用图标注入与自动连线）
3. 保留已有产物与可编辑路径，避免用户任务丢失
4. 完成回归后再逐步恢复 L2/L3 能力

## 6. Release Record Template

```text
Release ID:
Date:
Owner:

Preflight:
- status:
- blockers:

Tests:
- backend status:
- frontend status:

Smoke:
- sample output path:
- protocol fields verified:

Rollback Readiness:
- disable-action plan verified: yes/no
- L1 degrade plan verified: yes/no

Decision:
- go / no-go
```
