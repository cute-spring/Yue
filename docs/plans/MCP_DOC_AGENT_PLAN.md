# 文档检索子 Agent + 文件系统 MCP 落地计划（严格执行版）

目标：用户在对话框提问时，系统可通过 MCP 在用户指定目录中检索/读取 Markdown；主 Agent 基于“证据片段”生成回答，并返回可点击的文件路径信息（必要时包含片段范围/行号）。

设计参考：
- [agents.md](agents.md) 的主/子 Agent 分层、权限与工具正交、Task Envelope（消息契约）、HITL（人在回路）等工程化思想
- [TESTING.md](TESTING.md) 的验证基线与命令集合

---

## 1. 范围与非目标

### 1.1 范围（本计划必须交付）
- 文档检索能力：在指定根目录内搜索 Markdown 文件，并抽取与问题相关的证据片段（snippets）。
- 引用与溯源：回答必须附带 citations（至少包含 file path；可扩展到片段范围/行号）。
- 主/子 Agent 编排：
  - 主 Agent：理解问题、决定是否需要检索、编排子 Agent/MCP、合成最终回答、输出 citations。
  - 文档检索子 Agent：只负责检索与证据提取，返回结构化结果，不直接对用户输出长篇解释。
- 安全边界：支持 Yue 目录外读取时，必须“显式 allowlist + denylist 兜底 + 防路径穿越/符号链接逃逸 + 文件大小与超时限制”。

### 1.2 非目标（明确不做，避免范围失控）
- 不做自动写入/编辑用户文档（仅只读）。
- 不在早期引入重型向量库/复杂 RAG 基建；先用可解释的轻量排序策略。
- 不把权限控制写进 prompt 里当唯一手段（必须有代码层强制约束）。

---

## 2. 关键原则（必须遵守）

- 工具开关（能否调用）与权限策略（调用到什么程度）必须正交（参考 agents.md 的 Persona/Tools/Permission/Limits 四件套）。
- 子 Agent 不允许递归委派，避免无限任务树与难以审计的问题（参考 agents.md 主/子分层原则）。
- 所有子任务都必须有 Task Envelope（消息契约）：trace_id/task_id/deadline/auth_scope/context_refs 等字段齐全，保证可追踪、可重试、可演进。
- 任何“最终答案中的事实性结论”都必须有 citations；若检索无命中，必须明确声明未找到依据并给出下一步建议（关键词/目录）。
- 默认 deny：未显式配置 allowlist 时，不允许访问项目外目录。

---

## 3. 现状基线（与现有代码/文档对齐）

- MCP 管理与工具枚举
  - [manager.py](../backend/app/mcp/manager.py)
  - [mcp.py](../backend/app/api/mcp.py)
- Agent 配置与工具绑定
  - [agent_store.py](../backend/app/services/agent_store.py)
  - [agents.json](../backend/data/agents.json)
- 测试/验收流程基线
  - [TESTING.md](TESTING.md)

---

## 4. 阶段拆解（每一步可独立交付、可回滚、必须测试验证）

> 术语：
> - DoD = Definition of Done（完成定义）
> - 门禁 = 合并前必须满足的质量检查集合

### Phase 0｜质量门禁与基线固化（先立规矩）

目标：建立所有后续变更的测试与验收基线，防止“功能做出来但质量不可控”。

交付物：
- 统一的本地验证命令清单（引用 TESTING.md，不重复发明流程）。
- 冒烟集成测试：验证 MCP 连接、工具列表稳定 id（server:name）不回退。
- 关键链路可观测性基线：后续所有阶段都能复用相同的 trace/日志字段进行排障。

必须验证：
- 后端单测：按 TESTING.md 的 Backend Unit Tests 跑通。
- 前端构建：按 TESTING.md 的 Frontend Build 跑通。
- MCP 工具与状态 API：按 TESTING.md 的 curl 用例验证 tools/status 输出稳定。

DoD：
- 新增的冒烟测试在本机可稳定通过（重复跑 3 次）。
- 不引入新的 flake（偶现失败）测试。

回滚策略：
- 任意失败：回滚到仅保留测试改动，不引入行为变化。

---

### Phase 1｜最小可用文档检索（只允许 Yue/docs） [DONE]

