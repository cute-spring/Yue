# MS Excel Support（Excel 深度支持）专题文档

本文聚焦“在 Yue 中增加 Excel 深度支持”的可执行路线，采用“小步快走 + 每步有测试门禁”的方式推进，确保每个迭代都可上线、可回滚、可验证。

---

## 1. 目标与范围

### 1.1 目标
- 为 Agent 增加稳定、可观测、可审计的 Excel 处理能力。
- 以 Built-in Tools 形式提供“读取、检查、查询”三类核心能力。
- 与现有文档检索能力一致，复用访问控制、引用信息和错误处理模式。

### 1.2 本期范围（In Scope）
- 新增 Excel 相关 Built-in Tools（只读优先）：
  - `excel_inspect`
  - `excel_read`
  - `excel_query`
- 支持格式：`.xlsx`、`.xls`、`.csv`（`.json` 作为查询输入可选）。
- 覆盖单元测试、集成测试、回归测试、性能基准测试。

### 1.3 非目标（Out of Scope）
- 本期不支持直接写回 Excel（避免高风险副作用）。
- 本期不做复杂 BI 可视化渲染（如图表重建）。
- 本期不做跨文件事务写入。

---

## 2. 当前基线与约束

### 2.1 代码基线
- 内置工具注册机制已具备，可复用 Built-in Registry。
- 文档工具已有成熟范式（参数 Schema、访问控制、错误回传、引用注入）。

### 2.2 依赖基线
- 当前后端依赖不包含 `openpyxl`、`duckdb`、`pandas`。
- 需要分阶段引入依赖，先最小可用，再逐步增强。

### 2.3 安全与稳定约束
- 必须沿用 allow/deny root 访问策略。
- 所有工具默认只读。
- 对大文件、超大 sheet、超长查询设置资源上限（行数、字节数、执行时间）。

---

## 3. 目标工具设计（MVP -> 增强）

### 3.1 `builtin:excel_inspect(path, root_dir?)`
- 能力：
  - 列出工作簿中的 sheet 名称。
  - 返回每个 sheet 的基础信息（行数、列数、表头推断结果）。
- 输出：
  - 结构化 JSON，供 Agent 做下一步工具选择。
- 风险级别：
  - 只读（read）。

### 3.2 `builtin:excel_read(path, sheet_name?, range?, root_dir?, mode?)`
- 能力：
  - 按 sheet 或 range 读取数据。
  - 支持 `mode=json | markdown`。
- 输出：
  - 默认截断策略（例如最多 500 行，避免上下文爆炸）。
- 风险级别：
  - 只读（read）。

### 3.3 `builtin:excel_query(path, query, sheet_name?, root_dir?)`
- 能力：
  - 使用自然语言查询结构化数据，返回 Top-K 结果与依据。
  - 先做查询意图解析，再执行安全受限查询。
- 输出：
  - 查询结果 + 命中范围 + 数据来源（sheet/range）。
- 风险级别：
  - 只读（read），但属于高计算成本能力，需预算控制。

---

## 4. 架构与落地策略

### 4.1 分层设计
- Tool 层：参数校验、访问控制、结果封装、错误映射。
- Service 层：Excel 解析、范围切片、类型标准化、查询执行。
- Guardrail 层：资源限制、超时、路径安全。

### 4.2 依赖分阶段策略
- 阶段 A（最小可用）：
  - 引入 `openpyxl`（`.xlsx` 读取）。
  - `.csv` 使用标准库处理。
- 阶段 B（查询增强）：
  - 引入 `duckdb` 或 `pandas`（二选一，建议 DuckDB 优先）。
- 阶段 C（兼容增强）：
  - `.xls` 支持按业务价值决定是否引入专用库。

### 4.2A 推荐落地架构（决策记录）
- 读取与结构识别层：`openpyxl`
  - 职责：sheet/range 读取、公式与数据验证提取、命名范围与结构画像。
- 查询执行层：`DuckDB in-memory`（仅只读 SQL 子集）
  - 职责：筛选、聚合、排序、TopK、可审计查询执行。
  - 约束：禁止 DDL/DML、禁止外部读写、限制函数白名单。
