# 模型分层配置与路由方案

## 1. 背景与目标

当前系统已经支持多供应商、多模型、自定义模型、Agent 配置和 Skill/Tool 路由，但模型绑定方式仍以 `provider + model` 为主：

- 全局层以默认 provider/model 为主。
- Agent 层直接绑定具体 provider/model。
- 运行时主要依赖 capability 推断和显式覆盖。

这套方式能工作，但当系统开始同时承载以下两类任务时，问题会逐步显现：

- 轻任务：翻译、润色、摘要、简单问答。
- 重任务：工具调用、多 Skill 编排、多步规划、长上下文分析。

如果继续让每个 Agent 直接绑定某个具体模型，会出现三个问题：

1. 配置重复：很多 Agent 只是能力强弱不同，本质上不需要维护独立模型绑定。
2. 切换成本高：更换供应商或升级模型时，需要逐个 Agent 调整。
3. 路由不稳定：同一个 Agent 可能同时处理轻任务和重任务，固定模型无法兼顾成本、速度和成功率。

本方案目标是：

1. 在不推翻现有 `provider/model` 架构的前提下，引入一层“模型角色配置”。
2. 支持“通用模型”和“重度模型”分层，并预留按任务类型扩展的能力。
3. 让 Agent 尽量依赖“能力角色”而不是供应商模型名。
4. 支持后续按规则自动升级/降级模型，而不是全靠人工配置。

## 2. 设计原则

### 2.1 增量兼容

保留现有：

- `llm.provider`
- `{provider}_model`
- `custom_models`
- `agents.json` 中的 `provider/model`
- `capabilities.py` 的能力推断

在此基础上新增“路由配置层”，避免一次性重构过大。

### 2.2 角色优于模型名

系统内部优先配置“角色”而不是“模型名”。

推荐角色：

- `general_chat`
- `translation`
- `writing`
- `tool_use`
- `reasoning`
- `long_context`
- `meta`

底层再把这些角色映射到具体 `provider/model`。

### 2.3 显式优先，自动兜底

决策优先级建议为：

1. 请求级显式指定。
2. Agent 级模型角色覆盖。
3. 系统级模型角色默认值。
4. 基于任务特征自动升级。
5. 最终兜底到现有 `provider/model`。

### 2.4 控制复杂度

对普通用户只暴露两档：

- 默认通用模型
- 复杂任务模型

对高级用户再展开“按角色配置”。

## 3. 推荐落地形态

### 3.1 第一阶段产品形态

先落地你最关心的双层模型：

1. `默认通用模型`
   - 用于普通问答、翻译、摘要、改写、轻量文本生成。
2. `复杂任务模型`
   - 用于工具调用、多 Skill、复杂规划、重推理任务。

同时在系统内部不要只保存这两个标签，而是映射到更细的角色：

