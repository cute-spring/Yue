# Agent 分类与 Skill 分组挂载 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持现有 `skill_mode/visible_skills` 兼容的前提下，引入“传统 agent / 通用型 agent”分类与可复用的 skill group 机制，并完成后端、前端、迁移与测试闭环。

**Architecture:** 在 Agent 层新增 `agent_kind` 与 `skill_groups`，在 Skill Runtime 层增加“group -> visible skills”解析器，将技能可见性从“单 agent 手工维护”升级为“组装式治理”。运行时仍沿用现有路由、阈值与工具交集策略，只替换可见技能来源并补充观测字段，实现低风险渐进演进。

**Tech Stack:** FastAPI + Pydantic + JSON 文件持久化（backend）；SolidJS + TypeScript（frontend）；Pytest + Vitest/E2E（验证）。

---

## 文件结构与职责

- Modify: `backend/app/services/agent_store.py`
  - 扩展 `AgentConfig` 字段：`agent_kind/skill_groups/extra_visible_skills/resolved_visible_skills`
  - 保持旧字段 `skill_mode/visible_skills` 可读可写，兼容历史数据
- Create: `backend/app/services/skill_group_store.py`
  - 新增 `SkillGroupConfig` 数据模型与 JSON 持久化（原子写、备份恢复）
- Create: `backend/app/api/skill_groups.py`
  - 暴露 skill group CRUD + list API
- Modify: `backend/app/main.py`
  - 注册 `/api/skill-groups` 路由
- Modify: `backend/app/services/skill_service.py`
  - 将 `SkillRouter.get_visible_skills()` 改为支持 group 解析与降级策略
- Modify: `backend/app/api/chat.py`
  - 运行时改用解析后的 visible skills，补充 group 观测字段
- Create: `backend/scripts/migrate_agents_to_agent_kind_groups.py`
  - 一次性迁移历史 agent 到新字段
- Create: `backend/tests/test_skill_group_store_unit.py`
  - skill group 存储与恢复单测
- Modify/Create: `backend/tests/test_agent_store_unit.py`, `backend/tests/test_skill_runtime_integration.py`, `backend/tests/test_api_skills.py`
  - 覆盖分类、分组解析、路由与兼容路径
- Modify: `frontend/src/types.ts`
  - 增加 Agent/SkillGroup 新类型字段
- Modify: `frontend/src/components/AgentForm.tsx`
  - 新增 agent 类型切换、skill group 选择与兼容提示
- Modify: `frontend/src/pages/Agents.tsx`
  - 加载与提交 skill groups，维护表单状态
- Modify: `frontend/src/pages/Chat.tsx`
  - Manual 模式下优先使用 `resolved_visible_skills` 渲染技能选项
- Create/Modify: `frontend/e2e/skills-runtime-ui.spec.ts`
  - 验证两类 agent 与 group 挂载行为

---

## Chunk 1: 后端数据契约与存储层

### Task 1: 新增 Skill Group 持久化存储

**Files:**
- Create: `backend/app/services/skill_group_store.py`
- Test: `backend/tests/test_skill_group_store_unit.py`

- [x] **Step 1: 写失败单测（SkillGroupConfig 模型 + 基础 CRUD）**

```python
def test_create_and_list_skill_groups(tmp_path):
    store = SkillGroupStore(data_dir=str(tmp_path))
    created = store.create_group(SkillGroupConfig(name="backend-debug", skill_refs=["backend-api-debugger:1.0.0"]))
    groups = store.list_groups()
    assert created.name == "backend-debug"
    assert any(g.id == created.id for g in groups)
```

- [x] **Step 2: 运行单测，确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_group_store_unit.py -q`  
Expected: FAIL（`ModuleNotFoundError` 或 `SkillGroupStore` 未定义）

- [x] **Step 3: 实现最小 SkillGroupStore**

```python
class SkillGroupConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    skill_refs: List[str] = []
```

- [x] **Step 4: 再次运行单测，确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_group_store_unit.py -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/app/services/skill_group_store.py backend/tests/test_skill_group_store_unit.py
git commit -m "feat: add skill group store with atomic persistence"
```

### Task 2: 扩展 AgentConfig 支持分类与分组字段

**Files:**
- Modify: `backend/app/services/agent_store.py`
- Test: `backend/tests/test_agent_store_unit.py`

- [x] **Step 1: 写失败单测（默认值与兼容加载）**

