---
name: "mcp-doc-agent"
description: "Implements the MCP filesystem + doc-retrieval subagent plan with test gates. Invoke when building document search/reading via MCP, citations, or parent/child agent orchestration."
---

# MCP Doc Agent

本 Skill 用于把 [MCP_DOC_AGENT_PLAN.md](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/MCP_DOC_AGENT_PLAN.md) 里的方案落到代码与测试里，并严格执行“分阶段交付 + 每步验证 + 可回滚 + 可维护”。

## 何时使用

在以下场景必须调用本 Skill：
- 你要在 Yue 项目里实现“通过 MCP 检索/读取 Markdown，并在回答中返回 citations（文件路径/定位信息）”
- 你要实现主 Agent 编排 + 文档检索子 Agent 分层
- 你要扩展到 Yue 目录外读取，并要求 allowlist/denylist/防穿越/防 symlink 逃逸
- 你要把上述能力做成可测试、可观测、可回归的工程能力

## 产出物（每次调用必须明确交付）

- 变更文件列表（含可点击路径）
- 新增/更新的测试用例列表（含如何运行）
- 验收结果（按计划文档第 8 节逐项勾选）
- 回滚说明（触发条件 + 回退开关/策略）

## 执行规范（强制）

### 1) 分阶段推进（不得跳步）

严格按计划文档推进：
- Phase 0：质量门禁与基线固化
- Phase 1：最小可用（仅 Yue/docs）
- Phase 2：项目外读取（显式 allowlist）
- Phase 3：引入文档检索子 Agent
- Phase 4：检索质量提升与回归集
- Phase 5：强制引用输出规范
- Phase 6：UI 产品化展示（如在范围内）

每个 Phase 必须满足 DoD 后才能进入下一阶段。

### 2) 测试与门禁（不得省略）

每次实现一个可交付变更后，必须执行并记录结果：
- 后端单测（参考 [TESTING.md](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/TESTING.md)）
- 前端构建（如本次改动影响前端）
- API 冒烟（涉及 MCP/Agents/Chat 接口时）

若项目已有 lint/typecheck 命令，必须一并执行并保持通过；若无法确定命令，则优先搜索代码库与脚本定义。

### 3) 权限与安全（默认 deny）

任何文件系统读取能力必须满足：
- 默认 deny-by-default（未配置 allowlist 时不允许项目外访问）
- denylist 兜底
- 防路径穿越与 symlink 逃逸
- 文件大小/扫描数量/超时限制

子 Agent 必须只读，且不得具备递归委派能力。

### 4) 协议优先（结构化输出）

主↔子 Agent 协作与检索结果必须遵循计划文档第 9 节 Task Envelope。

子 Agent 必须返回结构化 output：
- citations[{path, snippet?, locator?, score?, reason?}]
- status: ok/no_hit/denied/timeout/error

主 Agent 生成最终回答时：
- 有 citations 才能输出事实性结论
- 无 citations 必须显式声明未找到依据，并给出 next steps

## 工作流模板（建议照抄）

### A) Phase N 实施步骤（每次循环）

1. 确认本次目标仅覆盖一个 Phase 的 DoD
2. 搜索代码库找到最小改动点
3. 实现最小改动并补测试
4. 运行测试/构建/冒烟并记录输出
5. 按第 8 节验收问题清单逐项勾选
6. 汇总变更、验收、回滚策略

### B) 常见失败与处理

- MCP 连接不稳定：优先在状态 API 与重试/超时策略上解决，禁止静默吞错
- 检索无命中：必须走 no_hit 分支，主 Agent 不得编造
- 安全策略误伤：通过 allowlist 精细化与更清晰错误信息修正，禁止放宽默认 deny

