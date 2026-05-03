# MCP Smart Paste — AI 智能配置解析 设计文档

> **状态：待 Review**
> **创建日期：** 2026-05-02
> **关联计划：** `docs/plans/2026-05-02-dual-mcp-transport-support-plan.md`

---

## 1. 背景与动机

### 1.1 现状

Yue 目前为 MCP Server 提供三条配置路径：

| 路径 | 入口 | 门槛 | 痛点 |
|------|------|------|------|
| Marketplace 模板向导 | "Add from Marketplace" | 中 | 12+ 字段，需逐个填写 |
| Manual JSON | "Add Manually" | 高 | 需手写 JSON，出错率高 |
| Raw Config | 直接编辑完整 JSON | 最高 | 面向开发者 |

三条路径都要求用户**具备结构化的 MCP 配置知识**，将信息手动拆解到 `command` / `args` / `url` / `headers` / `env` 等字段。但从同事、GitHub README、内部 Wiki 或其他工具中复制得到的配置信息，往往是**非结构化或半结构化**的片段，而不是可以直接落库的 `ServerConfig`。

因此，用户真正的痛点不是“不会填表”，而是：

- 手头已有配置线索，但格式不标准
- 无法快速判断这是 `stdio` 还是 `streamable_http`
- 不知道哪些字段该拆到 `env`、`headers`、`args`
- 害怕把 token、password、API key 明文填错位置

### 1.2 用户场景

- 同事发来一段 Claude Desktop 的 `mcpServers` JSON 配置
- 从 GitHub README 复制了一段 `npx @xxx/mcp-server --token xxx` 命令
- 从内部 Wiki 看到一个 MCP 服务地址 `https://mcp.internal.company.com/stream` 和 token 说明
- 收到一段自然语言描述："用 stdio 方式连我们公司的 Jira MCP，命令是 npx，包名 @company/jira-mcp，需要环境变量 JIRA_TOKEN"

用户期望：**粘贴 → 自动识别 → 微调 → 保存**，而非手动拆解字段。

### 1.3 目标

新增第四条配置路径 **"Smart Paste"**，利用项目已有的 LLM 基础设施，将任意格式的输入自动解析为结构化的 MCP 配置候选项，覆盖 `stdio` 和 `streamable_http` 两种 transport，并让用户在保存前完成最终确认。

### 1.4 定位与边界

Smart Paste 的定位是：

- **降低结构化转换成本**，而不是替代 Manual JSON / Raw Config
- **返回候选配置**，而不是返回可直接信任的最终配置
- **优先帮助用户从已有片段快速起步**，而不是从零生成复杂配置

本期目标不是追求 100% 自动化，而是尽可能把用户从“原始粘贴内容”推进到“可编辑、可保存的结构化候选配置”。

---

## 2. 当前架构参考

### 2.1 关键模块

| 模块 | 路径 | 职责 |
|------|------|------|
| API 路由 | `backend/app/api/mcp.py` | 配置 CRUD、模板验证、重载 |
| 数据模型 | `backend/app/mcp/models.py` | `ServerConfig` Pydantic 校验，transport 合约强制执行 |
| 连接管理 | `backend/app/mcp/manager.py` | `stdio` / `streamable_http` 连接、会话、状态 |
| 模板系统 | `backend/app/mcp/templates.py` | 模板定义、表单字段、渲染 |
| 前端页面 | `frontend/src/pages/Settings.tsx` | MCP Tab 状态管理、对话框调度 |
| 前端组件 | `frontend/src/pages/settings/components/McpSettingsTab.tsx` | MCP 列表、Add 菜单 |
| 模版弹窗 | `frontend/src/pages/settings/components/modals/McpMarketplaceModal.tsx` | 模板表单、transport 感知字段显隐 |
| 手动弹窗 | `frontend/src/pages/settings/components/modals/McpManualModal.tsx` | JSON 手工输入 |
| 原始配置弹窗 | `frontend/src/pages/settings/components/modals/McpRawConfigModal.tsx` | 完整 JSON 编辑 |
| 前端类型 | `frontend/src/pages/settings/types.ts` | TypeScript 类型定义 |
| 解析工具 | `frontend/src/pages/settings/settingsUtils.ts` | Manual JSON 解析逻辑 |

### 2.2 现有 LLM 基础设施

项目已集成 `pydantic_ai` 作为 LLM 调用框架，通过 `config_service.get_llm_config()` 获取 LLM 配置（provider、model、proxy 等）。这意味着 Smart Paste 可以直接复用现有 LLM 通道，无需引入新的 AI SDK 或额外依赖。

### 2.3 Transport 合约（当前已实现）

```python
# models.py — ServerConfig 校验规则
class ServerConfig(BaseModel):
    name: str
    transport: str = "stdio"          # "stdio" | "streamable_http"

    # stdio 专属
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None

    # streamable_http 专属
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    # 共用
    enabled: bool = True
    timeout: float = 60.0
    min_version: Optional[str] = None

    # 互斥校验：
    # - transport="stdio"             → command 必填，url/headers 禁止
    # - transport="streamable_http"   → url 必填，command/args 禁止
    # - 缺失 transport 兜底为 "stdio"
```

