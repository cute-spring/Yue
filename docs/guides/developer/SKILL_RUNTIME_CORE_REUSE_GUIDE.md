# Skill Runtime Core 复用与迁移指南

## 1. 这份指南解决什么问题

这份文档面向“想把 Yue 里的 Skill Runtime Core 拷贝到另一个同栈项目”的开发者。

目标不是把整个 Yue 搬过去，而是只迁移 **技能解析、导入门禁、兼容性评估、路由、运行时上下文、以及最小的宿主适配层**，让目标项目用很少的配置就能跑起来。

如果你只想要结论：

- 先复制 `backend/app/services/skills/` 这组核心包
- 再补一个很薄的 host adapter
- 然后在目标项目启动时调用 bootstrap
- 最后把目标项目自己的 agent/config/store 接口接进去

这套东西的设计思路是：

1. 核心逻辑尽量不懂 Yue
2. Yue 只保留宿主相关的适配层
3. 迁移时尽量“加适配，不改核心”

---

## 2. 你真正复用的是什么

当前可复用部分主要分成三层。

这里先说一个非常重要的边界：

- **现在就能稳定复制的**，是“core candidate + transition shell”的组合
- **未来真正想沉淀成独立可复用包的**，是纯 `skill runtime core`
- 所以这份指南讲的是“今天怎么安全迁移”，不是假装当前已经完全完成 externalization

### 2.1 核心候选层

这些文件最接近未来的可复用核心：

- `backend/app/services/skills/`
- `backend/app/services/skills/bootstrap.py`
- `backend/app/services/skills/runtime_seams.py`
- `backend/app/services/skills/runtime_catalog.py`
- `backend/app/services/skills/registry.py`
- `backend/app/services/skills/parsing.py`
- `backend/app/services/skills/import_service.py`
- `backend/app/services/skills/import_store.py`
- `backend/app/services/skills/import_models.py`
- `backend/app/services/skills/models.py`
- `backend/app/services/skills/policy.py`
- `backend/app/services/skills/compatibility.py`
- `backend/app/services/skills/routing.py`
- `backend/app/services/skills/actions.py`

这里有一个新的边界要点：

- `routing.py` 现在默认只保留 attribute-based visibility、打分和 fallback
- Yue 的 `skill group` 可见性语义已经收敛到 host adapter 层
- 如果目标项目也需要 group-based visibility，应在宿主侧提供自己的 visibility resolver，而不是把宿主组语义重新塞回 core routing

### 2.2 过渡兼容层

这部分不是未来纯核心包的一部分，但在当前阶段，另一个同栈项目要想低风险复用，通常仍然需要：

- `backend/app/services/skill_service.py`

它的角色是：

1. 提供 Stage4 runtime context 访问入口
2. 挂接 host adapter bundle
3. 保留旧 patch seam 的兼容能力

如果你今天就想“快速植入”，通常应该复制它。
如果你是在做最终 externalization，则它应被逐步缩小甚至替换。

### 2.3 Yue 宿主适配层

这些文件体现 Yue 自己的业务形状，目标项目通常要改写或替换：

- `backend/app/main.py`
- `backend/app/api/skills.py`
- `backend/app/api/skill_imports.py`
- `backend/app/api/skill_groups.py`
- `backend/app/services/skill_service.py` 里的宿主绑定部分
- `backend/app/services/skills/host_adapters.py`

### 2.4 示例技能与测试资产

如果你想快速验证复用是否成功，也可以复制：

- `backend/data/skills/`
- `backend/tests/test_skill_runtime_*`
- `backend/tests/test_api_skill_imports.py`
- `backend/tests/test_api_skills.py`

---

## 3. 目标项目应满足什么前置条件

目标项目最好满足以下条件：

1. 使用 Python + FastAPI
2. 后端包结构和 Yue 类似，至少能提供一个主应用入口
3. 有一个 agent 或 task 对象，可以表达“当前任务需要什么技能”
4. 有一套自己的配置入口，或者允许映射环境变量
5. 有一个持久化目录可保存 import 记录、技能组、运行时状态

如果目标项目和 Yue 的字段名不完全一样，也没关系。

原则是：**改宿主适配层，不改核心路由与解析逻辑。**

---

## 4. 推荐的迁移顺序

最稳妥的做法是分四步迁移。

### 第一步：先迁移核心包

先把 `backend/app/services/skills/` 复制到目标项目，例如：

```text
target_project/
  backend/
    app/
      services/
        skills/
```

如果目标项目的根包不是 `app`，就把 import 路径统一重写。

### 第二步：补 host adapter