目标：打通“提问 → 检索 → 证据片段 → 引用路径 → 回答”的闭环，先在低风险目录内完成。

交付物：
- MCP 工具能力（只读）：
  - `docs_search`: 搜索文档（通过 `mode="markdown"` 或 `doc_file_patterns=["**/*.md"]` 限定 Markdown）
  - `docs_read`: 读取文档（通过 `mode="markdown"` 或 `doc_file_patterns=["**/*.md"]` 限定 Markdown）
- 主 Agent 在回答中输出 citations（至少 1 条 file path）。

必须验证：
- 单元测试（后端）：
  - `.md` 扩展名限制
  - 文件大小上限
  - 编码异常处理（不可因单个坏文件导致整体失败）
- 集成测试（后端）：
  - 使用固定 fixtures 目录（可控的若干 md 文件）验证检索与读取输出结构稳定
- 手工验收：
  - 对 docs 里明确存在答案的问题，回答必须给出正确引用路径
  - 对 docs 里不存在答案的问题，必须明确“未命中依据”，不得编造

DoD：
- citations 输出结构化且稳定：最少包含 `path` 与 `snippet`（snippet 可为空但必须有 path）。
- 性能基线：在 docs 目录规模下检索 P95 延迟可接受，并记录基线数值用于后续回归。

回滚策略：
- 若 citations 影响对话体验，可临时在 UI 层隐藏，但后端仍保留结构字段（避免破坏协议）。

---

### Phase 2｜支持 Yue 目录外读取（显式 allowlist） [DONE]

目标：用户提供目标目录时，可在该目录检索/读取 Markdown，但必须安全可控。

交付物：
- allowlist 配置能力（纳入现有 `global_config.json` 配置体系，支持 `doc_access` 对象）。
- 安全策略强制执行（代码层）：
  - 路径穿越拦截（../）
  - 符号链接逃逸防护（realpath 校验）
  - denylist 兜底（macOS 系统敏感目录）
  - 超时与大小限制（避免大文件/大量文件拖垮服务）

必须验证：
- 安全单测：
  - 访问被拒绝目录（System/Library/private 等）必须失败
  - symlink 指向 allowlist 外必须失败
- 集成测试：
  - allowlist 配置开启：可读
  - allowlist 配置关闭：项目外读取必须拒绝，并返回可理解错误

DoD：
- 默认策略为 deny-by-default（未配置 allowlist 时不允许项目外访问）。
- 日志可审计但不泄露敏感内容（只记录必要的路径与规则命中原因）。

回滚策略：
- 一键回退为仅允许 Yue/docs（Phase 1 行为），保持功能可用但收缩权限。

---

### Phase 3｜引入“文档检索子 Agent”（主负责编排，子负责证据） [IN_PROGRESS]

目标：通过主/子分层，把检索复杂度与上下文噪音隔离出去；主 Agent 更稳定、更可维护。

交付物：
- 文档检索子 Agent：
  - 只绑定只读工具（filesystem search/read）
  - 输出严格结构化结果（citations 列表 + 简要理由/得分）
- 主 Agent 编排逻辑：
  - 识别何时需要检索
  - 调用子 Agent
  - 合并 citations 并生成最终回答
- Task Envelope（消息契约）字段落地：
  - trace_id、task_id、deadline、auth_scope、context_refs

必须验证：
- 权限验证：
  - 子 Agent 不可调用任何写入工具或递归委派能力
- 集成测试：
  - 主→子→主链路可追踪（trace_id 串起来）
  - 子任务超时后主 Agent 有可控降级策略（返回未命中/建议）

DoD：
- 子 Agent 输出不依赖自然语言解析（主 Agent 只消费 schema）。
- 失败可定位：能明确是“检索无命中”还是“权限拒绝/超时/文件不可读”。

回滚策略：
- 主 Agent 可降级为直接调用 MCP（Phase 1 模式），不阻断核心功能。

---

### Phase 4｜检索质量提升（可解释排序 + 回归集）

目标：提升“找到对的文档”的稳定性与可解释性，建立回归测试防止检索质量回退。

交付物：
- 轻量排序策略（可解释 score breakdown）：
  - 标题/文件名权重
  - 关键词命中与位置权重
  - 去重与片段合并（控制上下文长度）