### 2.4 Smart Paste 新增模块建议

为了避免将所有逻辑堆进单个 `parser.py`，建议拆分为以下模块：

| 模块 | 建议路径 | 职责 |
|------|----------|------|
| API 层 | `backend/app/api/mcp.py` | 暴露 `POST /api/mcp/parse` |
| 模型层 | `backend/app/mcp/smart_paste_models.py` | 请求/响应模型、候选配置模型 |
| 编排层 | `backend/app/mcp/smart_paste_service.py` | 输入预检、规则解析、LLM 调用、错误映射 |
| 安全层 | `backend/app/mcp/smart_paste_sanitizer.py` | 敏感值清洗、字段白名单、风险检测 |
| 校验复用 | `backend/app/mcp/models.py` | 继续复用 `ServerConfig` 进行兼容校验 |

### 2.5 LLM 调用前提

Smart Paste 会把用户粘贴的文本发送给已配置的 LLM provider，因此必须满足以下前提：

- provider / proxy / gateway 不将请求用于训练
- 请求内容不进行长期明文持久化
- 调试日志中不得记录用户原始粘贴内容
- 若存在多级代理，必须确认每一级都满足最小留存与脱敏要求

若以上条件无法满足，则 Smart Paste 功能默认关闭。

---

## 3. 设计方案

### 3.1 总体流程

```text
┌──────────┐     ┌──────────────────┐     ┌────────────────────┐     ┌──────────────┐     ┌──────────────┐
│  用户粘贴  │────▶│  前端输入预检查      │────▶│  后端解析编排         │────▶│  结构化预览    │────▶│  确认 + 保存  │
│  任意文本  │     │  空输入/超长/非法字符 │     │  Rule-first, LLM-second │     │  (可编辑表单)  │     │  POST /      │
└──────────┘     └──────────────────┘     └────────────────────┘     └──────────────┘     └──────────────┘
```

1. 用户在 "Smart Paste" 弹窗中粘贴任意文本
2. 前端先做本地预检查：
   - 空输入直接提示，不发请求
   - 超过 8000 字符直接拦截
   - 过滤明显非法控制字符
3. 后端接收 `POST /api/mcp/parse` 后，按以下优先级处理：
   - **规则解析优先（rule-first）**：优先识别标准 JSON、命令行片段、单一 URL 场景
   - **LLM 解析兜底（LLM-second）**：仅在规则解析无法完整提取结构化配置时调用 LLM
4. 后端对候选结果做统一后处理：
   - JSON / schema 解析
   - 敏感值清洗与占位符替换
   - `ServerConfig` 兼容性校验
   - 丢弃非法结果并保留可用结果
5. 前端展示结构化候选配置预览，用户可以逐条编辑、删除、选择保存
6. 用户确认后调用 `POST /api/mcp/` 保存；必要时可先调用 `POST /validate` 做无副作用校验

> 注意：Smart Paste 返回的是 **candidate config（候选配置）**，不是最终可信配置。所有结果都必须经过用户确认，且默认 `enabled=false`。

### 3.2 后端 API 契约

#### 新增端点：`POST /api/mcp/parse`

**位置：** `backend/app/api/mcp.py`，与现有 `POST /`、`POST /validate` 并列

**职责：**
- 接收用户粘贴的非结构化文本
- 返回一个或多个结构化 MCP 配置候选项
- 不做持久化写入
- 不直接启用任何 MCP Server
- 所有结果仅作为用户确认前的候选配置

**与现有端点的职责边界：**

| 端点 | 职责 |
|------|------|
| `POST /api/mcp/parse` | 将任意文本解析为候选配置 |
| `POST /api/mcp/validate` | 对用户编辑后的结构化配置做无副作用校验 |
| `POST /api/mcp/` | 持久化保存最终确认后的配置 |

**请求：**

```json
{
  "raw_text": "<用户粘贴的任意文本>"
}
```

**请求约束：**
- `raw_text` 不能为空
- `raw_text` 最大长度为 8000 字符
- 超长请求不做静默截断，直接返回 `400`
- 控制字符会在服务端再次过滤，保留换行与制表符

**成功响应（单条解析结果）：**

```json
{
  "ok": true,
  "results": [
    {
      "name": "my-mcp-server",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem"],
      "env": { "HOME": "${HOME}" },
      "url": null,
      "headers": null,
      "enabled": false,
      "timeout": 60.0,
      "min_version": null,
      "confidence": 0.95,
      "hints": [
        "已识别为 stdio 模式",
        "建议先以 enabled=false 保存，验证连接后再启用"
      ],
      "warnings": [],
      "missing_fields": [],
      "source_index": 0
    }
  ],
  "parse_mode": "rule",
  "error": null
}
```

