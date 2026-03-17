# Skills 长期架构升级与 Legacy 清理实施计划（2026-03-17）

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可长期演进的三层 Skills 体系，彻底移除 legacy 路径与兼容分支，并确保用户目录新建/更新 skill 可自动加载与生效。

**Architecture:** 采用 `builtin + workspace + user` 三层目录模型，统一由 `SkillDirectoryResolver` 与 `SkillRegistry` 驱动加载；Agent 数据统一收敛到根目录 `data/agents.json`，移除 `backend/data/agents.json` 迁移依赖。通过“启动全量 + 运行期增量热更新 + 冲突可观测”保障一致性与可运维性。

**Tech Stack:** FastAPI, Pydantic, Python pathlib/watchdog, pytest, Playwright（回归）

---

## 0. 背景与问题定义

当前实现存在以下长期风险：
- Skills 加载目录在启动时固定为 `backend/data/skills`，目录单一，环境扩展能力弱。
- AgentStore 仍含 legacy 兼容路径逻辑（`backend/data/agents.json`），导致跨机行为不透明。
- 用户在新机器创建/修改 skill 的加载链路缺少标准化目录、冲突策略与热更新保障。

目标状态：
- 支持三层目录并定义明确优先级和覆盖策略。
- 完全去除 legacy agents 路径分支。
- 用户目录新建 skill 后无需重启即可被识别（可配置热更新策略）。
- 可观测字段可回答“从哪加载、为何覆盖、为何不可用、为何未选中”。

---

## 1. 目标架构（To-Be）

### 1.1 三层技能目录

- L1 `builtin`（只读，随代码发布）
  - `backend/data/skills`
- L2 `workspace`（项目级可写，团队共享）
  - `data/skills`
- L3 `user`（用户级可写，机器个性化）
  - `~/.yue/skills`（支持 `YUE_USER_SKILLS_DIR` 覆盖）

### 1.2 加载优先级与冲突策略

- 默认优先级：`user > workspace > builtin`
- 冲突键：`name + version`
- 冲突决策：高优先级覆盖低优先级，并记录覆盖事件
- API 输出新增字段：`source_layer`, `source_dir`, `override_from`

### 1.3 运行时更新策略

- 启动时：全量扫描三层目录
- 运行时：目录监听 + 防抖重载（2s debounce）
- 失败容错：单 skill 解析失败不影响全局（fail-open on load, fail-closed on invalid skill selection）
- 管理接口：`POST /api/skills/reload` 支持按层重载与全量重载

### 1.4 Legacy 移除原则

- 移除 AgentStore 中 `_legacy_data_dir` 与“从 backend/data 迁移 agents.json”逻辑
- 移除任何读写 `backend/data/agents.json` 的运行时行为
- `backend/data/agents.json` 保留仅作为文档/样例来源，不再被程序引用

---

## 2. 范围与非目标

### 2.1 范围
- Skills 三层目录、冲突策略、热更新
- Agent legacy 兼容清理
- 相关 API、测试、观测补齐
- 运维迁移脚本与上线回滚预案

### 2.2 非目标
- 不在本期建设完整远程 registry 服务
- 不在本期引入签名验证或插件市场
- 不在本期改写前端核心交互范式（仅补充展示字段）

---

## 3. 文件级改动设计

### 3.1 后端核心

- Modify: `backend/app/main.py`
  - 替换当前单目录 `skills_dir` 初始化逻辑
  - 接入 `SkillDirectoryResolver`，注入三层目录列表

- Modify: `backend/app/services/skill_service.py`
  - 新增 `SkillDirectoryResolver`
  - 扩展 `SkillSpec` 元数据（source_layer/source_dir/override_from）
  - `SkillRegistry.load_all()` 支持多目录分层加载与冲突覆盖
  - 新增目录监听与增量刷新入口（可开关）

- Modify: `backend/app/api/skills.py`
  - `GET /api/skills` 和 `GET /api/skills/summary` 返回来源字段
  - `POST /api/skills/reload` 支持参数：`layer=all|builtin|workspace|user`

- Modify: `backend/app/services/agent_store.py`
  - 删除 `_legacy_data_dir` 及其迁移分支
  - 明确唯一数据源为根目录 `data/agents.json`
  - 保留原子写与备份恢复机制

- Modify: `backend/app/services/chat_service.py`
  - skill_effectiveness 增加字段预留（source_layer, override_hit）

### 3.2 配置与脚本

- Modify: `backend/data/global_config.json.example`
  - 增加 `skills_directory_strategy` 配置块：
    - `builtin_dir`
    - `workspace_dir`
    - `user_dir`
    - `watch_enabled`
    - `reload_debounce_ms`

