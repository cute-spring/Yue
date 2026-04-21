# 文档访问策略简化实施方案（Doc Access Policy Simplification）

- 日期：2026-04-20
- 作者：Codex（基于当前仓库实现分析）
- 适用范围：后端配置系统、文档工具链、Agent 配置、前端设置页

## 1. 背景与目标

当前“可访问目录”配置分散在多个层面：

1. `.env`（环境变量）
2. 全局配置（`global_config.json`，由 Settings UI 维护）
3. Agent 级目录限制（`doc_roots` / `doc_file_patterns`）

这导致用户体验和工程维护都偏复杂，目标是将其简化为：

1. 单一权威配置源（Single Source of Truth）
2. 分层继承但只允许收紧（Agent 不能放宽全局）
3. 明确、可解释、可观测的最终生效范围

## 2. 现状问题（基于代码核对）

### 2.1 配置优先级认知与实现存在不一致

- 文档存在两种表述：
  - `环境变量 > 配置文件`（`docs/guides/developer/DOCUMENT_ACCESS_CONFIG.md`）
  - `global_config.json > 环境变量`（`docs/guides/developer/CONFIGURATION.md`）
- 代码中 `AppSettings.settings_customise_sources` 当前是 `env -> dotenv -> init_kwargs`，即运行时偏向环境变量覆盖。

### 2.2 同一能力有不同读取路径，导致行为不统一

- `ConfigService.get_doc_access()` 会走 `AppSettings`，带 env 覆盖。
- 但 `backend/app/mcp/builtin/docs.py` 的 `_get_doc_access()` 直接读 `config_service.get_config().get("doc_access")`，绕开了 `get_doc_access()` 的统一解析。
- 结果：同样的 doc access 在不同调用路径下可能生效不一致。

### 2.3 Agent 级限制存在“可绕过”风险

- `doc_roots` 通过 `deps` 注入工具层。
- 但在 `resolve_docs_roots_for_search()` 中，如果用户显式传 `root_dir`，逻辑会优先校验 `allow_roots/deny_roots`，不再约束 `doc_roots`。
- 结果：Agent 设定的限定目录可被请求参数绕过（在全局 allow 范围内）。

### 2.4 用户心智负担高

- 同一能力有三个可配置入口，且可能互相覆盖。
- 用户无法快速理解“最终为什么这个目录可访问/不可访问”。

## 3. 设计原则

1. 默认拒绝（Deny by default）
2. 最小权限（Least privilege）
3. 显式拒绝优先（Deny overrides allow）
4. Agent 只能收紧，不能放宽
5. 可解释（Explainable effective policy）

## 4. 目标架构

### 4.1 单一权威源

采用 `global_config.json` 作为唯一持久化权威源（SoT）。

- UI 只编辑该权威源。
- `.env` 不再承载目录访问策略，仅保留运行环境参数（如端口、日志、provider key）。
- 为兼容旧部署，保留有限过渡期读取 `.env`，但不再作为长期控制入口。

### 4.2 分层模型（只收紧）

最终生效策略由三层合成：

1. Global 层（平台/实例级）
2. Project 层（项目级，可选）
3. Agent 层（会话/智能体级）

合并规则：

1. `effective_allow = intersect(global_allow, project_allow, agent_allow)`
2. `effective_deny = union(global_deny, project_deny, agent_deny)`
3. 任意层 deny 命中即拒绝
4. `agent_allow` 为空时表示“继承上层，不额外收紧”

## 5. 配置模型（建议 Schema v2）

```json
{
  "doc_access_policy": {
    "version": 2,
    "global": {
      "allow_roots": ["docs"],
      "deny_roots": [".git", ".venv", "node_modules"]
    },
    "project": {
      "allow_roots": ["."],
      "deny_roots": ["backend/data", "backend/data_temp"]
    }
  }
}
```

Agent 侧建议字段：

```json
{
  "doc_scope_mode": "inherit_or_restrict",
  "doc_restrict_roots": ["docs/architecture"],
  "doc_extra_deny_roots": ["docs/release"]
}
```

说明：

- `doc_scope_mode=inferit`（默认）：完全继承上层。
- `doc_scope_mode=restrict`：仅在上层允许范围内再收紧。
- 不再提供 Agent 层“扩大 allow”的能力。

## 6. 核心算法与校验

### 6.1 路径标准化

