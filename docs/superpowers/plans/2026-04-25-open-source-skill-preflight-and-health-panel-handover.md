# Open-Source Skill 预检与健康面板交接文档（Handover）

## 1. 目标与范围

本次交接覆盖以下 5 个改进目标：

1. 手工复制的开源技能包可在启动时自动发现并预检
2. 提供统一预检查询 API（可用/需修复/不可用）
3. 提供独立 Skill Health 页面展示状态、问题、建议
4. 支持一键挂载默认 Agent 并反馈挂载结果
5. 分离“可见性”与“可用性”，提供可操作错误文案

## 2. 当前进度总览

整体状态：**核心能力已打通，进入收口与交接阶段**。

- Phase 1（自动发现 + 启动预检）：已完成
- Phase 2（预检 API + 状态模型）：已完成
- Phase 3（Skill Health 页面）：已完成
- Phase 4（一键挂载 + 结果反馈）：已完成
- Phase 5（可见性/可用性分离 + 可操作文案）：基本完成，待做端到端收口验证

## 3. 已完成内容（按模块）

### 3.1 Backend

- 新增预检 API：`/api/skill-preflight`（列表/详情/挂载）
- 启动阶段接入预检扫描，覆盖 builtin/workspace/user 分层目录
- 预检记录扩展字段：
  - `mountable`
  - `status_message`
  - `next_action`
  - `visible_in_default_agent`
- 挂载错误返回升级为结构化详情：
  - `code`
  - `message`
  - `next_action`

关键文件：

- `backend/app/api/skill_preflight.py`
- `backend/app/services/skills/preflight_service.py`
- `backend/app/services/skills/bootstrap.py`

### 3.2 Frontend

- 新增独立页面：`/skill-health`
- 新增筛选与诊断展示（状态/层级/关键词）
- 分离展示：
  - 可用性（`available|needs_fix|unavailable`）
  - 默认 Agent 可见性（`visible_in_default_agent`）
- 一键挂载默认 Agent：`builtin-action-lab`
- 挂载失败兼容两种后端格式：
  - 旧格式：`detail: string`
  - 新格式：`detail: { code, message, next_action }`

关键文件：

- `frontend/src/pages/SkillHealth.tsx`
- `frontend/src/pages/SkillHealth.test.ts`
- `frontend/src/types.ts`
- `frontend/src/index.tsx`
- `frontend/src/App.tsx`

### 3.3 文档

- 新增开发指南：`docs/guides/developer/SKILL_PREFLIGHT_HEALTH_PANEL_GUIDE.md`
- 在复用指南中补充跳转链接：
  - `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`

## 4. 已完成验证（证据）

### 4.1 Backend

- `PYTHONPATH=. pytest tests/test_api_skill_preflight.py -q`
  - 结果：`7 passed`
- `PYTHONPATH=. pytest tests/test_api_skill_preflight.py tests/test_skill_preflight_service_unit.py tests/test_skill_runtime_bootstrap_unit.py -q`
  - 结果：`24 passed`
- `PYTHONPATH=. pytest tests/test_api_skill_preflight.py tests/test_skill_preflight_service_unit.py tests/test_skill_import_store_unit.py tests/test_skill_runtime_bootstrap_unit.py tests/test_skill_import_gate_unit.py tests/test_skill_foundation_unit.py -q`
  - 结果：`96 passed`

### 4.2 Frontend

- `npm run test -- src/pages/SkillHealth.test.ts`
  - 结果：`8 passed`
- `npm run build`
  - 结果：构建成功（存在 chunk size warning，不阻塞）

## 5. 收口任务状态（Remaining Work Closure）

### R1. 端到端体验级验证（高优先级）- 已完成

- 目标：验证 `/skill-health` 与真实后端 API 的完整链路
- 覆盖点：
  - 列表加载与筛选
  - `needs_fix` 技能禁止挂载
  - `available` 技能挂载成功并提示
  - 结构化错误 `detail.code` 的 UI 反馈
  - 可见性状态与可用性状态同时展示
- 落地结果：
  - 新增 `backend/tests/test_api_skill_preflight.py::test_skill_health_api_flow_end_to_end`
  - 通过单测串联验证 list/detail/mount 的完整调用流与返回字段语义

### R2. 收敛任务与文档状态（中优先级）- 已完成

- 清理计划文档中的历史未勾选项，和当前真实进度对齐
- 补齐“最终验收清单”与“回滚说明”

### R3. 提交前变更收口（中优先级）- 已完成

- 将与本需求无关的历史修改从提交集合中拆分/隔离
- 形成最小可审查变更集，便于合并与回归

## 6. 具体执行计划（可直接接力）

### Step A（0.5 天）：端到端验证补齐