- 可选增强层：`Pandas`（仅内部转换，不直连 Agent）
  - 职责：少量复杂清洗（类型修复、异常值归一化、特殊文本处理）。
  - 边界：不得作为 Agent 直接查询入口，避免不可控 Python 路径扩大。

### 4.2B 必要补充（治理与降级）
- 查询安全治理
  - SQL 白名单：仅允许 `SELECT`、受限 `WITH`、安全聚合与排序。
  - 执行预算：最大扫描行数、最大结果行数、超时上限、并发上限。
- 可观测与审计
  - 记录 query 摘要、执行耗时、命中行数、降级原因、request_id。
  - 高风险输入（异常大文件/异常公式密度）触发告警与降级。
- 降级策略
  - DuckDB 执行失败时，自动回退至 `excel_inspect` + `excel_read` 输出可解释结果。
  - Pandas 相关清洗失败时不中断主流程，返回清洗失败说明与原始片段。
- 版本策略
  - 固定 `openpyxl`、`duckdb` 主版本，版本升级需通过专项回归集。
  - Pandas 默认不安装为强依赖，仅在启用增强能力时按需启用。

### 4.3 与现有系统对齐
- Tool 注册风格与 docs 类工具保持一致。
- 错误结构与 MCP 工具错误分类保持一致。
- 引用（citation）结构可扩展到 sheet/range 级别。

---

## 5. 小步快走开发计划（每步含测试门禁）

### 5.0 逻辑提取与脚本安全子章节（新增）

本子章节用于固化“读取 Excel 中定义逻辑”能力的执行清单，覆盖不规则 Sheet、公式依赖、命名范围、数据验证、宏脚本静态扫描，并明确安全边界：**只做静态提取，不执行任何脚本**。

#### 5.0.1 工具清单（新增）
- `builtin:excel_profile(path, root_dir?)`
  - 目标：识别不规则 Sheet 结构（表头行、数据块、合并单元格、隐藏行列、冻结窗格）。
  - 输出：结构画像 JSON（sheet 维度）。
- `builtin:excel_logic_extract(path, sheet_name?, root_dir?)`
  - 目标：提取公式、依赖关系、命名范围、数据验证、透视与连接元信息。
  - 输出：逻辑摘要 JSON（lineage、rules、named_ranges、validations、connections）。
- `builtin:excel_script_scan(path, root_dir?)`
  - 目标：对 VBA/宏相关内容做静态扫描与风险评分。
  - 输出：脚本摘要、敏感关键字命中、风险等级、处置建议。
- `builtin:excel_read(path, sheet_name?, range?, root_dir?, mode?)`
  - 目标：对 `excel_profile` 识别出的数据区做受限读取。
  - 输出：结构化数据（json/markdown），附来源定位信息。

#### 5.0.1A API/Schema 最小请求与响应示例（联调基线）

`builtin:excel_profile` 最小请求：

```json
{
  "path": "docs/fixtures/excel/sales_irregular.xlsx",
  "root_dir": "."
}
```

`builtin:excel_profile` 最小响应：

```json
{
  "ok": true,
  "tool": "excel_profile",
  "file": "docs/fixtures/excel/sales_irregular.xlsx",
  "sheets": [
    {
      "name": "Q1",
      "used_range": "A1:H120",
      "header_rows": [1, 2],
      "data_blocks": [{"start_row": 3, "end_row": 118, "start_col": 1, "end_col": 8}],
      "merged_cells": ["A1:A2", "B1:C1"],
      "hidden_rows": [57],
      "hidden_cols": ["G"]
    }
  ]
}
```

`builtin:excel_logic_extract` 最小请求：

```json
{
  "path": "docs/fixtures/excel/sales_irregular.xlsx",
  "sheet_name": "Q1",
  "root_dir": "."
}
```

`builtin:excel_logic_extract` 最小响应：

