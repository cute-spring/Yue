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
**总体结论**：阶段一至阶段三核心路径已全面落地；阶段四（错误自愈）框架已在注册表层建立；`ExecTool` 已完成 7.1~7.5 的开发与单元测试验证，支持本地模式配置收敛；系统基线测试全绿。

### 已完成
- **阶段一核心**：`BaseTool`、Schema 转换、参数预处理已实现。
- **阶段二核心**：`ToolRegistry` 统一管理工具发现与分发，`chat.py` 已全面接入。
- **阶段三核心**：Provider Schema 翻译器支持 OpenAI/Claude/DeepSeek 差异化适配；`validate_params` 防御式校验生效。
- **阶段三/四错误协议**：注册表层统一捕获错误并返回 `{error_code, message, hint}`，支持敏感路径脱敏。
- **ExecTool 全量落地**：实现 `builtin:exec` 工具，包含安全拦截（Deny/Allow/Workspace）、异步执行、超时控制、本地模式策略收敛及注册表接入。
- **内置工具扩展**：`builtin:docs_list` 与 `builtin:exec` 已同步至 Agent 工具清单。

### 待处理 / 待补齐
- **工具元数据接口归一化**：目前 `/api/mcp/tools` 仍直接调用 `McpManager`。计划将其迁移至 `ToolRegistry`，实现 UI 展示与执行逻辑的完全同源。
- **Provider 差异化深度适配**：当前 Schema 翻译器已支持多 Provider，但仍可针对不同模型的 Long Context 或特定约束做进一步微调。
- **影子模式下线**：待生产环境验证稳定后，移除 `MCP_TOOL_SHADOW_MODE` 相关兼容逻辑，彻底停用 `McpManager` 中的旧工具包装代码。
- **ExecTool 回归验证**：完成 Step 7.6（Agent 回归与安全边界验证）。

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
**完成标准**：验收清单全部通过，且可回滚。### Step 5：工具元数据查询归一化 (Metadata Unification)
**目标**：将 `/api/mcp/tools` 的后端实现由 `McpManager` 迁移至 `ToolRegistry`。
1. 在 `ToolRegistry` 中新增 `get_all_available_tools_metadata()` 方法，复用已有的内置与 MCP 工具扫描逻辑。
2. 修改 `backend/app/api/mcp.py`，将 `list_tools` 路由指向注册表。
3. 验证前端 UI 展示的工具列表与执行时的工具属性（如 Schema）完全一致。
**完成标准**：UI 展示无误，后端 `McpManager.get_available_tools` 引用计数清零。

### Step 6：生产验证与清理 (Cleanup)
**目标**：彻底停用旧路径，简化代码库。
1. 在生产环境运行一段时间，观察日志中“影子模式”的匹配情况。
2. 若无异常，移除 `MCP_TOOL_SHADOW_MODE` 开关及其对比代码。
3. 清理 `McpManager` 中不再需要的工具包装函数（如旧的 `_wrap_mcp_tool` 等）。
**完成标准**：代码库无冗余逻辑，注册表成为唯一的工具管理入口。

---

## 4.3 ExecTool 功能分析与落地计划（参考 docs/shell.py）
**目标**：引入通用且安全的命令执行工具（ExecTool），覆盖构建/测试/脚本运行等场景，并与 ToolRegistry 的错误分流与 Hint 规范无缝对齐。

### 功能分析（基于参考实现）
1. **统一入口与 Schema 约束**  
   - 工具名固定为 `exec`，参数仅包含 `command` 与可选 `working_dir`，便于注册表自动生成 Schema，并确保 LLM 调用一致性。  
   - 参考实现路径：`docs/shell.py` 中 `ExecTool.parameters` 与 `ExecTool.name`。  
2. **安全防护主线**  
   - 默认 denylist 拦截高危命令（删除/格式化/电源操作/写盘/ fork bomb）。  
   - 支持可选 allowlist，适用于强管控环境（仅允许特定命令）。  
   - 支持 restrict_to_workspace，限制命令中的路径在工作目录内，阻断路径穿越与越权访问。  
3. **执行与资源控制**  
   - 异步执行子进程，支持超时回收，避免僵尸进程与资源泄露。  
   - 输出统一拼接 stdout/stderr/exit code，并进行长度截断，保证上游稳定性。  
4. **错误返回语义**  
   - 参考实现采用 `"Error: ..."` 文本作为错误输出，便于注册表上层统一归一化为 `{error_code, message, hint}` 结构。

### 风险评估与边界
- **命令注入与误操作**：LLM 生成命令存在高风险，必须使用 deny/allow + workspace 限制作为硬边界。  
- **路径越权**：需要跨平台路径识别（Windows/Posix），并避免误判相对路径。  
- **长时间执行与输出膨胀**：必须有超时与输出截断。  
- **错误协议一致性**：ExecTool 自身只返回文本错误，错误结构化应由注册表层完成，避免双重封装。  

### 实现计划（小步快走 + 每步测试门槛）
#### Step 7.1：定义 ExecTool 接口与参数 Schema ✅
**目标**：在 `backend/app/mcp/` 侧新增 ExecTool，实现 `name/description/parameters` 的标准化入口。  
**变更点**：仅新增工具类与注册表注册入口，不接入执行逻辑。  
**测试**：  
- 新增 `test_exec_tool_schema`（验证 required/optional 字段、description）。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：Schema 与参考实现一致，且不影响现有工具列表。

#### Step 7.2：接入基础安全防护（denylist + allowlist） ✅
**目标**：实现命令拦截策略，覆盖高危命令与可选 allowlist。  
**变更点**：新增 guard 逻辑与对应错误文本。  
**测试**：  
- 单测覆盖：`rm -rf`、`format`、`shutdown` 等被拒；allowlist 模式下仅允许命中命令。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：危险命令被拒，允许命令通过，返回一致的错误文本。

