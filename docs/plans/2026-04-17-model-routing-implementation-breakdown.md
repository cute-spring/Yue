# Model Routing Implementation Breakdown (2026-04-17)

> Status: Draft
> Parent plan: `docs/plans/2026-04-17-model-routing-configuration-plan.md`
> Scope: backend + frontend + config schema + observability

## 1. Goal

把“默认通用模型 + 复杂任务模型”的产品想法，收敛成一版可开发、可验收、可逐步上线的实现任务。

本次拆解遵循两个约束：

1. 不推翻当前 `provider/model` 体系。
2. 第一版先做最小可用闭环，再逐步细化到翻译/推理/工具调用角色。

## 2. Recommended Delivery Order

建议分 4 个阶段推进：

1. Phase 1: 配置与数据模型打底
2. Phase 2: 后端运行时路由接入
3. Phase 3: 前端设置页与 Agent 配置接入
4. Phase 4: 观测、灰度、规则优化

这样做的原因是：

- Phase 1 能先把数据结构固定住。
- Phase 2 能尽早验证核心路由逻辑。
- Phase 3 再把能力开放给用户配置。
- Phase 4 用于稳定上线，而不是把可观测性拖到最后补。

## 3. Phase 1: 配置与数据模型

### Task 1.1: 定义全局 `llm.routing` 配置结构

**目标**

在 `global_config.json` 的 `llm` 下新增 `routing` 配置，支持系统级模型角色映射。

**Files**

- Modify: `backend/app/services/config_service.py`
- Modify: `docs/guides/developer/CONFIGURATION.md`
- Reference: `backend/data/global_config.json.example`

**Steps**

- [ ] 在 `ConfigService` 中新增 `get_llm_routing_config()`
- [ ] 定义默认结构：
  - `default_mode`
  - `fallback_policy`
  - `auto_upgrade_enabled`
  - `roles.general_chat`
  - `roles.tool_use`
  - `roles.reasoning`
- [ ] 支持 `inherit` 语义
- [ ] 缺省情况下回退到 legacy 模式
- [ ] 更新开发者配置文档

**Acceptance**

- 未配置 `llm.routing` 时，系统行为不变
- 读取配置时能返回完整默认值
- `inherit` 角色能被正确解析

### Task 1.2: 扩展 Agent 数据模型

**目标**

让 Agent 可以声明“优先走哪个模型角色”，但仍兼容现有 `provider/model`。

**Files**

- Modify: `backend/app/services/agent_store.py`
- Modify: `backend/app/api/agents.py`
- Modify: `frontend/src/pages/settings/types.ts`

**Steps**

- [ ] 给 `AgentConfig` 增加字段：
  - `model_role`
  - `model_policy`
  - `upgrade_on_tools`
  - `upgrade_on_multi_skill`
- [ ] 在 `AgentConfigPublic` 中暴露上述字段
- [ ] 为旧 Agent 自动补默认值
- [ ] 确保现有内置 Agent 不需要立即重写

**Acceptance**

- 老的 `agents.json` 能正常加载
- 新字段缺失时不报错
- Agent API 能正确返回和保存新增字段

### Task 1.3: 设计统一的运行时解析对象

**目标**

为后续路由逻辑定义统一返回结构，避免到处散落 `provider/model` 判定。

**Files**

- New: `backend/app/services/llm/routing.py`

**Recommended shape**

```python
class ResolvedModel(BaseModel):
    provider: str
    model: str
    role: str | None = None
    resolution_source: str
    fallback_used: bool = False
    upgrade_trigger: str | None = None
```

**Steps**

- [ ] 定义 `ResolvedModel`
- [ ] 定义 `RoutingContext`
- [ ] 约定 `resolution_source` 枚举值：
  - `request_override`
  - `agent_role`
  - `system_role`
  - `auto_upgrade`
  - `legacy_agent_model`
  - `legacy_global_default`

**Acceptance**

- 路由层可以独立返回结构化结果
- 业务层不再自行拼 `provider/model`

## 4. Phase 2: 后端运行时路由

### Task 2.1: 实现角色解析

**目标**

将 `role -> provider/model` 的解析逻辑集中封装。

**Files**

- New: `backend/app/services/llm/routing.py`
- Modify: `backend/app/services/config_service.py`

**Steps**

- [ ] 实现 `resolve_role_config(role_name)`
- [ ] 支持 `inherit`
- [ ] 角色不存在时按 `fallback_policy` 回退
- [ ] 与 `custom_models` 保持兼容

**Acceptance**

- `general_chat`、`tool_use`、`reasoning` 都可被解析
- 配置缺失时回退稳定
- 不引入循环继承风险

### Task 2.2: 实现运行时模型选择主入口

**目标**

提供统一的 `resolve_runtime_model(...)`，作为所有聊天/Agent/Skill 路径的唯一入口。

**Files**

- New: `backend/app/services/llm/routing.py`

**Recommended API**

```python
def resolve_runtime_model(
    *,
    request_provider: str | None,
    request_model: str | None,
    request_model_role: str | None,
    agent_config: AgentConfig | None,
    has_tools: bool,
    selected_tool_count: int,
    skill_count: int,
    has_images: bool,
    task_hints: list[str] | None = None,
) -> ResolvedModel:
    ...
```