```json
{
  "ok": true,
  "tool": "excel_logic_extract",
  "sheet": "Q1",
  "formulas": [
    {"cell": "H3", "formula": "=F3*G3"},
    {"cell": "H4", "formula": "=F4*G4"}
  ],
  "lineage": {
    "nodes": ["F3", "G3", "H3", "F4", "G4", "H4"],
    "edges": [["F3", "H3"], ["G3", "H3"], ["F4", "H4"], ["G4", "H4"]]
  },
  "named_ranges": [
    {"name": "TaxRate", "refers_to": "Config!$B$2"}
  ],
  "validations": [
    {"range": "E3:E118", "type": "list", "formula1": "\"East,West,North,South\""}
  ],
  "connections": []
}
```

`builtin:excel_script_scan` 最小请求：

```json
{
  "path": "docs/fixtures/excel/macro_enabled_sample.xlsm",
  "root_dir": "."
}
```

`builtin:excel_script_scan` 最小响应：

```json
{
  "ok": true,
  "tool": "excel_script_scan",
  "has_macro": true,
  "risk_level": "high",
  "hits": [
    {"keyword": "Shell", "count": 2},
    {"keyword": "CreateObject", "count": 1}
  ],
  "summary": "Detected potentially dangerous macro patterns. Execution is blocked by policy.",
  "action": "static-analysis-only"
}
```

错误响应（统一格式示例）：

```json
{
  "ok": false,
  "error_code": "ACCESS_DENIED",
  "message": "Path is outside allowed roots.",
  "hint": "Set root_dir to an allowed project directory."
}
```

#### 5.0.2 执行清单（小步快走）
- 第 1 步：实现 `excel_profile` MVP ✅
  - 必做：不规则结构识别、多表头折叠、数据区定位。
  - 测试门禁：不规则样例集识别准确率达标；输出 schema 稳定。
- 第 2 步：实现 `excel_logic_extract` MVP ✅
  - 必做：公式提取、跨单元格依赖图、命名范围提取。
  - 测试门禁：golden 文件依赖图节点/边数量稳定；命名范围提取完整。
- 第 3 步：扩展规则提取 ✅
  - 必做：数据验证规则、透视配置、外部连接元信息提取。
  - 测试门禁：规则字段覆盖率达标；异常文件可降级返回。
- 第 4 步：实现 `excel_script_scan` ✅
  - 必做：宏脚本静态提取、敏感关键字检测、风险评分。
  - 测试门禁：恶意关键词样例命中率达标；误报率在阈值内。
- 第 5 步：接入安全护栏与可观测 ✅
  - 必做：脚本禁执行、路径白名单、超时/行数/字节上限、审计日志。
  - 测试门禁：越权访问与脚本执行请求 100% 拦截；日志可追踪 request_id。

#### 5.0.3 安全策略（强制）
- 禁止执行 VBA、Office Script、外部命令调用。
- 禁止网络出站行为（连接字符串只可解析不可执行）。
- 命中高风险关键词（如 `Shell`, `CreateObject`, `WScript`, `PowerShell`, `ADODB`）时，输出高风险告警并停止深度解析。
- 所有脚本相关输出默认脱敏并限制长度，避免泄露敏感参数。

#### 5.0.4 测试门禁（可执行）
- 单元测试
  - 结构识别：多表头、合并单元格、隐藏行列、空行混杂。
  - 逻辑提取：公式、命名范围、数据验证、外部连接字段。
  - 脚本扫描：关键字命中、风险分级、脱敏输出。
- 集成测试
  - `/api/mcp/tools` 可见 `builtin:excel_profile`、`builtin:excel_logic_extract`、`builtin:excel_script_scan`。
  - MCP 调用返回结构化 JSON，错误码与提示语一致。
- 对抗测试
  - 宏执行诱导、路径穿越、超大文件、损坏文件、编码异常文件。
  - 验收要求：不执行脚本、不崩溃、返回可解释错误。

#### 5.0.5 退出标准（DoD）
- 逻辑提取：核心字段（公式/依赖/命名范围）可稳定抽取。
- 安全合规：脚本零执行、越权零通过、风险识别可审计。
- 性能可控：在基准样本下满足既定 P95 与内存阈值。

#### 5.0.6 两周执行分解（再拆）