**成功响应（多条解析结果）：**

```json
{
  "ok": true,
  "results": [
    {
      "name": "filesystem-server",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/workspace"],
      "env": null,
      "url": null,
      "headers": null,
      "enabled": false,
      "timeout": 60.0,
      "min_version": null,
      "confidence": 0.92,
      "hints": ["已识别为 stdio 模式"],
      "warnings": [],
      "missing_fields": [],
      "source_index": 0
    },
    {
      "name": "company-jira",
      "transport": "streamable_http",
      "command": null,
      "args": null,
      "url": "https://mcp.internal.company.com/jira/stream",
      "headers": { "Authorization": "${JIRA_TOKEN}" },
      "env": null,
      "enabled": false,
      "timeout": 60.0,
      "min_version": null,
      "confidence": 0.88,
      "hints": ["已识别为 streamable_http 模式"],
      "warnings": ["检测到鉴权信息，已替换为环境变量占位符"],
      "missing_fields": [],
      "source_index": 1
    }
  ],
  "parse_mode": "hybrid",
  "error": null
}
```

**业务失败响应（请求合法，但未得到可用配置）：**

```json
{
  "ok": false,
  "results": [],
  "parse_mode": "ai",
  "error": "无法从输入中解析出有效的 MCP 配置，请检查输入内容或尝试手动配置。"
}
```

**Pydantic 模型定义建议：**

```python
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, confloat

class SmartPasteRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=8000)

class ParsedServerConfig(BaseModel):
    name: str
    transport: Literal["stdio", "streamable_http"]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: bool = False
    timeout: float = 60.0
    min_version: Optional[str] = None
    confidence: confloat(ge=0.0, le=1.0)
    hints: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    source_index: Optional[int] = None

class SmartPasteResponse(BaseModel):
    ok: bool
    results: List[ParsedServerConfig] = Field(default_factory=list)
    parse_mode: Literal["rule", "ai", "hybrid"] = "ai"
    error: Optional[str] = None
```

**多条结果语义：**
- `results[]` 顺序与原始文本中的出现顺序一致
- 每个结果项互相独立，可单独编辑、删除、保存
- 如果同一输入包含同一服务的多个 transport 方案，可以返回多条候选项，不强行合并

### 3.3 LLM Prompt 策略

#### 核心原则

1. **规则优先，LLM 兜底**
   - 标准 JSON、命令行片段、单一 URL 等高确定性输入优先走规则解析
   - 仅在规则解析无法完整提取结构化配置时调用 LLM

2. **输出必须是机器可校验的结构化结果**
   - 优先使用 schema-based structured output
   - 若底层 provider 仅支持 JSON mode，则仍必须经过后续 schema 校验

3. **密钥绝不直出**
   - 任何疑似 token / password / api key / secret / bearer token / JWT / 私钥片段，都不能在输出中原样出现
   - 高风险字段必须转成 `${ENV_NAME}` 占位符

4. **低置信度不猜测**
   - 无法确定的字段不填
   - 使用 `missing_fields` 和 `warnings` 提示用户补充

5. **多结果显式返回**
   - 同一输入若包含多个 MCP 配置，应全部返回到 `results[]`
   - 不擅自在多个候选项中二选一

#### System Prompt（中文版）

```text
你是一个 MCP (Model Context Protocol) 配置解析器。

## 你的任务
分析用户粘贴的文本，从中提取一个或多个 MCP Server 配置信息，返回结构化 JSON。

## 总体规则
- 输出必须严格符合给定 schema
- 如果无法确定字段值，不要猜测；保留为空，并在 missing_fields 中指出
- 如果文本中包含多个 MCP 配置，全部输出到 results
- 如果同一服务存在多种接入方式（如 stdio 和 streamable_http），可以分别输出多个候选项
- 普通网页 URL 不应误判为 MCP endpoint，只有明确语义指向 MCP 服务地址时才识别为 streamable_http

## Transport 判断规则
- 如果文本包含命令行格式（如 "npx ..."、"uvx ..."、"python -m ..."）或 "command"/"args" 字段 → transport = "stdio"
- 如果文本包含 HTTP/HTTPS URL 且语义明确为 MCP 端点 → transport = "streamable_http"
- 如果存在多个候选 transport，不要强行合并，分别输出

## 字段提取规则

### stdio 模式
- command: 提取最外层可执行命令
- args: 提取命令参数列表，保持顺序
- env: 提取环境变量；若值疑似敏感信息，改为 ${ENV_NAME}

### streamable_http 模式
- url: 提取完整的 HTTP/HTTPS MCP endpoint
- headers: 提取请求头；敏感值必须改为 ${ENV_NAME}
- env: 如果文本明确提到运行前需要设置环境变量，则提取

### 通用字段
- name: 生成简短、稳定、英文 kebab-case 名称
- enabled: 一律设为 false
- timeout: 默认 60.0
- confidence: 给出 0.0-1.0 的解析置信度
- hints: 提供简洁说明，至少包含 transport 识别结果
- warnings: 描述风险、冲突或敏感信息替换情况
- missing_fields: 列出当前仍需用户补充的关键字段

## 安全规则（极其重要）
- 任何看起来像 token、password、api key、secret、JWT、Bearer token、私钥片段的值，绝对不能原样输出
- 将其替换为 ${ENV_NAME} 占位符
- 对高风险 header（Authorization、X-API-Key 等）和高风险 env（名称含 token/secret/password/key），如存在值，必须输出占位符
- 在 warnings 或 hints 中提醒用户设置对应环境变量

## 输出要求
- 返回一个 JSON 对象
- 顶层只包含 results
- results 中每一项都必须符合 schema
- 如果无法识别任何有效 MCP 配置，返回 { "results": [] }
```

