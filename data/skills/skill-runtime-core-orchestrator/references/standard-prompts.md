# Standard Prompts

These prompts are meant to be copied with minimal edits.

## 1. Continue Current Batch

```text
请使用 `skill-runtime-core-orchestrator` 继续当前 batch。
先读取状态文件并判断当前 batch 是否仍然有效；
如果有效，就继续完成它；
如果已完成或失效，再选择下一个 batch。
完成后更新状态并汇报：
Completed in this batch / Verification / Updated status / Recommended next batch
```

## 2. Continue With Safe Parallelization

```text
请使用 `skill-runtime-core-orchestrator` 继续推进，
并主动评估当前剩余工作中可安全并行的部分。
优先选择 1 个 primary task group + 1-3 个 safe sidecar tasks 的 batch，
不要因为保守而把任务切得过碎，
但也不要跨出锁定范围。
批次完成后再统一汇报。
```

## 3. Force A Checkpoint

```text
请使用 `skill-runtime-core-orchestrator` 先不要继续扩展执行，
而是做一次 checkpoint。
读取当前状态文件，
总结当前 batch 的完成情况、未完成项、阻塞项、验证结果和推荐下一批任务，
并更新状态文件。
```

## 4. Focus On One Stage Only

```text
请使用 `skill-runtime-core-orchestrator`，
本轮只允许在当前锁定 stage 内推进，
不要跳到后续 stage，也不要顺手扩 scope。
如果当前 stage 内存在可并行任务，请在同一 batch 内加速完成。
完成后更新状态文件并汇报。
```

## 5. Resume After Manual Edits

```text
请使用 `skill-runtime-core-orchestrator`，
先检查状态文件与最近代码变化是否一致。
如果人工修改没有破坏当前 batch，就继续推进；
如果已经影响 batch 假设，就更新状态并重选 batch。
不要忽略状态一致性检查。
```

## 6. Ask For Maximum Throughput Without Drift

```text
请使用 `skill-runtime-core-orchestrator`，
在不偏离当前锁定目标的前提下，尽量提高吞吐量。
先评估剩余工作、依赖关系和可并行空间，
选择当前最有价值的较大 batch，
减少无意义暂停，
仅在真正阻塞、需要改计划、或 batch 完成时汇报。
```

## 7. Start The Default Next Batch In This Repo

```text
请使用 `skill-runtime-core-orchestrator`，
以 `docs/execution/skill-runtime-core-orchestrator-status.md` 为准，
直接启动 recommended next batch。
如果 recommended next batch 中存在可安全并行的 sidecar task，也一并执行。
执行后更新状态文件与验证记录。
```