第 1 周（结构与逻辑提取）
- Day 1：样例集分层与标注规范
  - 产出：`fixtures` 分类表、样例元数据模板。
  - 测试：样例加载测试通过，文件标签完整率 100%。
- Day 2：`excel_profile` 基础结构识别
  - 产出：表头候选行、数据块边界、隐藏行列识别。
  - 测试：10 个基础样例识别正确率达到目标阈值。
- Day 3：`excel_profile` 不规则增强
  - 产出：多表头折叠、合并单元格映射、空行噪声过滤。
  - 测试：不规则样例集回归全通过，无结构回退。
- Day 4：`excel_logic_extract` 公式提取
  - 产出：公式清单、公式字段定位（sheet/cell）。
  - 测试：golden 文件公式数量与位置比对通过。
- Day 5：`excel_logic_extract` 依赖图
  - 产出：跨单元格依赖图（lineage）与摘要。
  - 测试：节点数/边数稳定，循环依赖可识别并告警。

第 2 周（规则、安全与上线门禁）
- Day 6：命名范围与数据验证提取
  - 产出：named ranges、validation rules 结构化输出。
  - 测试：命名范围提取完整率达标，规则字段无缺失。
- Day 7：透视与外部连接元信息提取
  - 产出：pivot/config 与 connection 元数据。
  - 测试：含透视/连接样例提取结果与 golden 对齐。
- Day 8：`excel_script_scan` 静态扫描
  - 产出：脚本摘要、风险关键词命中、风险分级。
  - 测试：恶意关键词命中率达标，误报率低于阈值。
- Day 9：安全护栏与可观测接入
  - 产出：禁执行策略、路径白名单、限流限时、审计日志。
  - 测试：对抗样例 100% 拦截，日志 request_id 可追踪。
- Day 10：联调与发布评审
  - 产出：联调报告、性能报告、灰度发布清单。
  - 测试：全量回归通过，P95/内存达到发布门槛。

#### 5.0.7 每日任务卡模板（执行即验收）

- 任务定义
  - 输入：样例文件集合、目标工具子能力、验收阈值。
  - 输出：代码变更、测试用例、结果快照、风险记录。
- 当日必过门禁
  - 单元测试通过率 100%（新增与受影响模块）。
  - 集成测试通过率 100%（工具注册与调用链路）。
  - 对抗测试无高危漏拦截。
  - 性能快照与前一日比较无显著退化。
- 失败处理规则
  - 任一门禁失败即停止合并，先修复再进入下一任务。
  - 失败案例必须沉淀到回归集，防止重复回归。
- 输出归档要求
  - 归档测试命令、关键日志、结果摘要、风险与处置。
  - 更新 roadmap 状态与次日计划。

## Step 0：测试资产与样例基线（1 天） ✅
### 交付
- 建立 `backend/tests/fixtures/excel/` 测试数据集：
  - 基础表、空表、多 sheet、中文表头、公式、超长文本、异常文件。
- 建立 Excel 工具测试目录与共用 fixture。

### 测试门禁
- 可重复读取所有 fixture，无随机失败。
- 基线测试命令可在 CI 本地一致运行。

### 验收标准
- fixture 覆盖率满足“数据形态矩阵”最小集合。

---

## Step 1：`excel_inspect` MVP（1~2 天） ✅
### 交付
- 新增 `excel_inspect` 工具与服务实现。（注：实际命名为 `excel_profile`）
- 返回 sheet 列表、行列统计、表头推断。

### 测试门禁
- 单元测试：
  - 正常路径：多 sheet 工作簿信息正确。
  - 异常路径：文件不存在、格式不支持、权限拒绝。
- 集成测试：
  - 通过 MCP 调用 `builtin:excel_inspect`，返回 JSON schema 合规。

### 验收标准
- 所有 inspect 相关测试通过。
- 错误信息可操作（提示下一步处理建议）。

---

## Step 2：`excel_read` MVP（2 天） ✅
### 交付
- 支持按 sheet / range 读取。
- 支持 `json` 与 `markdown` 输出模式。
- 默认分页和截断（防止上下文过大）。