- Create: `backend/scripts/skills_env_diagnose.py`
  - 输出三层目录存在性、可读写性、skill 数量、冲突统计、不可用原因统计

- Create: `backend/scripts/migrate_agents_to_runtime_data.py`
  - 一次性迁移脚本：将 legacy agents 文件迁移到 `data/agents.json`
  - 含 dry-run 与 checksum 对比

### 3.3 前端

- Modify: `frontend/src/types.ts`
  - 扩展 Skill 类型字段（source_layer/source_dir/override_from）

- Modify: `frontend/src/pages/Chat.tsx`
  - 在 skill 下拉中可选展示来源层（如 `ppt-expert:1.0.0 [user]`）

- Modify: `frontend/src/components/AgentForm.tsx`
  - 可见技能提示冲突覆盖来源（只读提示）

### 3.4 测试

- Modify/Create: `backend/tests/test_skill_foundation_unit.py`
  - 多目录加载顺序与冲突覆盖断言

- Modify/Create: `backend/tests/test_skill_runtime_integration.py`
  - 热更新新增/修改/删除场景断言

- Modify/Create: `backend/tests/test_api_skills.py`
  - reload 分层参数与来源字段断言

- Modify/Create: `backend/tests/test_agent_store_unit.py`
  - 删除 legacy 后数据文件行为断言

- Modify/Create: `frontend/e2e/skills-runtime-ui.spec.ts`
  - 来源层展示与 unavailable 组合场景

---

## 4. 分阶段实施计划（6 周）

## Chunk 1: 目录分层与加载内核（Week 1-2）

### Task 1: 引入三层目录解析器

**Files:**
- Modify: `backend/app/services/skill_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_skill_foundation_unit.py`

- [x] **Step 1: 编写失败测试（目录优先级）**
  - 断言同名同版本 skill 在 `user > workspace > builtin` 顺序下命中 user 层

- [x] **Step 2: 运行单测确认失败**
  - Run: `pytest backend/tests/test_skill_foundation_unit.py -k directory_priority -v`
  - Expected: FAIL（当前尚不支持分层优先级）

- [x] **Step 3: 实现 SkillDirectoryResolver 与 load_all 分层合并**
  - 增加目录来源标记与冲突覆盖逻辑

- [x] **Step 4: 再次运行测试确认通过**
  - Run: `pytest backend/tests/test_skill_foundation_unit.py -k directory_priority -v`
  - Expected: PASS

- [ ] **Step 5: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(skills): add layered skill directory resolver and precedence"`

### Task 2: API 暴露来源元数据

**Files:**
- Modify: `backend/app/api/skills.py`
- Modify: `backend/app/services/skill_service.py`
- Test: `backend/tests/test_api_skills.py`

- [x] **Step 1: 先写 API 失败测试**
  - 断言 `/api/skills` 返回 `source_layer`

- [x] **Step 2: 跑测试确认失败**
  - Run: `pytest backend/tests/test_api_skills.py -k source_layer -v`

- [x] **Step 3: 实现字段透出**
  - 更新 response model 与序列化

- [x] **Step 4: 回归通过**
  - Run: `pytest backend/tests/test_api_skills.py -k source_layer -v`

- [ ] **Step 5: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(skills-api): expose source layer metadata"`

## Chunk 2: 彻底清理 Legacy（Week 3）

### Task 3: 删除 agent legacy 迁移分支

**Files:**
- Modify: `backend/app/services/agent_store.py`
- Test: `backend/tests/test_agent_store_unit.py`
- Test: `backend/tests/test_agent_store_persistence.py`

- [x] **Step 1: 写失败测试（无 legacy 文件时只使用 data/agents.json）**
- [x] **Step 2: 跑测试确认失败**
  - Run: `pytest backend/tests/test_agent_store_unit.py -k no_legacy_path -v`

- [x] **Step 3: 删除 `_legacy_data_dir` 与迁移逻辑**
  - 保留 `_recover_agents_file_if_needed` 原子恢复

- [x] **Step 4: 跑 agent store 全量测试**
  - Run: `pytest backend/tests/test_agent_store_unit.py backend/tests/test_agent_store_persistence.py -v`

- [ ] **Step 5: 提交（未执行：按要求不 commit）**
  - `git commit -m "refactor(agent-store): remove legacy backend/data migration path"`

### Task 4: 迁移脚本与上线保护

**Files:**
- Create: `backend/scripts/migrate_agents_to_runtime_data.py`
- Test: `backend/tests/test_agent_store_unit.py`