1. 所有路径做 `realpath + absolute`。
2. 统一分隔符，去重。
3. 拒绝根目录 `/` 作为 allow 根。
4. 保留系统保护 deny（macOS: `/System`, `/Library`；Linux: `/etc`, `/proc`, `/sys`, `/dev`）。

### 6.2 Allow 交集算法（前缀树语义）

当两个 allow 集合 A/B 做交集时：

- 若 `a` 是 `b` 子路径，交集项取 `a`。
- 若 `b` 是 `a` 子路径，交集项取 `b`。
- 否则无交集。

最终对交集结果做“父路径覆盖去重”。

### 6.3 访问判定

对候选路径 `p`：

1. `p` 必须位于 `effective_allow` 任一根下。
2. `p` 不得命中 `effective_deny` 任一根。
3. 同时满足时才允许。

### 6.4 root_dir 与 Agent 限制一致性

无论 `root_dir` 是否显式传入，都必须经过 `effective_policy` 校验。
不得因为用户传了 `root_dir` 就绕过 Agent 限制。

## 7. 实施步骤（分阶段）

### 阶段 A：引入统一策略内核（不改外部行为）

1. 新增策略解析器 `DocAccessPolicyResolver`（建议 `backend/app/services/doc_access_policy.py`）。
2. 实现：路径标准化、allow 交集、deny 合并、判定与 explain 输出。
3. 增加单元测试覆盖核心算法。

### 阶段 B：后端读路径收敛到统一入口

1. `ConfigService` 增加 `get_effective_doc_access(agent_ctx)`。
2. `mcp/builtin/docs.py`、`mcp/builtin/excel.py` 改为只用统一入口，不直接读 `get_config()`。
3. 修复 `root_dir` 显式传入时的 Agent 限制绕过。

### 阶段 C：配置入口简化

1. API 新增 `/api/config/doc_access_policy`（GET/POST）。
2. 原 `/api/config/doc_access` 保留兼容，内部映射到新模型。
3. `.env` 中 `DOC_ACCESS_*` 标记弃用：
   - 启动时记录 warning（一次/进程）
   - UI 显示“已弃用，建议迁移”

### 阶段 D：前端与 Agent 表单改造

1. Settings 页面仅保留“全局/项目策略”两块。
2. Agent 页面改为“继承/收紧”模式开关：
   - 默认继承
   - 收紧时展示 `restrict_roots` 与 `extra_deny_roots`
3. 新增“最终生效范围预览”按钮（调用 explain API）。

### 阶段 E：迁移与清理

1. 提供一次性迁移任务：将旧 `doc_access` 与 Agent `doc_roots` 映射到新字段。
2. 观测一到两个版本周期后，移除 `.env` 对 doc access 的控制能力。
3. 清理旧文档与旧接口说明。

## 8. 兼容策略与回滚

### 8.1 兼容

1. 读兼容：支持旧字段输入（`doc_access`、`doc_roots`）。
2. 写优先：新 UI 只写 `doc_access_policy` 与新 Agent 字段。
3. API 返回可同时带旧字段（deprecated 标记）供旧前端读取。

### 8.2 回滚

1. 保留特性开关 `doc_access_policy_v2_enabled`。
2. 若线上异常，可快速切回 v1 逻辑。
3. 迁移过程保持可逆（保留原字段快照一版）。

## 9. 观测与审计

新增日志与可观测事件：

1. `doc_access_effective_policy`：会话级输出最终 allow/deny（脱敏/截断）。
2. `doc_access_denied`：拒绝事件记录原因（outside_allow / hit_deny / invalid_root）。
3. `doc_access_policy_source`：标记来源（global/project/agent/deprecated_env）。

## 10. 测试计划

### 10.1 单元测试

1. allow 交集算法（父子路径、无交集、重复路径）
2. deny 优先级
3. symlink 逃逸防护
4. 显式 root_dir 与隐式 root_dir 在 Agent 限制下行为一致

### 10.2 集成测试

1. Settings 修改后 docs_search/docs_read 生效一致
2. Agent restrict 后无法访问策略外目录
3. 旧配置迁移后行为与预期一致

### 10.3 回归测试

1. 现有 docs/excel 工具正常读取授权目录
2. 常见 deny 目录（`.git`, `.venv`, `node_modules`）稳定拒绝

## 11. 验收标准（Definition of Done）