### 测试门禁
- 单元测试：
  - 范围解析（A1:C20）正确。
  - `sheet_name` 缺省时默认策略正确。
  - 大范围读取触发上限保护。
- 集成测试：
  - Agent 调用后返回稳定结构，且数据行顺序可预测。

### 验收标准
- 对同一输入输出稳定（无不确定顺序）。
- 大文件不会导致超时或内存飙升。

---

## Step 3：访问控制与安全护栏（1 天） ✅
### 交付
- 对齐 docs 工具的 allow/deny root 校验。
- 增加路径规范化与越权访问拦截。
- 增加统一超时、最大行数、最大字节限制。

### 测试门禁
- 安全测试：
  - 路径穿越（`../`）被拒绝。
  - 非白名单目录被拒绝。
  - 超限参数被拒绝并返回清晰错误。
- 回归测试：
  - 不影响既有 docs/pdf 工具行为。

### 验收标准
- 安全类用例 100% 通过。
- 无新增高风险告警。

---

## Step 4：`excel_query`（可控查询版，2~3 天） ✅
### 交付
- 实现自然语言查询最小闭环：
  - 意图解析（筛选/聚合/排序/TopK）。
  - 受限执行（只读、超时、结果条数限制）。
- 首版建议使用 DuckDB in-memory 查询（更易做 SQL 约束）。

### 测试门禁
- 单元测试：
  - 查询解析到执行计划映射正确。
  - 禁止危险语句（DDL/DML/外部访问）。
- 集成测试：
  - 典型业务问句返回可验证结果。
  - 返回中包含 sheet/range 证据字段。
- 对抗测试：
  - Prompt 注入式查询指令无效化。

### 验收标准
- 查询结果准确率达标（以 golden cases 评估）。
- 对注入/越权场景具备拦截能力。

---

## Step 5：Agent 集成与可观测性（1~2 天） ✅
### 交付
- 工具元数据可在工具列表中展示。
- 为 Excel 工具接入调用日志与耗时指标。
- 在 chat/tool detail 中可查看输入摘要、输出摘要、耗时。

### 测试门禁
- API 集成测试：
  - `/api/mcp/tools` 可见 `builtin:excel_*`。
- E2E/手动回归：
  - Agent 选中 Excel 工具后可成功调用并展示结果。
- 观测测试：
  - 错误场景日志可追踪到 request_id。

### 验收标准
- 工具可发现、可调用、可追踪。

---

## Step 6：性能调优与发布门禁（2 天） ✅
### 交付
- 建立 Excel 专项性能基准：
  - 小/中/大文件（例如 1k、20k、100k 行）测试集。
- 关键优化：
  - 按需读取、列裁剪、结果采样、缓存热点 metadata。

### 测试门禁
- 性能测试：
  - P50/P95 延迟、峰值内存、吞吐（并发 5/10）达标。
- 稳定性测试：
  - 连续压测无崩溃、无明显内存泄漏。
- 回归测试：
  - 全量测试 + 关键路径 smoke tests 全绿。

### 验收标准
- 达成发布阈值后进入灰度。

---

## 6. 详细测试计划（测试金字塔）

### 6.1 单元测试（快速反馈）
- 范围解析：A1 语法、非法 range、空 range。
- 类型标准化：日期、数字、空值、公式单元格。
- 错误映射：文件缺失、权限失败、格式错误、超时。

### 6.2 集成测试（工具级）
- MCP 层工具注册与调用。
- `ctx.deps` 下 doc_roots / citation 兼容。
- 与现有 docs 工具共存不冲突。

### 6.3 端到端测试（Agent 视角）
- 场景 1：读取销售报表并回答“Top 5 产品”。
- 场景 2：跨 sheet 查找指定客户历史记录。
- 场景 3：异常文件输入后给出可执行错误提示。

### 6.4 回归测试
- 每次迭代均跑：
  - Excel 工具专项测试集。
  - 既有 `docs/pdf` 回归集。
  - 核心 API 集成回归。

