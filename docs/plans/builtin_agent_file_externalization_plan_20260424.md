# Builtin Agent File Externalization Plan

## 1. Goal

将当前 hard code 在 Python 代码中的 builtin agent 定义外置到文件系统中，形成与 builtin skill 类似的内容驱动模式，同时保持运行时行为稳定：

- 开发机无需修改 Python 代码即可调整 builtin agent 定义
- 首次启动时自动 seed 缺失的 builtin agent
- 后续重启不覆盖用户在 UI 中对 builtin agent 的修改
- 尽量不改动现有 UI、API、运行时 agents.json 的使用方式

## 2. Scope

### In Scope

- 新增 builtin agent 文件目录与 schema
- 新增 builtin agent catalog / loader
- 将 `AgentStore` 的 builtin 来源从 hard code 切换为 YAML 文件
- 保留当前 runtime `agents.json` 作为运行时唯一权威源
- 启动时仅补缺，不覆盖已有 builtin agent 记录
- 增加单测与最小回归验证

### Out of Scope

- 不改 builtin skill 的 import-gate / legacy 机制
- 不把 agent 与 skill 强行合并为同一种 package schema
- 不实现 builtin definition 的自动升级合并
- 不在 UI 中直接编辑 builtin definition 文件
- 不调整 `/api/agents` 契约

## 3. Current Problem