#### LLM 调用参数

| 参数 | 建议值 | 说明 |
|------|--------|------|
| temperature | 0.0 | 保证确定性 |
| max_tokens | 2048 | 对单次解析足够 |
| response_format | structured output / `json_object` | 优先 structured output |
| timeout | 8-12s | 避免交互等待过长 |
| retry | 最多 1 次 | 仅用于 schema 修复重试 |
| model | light tier → balanced tier | 复杂输入可升级模型 |

#### LLM 调用处理流程

```text
raw_text
  │
  ▼
1. 输入预检查
   - 空输入 → 400
   - 超长 → 400
   - 控制字符过滤
  │
  ▼
2. 规则解析快路径
   - JSON / 命令行 / URL
   - 若结果完整且通过校验 → 直接返回 parse_mode=rule
  │
  ▼
3. 调用 LLM
   - 注入 system prompt
   - 使用 structured output / JSON mode
   - timeout 8-12s
  │
  ▼
4. schema 校验 + 安全清洗
   - JSON / schema 解析
   - 敏感值替换
   - 字段白名单校验
   - 逐条过 ServerConfig 兼容校验
  │
  ▼
5. 失败时最多重试 1 次
   - 将 schema 校验错误反馈给模型
   - 若仍失败 → 返回 ok=false
  │
  ▼
6. 返回 SmartPasteResponse
```

#### 降级策略

| 场景 | 行为 |
|------|------|
| 规则解析成功 | 直接返回 `parse_mode=rule`，不调用 LLM |
| LLM 服务不可用 | 返回 `503`，提示 AI 服务暂时不可用，并引导手动配置 |
| LLM 超时 | 返回 `504`，提示解析超时可重试 |
| LLM 返回非结构化结果 | 进行一次 schema 修复重试；仍失败则返回 `ok=false` |
| 部分结果校验失败 | 丢弃非法条目，保留合法条目，并在 `warnings` 中提示 |
| 无任何有效结果 | 返回 `200 + ok=false` |

### 3.4 前端 UI 设计

#### 在 MCP Tab 中新增 Smart Paste 入口

**位置变更：** 在 `McpSettingsTab.tsx` 的 Add 菜单中新增第三个按钮：

```text
Add from Marketplace    ← 已有
Add Manually            ← 已有
Smart Paste (AI)        ← 新增
```

#### SmartPasteModal 组件

**新增文件：** `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx`

**定位：**
- Smart Paste 适用于“我已经有一段配置片段，但不想手动拆字段”的场景
- 它不是从零创建复杂配置的唯一入口；复杂场景仍可回退到 Manual JSON 或 Raw Config

**UI 布局（3 个阶段）：**

```text
┌─────────────────────────────────────────────────┐
│  Smart Paste (AI)                          [✕]  │
│  ─────────────────────────────────────────────  │
│                                                 │
│  粘贴你的 MCP 配置信息                           │
│  ┌──────────────────────────────────────────┐   │
│  │  支持：                                     │   │
│  │  · Claude Desktop / Cursor MCP JSON 配置    │   │
│  │  · 命令行片段（如 npx @xxx/mcp-server）      │   │
│  │  · HTTP 端点 + token 描述                   │   │
│  │  · 自然语言描述                              │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │                                          │   │
│  │  (textarea, min-h-[180px], monospace)    │   │
│  │                                          │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  密钥安全：token/密码会自动转为 ${ENV_NAME} 占位符 │
│                                                 │
│  [取消]                        [AI 解析]        │
│                                                 │
│  解析完成后展示结构化预览                         │
│  支持单条/多条候选项的编辑、删除、勾选保存         │
└─────────────────────────────────────────────────┘
```

**状态机设计：**

```text
IDLE
  ├──[点击 AI 解析]────────────▶ PARSING
  │                             ├──[成功]────────▶ PREVIEW
  │                             ├──[失败]────────▶ ERROR_PARSE
  │                             └──[取消]────────▶ CANCELLED
  │
PREVIEW
  ├──[重新解析]────────────────▶ IDLE
  ├──[确认保存]────────────────▶ SAVING
  └──[编辑多条结果/删除候选项]──▶ PREVIEW
                               
SAVING
  ├──[全部成功]────────────────▶ DONE
  ├──[部分成功]────────────────▶ PARTIAL_SUCCESS
  └──[失败]────────────────────▶ ERROR_SAVE
```