- [x] **Step 1: 添加 dry-run 行为测试**
- [x] **Step 2: 实现迁移脚本**
- [x] **Step 3: 测试脚本行为**
  - Run: `python backend/scripts/migrate_agents_to_runtime_data.py --dry-run`
- [ ] **Step 4: 提交（未执行：按要求不 commit）**
  - `git commit -m "chore(migration): add one-time agent data migration script"`

## Chunk 3: 用户目录新增/更新 skill 热加载（Week 4-5）

### Task 5: 目录监听与增量重载

**Files:**
- Modify: `backend/app/services/skill_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [x] **Step 1: 写失败测试（用户目录新建 SKILL.md 自动可见）**
- [x] **Step 2: 跑测试确认失败**
  - Run: `pytest backend/tests/test_skill_runtime_integration.py -k user_dir_hot_reload -v`

- [x] **Step 3: 实现 watcher + debounce + reload hook**
  - 监听 `~/.yue/skills`（可被 env 覆盖）

- [x] **Step 4: 跑测试确认通过**
  - Run: `pytest backend/tests/test_skill_runtime_integration.py -k user_dir_hot_reload -v`

- [ ] **Step 5: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(skills-runtime): support user dir hot reload for new and updated skills"`

### Task 6: 分层重载 API

**Files:**
- Modify: `backend/app/api/skills.py`
- Test: `backend/tests/test_api_skills.py`

- [x] **Step 1: 写失败测试（layer 参数）**
- [x] **Step 2: 实现 `POST /api/skills/reload?layer=user`**
- [x] **Step 3: 回归测试**
  - Run: `pytest backend/tests/test_api_skills.py -k layered_reload -v`
- [ ] **Step 4: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(skills-api): add layered reload endpoint behavior"`

## Chunk 4: 观测、前端、发布（Week 6）

### Task 7: 可观测性字段补齐

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [x] **Step 1: 事件字段测试先行**
  - 增加 `selected_skill_source_layer`, `override_hit`

- [x] **Step 2: 实现写库与报表聚合**
- [x] **Step 3: 回归测试**
  - Run: `pytest backend/tests/test_skill_runtime_integration.py -k source_layer_metrics -v`

- [ ] **Step 4: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(observability): add skill source-layer effectiveness metrics"`

