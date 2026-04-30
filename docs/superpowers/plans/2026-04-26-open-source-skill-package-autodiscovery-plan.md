# Open Source Skill Package Auto-Discovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让开源 skill package 在复制到目标目录并重启 Yue 后自动发现；依赖满足时可安全执行 package 中声明的 scripts/resources/actions，依赖不满足时给出可操作修复建议。

**Architecture:** 采用统一“Skill 包接入网关”：启动扫描发现 -> 兼容解析（manifest 优先，SKILL.md 回退）-> 依赖预检与能力分级 -> 默认手动审批执行 -> 结构化结果与可观测闭环。执行路径统一下沉到技能服务层，避免 chat 入口直接耦合执行细节。

**Tech Stack:** Python/FastAPI、Yue skill registry/preflight/runtime、Pytest、TypeScript React SkillHealth 页面。

---

## Scope And Constraints

- 约束 1：先实现“启动时扫描自动发现”，暂不做热加载。
- 约束 2：解析策略为“manifest 优先，缺失时 SKILL.md + 目录结构回退推断”。
- 约束 3：第三方 skill action 默认 `manual approval`，不直接信任 package 内自动执行声明。
- 范围内：`backend/app/services/skills/*`、`backend/app/api/*`、`backend/tests/*`、`frontend/src/pages/SkillHealth.tsx`、相关文档。
- 范围外：实时目录监听、跨进程分布式执行器、远端依赖自动安装。

## Milestones

- M1（P0）：重启后自动发现第三方 skill package。
- M2（P0）：兼容解析产出统一 action/resource/script 模型。
- M3（P0）：依赖满足时 action 可经审批后真实执行。
- M4（P1）：Health 面板展示可用等级、阻塞项和修复命令。
- M5（P1）：测试与发布门禁覆盖核心回归场景。

## Chunk 1: 启动扫描自动发现（P0）

### Task 1.1 启动阶段接入统一扫描入口

**Files:**
- Modify: `backend/app/services/skills/bootstrap.py`
- Modify: `backend/app/services/skill_service.py`
- Modify: `backend/app/services/skills/preflight_service.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [ ] **Step 1: 写失败测试（启动后应包含新复制 skill）**

```python
def test_startup_refresh_discovers_copied_skill_package(...):
    # 构造临时目录并复制样例 skill 包
    # 初始化 runtime
    # 断言 preflight records 包含目标 skill_name
```

- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_runtime_integration.py -q -k startup_refresh_discovers`  
Expected: FAIL（未在启动阶段发现新包）

- [ ] **Step 3: 实现启动扫描调用链**
- [ ] **Step 4: 再次运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_runtime_integration.py -q -k startup_refresh_discovers`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/skills/bootstrap.py backend/app/services/skill_service.py backend/app/services/skills/preflight_service.py backend/tests/test_skill_runtime_integration.py
git commit -m "feat(skill): auto-discover skill packages at startup"
```

## Chunk 2: 兼容解析（manifest 优先 + 回退推断）（P0）

### Task 2.1 建立 package 兼容解析器

**Files:**
- Modify: `backend/app/services/skills/parsing.py`
- Modify: `backend/app/services/skills/models.py`
- Test: `backend/tests/test_skill_foundation_unit.py`

- [ ] **Step 1: 写失败测试（无 manifest 的 SKILL.md 包可被推断解析）**

```python
def test_parse_package_fallback_from_skill_md_and_layout(...):
    # 仅提供 SKILL.md + scripts/ + references/
    # 断言解析结果包含推断出的 scripts/resources/actions
```

- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_foundation_unit.py -q -k fallback_from_skill_md`  
Expected: FAIL

- [ ] **Step 3: 实现 manifest 优先 + 回退推断逻辑**
- [ ] **Step 4: 为回退推断结果添加 warning/来源标签（例如 inferred_from_layout）**
- [ ] **Step 5: 运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_foundation_unit.py -q -k fallback_from_skill_md`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/skills/parsing.py backend/app/services/skills/models.py backend/tests/test_skill_foundation_unit.py
git commit -m "feat(skill): add manifest-first compatible package parser"
```

## Chunk 3: 预检能力分级与修复建议（P0）

### Task 3.1 扩展依赖与资源检查矩阵

**Files:**
- Modify: `backend/app/services/skills/preflight_service.py`
- Modify: `backend/app/services/skills/import_models.py`
- Modify: `backend/app/api/skill_preflight.py`
- Test: `backend/tests/test_api_skill_preflight.py`

- [ ] **Step 1: 写失败测试（依赖缺失时返回 needs_fix + fix_command）**
- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_skill_preflight.py -q -k needs_fix`  
Expected: FAIL

- [ ] **Step 3: 实现标准状态机 `available/needs_fix/unavailable` 与结构化建议字段**
- [ ] **Step 4: 补齐 scripts/resources/actions 缺失的分项提示**
- [ ] **Step 5: 运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_skill_preflight.py -q -k needs_fix`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/skills/preflight_service.py backend/app/services/skills/import_models.py backend/app/api/skill_preflight.py backend/tests/test_api_skill_preflight.py
git commit -m "feat(skill): expose preflight capability levels and fix commands"
```

## Chunk 4: 统一执行调度与默认手动审批（P0）

### Task 4.1 下沉执行路径到 SkillActionDispatcher

