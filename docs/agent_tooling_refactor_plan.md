# Agent 工具系统重构方案 (Agent Tooling Refactor Plan)

本方案旨在将 `Yue` 的工具管理系统从目前的“配置驱动型”重化为“注册表驱动型”，引入 **Tool Registry** 模式，实现接口标准化、Schema 自动转换、防御式校验及错误自愈能力。

## 1. 核心目标
- **标准化 (Standardization)**: 建立统一的 `BaseTool` 接口，解耦工具实现与调用逻辑。
- **自动化 (Automation)**: 自动生成符合不同 LLM 规范的 JSON Schema。
- **健壮性 (Robustness)**: 在工具执行前进行参数校验，在执行后提供错误引导（Hint）。
- **动态性 (Dynamism)**: 支持在运行时动态挂载、卸载工具，支持“主子 Agent”的任务委派。

---

## 2. 平滑迁移原则 (Smooth Migration)
- **双轨运行**: 在关键阶段同时保留“旧路径”和“新路径”，以对比一致性。
- **可回滚**: 任意阶段出现异常时，可快速切回旧路径。
- **可观测**: 为每一步的关键行为设定清晰的日志与指标，便于追踪回归。
- **最小变更面**: 每一步只改动一个横切点，避免多点同时变更导致定位困难。

---

## 3. 前置定义与边界 (Pre-Definitions)
- **工具身份规则**: 统一工具 ID 格式与命名约束（如 `builtin:xxx`、`server:tool`），并明确 LLM 可见名称与内部真实名称的映射关系。
- **权限与白名单**: 明确工具授权策略的优先级、默认策略、冲突处理与回退行为。
- **Schema 范围**: 统一必选字段、类型映射规则、默认值策略与扩展字段的兼容范围。
- **错误协议**: 统一错误结构（错误码、提示、Hint 规范），约定哪些错误允许模型继续尝试。
- **数据观测**: 明确需要采集的核心指标与阈值（工具调用成功率、校验失败率、超时率、重试率）。

---

## 4. 重构路线图 (Roadmap)

我们将重构分为四个阶段，每一步都包含**重构前验证**、**重构实施**和**重构后回归测试**。

## 4.1 当前进度概览 (Status Snapshot)
**更新时间**：2026-03-01  
**总体结论**：阶段一与阶段二核心路径已落地；阶段三的 Provider Schema 翻译器已实现并接入链路；阶段四为“待开始”；影子模式稳定；Step 2.1~2.6 回归已完成。

### 已完成
- **阶段一核心**：`BaseTool`、Schema→Pydantic 模型转换、参数预处理与错误包装已实现；单测覆盖。
- **阶段二核心**：`ToolRegistry` 已引入；`chat.py` 已通过注册表获取工具；Registry 与 BaseTool 相关测试已补充。
- **阶段二影子模式**：新增 `MCP_TOOL_SHADOW_MODE` 开关；新旧路径工具清单与 Schema 对比日志已加入；对比单测已补充。
- **阶段三部分**：参数校验 `validate_params` 与错误提示 Hint 已落地（在 BaseTool wrapper 中）。
- **阶段三 Provider Schema 翻译器**：已新增 `schema_translator.py` 并接入 BaseTool/Registry/Chat 链路；OpenAI/Claude/DeepSeek 统一输出并支持 provider 透传。

### 未完成 / 待补齐
- **阶段四注册表层错误分流**：目前 Hint 在 BaseTool wrapper 层，注册表层未体现专用 `try-except` 分流与验证用例。
- **阶段三 Provider 差异化规则**：当前 Schema 翻译器为统一输出，尚未对各 Provider 做差异化字段/兼容性细节的深度适配。

### 当前测试状态（基线）
- `PYTHONPATH=backend pytest backend/tests/test_agent_regression.py` ✅  
- `PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py` ✅  
- `PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py` ✅  
- `PYTHONPATH=backend pytest backend/tests/test_mcp_manager_unit.py` ✅  
- `PYTHONPATH=backend python3 -m unittest discover backend/tests -v` ✅（部分集成用例因未启动后端或环境开关而跳过）