### Task 8: 前端来源展示与诊断脚本

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/Chat.tsx`
- Create: `backend/scripts/skills_env_diagnose.py`
- Test: `frontend/e2e/skills-runtime-ui.spec.ts`

- [x] **Step 1: 前端类型与展示测试**
- [x] **Step 2: 实现 UI 轻提示（来源层）**
- [x] **Step 3: 实现诊断脚本并本地跑通**
  - Run: `python backend/scripts/skills_env_diagnose.py`
- [x] **Step 4: 运行 E2E**
  - Run: `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`
- [ ] **Step 5: 提交（未执行：按要求不 commit）**
  - `git commit -m "feat(ui+ops): show skill source layer and add environment diagnose script"`

---

## 5. 数据迁移与切换步骤（Runbook）

### 5.1 切换前
- 备份：
  - `data/agents.json`
  - `backend/data/skills`
  - `data/skills`（若已有）
- 运行诊断脚本，保存快照

### 5.2 切换中
- 执行一次性迁移：
  - `python backend/scripts/migrate_agents_to_runtime_data.py`
- 首次启动时确认日志：
  - 三层目录已加载
  - 冲突覆盖统计可见
  - user 层路径可读可写

### 5.3 切换后
- 在 `~/.yue/skills/demo/SKILL.md` 新建技能，验证 30 秒内可见
- 修改该 skill 描述，验证变更可见
- 删除该 skill，验证从列表移除

---

## 6. 验收标准（DoD）

- legacy 清理
  - `agent_store.py` 中无 legacy 路径迁移分支
  - 运行时不再读取 `backend/data/agents.json`
- 三层技能体系
  - `builtin/workspace/user` 三层同时生效
  - 冲突覆盖行为可预测且可观测
- 用户目录可持续更新
  - 新建/修改/删除 skill 均可自动反映
  - 无需重启（watch 模式）
- 稳定性
  - 现有技能回归测试通过
  - API/集成/E2E 关键用例通过

---

## 7. 风险与对策

- 风险：目录监听在不同 OS 行为差异
  - 对策：监听失败时自动降级为轮询刷新（每 30s）
- 风险：多层覆盖引发“为什么是这份 skill”困惑
  - 对策：API 与 UI 统一展示 `source_layer` 与 `override_from`
- 风险：移除 legacy 造成旧环境启动失败
  - 对策：上线前跑迁移脚本；保留一次性回滚开关（配置回退到单目录）

---

## 8. 回滚预案

- 快速回滚开关：
  - 临时禁用 watcher
  - 临时只加载 `backend/data/skills`
- 数据回滚：
  - 恢复备份 `data/agents.json`
- 版本回滚：
  - 回退到上一个稳定 tag，并执行健康检查脚本

---

## 9. 验证命令清单

- 后端单测：
  - `pytest backend/tests/test_skill_foundation_unit.py -v`
  - `pytest backend/tests/test_skill_runtime_integration.py -v`
  - `pytest backend/tests/test_api_skills.py -v`
  - `pytest backend/tests/test_agent_store_unit.py backend/tests/test_agent_store_persistence.py -v`

- 前端 E2E：
  - `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`

- 质量门禁：
  - `cd backend && ruff check .`
  - `cd backend && mypy app`

---

## 10. 里程碑输出物

- M1：三层目录加载 + 来源字段 + 单测
- M2：legacy 清理 + 迁移脚本 + 回归
- M3：用户目录热更新 + 分层重载 API
- M4：可观测性 + 前端展示 + 运维诊断脚本 + 发布 runbook

---

## 11. 当前执行状态（更新于 2026-03-17）

### 11.1 总体状态

- 总体进度：M1~M4 开发与测试任务已完成，进入质量门禁收敛阶段。
- 关键目标达成：
  - 三层技能目录（builtin/workspace/user）已接入并生效。
  - legacy agents 路径兼容分支已移除，运行时仅使用 `data/agents.json`。
  - 用户目录新增/更新 skill 已支持热加载（watch + debounce）。
  - API/UI/可观测字段已补齐（`source_layer`、`override_from`、`override_hit`）。

### 11.2 已完成项（对应 Chunk）

- Chunk 1 完成：
  - 引入 `SkillDirectoryResolver` 与分层加载覆盖逻辑。
  - `/api/skills` 与 `/api/skills/summary` 返回来源元数据。
- Chunk 2 完成：
  - 移除 AgentStore legacy 迁移路径逻辑。
  - 新增一次性迁移脚本 `backend/scripts/migrate_agents_to_runtime_data.py`（含 dry-run/checksum）。
- Chunk 3 完成：
  - 实现用户目录 watcher + debounce 热更新。
  - `POST /api/skills/reload` 支持 `layer=all|builtin|workspace|user`。
- Chunk 4 完成：
  - 可观测事件新增 `selected_skill_source_layer`、`override_hit` 并落库聚合。
  - 前端展示来源层信息与覆盖提示。
  - 新增环境诊断脚本 `backend/scripts/skills_env_diagnose.py`。

### 11.3 已执行验证结果

- 通过：
  - `pytest backend/tests/test_skill_foundation_unit.py -v`
  - `pytest backend/tests/test_skill_runtime_integration.py -v`
  - `pytest backend/tests/test_api_skills.py -v`
  - `pytest backend/tests/test_agent_store_unit.py backend/tests/test_agent_store_persistence.py -v`
  - `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`
  - `python backend/scripts/migrate_agents_to_runtime_data.py --dry-run`
  - `python backend/scripts/skills_env_diagnose.py`
- 未通过（现阶段阻塞项）：
  - `cd backend && ruff check .`（仓库现有历史问题，非本次改动单独引入）
  - `cd backend && mypy app`（`app/mcp/models.py` 与 `app/api/models.py` 模块重名导致冲突）

### 11.4 风险与阻塞说明

- 阻塞 1：全仓 Ruff 基线债务较大，当前无法作为“零告警”发布门禁。
- 阻塞 2：Mypy 模块命名冲突导致类型检查提前中断，影响类型门禁可信度。

### 11.5 下一步计划（建议按优先级执行）

- P0（门禁解锁）：
  - 处理 mypy 模块冲突（重命名其一并修复导入），恢复 `mypy app` 可执行性。
  - 约定 lint 策略：
    - 方案 A：先引入“改动文件范围 lint 门禁”；
    - 方案 B：单独发起基线清理任务后恢复全仓 lint 门禁。
- P1（发布前验收）：
  - 按 Runbook 执行一次 staging 演练：
    - 迁移脚本 dry-run + 正式执行；
    - user 目录新增/修改/删除 skill 的 30 秒可见性验证；
    - 分层重载 API 验证与回滚开关演练。
- P2（运维收口）：
  - 产出一次发布快照（目录统计、冲突统计、不可用原因统计）。
  - 将 `skills_env_diagnose.py` 纳入上线前检查清单。