**多条结果交互语义：**
- 多条解析结果默认以 Accordion 或 Tab 展示
- 每条结果可独立：
  - 编辑字段
  - 删除
  - 勾选是否参与保存
- 支持“逐条保存”与“批量保存”
- 若批量保存时部分结果失败，前端进入 `PARTIAL_SUCCESS`，逐条展示成功与失败项，不整体丢失编辑状态

**低置信度展示规则：**
- `confidence >= 0.85`：正常展示
- `0.6 <= confidence < 0.85`：显示黄色提醒，建议用户检查
- `confidence < 0.6`：显示高风险提示，并高亮 `missing_fields`

**用户编辑后的提示策略：**
- 如果用户修改了关键字段（如 `transport`、`command`、`url`、`headers`、`env`），显示提示：
  - “以下解析说明基于初始 AI 结果，编辑后可能不再完全适用”
- `hints` 不自动消失，但应与编辑后的当前值做视觉区分

**请求取消：**
- 解析请求使用 `AbortController`
- 用户关闭弹窗或主动取消时，中断正在进行的 `POST /api/mcp/parse`

**命名冲突处理：**
- 保存前先检查是否与现有 MCP 名称冲突
- 若冲突：
  - 提示用户修改名称
  - 或自动建议一个去重名称

**组件 Props：**

```typescript
type McpSmartPasteModalProps = {
  onClose: () => void;
  onParse: (rawText: string) => Promise<SmartPasteResponse>;
  onSave: (configs: McpServerConfig[]) => Promise<void>;
};
```

**与 `Settings.tsx` 的集成点：**

```typescript
const [showSmartPaste, setShowSmartPaste] = createSignal(false);
```

以及解析 / 保存回调：

```typescript
const parseMcpSmartPaste = async (rawText: string): Promise<SmartPasteResponse> => {
  const res = await fetch('/api/mcp/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_text: rawText }),
  });
  return res.json();
};

const saveMcpSmartPaste = async (configs: McpServerConfig[]) => {
  const res = await fetch('/api/mcp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configs),
  });
  if (!res.ok) throw new Error('保存失败');
  await reloadMcp();
};
```

#### 前端类型补充（`types.ts` 新增）

```typescript
export type ParsedMcpConfig = {
  name: string;
  transport: 'stdio' | 'streamable_http';
  command: string | null;
  args: string[] | null;
  url: string | null;
  headers: Record<string, string> | null;
  env: Record<string, string> | null;
  enabled: boolean;
  timeout: number;
  min_version: string | null;
  confidence: number;
  hints: string[];
  warnings: string[];
  missing_fields: string[];
  source_index?: number | null;
};

export type SmartPasteResponse = {
  ok: boolean;
  results: ParsedMcpConfig[];
  parse_mode: 'rule' | 'ai' | 'hybrid';
  error?: string | null;
};
```

### 3.5 交互细节

| 场景 | 行为 |
|------|------|
| 粘贴后点击“AI 解析” | 按钮进入 loading，禁用重复提交，可取消请求 |
| 空输入 + 点击解析 | 前端直接提示“请输入配置信息”，不发请求 |
| 输入超过 8000 字符 | 前端直接拦截，提示精简内容后重试 |
| 解析成功，单条结果 | 展示表单式预览，字段可编辑 |
| 解析成功，多条结果 | 展示 Accordion / Tab；支持逐条编辑、删除、勾选保存 |
| 解析结果含 `missing_fields` | 高亮缺失字段，提醒用户补充 |
| 解析结果为低置信度 | 以警示样式展示，不建议直接保存 |
| 用户切换 transport | 清空互斥字段（stdio 切 HTTP 清 command/args；反之清 url/headers） |
| 用户修改关键字段后 | 保留 hints，但提示“解析说明可能已不完全适用” |
| 用户点击“重新解析” | 返回 IDLE，保留原始输入 |
| 解析失败 | 显示错误信息，保留原始输入，允许重试 |
| 用户点击“确认并保存” | 可按勾选项逐条或批量保存；必要时先调用 `POST /validate` |
| 保存成功 | 弹窗关闭，MCP 列表刷新 |
| 部分保存成功 | 展示成功/失败明细，保留失败项编辑状态 |
| 保存失败 | 显示错误信息，保留当前预览与编辑状态 |
| 用户关闭弹窗时仍在解析 | 中断请求，不保留悬挂中的网络状态 |

---

## 4. 安全设计

### 4.1 密钥与敏感信息处理

