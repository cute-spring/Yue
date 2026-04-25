# Startup Command Template

Use these templates to start or resume the orchestrator cleanly.

## Default Start

```text
请使用 `skill-runtime-core-orchestrator` 继续推进当前的 Skill Runtime Core externalization 主线。
以 `docs/execution/skill-runtime-core-orchestrator-status.md` 为准，
先读取锁定计划与状态，
评估剩余工作和可并行项，
选择当前最高价值的一批任务推进，
完成后更新状态文件并在批次 checkpoint 汇报。
```

## Start With Acceleration Bias

```text
请使用 `skill-runtime-core-orchestrator` 继续推进当前主线。
本轮优先考虑安全的并行加速，不要过度保守地只做一小步。
先读取状态文件，评估 blocking 和 parallelizable 工作，
选择一个较大的可控 batch 执行，
仅在 batch 完成、发现真实阻塞、或需要变更范围时汇报。
```

## Start Locked To Stage A + B

```text
请使用 `skill-runtime-core-orchestrator`，
锁定在 `Stage A + Stage B` 范围内推进 Skill Runtime Core 工作。
不要跳到后续 stage，
优先完成当前状态文件里定义的 next batch，
如存在可安全并行的 sidecar task，请一并推进，
完成后更新状态与验证记录。
```

## Re-Entry After Context Loss

```text
请使用 `skill-runtime-core-orchestrator` 恢复执行上下文。
先重新读取：
- `docs/plans/skill_runtime_core_externalization_plan_20260423.md`
- `docs/plans/skill_runtime_core_stage_ab_task_list_20260424.md`
- `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- `docs/architecture/Skill_Runtime_Current_Operation.md`
- `docs/execution/skill-runtime-core-orchestrator-status.md`

然后基于状态文件继续当前 batch 或选择下一个 batch，
不要重新发散规划。
```