把目标项目自己的：

- agent store
- config service
- skill group store
- feature flag service
- runtime config provider

包成一个很薄的 adapter。

### 第三步：接 bootstrap

在目标项目启动时，做三件事：

1. 解析技能运行时配置
2. 注册宿主适配器
3. 挂载技能路由

### 第四步：最后才接前端或更复杂的交互

先让后端 API 正常，再接 UI。

这样最容易定位问题，也最容易回滚。

---

## 5. 两种接入方式

### 5.1 复制式接入

适合当前阶段，目标是最快落地。

做法：

1. 复制 core candidate
2. 复制 `skill_service.py`
3. 复制 Yue 的 skill API，或者在目标项目里写等价 API
4. 接 host adapter
5. 接 bootstrap

优点：

- 最快
- 风险最低
- 最适合“先在另一个项目里跑起来”

代价：

- 仍然带着一部分 transitional shell

### 5.2 包式接入

适合 externalization 完成之后。

做法：

1. 只保留纯 core 包
2. 目标项目自己提供 route strategy 和 host adapters
3. 不再依赖 Yue 的 API 模块

优点：

- 结构最干净
- 真正可迁移

代价：

- 对当前代码基线来说，还不是最低风险路径

## 6. 最小可复用方案

如果你想先跑起来，最小可复用方案只需要四样东西：

1. `SkillRuntimeConfig`
2. `HostRuntimeAdapterBundle`
3. `mount_skill_runtime_routes(...)`
4. `bootstrap_skill_runtime_lifespan(...)`

也就是说，目标项目最少要能提供：

- 配置来源
- agent 查询
- feature flag 查询
- skill group 查询
- 一个 FastAPI app

---

这里要补一个现实约束：

- 当前 `mount_skill_runtime_routes(...)` 的默认 `DefaultSkillRuntimeRouteStrategy` 仍会 import Yue 风格的 `app.api.skills`、`app.api.skill_imports`、`app.api.skill_groups`
- 所以如果目标项目不准备直接复制这些 API 模块，就必须自己提供 `route_strategy`

## 7. 目标项目的推荐目录结构

建议目标项目长这样：

```text
target_project/
  backend/
    app/
      api/
        skills.py
        skill_imports.py
        skill_groups.py
      services/
        skills/
          ... core files ...
        skill_service.py
      integrations/
        skill_runtime/
          adapters.py
          bootstrap.py
          settings.py
    data/
      skills/
    tests/
      test_skill_runtime_bootstrap.py
      test_skill_runtime_smoke.py
```

如果目标项目只想用核心库，不想保留 Yue 命名，也可以把 `skills/` 独立成：

```text
target_project/
  skill_runtime_core/
```

但要记住：**包名可以换，边界不能乱。**

---

## 8. 目标项目需要实现的宿主适配器

### 8.1 AgentProvider

职责：根据 `agent_id` 获取 agent 对象。

要求：返回的对象至少要能表达这些字段：

- `skill_mode`
- `visible_skills`
- `skill_groups`
- `extra_visible_skills`
- `resolved_visible_skills`
- `enabled_tools`

如果你的项目字段名不同，就在 adapter 中映射。

### 8.2 FeatureFlagProvider

职责：返回功能开关字典。

建议至少支持：

- `skill_runtime_enabled`
- `skill_runtime_debug_contract_enabled`
- `skill_import_auto_activate_enabled`

### 8.3 SkillGroupResolver

职责：根据 group ids 返回可见 skill refs。

这层通常来自目标项目自己的权限、团队或角色系统。

### 8.4 HostConfigProvider

职责：读取目标项目的配置值。

这样你可以把 Yue 的 `YUE_*` 变量映射成目标项目自己的命名。

---

## 9. 最小接入代码示例

下面是一个比较接近“照着做就能跑”的接入方式。

### 9.1 适配器

```python
# target_project/backend/app/integrations/skill_runtime/adapters.py
from app.services.skills import build_default_host_runtime_adapter_bundle


def build_skill_runtime_adapters(agent_store, config_service, skill_group_store, host_config_provider=None):
    return build_default_host_runtime_adapter_bundle(
        agent_store=agent_store,
        config_service=config_service,
        skill_group_store=skill_group_store,
        host_config_provider=host_config_provider,
    )
```

### 9.2 启动 bootstrap