```python
def test_agent_config_defaults_include_agent_kind():
    cfg = AgentConfig(name="x", system_prompt="y")
    assert cfg.agent_kind == "traditional"
    assert cfg.skill_groups == []
```

- [x] **Step 2: 运行单测，确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_agent_store_unit.py -q`  
Expected: FAIL（字段不存在）

- [x] **Step 3: 实现最小字段扩展与兼容映射**

```python
class AgentConfig(BaseModel):
    agent_kind: str = "traditional"
    skill_groups: List[str] = []
    extra_visible_skills: List[str] = []
```

- [x] **Step 4: 再次运行单测，确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_agent_store_unit.py -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/app/services/agent_store.py backend/tests/test_agent_store_unit.py
git commit -m "feat: extend agent config with kind and skill groups"
```

### Task 3: 增加 Skill Groups API

**Files:**
- Create: `backend/app/api/skill_groups.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_skill_groups.py`

- [x] **Step 1: 写失败 API 测试（list/create/update/delete）**
- [x] **Step 2: 运行测试，确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_api_skill_groups.py -q`  
Expected: FAIL（404 或 router 未注册）

- [x] **Step 3: 实现 API 与路由注册**
- [x] **Step 4: 运行测试，确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_api_skill_groups.py -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/app/api/skill_groups.py backend/app/main.py backend/tests/test_api_skill_groups.py
git commit -m "feat: add skill group CRUD api"
```

---

## Chunk 2: Runtime 解析与路由接入

### Task 4: 实现 group -> visible skills 解析器

**Files:**
- Modify: `backend/app/services/skill_service.py`
- Modify: `backend/app/services/skill_group_store.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [x] **Step 1: 写失败测试（group + extra + legacy visible_skills 合并去重）**
- [x] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_runtime_integration.py -k visible -q`  
Expected: FAIL

- [x] **Step 3: 实现解析逻辑**

```python
resolved = dedupe(group_skill_refs + agent.extra_visible_skills + legacy_visible_skills_fallback)
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_runtime_integration.py -k visible -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/app/services/skill_service.py backend/tests/test_skill_runtime_integration.py backend/app/services/skill_group_store.py
git commit -m "feat: resolve visible skills from skill groups"
```

### Task 5: Chat Runtime 接入新可见技能来源与观测

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/test_skill_runtime_integration.py`

- [x] **Step 1: 写失败测试（manual/auto 模式下使用 resolved skills）**
- [x] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_runtime_integration.py -k "manual or auto" -q`  
Expected: FAIL

- [x] **Step 3: 实现接入**
  - 仅替换可见技能来源，不改动现有阈值策略
  - 追加观测字段：`selected_group_ids`, `resolved_skill_count`
- [x] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_runtime_integration.py -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/app/api/chat.py backend/app/services/chat_service.py backend/tests/test_skill_runtime_integration.py
git commit -m "feat: wire skill-group visibility into chat runtime"
```

### Task 6: 编写迁移脚本（历史数据平滑升级）

**Files:**
- Create: `backend/scripts/migrate_agents_to_agent_kind_groups.py`
- Test: `backend/tests/test_agent_store_persistence.py`

- [x] **Step 1: 写失败测试（dry-run 报告 + 实际迁移）**
- [x] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_agent_store_persistence.py -k migrate -q`  
Expected: FAIL

- [x] **Step 3: 实现迁移脚本**
  - `skill_mode=off` -> `agent_kind=traditional`
  - `skill_mode!=off` -> `agent_kind=universal` + 生成 legacy group
- [x] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH=$(pwd) pytest tests/test_agent_store_persistence.py -k migrate -q`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add backend/scripts/migrate_agents_to_agent_kind_groups.py backend/tests/test_agent_store_persistence.py
git commit -m "feat: add migration script for agent kind and skill groups"
```

---

## Chunk 3: 前端配置与交互改造

### Task 7: 前端类型与数据流扩展

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/Agents.tsx`

- [x] **Step 1: 先写类型/状态失败断言（如有现成测试则补测试）**
- [x] **Step 2: 运行前端测试确认失败**

Run: `cd frontend && npm run test -- Agents`  
Expected: FAIL（类型或字段缺失）

- [x] **Step 3: 实现字段接入**

```ts
type Agent = {
  agent_kind?: 'traditional' | 'universal';
  skill_groups?: string[];
  extra_visible_skills?: string[];
}
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd frontend && npm run test -- Agents`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add frontend/src/types.ts frontend/src/pages/Agents.tsx
git commit -m "feat: extend frontend agent model for skill groups"
```