当前 builtin agent 定义写在 [`backend/app/services/agent_store.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py) 的 `_builtin_*_agent()` 方法中，带来以下问题：

- 调整 builtin agent 需要修改 Python 代码
- 内容定义与运行时存储耦合过紧
- 启动时容易出现“默认值回填覆盖用户修改”的风险
- 与 builtin skill 已经采用目录扫描的模式不一致

## 4. Target Design

### 4.1 Directory Layout

第一阶段仅文件化 builtin agent，不强制迁移 builtin skill 目录：

```text
backend/data/builtin/
  agents/
    builtin-docs.yaml
    builtin-local-docs.yaml
    builtin-architect.yaml
    builtin-excel-analyst.yaml
    builtin-pdf-research.yaml
    builtin-ppt-builder.yaml
    builtin-action-lab.yaml
    builtin-translator.yaml
```

说明：

- `backend/data/skills` 暂时保持不变
- 后续如需统一 builtin 根目录，可在二期把 skill 平移到 `backend/data/builtin/skills`

### 4.2 Builtin Agent File Schema

每个 builtin agent 一个 YAML 文件，字段尽量贴近当前 `AgentConfig`：

```yaml
id: builtin-docs
name: Document Assistant
system_prompt: |
  Role: ...
provider: deepseek
model: deepseek-reasoner
model_selection_mode: tier
model_tier: balanced
model_role: null
model_policy: prefer_role
upgrade_on_tools: true
upgrade_on_multi_skill: true
enabled_tools:
  - builtin:docs_search
  - builtin:docs_read
doc_roots: []
doc_file_patterns:
  - "**/*.md"
  - "**/*.pdf"
require_citations: true
skill_mode: auto
visible_skills:
  - pdf-insight-extractor:1.0.0
agent_kind: traditional
skill_groups: []
extra_visible_skills: []
resolved_visible_skills: []
voice_input_enabled: true
voice_input_provider: browser
voice_azure_config: null
builtin: true
seed_policy: seed_only
```

新增元字段建议：

- `builtin: true`
- `seed_policy: seed_only`

第一阶段可只读取这两个元字段但不复杂化逻辑；如无必要，也可先不入 `AgentConfig`，由 catalog 层自行处理。

### 4.3 Runtime Behavior

运行时仍然以 `YUE_DATA_DIR/agents.json` 为唯一运行态数据源。

启动时执行 builtin seed：

- 若 runtime 中不存在该 builtin agent `id`，则创建
- 若 runtime 中已存在该 `id`，则绝不覆盖

等价规则：

```python
for builtin in builtin_catalog.list_builtin_agents():
    if not runtime_store.exists(builtin.id):
        runtime_store.create(builtin)
```

禁止再做以下自动回填：

- `system_prompt` 对齐覆盖
- `enabled_tools` 对齐覆盖
- `visible_skills` 对齐覆盖
- `skill_mode` 对齐覆盖
- 其他用户可能通过 UI 修改的字段覆盖

## 5. Implementation Plan

### Step 1. Introduce Builtin Agent Directory

目标：

- 新增 `backend/data/builtin/agents/`
- 把现有 8 个 builtin agent 定义转成 YAML 文件

执行项：

- 新建目录 `backend/data/builtin/agents`
- 将以下 builtin agent 从 `agent_store.py` 抽出到 YAML：
  - `builtin-docs`
  - `builtin-local-docs`
  - `builtin-architect`
  - `builtin-excel-analyst`
  - `builtin-pdf-research`
  - `builtin-ppt-builder`
  - `builtin-action-lab`
  - `builtin-translator`

完成标准：

- 所有当前 builtin agent 在文件目录中可完整表达
- 不丢失现有默认字段

### Step 2. Add Builtin Agent Catalog

目标：

- 新增独立 loader，负责扫描、解析、校验 builtin agent YAML

建议新增文件：

- `backend/app/services/builtin_agent_catalog.py`

建议职责：

- 解析目录中的 `*.yaml` / `*.yml`
- 转换为 `AgentConfig`
- 提供 `list_builtin_agents()`
- 对非法配置给出明确日志或异常

建议接口：

```python
class BuiltinAgentCatalog:
    def __init__(self, builtin_agents_dir: str | None = None): ...
    def list_builtin_agents(self) -> list[AgentConfig]: ...
```

完成标准：

- 能从目录中稳定读取 builtin agent
- 加载顺序可预测
- 对坏文件具备可观测错误

### Step 3. Refactor AgentStore to Use Catalog

目标：

- 移除 `AgentStore` 内部 hard-coded builtin 定义来源

执行项：

- 在 `AgentStore` 中注入或创建 `BuiltinAgentCatalog`
- 用 `catalog.list_builtin_agents()` 替换 `_builtin_agents()`
- 删除 `_builtin_*_agent()` 系列方法
- 保留 `_ensure_builtin_agents()`，但语义改为“仅补缺”

完成标准：

- `AgentStore` 不再包含具体 builtin agent prompt 和工具列表
- 启动逻辑只补缺，不覆盖已有 runtime 记录

### Step 4. Preserve Runtime Compatibility

目标：

- 保证现有 UI / API / 数据文件不需要迁移格式

执行项：

- 保持 `AgentConfig` 主体字段不变
- 保持 `/api/agents` 返回格式不变
- 保持 `YUE_DATA_DIR/agents.json` 为运行态权威源

完成标准：

- 前端无需改动即可继续使用
- 编辑、保存、重启后的行为稳定

### Step 5. Tests and Regression Coverage

目标：

- 建立最小可信回归面

至少新增以下测试：

1. `builtin agent yaml` 可被 catalog 正确加载
2. 缺失 builtin agent 时，启动会自动 seed
3. 用户已修改 builtin agent 时，重启不覆盖
4. 非法 yaml / 缺字段时，catalog 行为可预期

建议测试文件：

- `backend/tests/test_builtin_agent_catalog.py`
- `backend/tests/test_agent_store_unit.py`

建议回归命令：

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_builtin_agent_catalog.py \
  backend/tests/test_agent_store_unit.py \
  backend/tests/test_agent_store_persistence.py
```

## 6. Suggested File Changes

### New Files

- `backend/data/builtin/agents/*.yaml`
- `backend/app/services/builtin_agent_catalog.py`
- `backend/tests/test_builtin_agent_catalog.py`

### Modified Files

- `backend/app/services/agent_store.py`
- `backend/tests/test_agent_store_unit.py`
- `backend/tests/test_agent_store_persistence.py`

## 7. Rollout Strategy

建议按以下顺序落地：

1. 先新增 YAML 文件与 catalog，不删除旧 hard code
2. 加测试，确认 catalog 加载结果与旧 builtin 定义一致
3. 再切 `AgentStore` 到 catalog
4. 最后删除 `_builtin_*_agent()` 方法

这样可以避免一步改太大，降低回归风险。

## 8. Acceptance Criteria

- builtin agent 定义不再 hard code 在 `agent_store.py` 中
- 启动后缺失 builtin agent 能自动补齐
- UI 修改 builtin agent 设置后，重启不丢失
- `/api/agents` 行为与现有前端兼容
- 新增测试通过

## 9. Future Follow-ups

二期可以继续做：

- 将 builtin skill 目录迁移到 `backend/data/builtin/skills`
- 为 builtin agent definition 增加 version 字段
- 增加“definition 更新提示”而非自动覆盖
- 区分“系统模板”与“用户实例”
- 评估是否把 builtin agent 也纳入 import-gate 管理