### 交接信息（建议补充）
- 当前目标阶段：Step 3（注册表层错误分流与 Hint 规范化）
- 已完成内容：Provider Schema 翻译器已落地并接入链路；Step 2.1~2.6 测试已跑通；基线测试全绿（部分集成用例因未启动后端或环境开关而跳过）
- 关键开关/环境：`MCP_TOOL_SHADOW_MODE=1`（影子模式对比）
- 已知限制：部分 HTTP/集成测试需要后端运行；TestClient 版本不兼容时会跳过
- 运行约束：测试需 `PYTHONPATH=backend`
- 重要文件路径：
  - [schema_translator.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/schema_translator.py)
  - [base.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/base.py)
  - [registry.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/registry.py)
  - [chat.py](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
  - [agent_tooling_refactor_plan.md](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/agent_tooling_refactor_plan.md)

### 如果要新开绘画的最简交接模板
“我已完成 Provider Schema 翻译器并接入链路，进入 Step 3。请参考 agent_tooling_refactor_plan.md 的 4.2 Step 3 详细计划；测试需 PYTHONPATH=backend。当前基线测试已通过，后端未启动的集成测试会跳过。请从注册表层错误分流与 Hint 规范化开始实现。”

### 开启下一段绘画的具体指令（简短）
“进入 Step 3（注册表层错误分流与 Hint 规范化），按 4.2 的 Step 3 详细计划逐步实现并回归测试。”

### 阶段一：建立标准化工具基类 (BaseTool Interface)
**目标**：定义统一的工具基类，取代目前散落在 `mcp_manager` 中的包装逻辑。

1.  **重构前验证**：
    - 运行 `pytest backend/tests/test_mcp_manager_unit.py` 确保现有 MCP 工具转换逻辑正常。
    - 记录现有 MCP 工具 Schema 样例，作为对比基准。
    - 记录同一工具在不同 LLM Provider 下的当前输出差异（若存在）。
2.  **实施步骤**：
    - 在 `backend/app/mcp/` 下创建 `base.py`，定义 `BaseTool` 抽象类。
    - 实现 `to_pydantic_ai_tool()` 方法，将内部定义转换为 Pydantic AI 所需的 `Tool` 对象。
3.  **重构后验证**：
    - 编写单元测试验证 `BaseTool` 能正确生成 Schema。
    - 验证现有内置工具（如 `docs_search`）继承 `BaseTool` 后仍能正常工作。
    - 对比 Schema 的字段集与默认值是否一致。

### 阶段二：引入工具注册表 (Tool Registry)
**目标**：集中管理工具生命周期，支持工具的动态发现与分发。

1.  **重构前验证**：
    - 运行 `pytest backend/tests/test_agent_regression.py` 确保 Agent 能够正常加载并调用工具。
    - 记录旧路径输出的工具清单（按 Agent 维度），作为一致性基准。
2.  **实施步骤**：
    - 创建 `backend/app/mcp/registry.py`，实现 `ToolRegistry` 类。
    - 将 `mcp_manager.py` 中的工具加载逻辑迁移至注册表。
    - 在 `chat.py` 中通过注册表获取工具，而不是直接调用 `mcp_manager` 的私有转换方法。
    - 提供“影子模式”切换开关，允许新旧路径并行产出工具列表用于对比。
3.  **重构后验证**：
    - 验证 `@mention` 不同 Agent 时，注册表能准确返回该 Agent 授权的工具子集。
    - 对比新旧路径工具清单与 Schema，保证数量与字段一致。
    - 验证工具顺序与筛选稳定性，避免前端显示抖动。

### 阶段三：强化防御式校验与 Schema 自动转换
**目标**：在工具执行前拦截非法参数，并自动适配不同 LLM 的 Schema 要求。

1.  **重构前验证**：
    - 模拟一个带参数错误的 API 请求（如 `docs_read` 缺少 `path`），记录当前系统的报错行为（通常是 Python 后端抛出 500 或 Pydantic 校验失败）。
2.  **实施步骤**：
    - 在 `BaseTool.execute` 调用前增加 `validate_params` 逻辑。
    - 实现 Schema 翻译器，支持根据 `provider`（OpenAI/Claude/DeepSeek）生成对应的 Function 定义。
3.  **重构后验证**：
    - 再次发送带错误的请求，验证系统是否返回结构化的错误提示（如：`Missing required parameter: 'path'`），且状态码为 200（作为模型可理解的上下文返回）。
    - 验证对正确参数的请求结果与旧路径一致。
    - 验证错误提示不会泄漏敏感路径或内部实现细节。

### 阶段四：实现错误自愈与 Hint 引导机制
**目标**：当工具执行出错时，返回带有“改进建议”的错误信息，引导 Agent 自动修正。

1.  **重构前验证**：
    - 运行 `builtin-local-docs` Agent 访问不存在的目录，观察其是否会陷入死循环或直接报错停止。
2.  **实施步骤**：
    - 在注册表的 `call` 方法中增加 `try-except` 捕获。
    - 针对常见错误（文件未找到、权限不足、超时）返回带有 `[Hint: ...]` 前缀的提示词。
3.  **重构后验证**：
    - 验证 Agent 在收到 Hint 后，能否尝试修正参数（例如：尝试父目录或列出当前目录文件）完成任务。
    - 验证正常路径的响应不包含 Hint，避免误导。
    - 验证 Hint 不会引导超出权限边界的行为。

---

## 4.2 下一步执行计划（小步快走）(Next Steps with Test Gates)
原则：每一步都包含**变更最小化**、**可回滚**、**有测试门槛**；每步完成后再进入下一步。

### Step 0：基线回归与一致性基准
**目标**：锁定当前功能基线，形成可比对的工具清单与 Schema 样例。
1. 运行基础回归与单测  
   - `pytest backend/tests/test_agent_regression.py`  
   - `pytest backend/tests/test_base_tool_unit.py`  
   - `pytest backend/tests/test_tool_registry_integration.py`  
2. 记录工具清单快照（按 Agent 维度、含 Schema）  
3. 形成对比基准（工具数量、名称、required 字段与默认值）
**完成标准**：测试全绿；工具清单与 Schema 基线文件可复用。

### Step 1：实现“影子模式”并行对比
**目标**：新旧路径同时产出工具列表并对比差异，确保结果一致后再切换。
1. 增加影子模式开关（配置项或环境变量）  
2. 影子模式下同时获取新旧路径工具列表，输出差异日志（仅诊断，不影响返回）  
3. 增加对比单测（差异为空或在允许范围内）
**检测与测试**：  
- `pytest backend/tests/test_mcp_manager_unit.py`  
- 新增影子模式对比用例  
**完成标准**：影子模式下对比差异为 0；工具顺序稳定；功能不受影响。

### Step 2：Provider Schema 翻译器（细化）
**目标**：按 Provider 输出对应 Function Schema，保证 LLM 兼容性与字段一致性。

#### Step 2.1 定义翻译接口与结构
**目标**：统一入口函数，输入 BaseTool.parameters，输出各 Provider 的函数 schema。  
**实施**：  
- 新增 schema 翻译器模块（放在 `backend/app/mcp/` 或 `backend/app/services/` 目录）  
- 定义 `to_provider_schema(provider, parameters)` 和返回结构  
**测试**：  
- 新增单测：空 schema / 仅 required / enum / array / object 类型  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：单测全绿，接口签名稳定。

#### Step 2.2 实现 OpenAI 适配
**目标**：输出 OpenAI Functions 兼容 schema。  
**实施**：  
- 映射 `type/required/description` 等字段  
**测试**：  
- 新增 OpenAI 对比用例（字段一致、required 一致）  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：对比一致且无字段丢失。

#### Step 2.3 实现 Claude 适配
**目标**：输出 Claude Tools 兼容 schema。  
**实施**：  
- 复用公共结构，仅做必要字段改名/格式调整  
**测试**：  
- 新增 Claude 对比用例  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：对比一致且字段完整。

#### Step 2.4 实现 DeepSeek 适配
**目标**：输出 DeepSeek Function 兼容 schema。  
**实施**：  
- 对齐 OpenAI 格式或 DeepSeek 特定字段  
**测试**：  
- 新增 DeepSeek 对比用例  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：三家 Provider schema 与旧路径一致。

#### Step 2.5 集成到工具生成链路
**目标**：在生成 Pydantic Tool 或工具列表时可按 provider 输出。  
**实施**：  
- 在 registry/manager 侧接入翻译器开关  
**测试**：  
- 新增集成用例（模拟 provider 切换）  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py`  
**完成标准**：工具清单稳定、schema 正确。

#### Step 2.6 全量回归
**运行**：`PYTHONPATH=backend python3 -m unittest discover backend/tests -v`  
**完成标准**：全绿（集成类按条件跳过）。

### Step 3 详细执行计划（建议）
**目标**：在注册表层统一错误分流与 Hint 规范，并保持返回结构稳定。
1. **注册表层错误分流**  
   - 在 `ToolRegistry.call` 或调用链的集中入口包裹 `try-except`，仅覆盖工具执行阶段  
   - 明确可捕获异常清单（参数缺失、类型错误、文件不存在、权限不足、超时）  
2. **Hint 规范化与错误码结构**  
   - 统一错误结构：`{error_code, message, hint}`  
   - Hint 文案保持“可执行建议”风格，不泄露敏感路径  
3. **与 BaseTool wrapper 的职责边界**  
   - BaseTool 只负责参数校验与最小错误包装  
   - 注册表层负责策略化分流与标准化错误输出  
4. **测试门槛**  
   - 新增用例：工具执行异常时返回结构化 Hint  
   - 新增用例：正常路径返回不包含 Hint  
   - 运行：`PYTHONPATH=backend pytest backend/tests/test_agent_regression.py`  
**完成标准**：错误路径输出结构化 Hint；正常路径无 Hint；无敏感路径泄露。

### Step 3：注册表层错误分流与 Hint 规范化
**目标**：在注册表层统一捕获执行错误并返回结构化 Hint，避免误导与越权。
1. 在注册表或调用链增加错误分流（仅对工具执行阶段）  
2. 规范 Hint 文案与错误码结构  
3. 增加“正常路径无 Hint”的断言
**检测与测试**：  
- 新增错误自愈用例  
- 执行 `pytest backend/tests/test_agent_regression.py`  
**完成标准**：错误路径返回 Hint；正常路径无 Hint；无敏感路径泄露。

### Step 4：完成验收与回滚开关确认
**目标**：确保功能稳定，保留回滚路径，达成验收清单。
1. 全量回归  
   - `python3 -m unittest discover backend/tests -v`  
2. 对比工具清单与 Schema  
3. 确认回滚开关与文档一致
**完成标准**：验收清单全部通过，且可回滚。

## 5. 验证与回归策略 (Verification & Regression)

### 3.1 核心测试集
- **单元测试**: 覆盖 `BaseTool` 的 Schema 生成、参数校验逻辑。
- **集成测试**: 模拟 `mcp_manager` 加载远程 MCP 服务器工具，验证注册表的发现能力。
- **回归测试 (Mandatory)**: 运行 `backend/tests/test_agent_regression.py`，确保“主子 Agent”查询等核心业务不受影响。
- **系统测试**: 运行 `python3 -m unittest discover backend/tests -v` 保证后端整体可用。
### 3.2 每阶段必要测试用例 (Stage Test Matrix)
- **阶段一**: Schema 对比、内置工具行为一致、工具名称合法性、空参数工具兼容性
- **阶段二**: 工具清单一致性、Agent 授权隔离、工具排序稳定、影子模式对比
- **阶段三**: 参数缺失/类型错误校验、Provider Schema 适配、错误结构一致性、正确请求对比
- **阶段四**: 错误分流与 Hint 指引、正常路径无 Hint、权限边界守护

### 3.3 关键指标 (KPIs)
- **零中断**: 重构过程中 API 接口定义不发生 Break Change。
- **Schema 一致性**: 自动生成的 Schema 与现有手动定义的字段 100% 匹配。
- **自愈率**: 针对参数缺失类错误，Agent 的二次尝试成功率提升 > 50%。

---

## 6. 变更验收清单 (Acceptance Checklist)
- 工具清单与 Schema 与旧路径一致
- 所有 Agent 的工具权限仍按白名单生效
- `builtin-local-docs` 正常检索并引用本地文档
- 回归测试与后端测试均通过

---

## 7. 文件映射参考 (File Mapping)
- `backend/app/mcp/base.py`: 新增，定义工具基类。
- `backend/app/mcp/registry.py`: 新增，定义工具注册表。
- `backend/app/mcp/manager.py`: 修改，将转换与存储逻辑外包给注册表。
- `backend/app/api/chat.py`: 修改，改为从注册表获取工具。

---
*Generated by Agent Architect (2026-03-01)*