### Task 8: AgentForm 增加“类型 + 分组 + 补充技能”配置

**Files:**
- Modify: `frontend/src/components/AgentForm.tsx`
- Modify: `frontend/src/components/AgentCard.tsx`
- Test: `frontend/e2e/skills-runtime-ui.spec.ts`

- [x] **Step 1: 新增 E2E 失败用例（切换类型、选择 group、保存回显）**
- [x] **Step 2: 运行 E2E 确认失败**

Run: `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`  
Expected: FAIL

- [x] **Step 3: 实现表单交互与提交 payload**
- [x] **Step 4: 运行 E2E 确认通过**

Run: `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add frontend/src/components/AgentForm.tsx frontend/src/components/AgentCard.tsx frontend/e2e/skills-runtime-ui.spec.ts
git commit -m "feat: add agent kind and skill group form controls"
```

### Task 9: Chat 手动模式技能选择兼容 resolved 列表

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`
- Modify: `frontend/src/hooks/useChatState.ts`
- Test: `frontend/e2e/skills-runtime-ui.spec.ts`

- [x] **Step 1: 写失败 E2E（通用 agent 下 skill selector 正常可选）**
- [x] **Step 2: 运行 E2E 确认失败**

Run: `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`  
Expected: FAIL

- [x] **Step 3: 实现优先使用 `resolved_visible_skills` 的渲染逻辑**
- [x] **Step 4: 再跑 E2E 确认通过**

Run: `cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`  
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add frontend/src/pages/Chat.tsx frontend/src/hooks/useChatState.ts frontend/e2e/skills-runtime-ui.spec.ts
git commit -m "feat: support resolved visible skills in chat selector"
```

---

## Chunk 4: 联调、回归与发布门禁

### Task 10: 全量回归与发布前检查

**Files:**
- Modify: `docs/TESTING.md`（补充新能力验证步骤）
- Modify: `docs/plans/agent_classification_and_skill_group_plan_20260319.md`（勾选完成项）

- [x] **Step 1: 后端核心回归**

Run:
`cd backend && PYTHONPATH=$(pwd) pytest tests/test_skill_group_store_unit.py tests/test_agent_store_unit.py tests/test_api_skill_groups.py tests/test_skill_runtime_integration.py -v`  
Expected: PASS

- [x] **Step 2: 前端核心回归**

Run:
`cd frontend && npm run test -- AgentForm`  
Expected: PASS

- [x] **Step 3: E2E 回归**

Run:
`cd frontend && npm run test:e2e -- skills-runtime-ui.spec.ts`  
Expected: PASS

- [x] **Step 4: 项目质量门禁**

Run:
`./check.sh`  
Expected: 全部通过；若失败，记录是历史基线债务还是本次引入

- [x] **Step 5: 发布策略**
  - 先灰度：仅 `agent_kind=universal` 且指定 group 的 agent 生效
  - 提供一键回滚：关闭 runtime flag 或迁移脚本回滚文件
  - 观察 24 小时：`skill_selected` 成功率、fallback 比例、工具拒绝率

- [x] **Step 6: 提交**

```bash
git add docs/TESTING.md docs/plans/agent_classification_and_skill_group_plan_20260319.md
git commit -m "docs: finalize rollout and verification plan for agent kind and skill groups"
```

---

## 风险清单与缓解

- [x] **兼容性风险：** 老 agent 无 `agent_kind` 字段导致行为偏差  
  缓解：后端默认值 + 迁移脚本 dry-run 报告
- [x] **配置膨胀风险：** group 与 extra_visible_skills 叠加导致理解困难  
  缓解：UI 提供“最终可见技能数”和来源标签
- [x] **路由误选风险：** 可见技能增多后 auto 模式误判提升  
  缓解：保留阈值，增加切换冷却窗口（后续优化项）
- [x] **发布风险：** 前后端字段不一致  
  缓解：先后端兼容上线，再前端启用入口，最后迁移数据

---

## 验收标准（Definition of Done）

- [x] 支持两类 agent：`traditional` / `universal`，并可在 UI 配置
- [x] 支持 skill group CRUD，并可挂载到多个 agent
- [x] runtime 使用解析后的可见技能集合，旧 `visible_skills` 仍可兼容
- [x] manual / auto 路由与工具交集策略保持稳定
- [x] 新增测试通过，`./check.sh` 可执行并记录结果
- [x] 提供可回滚迁移路径与运行观测指标