- 检索回归集（golden queries）：
  - 固定 query → 期望 topN 命中文档路径

必须验证：
- 回归测试：
  - 每次改排序策略必须跑 golden tests
- 性能测试：
  - 在 1k/5k/10k md 文件量级下记录 P95，并设定警戒线

DoD：
- 检索结果具备可解释性（每条 citation 可说明为何命中）。
- 回归集覆盖核心场景：存在/不存在、同名文件、多目录、长文档。

回滚策略：
- 排序策略可配置化；出现回退可切换到基础排序（文件名/简单关键词）。

---

### Phase 5｜强制引用输出规范（“无引用不结论”）

目标：把“可信回答”固化为系统行为：主 Agent 的事实性回答必须可溯源。

交付物：
- 主 Agent 输出协议：
  - Answer（结论）
  - Citations（路径 + 片段）
  - Gaps（未命中的信息点与建议）
- 失败策略：
  - 未命中 → 明确声明无法从文档确认，并提示用户提供目录/关键词/更多上下文

必须验证：
- 端到端验收：
  - 文档缺失答案时不得编造（必须出现 Gaps/未命中声明）
  - 引用路径必须存在且可打开

DoD：
- 任意事实性回答都能追溯到至少 1 条 citation，或明确声明“无依据”。

回滚策略：
- 可临时放宽为“建议引用”，但必须保留 citations 字段供审计与 UI 展示。

---

### Phase 6｜产品化展示（来源卡片/点击跳转）（可选）

目标：让用户能快速验证答案来源，提升信任与效率。

交付物：
- UI 来源卡片：标题、路径、片段、复制路径
- 安全预览（可选）：通过后端提供受控预览接口，而不是前端直接读本地文件系统

必须验证：
- 前端 e2e（Playwright）：
  - 提问→出现 citations 卡片→复制路径可用
- 安全验收：
  - UI 不暴露 allowlist 外敏感路径内容

DoD：
- 用户可在 2 次点击内打开来源，且体验稳定。

---

## 5. 测试矩阵（所有阶段通用门禁）

后端：
- 单元测试：核心逻辑、路径校验、解析、排序
- 集成测试：主→子→MCP 链路、超时/拒绝/未命中分支
- API 冒烟：/api/mcp/tools、/api/mcp/status、Agents 配置接口（参考 TESTING.md）

前端：
- 构建必须通过（参考 TESTING.md）
- 关键交互 e2e：Chat 引用展示（Phase 6）

可靠性：
- 重复运行 3 次无 flake
- 超时、权限拒绝、文件不可读均有一致且可理解的错误语义

---

## 6. 运行与观测（上线后必须具备）

结构化日志字段（最少）：
- trace_id、agent_id、tool_id、latency_ms、status、deny_reason（如有）

指标（最少）：
- 检索 P95 延迟、命中率（queries with citations）、拒绝率（policy denies）、超时率

审计：
- 记录“读取了哪些路径”（只记录路径与片段 hash/长度，避免记录敏感正文）

---

## 7. 验收总标准（最终必须满足）

- 用户提问后，系统能在用户指定目录（allowlist 内）检索 Markdown 并回答。
- 答案附带可验证的 citations（文件路径必备）。
- 未命中时不编造，并给出下一步建议。
- 子 Agent 仅只读、不可越权、不可递归委派；全链路可追踪与可回滚。
- 全量测试与构建按 TESTING.md 通过，新增测试覆盖关键风险点（路径安全、超时、未命中）。

---

## 8. 阶段验收问题清单（统一口径）

目的：把每个 Phase 的“通过/不通过”判断标准统一为一组可复用的问题，避免验收随人而变。

### 8.1 Phase 0（质量门禁与基线固化）
- 是否明确了唯一的“跑测试/跑构建/跑冒烟”的命令路径，并与 [TESTING.md](TESTING.md) 一致？
- 是否新增了至少 1 个冒烟集成测试，覆盖 MCP 初始化与 tools/status 的基本可用性？
- 是否出现任何不稳定测试（重复跑 3 次会失败）？如果有，是否已修复或移除？
- 是否建立了最小可观测性字段（trace_id/status/latency）且不泄露敏感内容？
- 是否有明确的回滚点（回滚后系统仍可正常运行且功能不倒退）？