1. 用户侧仅需理解两个入口：
   - Settings（全局/项目）
   - Agent（仅收紧）
2. “为什么能访问/不能访问”可由 explain API 一次解释清楚。
3. 任意显式 `root_dir` 不能绕过 Agent 收紧策略。
4. `.env` 不再作为 doc access 主入口（至少进入弃用期并有迁移提示）。
5. 文档与实现优先级描述完全一致。

## 12. 风险与缓解

1. 风险：历史项目依赖 `.env` 覆盖行为。
   - 缓解：双读兼容 + warning + 迁移脚本 + 灰度开关。
2. 风险：路径交集算法引入边界 bug。
   - 缓解：单元测试覆盖路径拓扑 + 真机集成测试。
3. 风险：前后端字段切换导致 UI 配置丢失。
   - 缓解：后端写入前做 schema 校验并保留备份字段。

## 13. 预估排期（建议）

1. 第 1 周：阶段 A-B（统一内核 + 后端收敛）
2. 第 2 周：阶段 C-D（API/UI 改造 + 预览解释）
3. 第 3 周：阶段 E（迁移、灰度、回归）

## 14. 建议的首批改动文件（便于任务拆解）

1. `backend/app/services/config_service.py`
2. `backend/app/services/doc_retrieval.py`
3. `backend/app/mcp/builtin/docs.py`
4. `backend/app/mcp/builtin/excel.py`
5. `backend/app/services/chat_runtime.py`
6. `backend/app/api/config.py`
7. `backend/app/api/agents.py`
8. `frontend/src/pages/Settings.tsx`
9. `frontend/src/components/AgentForm.tsx`
10. `docs/guides/developer/DOCUMENT_ACCESS_CONFIG.md`
11. `docs/guides/developer/CONFIGURATION.md`

---

如果按“最小改动优先”执行，建议先落地两件事再扩展：

1. 后端统一读口（消除多套读取路径）
2. 修复 `root_dir` 绕过 Agent 限制

这两项可以在不大改 UI 的情况下，先显著降低安全和维护风险。

## 15. 当前进度快照（更新于 2026-04-20）

### 15.1 总体完成度（估算）

- 当前整体完成度：约 **30%**（25%-35% 区间）
- 估算口径：按阶段 A-E 里程碑加权，结合已落地代码与测试证据

### 15.2 分阶段状态

1. 阶段 A（统一策略内核）：**未完成**
   - 尚未引入独立 `DocAccessPolicyResolver`
2. 阶段 B（后端读路径收敛）：**核心完成**
   - `docs/excel` 工具已统一通过 `ConfigService` 入口读取 `doc_access`
   - 新增 `ConfigService.get_doc_access_roots()` 作为工具层 roots 统一取值口
   - 修复 `root_dir` 显式传参可绕过 Agent `doc_roots` 的问题
   - 增加 fail-closed 规则：`doc_roots` 存在但全部失效时不再回退到全局默认根
3. 阶段 C（配置入口简化）：**未开始**
4. 阶段 D（前端与 Agent 表单改造）：**未开始**
5. 阶段 E（迁移与清理）：**未开始**

### 15.3 已落地关键改动（已合并到工作区）

1. 后端统一读取入口
   - `backend/app/mcp/builtin/docs.py`
   - `backend/app/mcp/builtin/excel.py`
   - `backend/app/services/config_service.py`
2. `root_dir` 策略一致性与 fail-closed
   - `backend/app/services/doc_retrieval.py`
3. 回归与守卫测试
   - `backend/tests/test_doc_retrieval.py`
   - `backend/tests/test_docs_builtin.py`
   - `backend/tests/test_excel_builtin.py`
   - `backend/tests/test_config_service_unit.py`
   - `backend/tests/test_doc_access_guard.py`

### 15.4 已验证证据

1. 定向 RED -> GREEN（新增入口与行为约束）
2. 相关回归集通过：
   - `PYTHONPATH=backend pytest -q backend/tests/test_doc_retrieval.py backend/tests/test_docs_builtin.py backend/tests/test_excel_builtin.py backend/tests/test_config_service_unit.py`
   - 结果：`103 passed`（含已有 warnings）
3. 静态守卫扫描通过：
   - `rg 'get_config\(\)\.get\("doc_access"\)|get_config\(\)\["doc_access"\]' backend/app`
   - 结果：无匹配