```python
# target_project/backend/app/main.py
from fastapi import FastAPI

from app.services.skills import (
    bootstrap_skill_runtime_app,
    bootstrap_skill_runtime_lifespan,
    build_skill_runtime_bootstrap_spec_from_env,
)
from app.services.skill_service import (
    get_stage4_lite_runtime_context,
    register_stage4_lite_host_runtime_adapter_bundle,
)

from app.integrations.skill_runtime.adapters import build_skill_runtime_adapters

adapters = build_skill_runtime_adapters(
    agent_store=agent_store,
    config_service=config_service,
    skill_group_store=skill_group_store,
    host_config_provider=host_config_provider,
)
register_stage4_lite_host_runtime_adapter_bundle(adapters)

bootstrap_spec = build_skill_runtime_bootstrap_spec_from_env(
    host_config_adapter=adapters.host_config_provider,
)

app = FastAPI(
    lifespan=bootstrap_skill_runtime_lifespan(
        runtime_context_provider=get_stage4_lite_runtime_context,
        bootstrap_spec=bootstrap_spec,
    )
)

bootstrap_skill_runtime_app(app, bootstrap_spec=bootstrap_spec)
```

### 9.3 如果你不复制 Yue 的 API 模块

那就不要直接用默认 route strategy，而要自己实现一个：

```python
from dataclasses import dataclass

from app.services.skills import SkillRuntimeRouteMountOptions


@dataclass
class HostSkillRuntimeRouteStrategy:
    def mount(self, app, options: SkillRuntimeRouteMountOptions) -> None:
        from app.api import host_skills, host_skill_imports

        app.include_router(host_skills.router, prefix=f"{options.api_prefix}/skills", tags=["skills"])
        app.include_router(
            host_skill_imports.router,
            prefix=f"{options.api_prefix}/skill-imports",
            tags=["skill-imports"],
        )
```

然后在 bootstrap spec 中传入这个 strategy：

```python
route_strategy = HostSkillRuntimeRouteStrategy()
bootstrap_spec = build_skill_runtime_bootstrap_spec_from_env(
    host_config_adapter=adapters.host_config_provider,
    route_strategy=route_strategy,
)
```

### 9.4 启动顺序

建议顺序如下：

1. 注册宿主适配器
2. 生成 bootstrap spec
3. 创建 FastAPI app
4. 绑定 lifespan
5. 挂载 skill routes

---

## 10. 最小配置示例

目标项目最少配置这些变量即可：

```env
SKILL_RUNTIME_BUILTIN_SKILLS_DIR=/absolute/path/to/backend/data/skills
SKILL_RUNTIME_WORKSPACE_SKILLS_DIR=/absolute/path/to/workspace/data/skills
SKILL_RUNTIME_USER_SKILLS_DIR=/absolute/path/to/user/skills
SKILL_RUNTIME_DATA_DIR=/absolute/path/to/runtime-data
SKILL_RUNTIME_MODE=import-gate
SKILL_RUNTIME_WATCH_ENABLED=false
SKILL_RUNTIME_RELOAD_DEBOUNCE_MS=2000
SKILL_RUNTIME_API_PREFIX=/api
SKILL_RUNTIME_INCLUDE_SKILL_IMPORTS=true
SKILL_RUNTIME_INCLUDE_SKILL_GROUPS=true
```

这里再强调一次：

- 如果你不显式配置这些路径，当前实现会回退到 Yue 风格的仓库相对路径和 `~/.yue/...` 默认值
- 这些默认值对 Yue 本身方便，但对目标项目不应视作稳定复用契约
- 所以跨项目集成时，建议全部显式配置

### 推荐的最低配置含义

- `SKILL_RUNTIME_MODE=import-gate`
  - 适合默认走导入门禁
  - 比较符合当前“只允许已接受技能进入运行时”的思路

- `SKILL_RUNTIME_WATCH_ENABLED=false`
  - 建议先关闭，等基础路径稳定后再打开
  - 可以显著减少排障噪音

- `SKILL_RUNTIME_DATA_DIR`
  - 决定 import store、skill group 等持久化落点
  - 目标项目最好显式配置，不要依赖隐式默认值

---

## 11. 迁移后的验证步骤

### 10.1 基础启动验证

启动后确认：

1. 应用能正常启动
2. `/api/skills` 可访问
3. `/api/skill-imports` 可访问
4. `runtime_context` 正常构建
5. 路由挂载来源符合预期：
   - 复制式接入：允许使用 Yue 风格默认 route strategy
   - 包式接入：必须验证自定义 route strategy 已生效

### 10.2 导入验证

把一个标准 skill 包放到可访问目录后，验证：

1. 能解析 `SKILL.md`
2. 能生成 import preview
3. 能生成 compatibility report
4. 能进入 active 状态

