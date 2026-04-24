# Execution Workspace

本目录用于存放“持续推进型执行工作流”的状态文件、速查页和后续执行产物。

当前已接入的执行器：

- **[Skill Runtime Core Orchestrator](./skill-runtime-core-orchestrator-status.md)** - 用于按批次推进 `Skill Runtime Core externalization` 主线

---

## 当前可用工作流

### Skill Runtime Core Orchestrator

对应 skill：

- [skill-runtime-core-orchestrator](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/SKILL.md)

当前状态文件：

- [skill-runtime-core-orchestrator-status.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/execution/skill-runtime-core-orchestrator-status.md)

常用模板：

- [startup-command-template.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/references/startup-command-template.md)
- [standard-prompts.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/references/standard-prompts.md)

辅助脚本：

- [validate_status.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/scripts/validate_status.py)
- [select_next_batch.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/skill-runtime-core-orchestrator/scripts/select_next_batch.py)

---

## 最常用的调用方式

### 1. 默认继续推进

```text
请使用 `skill-runtime-core-orchestrator` 继续推进当前的 Skill Runtime Core externalization 主线。
以 `docs/execution/skill-runtime-core-orchestrator-status.md` 为准，
先读取锁定计划与状态，
评估剩余工作和可并行项，
选择当前最高价值的一批任务推进，
完成后更新状态文件并在批次 checkpoint 汇报。
```

### 2. 带并行加速倾向

```text
请使用 `skill-runtime-core-orchestrator` 继续推进当前主线。
本轮优先考虑安全的并行加速，不要过度保守地只做一小步。
先读取状态文件，评估 blocking 和 parallelizable 工作，
选择一个较大的可控 batch 执行，
仅在 batch 完成、发现真实阻塞、或需要变更范围时汇报。
```

### 3. 直接启动当前推荐批次

```text
请使用 `skill-runtime-core-orchestrator`，
以 `docs/execution/skill-runtime-core-orchestrator-status.md` 为准，
直接启动 recommended next batch。
如果 recommended next batch 中存在可安全并行的 sidecar task，也一并执行。
执行后更新状态文件与验证记录。
```

---

## 这个执行器适合做什么

适合：

- 多阶段架构收口
- 有锁定计划文档的大任务
- 需要状态连续性和批次推进的工作
- 需要“尽量并行，但不失控”的执行任务

不适合：

- 非计划型的一次性小修
- 完全开放式探索
- 没有状态文件和边界文档的任务

---

## 使用建议

1. 每次继续前，优先以状态文件为准，而不是只靠会话记忆。
2. 如果你做了人工修改，再调用一次“状态一致性检查”类 prompt。
3. 如果后续为别的主线创建新的 orchestrator，也建议在本目录下为它放一份独立状态文件和速查入口。