| 层级 | 策略 |
|------|------|
| **输入层** | 限制输入长度为 8000 字符；过滤非法控制字符；不允许空输入 |
| **LLM Prompt 层** | 明确要求：任何 token/password/api key/secret/JWT/Bearer token/私钥片段都必须替换为 `${ENV_NAME}` 占位符 |
| **规则 / LLM 输出后处理** | 对高风险字段做二次脱敏：`Authorization`、`X-API-Key`、含 `token` / `secret` / `password` / `key` 的 env key 等，若值非占位符则强制替换 |
| **后端校验层** | 仅允许白名单字段；高风险字段必须通过占位符规则校验；最终结果仍需过 `ServerConfig` 兼容校验 |
| **日志层** | 不记录 `raw_text` 原文；仅记录长度、哈希、解析结果数量、风险标记、trace id |
| **前端展示层** | Toast、错误提示、调试输出中不得回显用户原始粘贴内容 |

### 4.2 LLM 供应链安全边界

- Smart Paste 允许向已配置的 LLM provider 发送用户粘贴文本，因此必须满足以下前提条件：
  - provider / proxy / gateway 不将请求用于训练
  - 请求内容不进行长期明文持久化
  - 调试日志中不得记录 `raw_text`
  - 若存在多级代理，必须确认每一级的留存与脱敏策略
- 若上述条件无法满足，则 **默认禁用 Smart Paste 功能**

### 4.3 输入校验与防滥用

- 前端 + 后端双重校验：
  - 空输入拒绝
  - 超长输入拒绝
  - 控制字符过滤
- `POST /api/mcp/parse` 需具备：
  - 身份校验
  - 用户级限流
  - 请求体大小限制
  - trace id / audit id
- Prompt injection 处理原则：
  - 使用清晰的 system / user input 分隔
  - 不信任模型输出本身
  - 最终安全边界不依赖 Prompt，而依赖 schema 校验、字段白名单和后处理脱敏

### 4.4 敏感值检测兜底

作为 Prompt 与字段级规则之外的兜底措施，后端应额外检测以下模式：

- Bearer token
- JWT
- 常见 `sk-` 风格 key
- API key 随机串
- PEM 私钥头部片段

> 正则检测仅作为最后一道兜底，不能替代字段级策略和结构化校验。

---

## 5. 错误处理矩阵

| 场景 | HTTP Status | 响应语义 |
|------|-------------|----------|
| `raw_text` 为空 | 400 | `{"ok":false,"error":"请输入配置信息"}` |
| `raw_text` 超长（>8000） | 400 | `{"ok":false,"error":"输入文本过长，请精简后重试"}` |
| 含非法控制字符 | 400 | `{"ok":false,"error":"输入包含非法字符，请清理后重试"}` |
| 未登录或无权限调用 | 401 / 403 | `{"ok":false,"error":"无权使用该功能"}` |
| 触发限流 | 429 | `{"ok":false,"error":"请求过于频繁，请稍后再试"}` |
| LLM 服务不可用 | 503 | `{"ok":false,"error":"AI 服务暂时不可用，请使用手动配置"}` |
| LLM 调用超时 | 504 | `{"ok":false,"error":"解析超时，请重试或使用手动配置"}` |
| LLM 返回非结构化结果且修复失败 | 502 | `{"ok":false,"error":"解析失败，请重试"}` |
| 请求合法，但未解析出可用 MCP 配置 | 200 | `{"ok":false,"error":"无法从输入中解析出有效的 MCP 配置"}` |
| 多条候选中部分失败 | 200 | 返回合法结果，并在 `warnings` 中提示部分候选已丢弃 |
| 保存阶段命名冲突 | 409 | `{"ok":false,"error":"配置名称已存在，请修改后重试"}` |
| 未预期内部错误 | 500 | `{"ok":false,"error":"内部错误，请稍后重试"}` |

**错误处理原则：**
- `4xx`：输入非法、权限不足或调用受限
- `5xx`：依赖服务异常或内部错误
- `200 + ok=false`：请求格式合法，但未得到可用候选配置
- 面向用户的错误文案不暴露 provider、堆栈、内部实现细节或原始输入内容

---

## 6. 对现有代码的影响

### 6.1 后端：对存储与连接链路零破坏，但引入新的解析编排能力

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `backend/app/api/mcp.py` | 新增路由 | 添加 `POST /parse` 端点 |
| `backend/app/mcp/smart_paste_models.py` | 新增文件 | `SmartPasteRequest` / `SmartPasteResponse` / `ParsedServerConfig` |
| `backend/app/mcp/smart_paste_service.py` | 新增文件 | 输入预检、解析编排、错误映射 |
| `backend/app/mcp/smart_paste_sanitizer.py` | 新增文件 | 敏感值替换、字段白名单校验、风险检测 |
| `backend/app/mcp/models.py` | 不改或极小改动 | 继续复用 `ServerConfig` 做最终兼容校验 |