- `general_chat` 默认指向“默认通用模型”
- `translation` 默认复用 `general_chat`
- `writing` 默认复用 `general_chat`
- `tool_use` 默认指向“复杂任务模型”
- `reasoning` 默认指向“复杂任务模型`

这样 UI 简单，但底层可扩展。

### 3.2 第二阶段扩展形态

当你们想进一步提升精细度时，再开放这些可选角色：

- `translation`
- `tool_use`
- `reasoning`
- `vision`
- `meta`

不建议一开始就开放太多，否则用户会被配置项淹没。

## 4. 配置结构建议

建议在 `global_config.json` 的 `llm` 下新增 `routing` 字段。

```json
{
  "llm": {
    "provider": "openai",
    "settings": {
      "meta_enabled": true,
      "meta_provider": "openai",
      "meta_model": "gpt-4o-mini"
    },
    "routing": {
      "default_mode": "role_based",
      "fallback_policy": "use_general_chat",
      "auto_upgrade_enabled": true,
      "roles": {
        "general_chat": {
          "provider": "openai",
          "model": "gpt-4o-mini"
        },
        "translation": {
          "inherit": "general_chat"
        },
        "writing": {
          "inherit": "general_chat"
        },
        "tool_use": {
          "provider": "openai",
          "model": "gpt-4o"
        },
        "reasoning": {
          "provider": "deepseek",
          "model": "deepseek-reasoner"
        },
        "meta": {
          "inherit": "general_chat"
        }
      },
      "rules": {
        "tool_call_requires_role": "tool_use",
        "multi_skill_requires_role": "reasoning",
        "translation_prefers_role": "translation",
        "vision_prefers_capability": "vision"
      }
    }
  }
}
```

### 4.1 字段说明

- `default_mode`
  - `legacy`：完全沿用现有 provider/model。
  - `role_based`：优先走角色路由。

- `fallback_policy`
  - `use_general_chat`：找不到配置时回退到通用模型。
  - `use_legacy_agent_model`：找不到配置时回退到 Agent 当前 model。
  - `fail_closed`：找不到配置直接报错。

- `auto_upgrade_enabled`
  - 是否允许根据任务复杂度自动升级模型。

- `roles`
  - 系统级角色到具体模型的映射。

- `inherit`
  - 允许角色复用，减少重复配置。

- `rules`
  - 运行时从任务特征映射到角色的规则配置。

## 5. Agent 配置建议

当前 `AgentConfig` 只有：

- `provider`
- `model`

建议新增可选字段，但保留原字段兼容：

```json
{
  "id": "builtin-translator",
  "name": "Translator",
  "system_prompt": "...",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "model_role": "translation",
  "model_policy": "prefer_role",
  "upgrade_on_tools": true,
  "upgrade_on_multi_skill": true
}
```

### 5.1 新字段定义

- `model_role`
  - Agent 默认优先使用的角色，如 `translation`、`tool_use`。

- `model_policy`
  - `prefer_role`：优先走角色映射，找不到再回退 `provider/model`。
  - `force_direct`：强制使用当前 Agent 的 `provider/model`。
  - `system_default`：忽略 Agent 自定义，完全跟随系统。

- `upgrade_on_tools`
  - 当请求触发工具调用时，是否自动切到 `tool_use`。

- `upgrade_on_multi_skill`
  - 当请求触发多 Skill 编排时，是否自动切到 `reasoning`。

### 5.2 推荐迁移策略

内置 Agent 可以先这样迁移：

- Translator Agent -> `model_role=translation`
- Architect / PDF Researcher / Docs Agent -> `model_role=reasoning`
- Excel / PPT / Action Lab -> `model_role=tool_use`

这样不会破坏现有默认行为，但后续切换模型时不需要逐个改模型名。

## 6. 运行时路由规则

### 6.1 推荐路由流程

运行时新增一个统一入口，例如：

- `resolve_runtime_model(request, agent_config, tool_context, skill_context)`

内部流程建议如下：

1. 如果请求显式指定 `provider/model`，直接使用。
2. 如果请求显式指定 `model_role`，按角色解析。
3. 如果 Agent 配置了 `model_policy=force_direct`，使用 Agent 的 `provider/model`。
4. 如果 Agent 配置了 `model_role`，先解析该角色。
5. 若检测到工具调用场景且 `upgrade_on_tools=true`，升级到 `tool_use`。
6. 若检测到多 Skill 或复杂规划场景且 `upgrade_on_multi_skill=true`，升级到 `reasoning`。
7. 若消息是纯翻译、纯改写、纯总结，优先走 `translation` 或 `general_chat`。
8. 若消息包含图片且目标模型无 `vision` 能力，切换到支持 `vision` 的角色或模型。
9. 若以上都未命中，回退到系统 `general_chat`。
10. 最终若仍无法解析，回退到 legacy `provider/model`。

### 6.2 复杂度判定信号

建议不要一开始做复杂分类模型，先用可解释规则：

- `has_tools`
  - 当前 Agent 有 enabled_tools，且请求路径允许工具调用。

- `tool_selected`
  - 运行时已经确定会触发 MCP / builtin tool。

- `skill_count > 1`
  - 命中多个 Skill 或需要 Skill 自动选择。

- `requires_reasoning`
  - 命中 `reasoning` capability 或检测到“分析、比较、规划、诊断”等任务特征。

- `is_translation_like`
  - 请求短、结构清晰，命中翻译意图。

- `has_images`
  - 请求包含图片。

第一阶段不要追求百分百智能，目标是“简单任务尽量轻，复杂任务稳定升档”。

## 7. UI 方案建议

基于现有 [LlmSettingsTab.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/settings/components/LlmSettingsTab.tsx) 和模型管理弹窗，建议这样扩展。

### 7.1 设置页新增一个块

建议名称：

- `Model Routing`

显示两档核心配置：

1. `默认通用模型`
2. `复杂任务模型`

每一项都允许用户选择：

- Provider
- Model

同时显示说明文案：

- 默认通用模型：用于普通聊天、翻译、润色、摘要。
- 复杂任务模型：用于工具调用、多 Skill、复杂分析。

### 7.2 高级设置折叠区

在“Advanced”中再展示：

- 翻译模型
- 工具调用模型
- 推理模型
- Meta 模型是否继承通用模型
- 自动升级开关
- 回退策略

### 7.3 Agent 编辑页扩展

在 [AgentForm.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/AgentForm.tsx) 中新增：

- `模型策略`
- `默认角色`
- `启用工具时自动升级`
- `多 Skill 时自动升级`

默认收起，仅高级用户可见。

## 8. 后端落地建议

### 8.1 数据模型

建议修改以下结构：

- [backend/app/services/agent_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py)
  - 为 `AgentConfig` 增加 `model_role`、`model_policy`、`upgrade_on_tools`、`upgrade_on_multi_skill`

- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py)
  - 新增 `get_llm_routing_config()`
  - 新增 `resolve_model_role(role_name)`
  - 新增 `resolve_runtime_model(...)`

- [backend/app/services/llm/capabilities.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/llm/capabilities.py)
  - 保持能力推断职责，不承担路由职责

### 8.2 API

建议新增或扩展：

- `GET /api/config`
  - 返回 `llm.routing`

- `PUT /api/config`
  - 支持更新 `llm.routing`

- `GET /api/models/providers`
  - 保持现有功能，继续负责模型发现

- `POST /api/chat`
  - 增加可选字段 `model_role`

- `POST /api/agents`
  - 支持保存 Agent 的路由策略字段

### 8.3 运行时接入点

建议在真正构建模型实例前统一走路由层，不要让各业务模块自行判断。

优先接入点：

- Chat 主链路
- Agent 运行链路
- Skill 自动选择链路
- 多模态链路

目标是让“选哪个模型”只有一个中心出口。

## 9. 兼容与迁移

### 9.1 兼容策略

新增能力时，默认保持向后兼容：

- 老配置没有 `llm.routing` 时，系统按 legacy 模式运行。
- 老 Agent 没有 `model_role` 时，继续使用原 `provider/model`。
- 只有当用户启用 `role_based` 时，才启用新逻辑。

### 9.2 数据迁移

迁移不需要强制脚本，可按惰性策略：

1. 先上线新字段和默认值。
2. 读取老 Agent 时自动补默认值。
3. 只有用户编辑并保存 Agent 时，才写入新字段。

这能显著降低一次性迁移风险。

## 10. 监控与评估建议

这个方案是否真的有效，关键不在配置本身，而在可观测性。

建议在日志和 trace 中增加：

- `resolved_provider`
- `resolved_model`
- `resolved_role`
- `resolution_source`
  - request
  - agent_role
  - system_role
  - auto_upgrade
  - legacy_fallback
- `tool_count`
- `skill_count`
- `upgrade_trigger`
- `latency_ms`
- `token_usage`
- `success/failure`

这样后续才能回答这些关键问题：

- 翻译任务是不是被成功路由到轻模型？
- 工具型任务是否稳定升级到重模型？
- 哪个角色最费钱？
- 哪个路由规则带来了失败率上升？

## 11. 推荐实施顺序

### Phase 1：最小可用版本

目标：快速把“通用模型 + 复杂任务模型”跑起来。

范围：

- `llm.routing.roles.general_chat`
- `llm.routing.roles.tool_use`
- `llm.routing.roles.reasoning`
- UI 暴露“默认通用模型”和“复杂任务模型”
- Agent 新增 `model_role` 和 `model_policy`
- 聊天主链路接入统一路由

价值：

- 已能覆盖你提出的核心诉求。
- 改动面相对可控。

### Phase 2：精细化

范围：

- 新增 `translation` 角色
- 加入自动升级规则
- Agent 级升级开关
- 请求级 `model_role`

价值：

- 让翻译类、轻问答类和复杂调用类拉开成本档位。

### Phase 3：智能优化

范围：

- 基于 trace 统计优化规则
- 失败后自动重试到更强模型
- 结合 capability 和上下文长度做更精确路由

价值：

- 从“可配置”升级到“可自优化”。

## 12. 结论与最终建议

你的想法是成立的，而且应该做，但建议从“两个模型槽位”升级为“简单 UI + 角色化底层”的方案。

最推荐的落地姿势是：

1. UI 先只给用户两个入口：`默认通用模型` 和 `复杂任务模型`。
2. 后端内部用 `model role` 做统一抽象，而不是让 Agent 直接绑定供应商模型名。
3. Agent 增加 `model_role` 与 `model_policy`，但保持旧字段兼容。
4. 聊天、Skill、Tool、多模态共用一个运行时模型解析入口。
5. 先用规则式自动升级，不要一开始做过度智能化分类。

这条路线的优点是：

- 对用户简单。
- 对实现友好。
- 对未来扩展安全。
- 对供应商切换成本低。

如果进入实现阶段，下一步最值得先做的是：

1. 补 `global_config.json` 的 `llm.routing` 结构。
2. 给 `AgentConfig` 加模型角色字段。
3. 在 Chat 主链路插入统一的 `resolve_runtime_model()`。
4. 在设置页加一个 `Model Routing` 分组。