**Steps**

- [ ] 实现请求级 override 优先
- [ ] 实现 Agent `model_policy=force_direct`
- [ ] 实现 Agent `model_role`
- [ ] 实现 `has_tools -> tool_use`
- [ ] 实现 `skill_count > 1 -> reasoning`
- [ ] 实现 `has_images -> vision capability check`
- [ ] 实现 legacy fallback

**Acceptance**

- 同一条请求只经过一个模型解析入口
- 工具调用场景能切到 `tool_use`
- 多 Skill 场景能切到 `reasoning`
- 轻量任务不会无故升级

### Task 2.3: 识别“轻任务”和“复杂任务”

**目标**

先用可解释规则，而不是复杂分类器。

**Files**

- New or Modify: `backend/app/services/llm/routing.py`
- Possibly modify: `backend/app/services/chat_prompting.py`
- Possibly modify: `backend/app/services/skill_service.py`

**Steps**

- [ ] 增加基础 hint 生成逻辑：
  - `translation`
  - `summarization`
  - `rewrite`
  - `analysis`
  - `planning`
- [ ] 先用简单关键词和上下文特征判定
- [ ] 翻译命中时优先使用 `translation`，未配置时回退 `general_chat`

**Acceptance**

- 翻译类请求能命中轻量角色
- 复杂分析请求不会被错误地压到轻模型

### Task 2.4: 接入聊天主链路

**目标**

在真正创建模型实例前，统一调用路由层。

**Files**

- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/app/services/chat_runtime.py`
- Modify: `backend/app/api/chat_schemas.py`

**Steps**

- [ ] 给 chat request 增加可选字段 `model_role`
- [ ] 进入聊天主链路时构造 `RoutingContext`
- [ ] 用 `ResolvedModel.provider/model` 替换原始直连
- [ ] 保持现有请求参数兼容

**Acceptance**

- 普通聊天仍可正常工作
- 显式传 `provider/model` 时优先级正确
- 显式传 `model_role` 时可以生效

### Task 2.5: 接入 Agent 与 Skill 路径

**目标**

避免只在普通聊天接入，导致 Agent/Skill 仍走旧逻辑。

**Files**

- Modify: `backend/app/services/skill_service.py`
- Modify: `backend/app/services/skills/routing.py`
- Modify: `backend/app/api/agents.py`

**Steps**

- [ ] Agent 执行前统一构造路由上下文
- [ ] Skill 自动选择后把 `skill_count` 传入模型解析
- [ ] 工具型 Agent 根据 `enabled_tools` 决定是否允许升级

**Acceptance**

- 工具型 Agent 能正确走复杂任务模型
- 翻译型 Agent 能优先走轻模型角色
- Skill 自动模式与新路由兼容

## 5. Phase 3: 前端与配置体验

### Task 3.1: 设置页新增 `Model Routing` 分组

**目标**

在当前 LLM 设置页中提供最小但可用的路由配置 UI。

**Files**

- Modify: `frontend/src/pages/settings/components/LlmSettingsTab.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/settings/types.ts`

**Steps**

- [ ] 新增 `Model Routing` UI 区块
- [ ] 提供两个主要选择器：
  - 默认通用模型
  - 复杂任务模型
- [ ] 每个选择器支持 provider + model
- [ ] 增加说明文案
- [ ] 保存到 `llm.routing.roles.general_chat/tool_use/reasoning`

**Acceptance**

- 用户可在 UI 中配置两档模型
- 未配置时页面显示合理默认值
- 保存后刷新仍能正确回显

### Task 3.2: 高级路由设置

**目标**

给高级用户开放更细粒度控制，但默认折叠。

**Files**

- Modify: `frontend/src/pages/settings/components/LlmSettingsTab.tsx`

**Steps**

- [ ] 增加高级折叠面板
- [ ] 提供：
  - 翻译模型角色
  - 自动升级开关
  - fallback policy
- [ ] 清晰标注“高级配置”

**Acceptance**

- 默认界面不复杂
- 高级用户能配置更细规则

### Task 3.3: Agent 编辑表单接入

**目标**

支持按 Agent 覆盖系统默认模型策略。

**Files**

- Modify: `frontend/src/components/AgentForm.tsx`
- Modify: `frontend/src/components/AgentForm.test.tsx`
- Modify: `frontend/src/types.ts`

**Steps**

- [ ] 增加 `model_role` 字段
- [ ] 增加 `model_policy` 下拉框
- [ ] 增加两个升级开关
- [ ] 默认隐藏在高级设置中

**Acceptance**

- Agent 可配置默认角色
- 不修改旧 Agent 时，表现不变

## 6. Phase 4: 观测与灰度

### Task 4.1: 增加路由决策日志

**目标**

把“最后到底选了哪个模型、为什么选它”记录下来。

**Files**

- Modify: `backend/app/services/chat_runtime.py`
- Modify: `backend/app/api/chat_trace_schemas.py`
- Modify: `backend/app/observability.py`

**Steps**

- [ ] 在 trace/log 中增加字段：
  - `resolved_provider`
  - `resolved_model`
  - `resolved_role`
  - `resolution_source`
  - `upgrade_trigger`
- [ ] 记录 `tool_count`、`skill_count`
- [ ] 避免泄漏敏感 prompt 内容

**Acceptance**

- 每次请求都能追溯模型决策来源
- 调试时能区分是配置命中还是自动升级

### Task 4.2: 灰度开关

**目标**

支持先对少量请求或仅测试环境开启新路由。

**Files**

- Modify: `backend/app/services/config_service.py`
- Modify: `backend/app/core/settings.py`

**Steps**

- [ ] 增加 feature flag：
  - `llm_routing_enabled`
  - `llm_routing_auto_upgrade_enabled`
- [ ] 让新逻辑可被整体关闭

**Acceptance**

- 可以快速回退到 legacy 模式
- 上线风险可控

### Task 4.3: 基础评估看板数据

**目标**

让后续规则优化有数据依据。

**Files**

- Modify: existing logging/metrics pipeline if available

**Steps**

- [ ] 统计各角色请求次数
- [ ] 统计各角色平均耗时
- [ ] 统计各角色 token 使用
- [ ] 统计复杂任务升级比例

**Acceptance**

- 能回答“轻任务是否真的走了轻模型”
- 能回答“复杂任务升级后是否提升成功率”

## 7. Testing Breakdown

### Backend unit tests

**Suggested files**

- New: `backend/tests/test_llm_routing_unit.py`

**Cases**

- [ ] 无 `llm.routing` 时走 legacy
- [ ] `model_role` 命中系统角色
- [ ] `inherit` 角色解析
- [ ] `force_direct` 优先级
- [ ] `has_tools -> tool_use`
- [ ] `skill_count > 1 -> reasoning`
- [ ] `translation hint -> translation/general_chat`
- [ ] vision 缺失时切换支持 vision 的模型

### Backend integration tests

**Suggested files**

- Modify: `backend/tests/test_api_chat_unit.py`
- Modify: `backend/tests/test_agents_generate_api.py`

**Cases**

- [ ] chat request 传 `model_role`
- [ ] chat request 传 `provider/model`
- [ ] Agent 配置 `model_role`
- [ ] Skill 自动模式与路由兼容

### Frontend tests

**Suggested files**

- Modify: `frontend/e2e/settings-general.spec.ts`
- Modify: `frontend/e2e/custom-models.spec.ts`
- New: `frontend/e2e/model-routing-settings.spec.ts`
- Modify: `frontend/src/components/AgentForm.test.tsx`

**Cases**

- [ ] 设置页显示并保存两档模型
- [ ] 高级路由配置可展开
- [ ] AgentForm 可保存 `model_role`

## 8. Recommended PR Split

建议拆成 4 个 PR，评审压力最小。

### PR 1: Schema + backend config foundation

**Includes**

- `llm.routing` schema
- `AgentConfig` 扩展
- unit tests

**Do not include**

- chat runtime 改造
- frontend UI

### PR 2: Runtime routing

**Includes**

- `routing.py`
- chat/agent/skill 接入
- backend integration tests

### PR 3: Settings + Agent UI

**Includes**

- 设置页 `Model Routing`
- AgentForm 高级配置
- frontend tests

### PR 4: Observability + rollout controls

**Includes**

- trace/log 字段
- feature flags
- 文档补齐

## 9. Risks And Mitigations

### Risk 1: 路由逻辑散落，最后变成“多处判定”

**Mitigation**

- 强制所有入口调用 `resolve_runtime_model()`
- 不允许在业务层再次硬编码任务复杂度判断

### Risk 2: 与现有 capability 推断职责冲突

**Mitigation**

- `capabilities.py` 只负责模型能力识别
- `routing.py` 只负责模型选择

### Risk 3: UI 配置过重

**Mitigation**

- 第一版只露出两个主配置位
- 高级配置默认折叠

### Risk 4: 老 Agent 行为回归

**Mitigation**

- 默认为 legacy 兼容
- 引入 feature flag
- Agent 默认 `model_policy=prefer_role` 但无 role 时回退 direct model

## 10. Suggested Team Assignment

如果要并行推进，建议这样分工：

### Backend A

- `ConfigService`
- `routing.py`
- chat runtime 接入

### Backend B

- `AgentConfig` / agents API
- skill routing 接入
- backend tests

### Frontend

- Settings `Model Routing`
- AgentForm 高级配置
- e2e / component tests

### QA / Product

- 验证翻译类、工具类、复杂推理类三条典型链路
- 验证 fallback 和灰度开关

## 11. Definition Of Done

满足以下条件，才算这一能力真正可交付：

- [ ] `llm.routing` 配置已支持并默认兼容 legacy
- [ ] Agent 支持 `model_role` 与 `model_policy`
- [ ] Chat / Agent / Skill 共用一个运行时模型解析入口
- [ ] 设置页可以配置两档模型
- [ ] 关键路由决策可观测
- [ ] 有单测、集成测试和基础前端验证
- [ ] 可以通过 feature flag 一键回退