### 6.2 前端：增量新增

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `frontend/src/pages/settings/types.ts` | 新增类型 | `ParsedMcpConfig`、`SmartPasteResponse` 等 |
| `frontend/src/pages/settings/components/modals/McpSmartPasteModal.tsx` | 新增文件 | Smart Paste 弹窗组件 |
| `frontend/src/pages/settings/components/McpSettingsTab.tsx` | 修改 | Add 菜单新增入口 |
| `frontend/src/pages/Settings.tsx` | 修改 | 增加 Smart Paste 状态与请求回调 |

### 6.3 不变的部分

- Marketplace 模板系统：不受影响
- Manual JSON / Raw Config：不受影响
- Manager 连接管理：不受影响
- 最终保存仍走现有 MCP 配置写入链路

### 6.4 新增复杂度说明

虽然该方案对现有 MCP 配置持久化和连接流程是零破坏性的，但会新增以下运行时复杂度：

- LLM 外部依赖与超时处理
- 安全脱敏与审计要求
- 解析接口的配额、限流与可观测性
- 多结果候选项的前端状态管理

---

## 7. 测试计划

### 7.1 后端单元测试

| 测试用例 | 输入 | 预期 |
|---------|------|------|
| 解析 Claude Desktop 格式 JSON | `{"mcpServers":{"fs":{"command":"npx","args":["-y","@anthropic/mcp-server-filesystem"]}}}` | 1 result, `transport=stdio`, `name=fs`, `parse_mode=rule` |
| 解析命令行片段 | `npx -y @company/mcp-server --port 3000` | 1 result, `transport=stdio`, `args` 顺序正确 |
| 解析 HTTP 端点描述 | `我的 MCP 地址是 https://mcp.company.com/stream，token 是 sk-abc123` | 1 result, `transport=streamable_http`，敏感值已替换，无明文泄露 |
| 空输入 | `""` | HTTP 400 |
| 超长输入 | 8000+ 字符 | HTTP 400 |
| 非法控制字符 | 含非法控制字符文本 | HTTP 400 |
| 无效输入 | `"hello world"` | `200 + ok=false` |
| 多条 MCP 配置 | 含多个 `mcpServers` 的 JSON | 返回多条结果，顺序稳定 |
| LLM 返回非结构化内容 | Mock LLM 返回纯文本 | 进行一次修复重试，仍失败则 `ok=false` |
| 后处理校验失败 | LLM 返回缺少 `command` 的 stdio 配置 | 非法条目被丢弃 |
| 部分结果合法、部分不合法 | 混合输出 | 保留合法结果，并在 `warnings` 中说明 |
| Bearer token 明文输入 | 含 `Authorization: Bearer xxx` | 输出不得含原 token |
| JWT 输入 | JWT 字符串 | 输出不得原样保留 |
| PEM 私钥片段输入 | 私钥片段 | 必须拒绝或清洗，不得原样输出 |

### 7.2 契约测试

| 测试用例 | 说明 |
|---------|------|
| `SmartPasteResponse` schema snapshot | 保证返回结构稳定 |
| `parse_mode` 枚举兼容性 | 前后端约定一致 |
| `warnings` / `missing_fields` 字段兼容性 | 前端可稳定消费新增字段 |
| `results[]` 顺序一致性 | 多结果返回顺序与输入顺序一致 |

### 7.3 前端单元测试

| 测试用例 | 说明 |
|---------|------|
| 空输入 + 点击解析 | 前端拦截，不发请求 |
| 超长输入 + 点击解析 | 前端拦截并提示 |
| 解析中按钮状态 | 按钮 disabled，显示 loading |
| 取消解析 | 请求被 abort，状态恢复 |
| 解析成功后展示预览 | 字段正确回填，`hints` / `warnings` 展示 |
| 低置信度结果展示 | 高亮风险和 `missing_fields` |
| 切换 transport 清空互斥字段 | stdio → HTTP 清空 command/args |
| 多结果勾选保存 | 仅提交勾选项 |
| 删除某条候选配置 | 该条从 UI 中移除 |
| 保存成功后关闭弹窗 | `onClose` 被调用 |
| 保存失败后保留编辑态 | 当前表单值不丢失 |
| 同名冲突提示 | 正确展示冲突错误 |

### 7.4 E2E 测试

| 测试用例 | 说明 |
|---------|------|
| Smart Paste 解析 stdio 配置并保存 | 粘贴命令行 → 解析 → 确认保存 → 列表出现 |
| Smart Paste 解析 streamable_http 配置并保存 | 粘贴 URL → 解析 → 确认保存 → 列表出现 |
| Smart Paste 多结果部分保存 | 粘贴多配置 → 删除/取消部分项 → 保存剩余项 |
| 解析失败后重试成功 | 首次失败 → 保留输入 → 再次解析成功 |
| 保存失败后修改重试 | 命名冲突 → 修改 name → 重试成功 |

### 7.5 稳定性与验收指标

- 同一输入的多次解析结果应保持可接受的一致性
- 敏感值明文泄露测试必须为 0
- 核心 happy path 成功率应达到可接受水平
- 解析接口需监控：
  - 成功率
  - `p95` 延迟
  - 超时率
  - 人工修改率