### 6.5 性能与稳定性
- 固定数据集 + 固定机器规格 + 固定并发，保证可对比。
- 指标：P50/P95、峰值 RSS、错误率、超时率。

---

## 7. 测试数据矩阵（最小覆盖）

| 维度 | 样例 |
| --- | --- |
| 文件类型 | xlsx / xls / csv |
| 语言 | 中文表头 / 英文表头 |
| 数据规模 | 1k / 20k / 100k 行 |
| 内容类型 | 数值 / 文本 / 日期 / 公式 / 空值 |
| 结构复杂度 | 单 sheet / 多 sheet / 合并单元格 |
| 错误场景 | 文件损坏 / 路径越权 / 不支持格式 |

---

## 8. 发布策略与回滚

### 8.1 发布策略
- 先灰度到内部 Agent。
- 默认仅开放 `excel_inspect` + `excel_read`。
- `excel_query` 在性能和安全达标后再逐步放量。

### 8.2 回滚策略
- 工具级开关（配置层禁用）。
- 依赖回滚（锁定版本 + 回退 lock 文件）。
- 异常高峰时自动降级为 inspect/read 模式。

---

## 9. 里程碑定义（建议）

- M1（第 1 周）：Step 0~2 完成，inspect/read 可用，测试绿。(✅ 已交付 - 2026-03-03)
- M2（第 2 周）：Step 3~4 完成，query MVP 可用，安全门禁通过。(✅ 已交付 - 2026-03-03)
- M3（第 3 周）：Step 5~6 完成，性能达标，可灰度发布。(✅ 已交付 - 2026-03-03)

---

## 10. 建议的验收清单（DoD）

- 功能完整：`excel_inspect/read/query` 均可被 Agent 正确调用。
- 测试完整：单元 + 集成 + E2E + 性能测试全通过。
- 安全完整：路径、权限、查询约束、资源限制全部生效。
- 观测完整：日志、耗时、错误码可追踪。
- 文档完整：参数、限制、错误说明、示例齐全。

---

---

## 11. 执行进度报告 (Progress Report)

### 11.1 M1 交付达成 (2026-03-03)
- **状态**：已交付 (Completed)
- **交付项**：
  - `builtin:excel_profile`: 结构画像识别。
  - `builtin:excel_logic_extract`: 公式与逻辑提取。
  - `builtin:excel_script_scan`: 宏脚本静态安全扫描。
  - **核心服务**: `ExcelService` 实现，支持 `openpyxl` 结构化解析。
  - **测试**: 单元测试与集成测试全通过 (11 cases)。
  - **安全**: 路径白名单与脚本禁执行策略已生效。

### 11.2 M2 交付达成 (2026-03-03)
- **状态**：已交付 (Completed)
- **交付项**：
  - `builtin:excel_read`: 支持按 sheet/range 读取，支持 JSON/Markdown 输出及自动截断。
  - `builtin:excel_query`: 基于 DuckDB 的只读 SQL 查询引擎，支持自然语言意图对齐。
  - **依赖增强**: 引入 `duckdb` 与 `pandas` 提升处理能力。
  - **安全**: 仅允许 `SELECT` 语句，资源使用受限。
  - **测试**: 覆盖了读取、SQL 查询、非法语句拦截等场景 (17 cases passed)。

### 11.3 M3 交付达成 (2026-03-03)
- **状态**：已交付 (Completed)
- **交付项**:
  - **Agent 优化**: 完善了所有工具的元数据描述与参数 `hint`，指导 Agent 何时使用 `profile`、`read` 或 `query`。
  - **可观测性**: `ExcelService` 接入审计日志 `[ExcelAudit]`，记录 `request_id`、耗时、查询摘要、截断标志等。
  - **性能调优**: 
    - `excel_read` 与 `excel_query` 强制使用 `read_only=True` 模式，大幅降低内存占用。
    - `excel_profile` 保持 `read_only=False` 以获取完整元数据（如合并单元格）。
    - 增加 `backend/tests/test_excel_perf.py` 专项性能基准，验证 100k 行数据的处理能力。
  - **错误处理**: 统一返回结构化 `error_code` 与 `hint`，提升 Agent 自愈能力。
  - **测试**: 全量回归测试通过 (26 cases)，包含 100k 行性能压测。