### 8.2 Phase 1（最小可用：仅 Yue/docs）
- 对于 docs 内明确存在答案的问题，是否能稳定命中并返回至少 1 条 citations（含 path）？
- 对于 docs 内不存在答案的问题，是否能稳定输出“未命中依据”，并给出下一步建议（关键词/目录）？
- 是否严格只读（不修改任何文件、不产生副作用）？
- 是否有文件大小/读取长度限制，避免把超长文档一次性灌入上下文？
- 是否覆盖了关键异常：坏编码文件、权限不足文件、空文件、超长行？

### 8.3 Phase 2（项目外读取：allowlist + 安全边界）
- 默认策略是否为 deny-by-default：未配置 allowlist 时，项目外读取是否必然被拒绝？
- 是否能防止路径穿越（../）与符号链接逃逸（symlink 指向 allowlist 外）？
- denylist 兜底是否覆盖常见敏感目录（macOS System/Library/private 等）并验证有效？
- 拒绝时的错误信息是否可理解、可定位（知道是“被哪个规则拒绝”），且不泄露敏感正文？
- 是否具备超时/限流/最大文件数等保护，避免大目录扫描拖垮服务？

### 8.4 Phase 3（文档检索子 Agent：主编排 + 子取证）
- 子 Agent 是否被严格约束为只读，并且不具备递归委派能力？
- 主→子→主链路是否可追踪（trace_id 串起来），并能在日志中定位一次请求的完整路径？
- 子 Agent 的输出是否为结构化 schema（主 Agent 不需要解析自然语言才能拿到 citations）？
- 子任务超时/失败时，主 Agent 是否有确定的降级行为（声明未命中/建议用户补充）？
- 是否验证“工具权限收缩”真实生效：子 Agent 不能调用未授权的 MCP 工具？

### 8.5 Phase 4（检索质量提升：可解释排序 + 回归集）
- 是否存在一套最小回归集（golden queries），能覆盖核心场景且每次变更都能跑？
- 每条 citations 是否能解释“为什么命中”（至少有简要 reason 或 score breakdown）？
- 性能是否有可量化基线（P95），并设定了回退阈值或报警阈值？
- 是否避免“同一文件多个片段重复输出”，且能合并/去重控制上下文长度？
- 排序策略是否可配置，出现回归时能快速切回基础排序？

### 8.6 Phase 5（强制引用：无引用不结论）
- 对事实性问题：是否始终提供 citations；若无 citations，是否强制降级为“不确定/未找到依据”？
- 对不存在答案的问题：是否严格不编造，并能输出 Gaps（缺失信息点）？
- citations 的 path 是否可用（文件存在、可打开、路径真实）？
- 是否避免将敏感内容直接回显（尤其是 allowlist 边界附近的文件）？
- 是否具备“引用最小化”：只引用必要片段，避免大段原文泄露？

### 8.7 Phase 6（产品化展示：来源卡片/跳转）
- 是否在 UI 中清晰展示 citations（标题/路径/片段）且可复制路径？
- 是否保证前端不直接访问本地文件系统（只消费后端已校验的引用信息）？
- 是否具备一致的错误展示（未命中、权限拒绝、超时），并引导用户下一步操作？
- e2e 是否覆盖“提问→出现来源卡片→复制/跳转”的关键路径？
- 是否验证在不同规模 citations 数量下 UI 不崩（分页/折叠/上限策略明确）？

---

## 9. Task Envelope 协议（最小可实现版）

目的：把主↔子 Agent 的协作与 MCP 检索结果沉淀为稳定协议，确保可追踪、可重试、可演进、可审计。

### 9.1 通用约束
- 统一链路追踪：一次用户提问生成一个 trace_id，贯穿主 Agent、子 Agent、MCP 工具调用。
- 超时成为协议字段：deadline_ms 或 deadline_ts 必填，子任务超时必须可控终止并返回可识别状态。
- 最小权限原则：auth_scope 明确声明子任务允许的能力集合，默认不继承“主 Agent 的全部权限”。
- 传引用不传全文：context_refs 传“证据引用”，主 Agent 需要全文时再按引用拉取（受权限约束）。