#### Step 7.3：工作目录约束与路径越权防护 ✅
**目标**：实现 restrict_to_workspace 逻辑与路径解析，兼容 Windows/Posix。  
**变更点**：解析命令中的绝对路径并校验必须位于 cwd 下。  
**测试**：  
- 单测覆盖：`../`、绝对路径越界、相对路径误判保护。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：越权路径被拒，合法路径放行，无误杀相对路径。

#### Step 7.4：执行链路（异步执行 + 超时 + 输出截断） ✅
**目标**：完成真实执行能力与资源控制策略。  
**变更点**：引入异步子进程执行、超时回收、stdout/stderr/exit code 拼装、输出截断。  
**测试**：  
- 单测覆盖：`echo` 成功输出、超时命令返回超时错误、非零退出码包含 exit code。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：输出一致、超时可控、无僵尸进程泄露。

#### Step 7.5：接入 ToolRegistry 与错误结构化 ✅
**目标**：注册 ExecTool 并确保错误走注册表层 `{error_code, message, hint}`。  
**变更点**：注册表新增 ExecTool 注册与错误分流映射，不修改 ExecTool 自身错误文本约定。  
**测试**：  
- 集成测试覆盖：ExecTool 正常路径无 Hint；错误路径返回结构化 Hint。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py`  
**完成标准**：工具可用，错误结构化正确，正常路径无 Hint。

#### Step 7.6：Agent 回归与安全边界验证
**目标**：验证主子 Agent 与本地文档流不受影响，并确保 ExecTool 不越权。  
**变更点**：仅回归验证，不引入额外功能。  
**测试**：  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_agent_regression.py`  
- 可选全量：`PYTHONPATH=backend python3 -m unittest discover backend/tests -v`  
**完成标准**：回归全绿；ExecTool 行为符合安全边界与错误协议。

### 额外补充建议（可选增强）
#### Step 7.7：并发与队列隔离
**目标**：限制并发执行数量，避免资源竞争与系统抖动。  
**变更点**：为 ExecTool 添加可配置的并发上限或队列化策略。  
**测试**：  
- 单测覆盖：并发超限时返回结构化错误或排队提示。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py`  
**完成标准**：并发限制生效，未影响正常工具链路。

#### Step 7.8：命令模板化与参数白名单
**目标**：降低命令注入风险，提升可控性。  
**变更点**：支持“命令模板 + 参数白名单”模式，限制可变参数范围。  
**测试**：  
- 单测覆盖：非法参数被拒、合法参数通过、模板命令渲染正确。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：仅允许白名单参数，模板替换无旁路。

#### Step 7.9：敏感信息脱敏与审计日志
**目标**：避免输出泄露路径/密钥，并为安全审计保留依据。  
**变更点**：对输出进行模式脱敏（如 token/路径），记录受限命令与拒绝原因。  
**测试**：  
- 单测覆盖：脱敏规则生效且不破坏正常输出。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：敏感信息不可见，审计日志可追溯。

#### Step 7.10：跨平台执行一致性验证
**目标**：验证 Windows/Posix 路径与 shell 差异下行为一致。  
**变更点**：补充平台差异用例与路径解析回归。  
**测试**：  
- 单测覆盖：Windows 盘符路径/Posix 绝对路径/相对路径。  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
**完成标准**：跨平台路径策略一致，误判率可控。

### 本地模式可选配置块（个人使用）✅
**适用**：仅在个人本地开发机运行、强调效率与可用性、接受适度风险。  
**目标**：在不破坏安全底线前提下，降低阻拦频率与维护成本。  
**建议配置**（已在 `ExecToolConfig.from_settings` 中实现逻辑收敛）：  
1. **策略收敛**：保持 denylist，默认关闭 allowlist，减少误拦截。  
2. **超时放宽**：默认 timeout 提升至 180–300s，适配构建/依赖安装耗时。  
3. **并发放宽**：不开启队列或设置较高并发上限，避免等待。  
4. **跨平台降级**：若仅 macOS/Linux，Windows 路径兼容策略与测试降为可选。  
5. **日志降噪**：保留拒绝原因与关键错误，减少高频审计细节。  
6. **保留底线**：继续启用 restrict_to_workspace，避免误操作影响全盘。  
**验证建议**：  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_base_tool_unit.py`  
- 运行：`PYTHONPATH=backend pytest backend/tests/test_tool_registry_integration.py`  
**完成标准**：本地模式下功能可用、无明显误拦截，且未突破目录边界。

### ExecTool UI 手测用例（推荐）
**前置**：在 UI 的 Agent 设置页启用 `builtin:exec`，保存后生效。  
1. **基础执行**：输入“列出当前目录文件”。  
   - 预期：返回 `ls`/`dir` 输出；无 Hint 字段。  
2. **危险命令拦截**：输入“执行 rm -rf test_file”。  
   - 预期：返回结构化错误（`error_code/message/hint`）；提示包含安全拦截原因。  
3. **路径越权拦截**：输入“读取 /etc/passwd”（或 Windows 的 `C:\Windows\win.ini`）。  
   - 预期：返回结构化错误；Hint 提示仅允许工作目录内路径。  
4. **本地模式超时放宽**：将 `exec_tool.local_mode=true` 且 `timeout_s=5`，重启后端；输入“sleep 10 && echo Done”。  
   - 预期：仍能成功返回 Done（超时自动放宽到 180s+）。  
5. **错误自愈提示**：输入“在 non_existent_dir 下执行 ls”。  
   - 预期：返回结构化错误与 Hint；建议检查路径或列出父目录。

---

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