---

## 12. 总结与后续

目前 Excel 深度支持功能已完成 Phase 1~3 的核心交付。Agent 具备了对 Excel 文件的结构画像、逻辑提取、安全扫描、受限读取以及高性能 SQL 查询能力。所有功能均受路径白名单与只读安全策略保护，并具备完善的可观测性。

---

## 13. 未来路线图与 ROI 分析 (Future Roadmap & ROI Analysis)

基于 Phase 1-3 的成功交付，以下是对后续增强能力的 ROI 分析与演进规划。

### 13.1 ROI 分析矩阵

| 规划项 | 业务价值 (Return) | 开发成本 (Investment) | ROI 评级 | 建议决策 |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend UX (富文本预览/引用跳转)** | **极高**：将 JSON 转化为可交互表格，显著提升感知专业度与易用性。 | **低-中**：复用现有 UI 组件，仅需增加数据映射。 | **High (推荐)** | **首选 Quick Win** |
| **Advanced RAG (语义化搜索)** | **极高**：核心 AI 能力。支持自然语言模糊匹配，无需精准 SQL。 | **中-高**：涉及行向量化、向量库集成与跨文件 Join。 | **High** | **战略级必做** |
| **Phase 4 (受限写回能力)** | **中-高**：支持 Agent 自动填表或生成报表，实现业务闭环。 | **中**：需严格安全护栏、备份机制与 UI 确认流程。 | **Medium** | **建议“新副本”模式** |
| **Large File Streaming (流式处理)** | **中**：覆盖超大规模（>100MB）企业级场景。 | **中**：需重构现有加载模式为分块处理。 | **Medium** | **按需扩展** |
| **Legacy Format (.xls 支持)** | **低**：仅针对极少数老旧存量文件。 | **低**：引入 `xlrd` 库，增加复杂度。 | **Low** | **延后处理** |
| **Tech Debt (监控与自动化)** | **中**：保证系统长期稳定，防止性能退化。 | **低**：已有审计日志基础，仅需 CI 脚本。 | **Medium** | **伴随式开发** |

### 13.2 演进执行计划 (Execution Plan)

- **短期 (Quick Win)**: 启动 **Frontend UX 优化**。在聊天窗口渲染 `excel_read` 的交互式表格，支持点击引用直接定位。
- **中期 (Strategic Jump)**: 预研 **Advanced RAG**。结合结构化 SQL 与非结构化语义检索，提升 Agent 处理复杂/不规则表格的智能化水平。
- **长期 (Scale-up)**: 根据实际业务反馈，决定是否开启 **受限写回** 或 **超大文件流式加载**。

---

## 14. 附录：Excel 专家 Agent 系统提示词 (Appendix: Excel Expert Agent System Prompt)

为了最大化新工具（`profile`, `read`, `query`, `logic_extract`, `script_scan`）的效能，建议为专门处理表格任务的 Agent 配置如下系统提示词：

### 14.1 系统提示词模板