### 10.3 路由验证

验证一个 agent 能：

1. 通过 visible skills 找到候选技能
2. 根据 task 选择合适 skill
3. 返回 reason_code 和 fallback_used
4. 在 debug 开关开启时返回诊断 contract

### 10.4 收口验证

如果你要确认“复用不是伪复用”，请额外验证：

1. 目标项目没有直接依赖 Yue 的 frontend
2. 核心包没有强绑定 Yue 的 agent store 名称
3. bootstrap 过程只通过 adapter 获取宿主能力

---

## 12. 常见坑

### 坑 1：把核心代码和宿主代码混在一起改

症状：

- 迁移一次后，下一次又要再 fork 一次

建议：

- 核心包只改通用能力
- 宿主差异统一放进 adapter

### 坑 2：照搬 Yue 的环境变量命名

症状：

- 目标项目里到处都是 `YUE_*`

建议：

- 用 `HostConfigProvider` 做映射
- 只在迁移初期保留兼容 alias

### 坑 3：先接前端再接后端

症状：

- UI 看起来像接上了，但实际 runtime 不通

建议：

- 先做 API smoke test，再接 UI

### 坑 4：忽略 skill group / visibility 适配

症状：

- 技能导入成功但路由不到

建议：

- 先定义好 group -> refs 的适配逻辑
- 再接 routing

### 坑 5：以为 `build_skill_runtime(...)` 已经能一次性接收全部 adapters

症状：

- 你按未来形态写出 `build_skill_runtime(config=..., adapters=...)`
- 结果发现当前代码里并没有这个签名

建议：

- 把它理解为“目标 API 形态”
- 当前代码应按“先构建 runtime，再注册 host adapter bundle”的方式接入

---

## 13. 推荐的迁移节奏

### 第 1 周

- 复制核心包
- 完成 adapter
- 跑通 startup

### 第 2 周

- 接入 import gate
- 验证导入、激活、路由
- 补最小回归测试

### 第 3 周

- 关闭 watch mode 外部噪音
- 打磨配置映射
- 接入 UI 或更上层能力

---

## 14. 这套方案为什么可复用

它可复用的关键原因是：

1. 核心能力已经分层
2. 运行时已经有 context / provider seam
3. import gate、routing、compatibility、bootstrap 都能通过适配器连接
4. 目标项目只需要懂自己的 agent/config/store，不需要懂 Yue 的全部内部

换句话说，真正复用的是 **技能运行机制**，不是 **Yue 的整个平台**。

---

## 15. Excalidraw 发布门禁（Chunk 5）

当 `excalidraw-diagram-generator` 或同类“文档+脚本”技能变更涉及 action schema、脚本执行路径、或产物协议时，发布前必须满足以下门禁。

### 15.1 发布前检查

1. **preflight 全绿**：确认 Skill Health 面板对 Excalidraw 检查项为可用状态，且无 blocker。
2. **关键测试通过**：至少通过 action/unit、e2e/unit，以及核心回归集合。
3. **样例图可打开**：实际产出的 `.excalidraw` 文件能被 Excalidraw 打开，且 `output_file_path` 可追踪。
4. **失败路径可恢复**：图标缺失、`.edit` 冲突、非法 JSON 三类失败均返回可定位错误且不破坏原始文件。

### 15.2 回滚策略

1. **禁用 action**：优先通过运行时开关或策略层禁止 Excalidraw action 调用，保留技能可见但不执行脚本。
2. **降级到 L1**：仅保留基础图生成与文本指引，停止图标注入和自动连线增强。
3. **保留可编辑产物**：故障场景保留可继续编辑文件路径，避免用户任务中断。

### 15.3 Smoke/Regression 命令基线

```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skill_preflight.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_orchestrator_unit.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py -q -k list_action_states
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_skill_actions_unit.py -q
PYTHONPATH=. pytest /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_excalidraw_skill_e2e_unit.py -q

cd /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend
npm test -- /Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/SkillHealth.test.ts
```

## 16. 相关文档

- [Skill Runtime Current Operation](../../architecture/Skill_Runtime_Current_Operation.md)
- [Skill Runtime Core Externalization Plan](../../plans/skill_runtime_core_externalization_plan_20260423.md)
- [Skill Import Gate Implementation Design](../../plans/skill_import_gate_implementation_design_20260421.md)
- [Skill Import Runtime Execution Plan](../../plans/skill_import_runtime_execution_plan_20260421.md)
- [Skill Preflight And Health Panel Guide](./SKILL_PREFLIGHT_HEALTH_PANEL_GUIDE.md)