## 16. 剩余阶段加速执行 Prompt（可直接用）

### 16.1 阶段 A 加速（统一策略内核）

```text
/ralph --no-deslop 请在 /Users/gavinzhang/ws-ai-recharge-2026/Yue 推进“文档访问策略简化”阶段 A，结合 tdd + build-fix，以最小改动引入统一策略内核。

目标：
1) 新增 backend/app/services/doc_access_policy.py（DocAccessPolicyResolver）；
2) 实现路径标准化、allow 交集、deny 合并、访问判定、explain 输出；
3) 在不改变外部 API 形状的前提下，让 doc_retrieval 复用该内核；
4) 补齐核心单测（交集、deny 优先、symlink 逃逸、显式/隐式 root_dir 一致性）。

约束：
- 严格 TDD：先写失败测试（RED）再实现（GREEN）；
- 不改 UI，不引入 v2 API；
- 保持向后兼容。

验证：
- 运行 doc_access/docs 相关测试集；
- 给出 RED->GREEN 证据和变更文件清单。
```

### 16.2 阶段 C 加速（后端 API 简化与兼容）

```text
/ralph --no-deslop 请在 /Users/gavinzhang/ws-ai-recharge-2026/Yue 推进“文档访问策略简化”阶段 C，结合 tdd + build-fix，完成配置入口简化。

目标：
1) 新增 /api/config/doc_access_policy（GET/POST）；
2) 保留 /api/config/doc_access 兼容，并内部映射到新模型；
3) 对 DOC_ACCESS_* env 提供弃用 warning（一次/进程），不破坏现有行为；
4) 补齐 API 单测与兼容回归。

约束：
- 最小改动，不改前端；
- 向后兼容优先；
- 禁止回滚现有用户改动。

验证：
- 至少运行 backend/tests/test_api_config_unit.py 与 config/doc_access 相关测试；
- 输出 RED->GREEN 证据。
```

### 16.3 阶段 D 加速（前端设置与 Agent 收紧模式）

```text
/ralph --no-deslop 请在 /Users/gavinzhang/ws-ai-recharge-2026/Yue 推进“文档访问策略简化”阶段 D，结合 tdd + build-fix，完成最小可用前端改造。

目标：
1) Settings 页面改为“全局/项目策略”主视图；
2) Agent 页面改为“继承/收紧”模式；
3) 增加“最终生效范围预览”按钮并调用 explain API；
4) 保持旧字段读取兼容，避免用户配置丢失。

约束：
- 最小 UI 改动，遵循现有设计系统；
- 不做无关重构。

验证：
- 前端单测/集成测试 + 手工关键路径验证（配置保存、回显、预览）；
- 输出行为变更清单与截图/日志证据。
```

### 16.4 阶段 E 加速（迁移、灰度、清理）

```text
/ralph --no-deslop 请在 /Users/gavinzhang/ws-ai-recharge-2026/Yue 推进“文档访问策略简化”阶段 E，结合 tdd + build-fix，完成迁移与清理落地。

目标：
1) 提供一次性迁移任务：旧 doc_access + agent doc_roots 映射到新字段；
2) 增加 feature flag（doc_access_policy_v2_enabled）与回滚路径；
3) 观察窗口内双读兼容，完成后计划移除 .env doc access 主入口；
4) 同步文档：DOCUMENT_ACCESS_CONFIG.md 与 CONFIGURATION.md，消除优先级冲突描述。

约束：
- 迁移可逆；
- 不破坏存量项目运行。

验证：
- 迁移前后对照测试；
- 灰度开关启停回归；
- 文档与实现一致性核对结果。
```

### 16.5 一键收尾 Prompt（A->E 串行推进）

```text
/ralph --no-deslop 请在 /Users/gavinzhang/ws-ai-recharge-2026/Yue 以“文档访问策略简化”全量收尾为目标，按 A->E 串行推进，每阶段都执行 tdd + build-fix：

阶段顺序：
1) A 统一策略内核
2) C API 简化与兼容
3) D 前端/Agent 表单改造
4) E 迁移、灰度、清理

每阶段必须：
- 先 RED 后 GREEN；
- 输出阶段完成标准、变更文件、验证命令与结果；
- 未满足 DoD 不得进入下一阶段。

全局约束：
- 最小改动、向后兼容；
- 不回滚用户已有改动；
- 不做无关重构。
```