### 9.2 TaskRequest（主 → 子）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| trace_id | 是 | 全链路追踪 id（一次用户提问固定不变） |
| task_id | 是 | 子任务唯一 id（用于幂等与排障） |
| parent_task_id | 否 | 父任务 id（用于任务树） |
| sender | 是 | 固定为 primary（或主 Agent 标识） |
| recipient | 是 | 子 Agent 标识（例如 doc_retrieval） |
| intent | 是 | 意图标签（例如 search_and_extract_evidence） |
| input | 是 | 结构化输入（query、target_roots、限制条件等） |
| context_refs | 否 | 上下文引用（避免传大量历史消息） |
| auth_scope | 是 | 最小权限集合（例如 kb.read / filesystem.read / filesystem.search） |
| idempotency_key | 是 | 重试去重用；同一任务重复发送不产生重复副作用 |
| deadline_ms | 是 | 子任务执行预算（毫秒） |

### 9.3 TaskProgress（子 → 主）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| trace_id | 是 | 与 TaskRequest 一致 |
| task_id | 是 | 与 TaskRequest 一致 |
| status | 是 | pending / running / completed / error / cancelled / timeout |
| events | 否 | 结构化进度事件数组（例如 tool 调用开始/结束） |
| metrics | 否 | tokens、latency_ms、files_scanned、hits 等 |
| partial_output | 否 | 阶段性产出（例如先返回候选文档列表） |

### 9.4 TaskResult（子 → 主）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| trace_id | 是 | 与 TaskRequest 一致 |
| task_id | 是 | 与 TaskRequest 一致 |
| status | 是 | ok / no_hit / denied / timeout / error |
| output | 是 | 结构化结果（见 9.5） |
| errors | 否 | 错误列表（可重试/不可重试分类） |
| metrics | 否 | tokens、latency_ms、files_scanned、hits 等 |

### 9.5 文档检索子 Agent 的 output（最小字段集合）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| query | 是 | 原始问题或检索 query |
| target_roots | 是 | 实际使用的根目录列表（必须是 allowlist 命中后的结果） |
| citations | 是 | 引用数组（见下表） |
| summary | 否 | 子 Agent 给主 Agent 的一句话总结（不应替代 citations） |
| gaps | 否 | 未找到的信息点（便于主 Agent 与用户对齐） |

citations[] 最小字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| path | 是 | 文件路径（优先返回绝对路径；UI 可额外显示相对路径） |
| snippet | 否 | 与问题最相关的文本片段（长度受控） |
| locator | 否 | 定位信息（例如行号范围、段落标题、偏移量） |
| score | 否 | 相关性分数（可解释策略下推荐提供） |
| reason | 否 | 命中原因（关键词、标题匹配等） |

### 9.6 状态与错误语义（统一口径）

status 取值与含义：
- ok：有命中 citations（可能为空 snippet，但 path 必须存在）
- no_hit：未找到可用证据；必须返回 gaps 或 next_steps 建议
- denied：权限或策略拒绝（必须可解释：命中 denylist/未命中 allowlist/越权等）
- timeout：超过 deadline_ms
- error：其它错误（读取失败、解析失败等）

错误分类建议（errors[]）：
- retryable：可重试（短暂 I/O 失败、临时 MCP 断连等）
- non_retryable：不可重试（权限拒绝、文件不存在等）

---

## 10. 执行记录模板（后续严格按此填报）

> 目的：把“计划”变成“可执行过程控制”，每一阶段都能被审计与复盘。

### 10.1 阶段执行卡（每个 Phase 一张）

- Phase：P?
- 负责人：
- 计划开始/结束日期：
- 变更范围（文件/模块）：
- 风险点：
- 验收人：

**门禁清单（必须逐项勾选）**
- [ ] 后端单测通过
- [ ] 前端构建通过
- [ ] 冒烟/集成测试通过
- [ ] 回归集（如适用）通过
- [ ] 日志与指标符合要求
- [ ] 回滚方案已演练或至少可执行

**验收结果**
- 结论：通过 / 不通过
- 发现问题与修复记录：
- 遗留项（必须明确 owner 与截止时间）：