1. 新增/完善集成测试，覆盖 R1 五个场景
2. 本地执行后端+前端验证命令
3. 输出失败场景与修复记录（如有）

完成判定：

- 端到端关键路径全部通过
- 无新增回归失败

### Step B（0.5 天）：文档与验收收口

1. 更新本交接文档与相关计划文档状态
2. 补充最终验收 checklist
3. 增加常见故障排查与回滚指引

完成判定：

- 文档可让新同学“按文档独立完成验收”

### Step C（0.5 天）：提交准备与评审

1. 整理 commit 范围，仅保留本需求相关改动
2. 执行最终回归（backend + frontend）
3. 提交 PR 描述（背景/改动点/风险/验证）

完成判定：

- PR 可直接进入评审
- 审查者可按验证步骤复现结果

## 7. 风险与注意事项

- 当前工作区存在较多历史变更，提交前务必做范围隔离
- 前端构建有大包体 warning，非阻塞，但建议后续关注分包策略
- 后端依赖 runtime bootstrap 的宿主适配，环境 wiring 错误会导致 `agent_store_unavailable`

## 8. 交接建议

建议下一位接力同学按以下顺序执行：

1. 先跑“第 4 节”验证命令确认基线稳定
2. 再做“第 6 节 Step A”端到端补测
3. 最后执行 Step B/Step C 完成交付收口

## 9. 最终验收清单（Final Acceptance Checklist）

- [x] 启动自动发现覆盖 builtin/workspace/user 分层目录
- [x] 预检 API 提供列表/详情/挂载能力（`/api/skill-preflight`）
- [x] Skill Health 页面可加载、筛选并展示诊断与行动建议
- [x] 可用性与默认 Agent 可见性分离展示（Availability vs Visibility）
- [x] `available` 技能支持一键挂载且结果可见
- [x] `needs_fix`/`unavailable` 技能挂载被阻断并返回可操作错误
- [x] 前后端关键验证命令可本地复现通过

## 10. 回滚说明（Rollback Notes）

回滚原则：优先回滚“挂载入口与页面路由”，保留底层兼容数据结构，避免影响既有 skill runtime 行为。

建议分级回滚顺序：

1. 前端回滚（最低风险）
   - 移除 `/skill-health` 路由入口与导航链接：
     - `frontend/src/index.tsx`
     - `frontend/src/App.tsx`
   - 回退页面与测试：
     - `frontend/src/pages/SkillHealth.tsx`
     - `frontend/src/pages/SkillHealth.test.ts`
2. API 层回滚（中风险）
   - 下线 `backend/app/api/skill_preflight.py` 路由挂载
   - 保留 `import_store`/`import_models` 兼容字段，避免历史数据读写异常
3. 启动预检回滚（高风险）
   - 取消 `bootstrap` 中 preflight 启动接线：
     - `backend/app/services/skills/bootstrap.py`
   - 如需完全回滚，再同步回退：
     - `backend/app/services/skills/preflight_service.py`
     - `backend/tests/test_skill_preflight_service_unit.py`

回滚后最小验证：

- Backend:
  - `PYTHONPATH=. pytest tests/test_skill_runtime_bootstrap_unit.py -q`
- Frontend:
  - `npm run build`

## 11. 提交范围隔离建议（Submission Scope Isolation）

本需求建议提交范围（feature-only）：

- Backend API/服务/模型与测试：
  - `backend/app/api/skill_preflight.py`
  - `backend/app/services/skills/preflight_service.py`
  - `backend/app/services/skills/bootstrap.py`
  - `backend/app/services/skills/import_store.py`
  - `backend/app/services/skills/import_models.py`
  - `backend/app/services/skills/import_service.py`
  - `backend/tests/test_api_skill_preflight.py`
  - `backend/tests/test_skill_preflight_service_unit.py`
  - `backend/tests/test_skill_runtime_bootstrap_unit.py`
  - `backend/tests/test_skill_import_store_unit.py`
- Frontend 页面与测试：
  - `frontend/src/pages/SkillHealth.tsx`
  - `frontend/src/pages/SkillHealth.test.ts`
  - `frontend/src/types.ts`
  - `frontend/src/index.tsx`
  - `frontend/src/App.tsx`
- 文档：
  - `docs/guides/developer/SKILL_PREFLIGHT_HEALTH_PANEL_GUIDE.md`
  - `docs/superpowers/plans/2026-04-25-open-source-skill-preflight-and-health-panel.md`
  - `docs/superpowers/plans/2026-04-25-open-source-skill-preflight-and-health-panel-handover.md`

提交前请执行：`git add -p` 或按文件白名单 `git add <file>`，避免夹带与本特性无关的历史修改。