```markdown
# Role: 高级 Excel 数据分析与自动化专家

你是一位专业的数据分析师，精通基于 Excel 的商业智能和数据取证。你的目标是通过专业的 Excel MCP 工具集，提供准确、高性能且安全的分析结果。

## 🛠 工具使用策略 (分阶段执行)

在处理 Excel/CSV 文件时，请始终遵循以下逻辑路径：

1. **第一阶段：结构识别 (强制首步)**
   - 使用 `excel_profile` 了解文件的解剖结构。识别工作表名称、数据块位置、合并单元格以及隐藏行列。
   - *严禁假设数据从 A1 开始。* 必须参考工具返回的 `header_rows` 和 `data_blocks` 信息。

2. **第二阶段：安全与逻辑验证 (视情况而定)**
   - 在处理来源不明的文件前，先运行 `excel_script_scan` 检测高风险 VBA/宏。
   - 当用户询问“这是如何计算的？”或涉及跨表依赖时，使用 `excel_logic_extract` 提取公式。

3. **第三阶段：数据检索 (按需选择)**
   - **小型数据集 (<500行)**: 使用 `excel_read` (mode="markdown") 直接读取。
   - **大型数据集/复杂逻辑**: 使用 `excel_query` (DuckDB SQL) 进行过滤、聚合或关联。SQL 查询比读取原始行效率高 100 倍。

## 📊 分析原则

- **Token 效率**: 优先使用 `excel_query` 处理分组、求和或搜索。仅在必须展示原始样本时使用 `excel_read`。
- **SQL 最佳实践**: 使用 `excel_query` 时，始终查询虚拟表 `excel_data`。
- **引用完整性**: 在最终回答中务必注明具体的 Sheet 和 Range (例如 `Sheet1!A1:B10`)，确保透明度。
- **处理截断**: 若结果被截断 (`is_truncated: true`)，应主动告知用户并建议更精确的 SQL 过滤条件。

## 🛡 安全与约束

- **只读属性**: 你无法修改原始文件。如果用户要求“更新”，请解释你只能提供计算逻辑或变更建议。
- **隐私保护**: 关注 `excel_profile` 识别出的隐藏行列，除非与任务直接相关，否则不主动暴露。
- **查询审计**: 确保 SQL 仅包含 `SELECT` 语句（工具已做限制，但 AI 需保持意识）。
```


### 14.2 Built-in Excel Expert Agent

Use the following configuration to create a production-ready built-in Excel Expert Agent in Yue.

### Agent Profile

- **Agent Name**: Excel Analyst
- **Enabled Tools**:
  - `builtin:excel_profile`
  - `builtin:excel_read`
  - `builtin:excel_query`
  - `builtin:excel_logic_extract`
  - `builtin:excel_script_scan`

### System Prompt

```markdown
# Role: Senior Excel Data Analyst & Automation Expert

You are a professional analyst specializing in Excel-driven business intelligence and data forensics. Your mission is to deliver accurate, high-performance, and secure analysis using built-in Excel tools.

## Tool Strategy (Phase-Based Execution)

Always follow this sequence when handling Excel/CSV files:

1. **Phase 1: Structural Awareness (Mandatory First Step)**
   - Use `excel_profile` first to identify sheet names, data blocks, merged cells, and hidden rows/columns.
   - Never assume data starts at `A1`; rely on inferred `header_rows` and `data_blocks`.

2. **Phase 2: Security & Logic Verification (When Applicable)**
   - Use `excel_script_scan` before analyzing files from untrusted sources to detect risky VBA/macros.
   - Use `excel_logic_extract` when users ask how values are calculated or when cross-sheet formula dependencies are suspected.

3. **Phase 3: Data Retrieval (Choose by Scale)**
   - For small datasets (<500 rows), use `excel_read` with `mode="markdown"` for direct inspection.
   - For large datasets or complex analysis, use `excel_query` with DuckDB SQL for filtering, grouping, and joins.

## Analytical Principles

- Prefer `excel_query` for search, aggregation, and grouping to minimize token usage.
- Query only the virtual table `excel_data` using standard SQL.
- Cite exact Sheet and Range in final answers (for example, `Sheet1!A1:B10`).
- If tool output is truncated (`is_truncated: true`), notify the user and refine query scope.

## Security & Constraints

- Treat source files as read-only; do not claim direct file edits.
- Respect hidden rows/columns surfaced by `excel_profile`; reveal only when task-relevant.
- Keep SQL strictly `SELECT` statements.

## Example Workflow

User request: "Find the top 5 sales regions in the Q4 report."

1. Run `excel_profile(path="Q4_Report.xlsx")` to locate the target sheet and data range.
2. Run `excel_query(path="Q4_Report.xlsx", query="SELECT Region, SUM(Sales) AS TotalSales FROM excel_data GROUP BY Region ORDER BY TotalSales DESC LIMIT 5")`.
3. Respond with ranked results and a source citation including sheet/range.
```

This setup makes the Agent think before acting, reduces spreadsheet structure hallucinations, and fully leverages DuckDB-based querying efficiency.