---

## 8. 实现顺序

```text
Step 1: 定义 Smart Paste 强约束模型与 API 契约
Step 2: 实现后端输入预检与错误映射
Step 3: 实现规则解析快路径（JSON / 命令行 / URL）
Step 4: 实现安全清洗、字段白名单校验与 ServerConfig 兼容校验
Step 5: 接入真实 LLM 调用（schema-first，失败时最多重试 1 次）
Step 6: 前端 SmartPasteModal 组件 + Settings 集成
Step 7: 接入多结果预览、逐条保存、取消解析、冲突处理
Step 8: 后端单元测试 + 契约测试
Step 9: 前端单元测试 + E2E 测试
Step 10: 手动冒烟测试 + 指标观测验证
```

**说明：**
- 安全清洗与契约设计必须前置，避免先接入 LLM 再返工
- 规则解析快路径应作为本期能力，而不是未来扩展项
- 前端在接真实 LLM 前可先基于 mock response 联调

---

## 9. 风险与缓解

| 风险 | 等级 | 触发条件 | 缓解措施 |
|------|------|----------|---------|
| LLM 解析结果不稳定 | High | 同一输入多次解析结果漂移明显 | `temperature=0.0`、schema 校验、必要时重试 1 次、规则快路径优先 |
| 密钥泄露到 provider / proxy / 日志链路 | Critical | provider 或代理存在明文留存 | 上线前确认 retention policy；不满足要求则禁用 Smart Paste |
| 明文敏感值未被替换 | Critical | Prompt / 后处理 / 字段校验任一层失效 | Prompt 约束 + 字段级强制占位符 + 正则兜底 + 测试覆盖 |
| 解析接口被滥用导致成本失控 | High | 高频调用或恶意刷接口 | 用户级限流、请求大小限制、配额与审计 |
| LLM 调用延迟过高 | High | `p95` 延迟超出可接受范围 | 规则快路径、模型降级、超时控制、失败快速返回 |
| 用户过度依赖 AI 解析 | Medium | 用户把候选项当最终可信配置 | 默认 `enabled=false`，保留 Manual / Raw 路径，并在 UI 中强调需人工确认 |
| 多结果保存语义不清 | Medium | 批量保存出现部分失败 | 前端支持逐条保存、部分成功态、失败项保留编辑状态 |
| Prompt injection 干扰模型输出 | Medium | 恶意输入试图改写系统规则 | system/user 分隔、schema 校验、字段白名单、不信任模型输出 |

**上线门槛：**
- provider / proxy 数据留存策略已确认
- 敏感值泄露测试为 0
- 规则解析与 LLM 解析都能通过核心 happy path
- 解析失败时用户仍可顺畅回退到手动配置

---

## 10. 未来扩展（不在本期范围内）

- **连接测试按钮**：解析预览后直接测试 MCP 连接，形成“粘贴 → 解析 → 验证 → 保存”闭环
- **解析历史**：记录用户最近使用的解析结果摘要，便于复用
- **批量导入**：一次粘贴多个来源的混合格式文本
- **多语言 hints/warnings**：根据前端语言环境本地化 AI 说明信息
- **高级规则识别器**：支持更复杂的 README、Shell 脚本和文档块提取

> 说明：规则解析快路径是本期能力，不属于未来扩展。

---

## 11. 非功能要求

### 11.1 可用性

- Smart Paste 不是唯一入口；AI 不可用时，用户仍可使用 Manual JSON / Raw Config 完成配置
- 解析失败不应阻断用户继续完成 MCP 配置

### 11.2 性能

- 解析接口应控制交互等待时间，避免长时间阻塞弹窗操作
- 优先通过规则快路径缩短大部分请求的解析时间
- 应持续监控 `p95` 延迟、超时率和失败率

### 11.3 安全

- 敏感值明文泄露为 0
- 请求原文不写入日志
- provider / proxy 不得用于训练或长期明文存储

### 11.4 可观测性

- 记录指标：请求量、成功率、失败率、超时率、`parse_mode` 分布、人工修改率
- 所有请求带 trace id / audit id
- 审计中仅记录摘要，不记录原始粘贴内容

### 11.5 可扩展性

- 支持未来新增更多 transport 类型
- 支持未来引入连接测试、批量导入等扩展能力

---

## 12. 开放问题 / 待决策项

1. `POST /api/mcp/parse` 返回结果后，前端是否必须先调用 `POST /validate` 再允许保存？
2. 多条候选项默认是逐条保存，还是允许批量保存？
3. 若保存时 `name` 冲突，策略是报错、自动重命名，还是让用户手动修改？
4. 低置信度结果是否允许直接保存，还是必须先补全关键字段？
5. 若 provider / proxy 无法提供明确的数据留存承诺，是否默认关闭 Smart Paste？
6. `hints` / `warnings` 是否需要随前端 UI 语言做国际化？