**Files:**
- Create: `backend/app/services/skills/action_dispatcher.py`
- Modify: `backend/app/services/skills/actions.py`
- Modify: `backend/app/api/chat_stream_runner.py`
- Test: `backend/tests/test_api_chat_unit.py`
- Test: `backend/tests/test_excalidraw_skill_actions_unit.py`

- [ ] **Step 1: 写失败测试（审批通过后可执行，未审批不可执行）**
- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_chat_unit.py -q -k requested_action`  
Expected: FAIL

- [ ] **Step 3: 实现 `SkillActionDispatcher.execute()` 统一执行和事件上报**
- [ ] **Step 4: 在 chat_stream_runner 中改为调用 dispatcher，不直接执行工具**
- [ ] **Step 5: 强制第三方包默认 manual approval（平台策略优先于 package 声明）**
- [ ] **Step 6: 运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_chat_unit.py backend/tests/test_excalidraw_skill_actions_unit.py -q`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/skills/action_dispatcher.py backend/app/services/skills/actions.py backend/app/api/chat_stream_runner.py backend/tests/test_api_chat_unit.py backend/tests/test_excalidraw_skill_actions_unit.py
git commit -m "feat(skill): unify action execution dispatch with manual-approval default"
```

## Chunk 5: scripts/resources 全量利用策略（P1）

### Task 5.1 资源索引与参数注入

**Files:**
- Modify: `backend/app/services/skills/routing.py`
- Modify: `backend/app/services/skills/excalidraw_orchestrator.py`
- Modify: `backend/app/services/skills/actions.py`
- Test: `backend/tests/test_excalidraw_orchestrator_unit.py`

- [ ] **Step 1: 写失败测试（请求执行时可命中资源索引并透传到脚本参数）**
- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_excalidraw_orchestrator_unit.py -q -k resource_index`  
Expected: FAIL

- [ ] **Step 3: 实现 resources/scripts/references 索引器并接入参数构建**
- [ ] **Step 4: 在结果中回传 `resource_resolution_trace` 便于排障**
- [ ] **Step 5: 运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_excalidraw_orchestrator_unit.py -q -k resource_index`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/skills/routing.py backend/app/services/skills/excalidraw_orchestrator.py backend/app/services/skills/actions.py backend/tests/test_excalidraw_orchestrator_unit.py
git commit -m "feat(skill): add full resource indexing and argument injection"
```

## Chunk 6: 前端健康与可观测闭环（P1）

### Task 6.1 展示能力等级与最近执行状态

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/SkillHealth.tsx`
- Modify: `frontend/src/pages/SkillHealth.test.ts`
- Modify: `backend/app/api/skill_preflight.py`

- [ ] **Step 1: 写失败测试（Health 页面显示等级/阻塞项/修复命令/最近成功率）**
- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm test -- /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.test.ts`  
Expected: FAIL

- [ ] **Step 3: 扩展 API 与前端类型，渲染新增字段**
- [ ] **Step 4: 运行测试验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm test -- /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/pages/SkillHealth.tsx frontend/src/pages/SkillHealth.test.ts backend/app/api/skill_preflight.py
git commit -m "feat(skill-health): expose capability level blockers and success rate"
```

## Chunk 7: 回归门禁与交付文档（P1）

### Task 7.1 建立发布前硬门禁

**Files:**
- Modify: `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- Create: `docs/guides/developer/OPEN_SOURCE_SKILL_PACKAGE_ONBOARDING_CHECKLIST.md`
- Modify: `backend/tests/test_skill_runtime_integration.py`

- [ ] **Step 1: 写失败测试（copy 开源包并重启后可发现 + 审批后可执行）**
- [ ] **Step 2: 运行测试验证 RED**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_runtime_integration.py -q -k onboarding_smoke`  
Expected: FAIL

- [ ] **Step 3: 补齐 smoke 场景并形成 checklist（发现/预检/审批/执行/回滚）**
- [ ] **Step 4: 运行完整回归验证 GREEN**

Run: `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_runtime_integration.py backend/tests/test_api_chat_unit.py backend/tests/test_api_skill_preflight.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md docs/guides/developer/OPEN_SOURCE_SKILL_PACKAGE_ONBOARDING_CHECKLIST.md backend/tests/test_skill_runtime_integration.py
git commit -m "docs(skill): add onboarding checklist and release gates for open-source packages"
```

## Verification Commands (Final Gate)

- [ ] `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_foundation_unit.py -q`
- [ ] `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_skill_preflight.py -q`
- [ ] `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_api_chat_unit.py -q`
- [ ] `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend && PYTHONPATH=. pytest backend/tests/test_skill_runtime_integration.py -q`
- [ ] `cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend && npm test -- /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.test.ts`

## Rollback Strategy

- 快速回滚：关闭第三方 skill action 调度，仅保留 discover + preflight 可见性。
- 安全回滚：保持 `manual approval` 默认策略，不回滚该保护措施。
- 数据回滚：执行失败时不删除已有产物，保留 `artifact_path` 便于人工恢复。

## Definition Of Done

- 将开源 skill package 复制到目标目录并重启 Yue 后，系统自动发现并展示该 skill。
- 在依赖满足前提下，skill package 的声明动作可在审批后真实执行，且事件与产物路径完整。
- 在依赖不满足时，系统返回 `needs_fix/unavailable` 与明确修复指令，不发生静默失败。
- Health 页面可展示能力等级、阻塞项、修复命令与最近执行成功率。
