# Observability & Transparency Plan (Phase 6.3)

## Scope

This document expands ROADMAP item **6.3 Observability & Transparency (执行透明化)** into an implementation-ready plan.

### Goals
- Provide a real-time tool-call panel for MCP and built-in tools.
- Provide a visual execution trace for main-task and sub-task progress.
- Improve trust, debuggability, and operator control for autonomous runs.

### Non-Goals
- Redesigning the full chat UI layout.
- Building a long-term analytics warehouse in this phase.
- Exposing sensitive secrets or raw credentials in any UI payload.

## Architecture Impact Assessment (基于当前架构的改动与侵入性评估)

This section evaluates implementation impact against the current Yue codebase and is intended to answer three practical questions: whether this is a major rewrite, how invasive it is, and how much risk it introduces to existing features.

### Executive Conclusion
- This plan is **not** a full architectural rewrite, but it is a **cross-cutting enhancement**.
- Expected scope is **medium-to-large engineering effort** across backend execution path, stream contract, frontend consumption/rendering, and persistence.
- Invasiveness is **medium**: it touches core runtime paths, but can be controlled with staged rollout and feature flags.
- Impact on existing functionality is **controllable** if we preserve the text-stream happy path as the primary compatibility contract.

### Why It Is Not a “Very Large Rewrite”
- The proposal extends existing runtime and stream mechanisms instead of replacing the current chat architecture.
- Current tool integration already goes through the registry/wrapper path (MCP + built-in unified), which aligns with the planned interception model.
- The proposal explicitly excludes full chat UI redesign and long-term analytics warehousing in this phase.

### Current Architecture Baseline and Fit

#### 1) Backend runtime path (high fit)
- Current stream orchestration is centralized in `backend/app/api/chat.py` and already emits structured SSE chunks (`chat_id`, `meta`, token/content/metrics/error payloads).
- Current tool execution already has a unified wrapper boundary in `backend/app/mcp/registry.py` (`_to_pydantic_ai_tool` wrapper).
- MCP execution has a concrete boundary in `backend/app/mcp/base.py` (`McpTool.execute`), suitable for lifecycle timing/status instrumentation.
- Result: planned event interception points match real code boundaries; no forced architecture switch is required.

#### 2) Frontend stream consumption (moderate fit)
- Current frontend stream parser in `frontend/src/hooks/useChatState.ts` processes line-based SSE JSON with field-branch logic (`chat_id/meta/content/thought/metrics/citations/error`).
- It can be extended to support new `kind=tool_event|trace_event` payloads with backward-compatible parsing.
- Risk exists if event ordering/frequency changes increase UI update pressure, but the parser already has buffering/throttled flush behavior.

#### 3) Persistence baseline (low fit, requires net-new module)
- Current SQLite service layer (`backend/app/services/chat_service.py`) persists only `sessions/messages` and message-level metrics.
- No existing `run_traces` / `tool_calls` / `tool_call_chunks` tables are present.
- This part is additive rather than breaking, but introduces migration and write-amplification concerns.

### Invasiveness by Layer

| Layer | Invasiveness | Reason |
| :--- | :--- | :--- |
| Chat stream orchestration (`chat.py`) | Medium | Core path changes for event emit/order/error mapping; must preserve current text stream behavior. |
| Tool wrapper boundary (`registry.py`) | Medium | Adds before/after instrumentation for all tools; broad blast radius but single choke-point is beneficial. |
| MCP execute boundary (`base.py`) | Low-Medium | Focused latency/status capture at one function boundary. |
| Frontend stream/store/render | Medium | Requires new event-store branch and new panels, but can keep current message rendering path intact. |
| Persistence and replay | Medium | New schema/service endpoints; additive yet operationally sensitive (volume/indexing). |
| Existing chat UX compatibility | Low (if staged) | Unknown event kinds can be ignored; text stream remains primary contract. |

### Existing Feature Impact Assessment

#### 1) Chat response continuity
- Primary risk: regressions in SSE sequencing or exception handling inside `chat_stream`.
- Mitigation: preserve current output sequence contract for `chat_id/meta/content/error`, append observability events without blocking text generation.

#### 2) Tool execution reliability
- Primary risk: wrapper instrumentation introducing latency/error side effects.
- Mitigation: make instrumentation fail-open and non-blocking; tool call result path remains source of truth.

#### 3) Frontend rendering stability
- Primary risk: high-frequency event updates causing extra renders or duplicated items on reconnect.
- Mitigation: event dedup by stable `event_id`, idempotent upsert, and buffered UI updates.

#### 4) Data/store pressure
- Primary risk: optional chunk persistence (`tool_call_chunks`) significantly increases writes under long outputs.
- Mitigation: staged enablement, payload truncation, configurable sampling/limits, and indexed queries by `run_id`.

### Risk Grading

| Dimension | Risk Level | Notes |
| :--- | :--- | :--- |
| Architecture mismatch risk | Low | Plan aligns with existing registry/wrapper design. |
| Runtime regression risk | Medium | Core stream path is touched; requires strict compatibility tests. |
| Frontend regression risk | Medium | SSE contract extension + panel rendering complexity. |
| Data/ops risk | Medium | New tables and replay semantics on SQLite must be bounded. |
| Rollback complexity | Low-Medium | Feature-flag strategy makes rollback practical if designed as emit-first. |

### Implementation Decision Guidance
- Recommendation: proceed, but enforce phased rollout (`emit-only -> persistence -> UI internal -> gradual release`).
- Must-have guardrail: “core chat text stream unaffected” as a hard compatibility principle.
- Must-have quality gate: add/adjust backend and frontend tests for ordering, dedup, reconnect replay, error-path parity, and limit-trigger handling.
- Must-have safety gate: redaction before SSE, DB write, and any external export sink.

---

## Product Requirements

### 1) Detailed Tool Call Panel
- Show each tool invocation in execution order.
- Show status lifecycle: `queued` → `running` → `success|error|cancelled`.
- Show input summary and output summary in real time.
- Show latency metrics: start time, end time, duration.
- Support expandable details for full payload inspection.
- Support filtering by status, tool name, and time range.

### 2) Visual Agent Trace
- Show top-level task and sub-task hierarchy.
- Show state transitions per node: `pending`, `in_progress`, `completed`, `failed`.
- Show timestamps and elapsed duration per node.
- Show relation between a trace node and linked tool calls.
- Support compact timeline mode and graph mode.

### 3) Safety and Transparency Rules
- Redact secrets in tool input/output before persistence and rendering.
- Truncate oversized payloads with explicit expand controls.
- Mark uncertain or partial outputs in trace and panel consistently.

---

## Architecture Solution

## Event Model

Adopt an event-first model where runtime components emit normalized events consumed by both persistence and streaming layers.

### Core Event Types
- `run.started`
- `trace.node.created`
- `trace.node.updated`
- `tool.call.started`
- `tool.call.stream_delta`
- `tool.call.finished`
- `run.finished`

### Shared Event Envelope
- `event_id`
- `run_id`
- `session_id`
- `timestamp`
- `event_type`
- `sequence`
- `payload`

---

## Backend Plan

### 1) Event Emission
- Add a centralized runtime emitter in the agent execution path.
- Emit trace events whenever planner/executor creates or updates sub-tasks.
- Emit tool events at call start, delta stream, and finish.

### 2) Persistence
- Add tables:
  - `run_traces` for trace nodes and status transitions.
  - `tool_calls` for normalized invocation records.
  - `tool_call_chunks` for optional streamed output chunks.
- Indexes:
  - `tool_calls(run_id, started_at)`
  - `run_traces(run_id, parent_node_id, sequence)`

### 3) Streaming API
- Extend existing streaming channel to include trace and tool events.
- Ensure ordering via sequence and monotonic timestamp fallback.
- Provide replay endpoint for reconnect and historical inspection.

### 4) Redaction and Limits
- Add payload sanitizer middleware before write and stream.
- Mask known secret patterns and configurable key names.
- Enforce payload byte limits with truncation metadata fields.

---

## Frontend Plan

### 1) Tool Panel UI
- Add a right-side or bottom dock panel with list + detail split view.
- Render call cards with status badge, tool name, duration, and timestamp.
- Add expandable JSON viewer for sanitized input/output.
- Add filters and search for fast triage.

### 2) Trace Visualization UI
- Build a trace tree with parent-child indentation and progress states.
- Add timeline mode for chronological debugging.
- Add direct jump from trace node to linked tool calls.

### 3) State Management
- Maintain in-memory event store keyed by `run_id`.
- Apply incoming stream events incrementally with idempotent upserts.
- Support replay hydration from backend on refresh/reconnect.

---

## API Contracts

### Stream Event Contract
- Existing stream adds `kind: "trace_event" | "tool_event"` records.
- Each event includes stable IDs for deduplication.

### Query Endpoints
- `GET /api/runs/{run_id}/trace`
- `GET /api/runs/{run_id}/tool-calls`
- `GET /api/runs/{run_id}/tool-calls/{call_id}`

### Response Expectations
- All timestamps in ISO 8601.
- All durations in milliseconds.
- Redaction flags on any truncated or masked fields.

---

## Pydantic AI Integration Decisions

This section evaluates the external proposal against the current Yue architecture and defines what should be adopted in Phase 6.3.

### Current Architecture Constraint
- Yue currently injects tools via `tools=...` from the internal registry (MCP tools + built-in tools unified as Pydantic AI `Tool`), not via `mcp_servers=[...]` directly.
- Therefore, all observability and guardrails should be designed around the existing registry/wrapper path first.

### Proposal Evaluation Matrix

| Proposal Item | Fit for Yue | Decision | Notes |
| :--- | :--- | :--- | :--- |
| `UsageLimits(tool_calls_limit=...)` | High | Adopt | Native in current Pydantic AI version; directly supports tool-call hard limits. |
| `UsageLimitExceeded` graceful handling | High | Adopt | Map to user-friendly SSE/system event and partial-result fallback. |
| Multi-dimensional limits (`request_limit`, `total_tokens_limit`) | High | Adopt | Add tier-based policies (free/pro) and per-run overrides. |
| Logfire tracing | Medium-High | Adopt (optional) | Dependency already exists in backend; enable as optional external observability backend. |
| MLflow autolog (`mlflow.pydantic_ai.autolog`) | Medium | Defer | Useful but currently not installed; postpone until observability stack decision is finalized. |
| `process_tool_call` hook on `MCPServerStdio` | Medium | Partial adopt | Valid API, but only applies when using direct `mcp_servers`; for current architecture, implement equivalent interception in tool wrapper layer. |
| Custom structured logs in tool code | High | Adopt | Immediate value; use unified event schema and redaction policy. |

### Concrete Adoption in Yue

### 1) Hard limits (anti-runaway)
- Apply `usage_limits` per run in agent execution.
- Baseline policy:
  - `tool_calls_limit`: required, strict cap.
  - `request_limit`: optional, prevent infinite reasoning loops.
  - `total_tokens_limit`: optional, constrain total cost.
- On `UsageLimitExceeded`:
  - Emit terminal event (`run.limited`) with reason and current counters.
  - Return clear user-facing message: partial completion + next-step suggestion.

### 2) Tool-call observability (what was called)
- Capture for each call:
  - tool name, call id, normalized args (sanitized), start/end timestamps, duration, status, error summary.
- For Yue’s current wrapper-based tools:
  - Instrument at unified tool wrapper boundary and MCP execute boundary.
  - Emit `tool.call.started` and `tool.call.finished` events to stream and storage.

### 3) External tracing strategy
- Phase 6.3 default: internal event pipeline is source of truth.
- Optional export:
  - Logfire as first external sink.
  - MLflow as future extension if team adopts MLflow stack.

### 4) Security requirements for logs/events
- Never store raw secrets in tool args/results.
- Apply key-based masking and pattern-based masking before:
  - SSE push,
  - DB persistence,
  - external tracing export.

### Implementation Priority Update
- Move `usage_limits` support into Milestone A scope (must-have, not optional).
- Keep MLflow integration out of critical path; treat as Milestone C/D optional enhancer.

---

## Detailed Execution Blueprint

### A) File-Level Implementation Map

| Area | Primary File | Planned Changes | Output |
| :--- | :--- | :--- | :--- |
| Stream orchestration | `backend/app/api/chat.py` | Add event emission points, add `usage_limits` passing, catch `UsageLimitExceeded`, emit SSE observability events | Real-time `tool_event` and `trace_event` in existing stream |
| Tool wrapper interception | `backend/app/mcp/registry.py` | Instrument wrapper boundary before/after tool execute, normalize args/result metadata, attach call id | Unified tool lifecycle events across MCP + built-in tools |
| MCP execution boundary | `backend/app/mcp/base.py` | Record MCP call start/end/error at `McpTool.execute` boundary | Accurate latency and status for MCP calls |
| Event persistence | `backend/app/services/*` (new service module) | Add event writer interface and SQLite writes for `tool_calls` / `run_traces` | Replay and historical inspection |
| Frontend stream consumer | `frontend/src/*` (chat stream handler) | Parse `kind=tool_event|trace_event`, incremental store update, dedup by event id | Stable real-time rendering |
| Observability UI | `frontend/src/*` (new panel components) | Tool call panel + trace tree/timeline + filter/search | User-visible transparency layer |

### B) Event Contract Granularity

### `tool.call.started`
- Required fields:
  - `event_id`, `run_id`, `session_id`, `sequence`, `timestamp`
  - `call_id`, `tool_name`, `tool_type` (`mcp` or `builtin`)
  - `input_preview`, `input_redacted`, `trace_node_id` (optional)

### `tool.call.finished`
- Required fields:
  - `event_id`, `run_id`, `sequence`, `timestamp`
  - `call_id`, `status` (`success|error|cancelled`)
  - `duration_ms`, `output_preview`, `output_redacted`
  - `error_code`, `error_message` (only when failed)

### `run.limited`
- Required fields:
  - `event_id`, `run_id`, `sequence`, `timestamp`
  - `reason` (`tool_calls_limit|request_limit|total_tokens_limit`)
  - `usage_snapshot` (current counters)
  - `user_message` (friendly fallback text)

### C) Usage Limits Policy Matrix

| Tier | tool_calls_limit | request_limit | total_tokens_limit | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| Default | 8 | 12 | 120000 | Balanced baseline |
| Strict | 4 | 8 | 60000 | Cost-sensitive mode |
| Premium | 16 | 20 | 240000 | High-complexity workflows |

- Policy source:
  - Agent-level default from config.
  - Request-level override (bounded by server maximum).
- Guardrail:
  - Any client override above server maximum is clamped and logged.

### D) End-to-End Flow (Single Run)

1. `run.started` emitted when stream starts.
2. Agent invokes a tool:
   - Emit `tool.call.started`.
   - Execute tool.
   - Emit `tool.call.finished`.
3. If limit reached:
   - Catch `UsageLimitExceeded`.
   - Emit `run.limited`.
   - Continue returning partial textual answer with explicit reason.
4. On completion:
   - Emit `run.finished`.
   - Persist final usage summary.

### E) Frontend Rendering Rules

- Tool panel item key: `call_id`.
- Status mapping:
  - `tool.call.started` → `running`
  - `tool.call.finished:success` → `success`
  - `tool.call.finished:error` → `error`
- Duration:
  - Use backend `duration_ms` if provided.
  - Fallback to `(finished_at - started_at)` client-side.
- Redaction display:
  - If `*_redacted=true`, show masked badge and expandable warning.

### F) Test Gates (Detailed)

### Backend Unit
- Emits `tool.call.started` before execution and `tool.call.finished` after execution.
- Failed tool execution still emits `tool.call.finished` with `status=error`.
- `UsageLimitExceeded` is converted to `run.limited` event and user-safe message.
- Redactor masks keys (`api_key`, `token`, `authorization`) and common secret patterns.

### Backend Integration
- SSE ordering is monotonic by `sequence`.
- Reconnect replay returns identical event sequence for same run.
- Mixed MCP + built-in tool run produces consistent schema.

### Frontend
- Tool panel updates state incrementally without full rerender.
- Event dedup prevents duplicate cards after reconnect.
- Filtering by tool/status/time works under 500+ events.

### G) Rollout and Rollback

### Rollout
- Stage 1: emit-only (stream), no persistence.
- Stage 2: enable persistence behind feature flag.
- Stage 3: enable UI panel for internal users.
- Stage 4: gradual rollout by tenant/user segment.

### Rollback
- Disable observability stream payload via feature flag.
- Keep core chat text stream unaffected.
- Preserve backward compatibility by ignoring unknown SSE `kind` on frontend.

---

## Expected User-Facing Outcomes (预期效果)

### 1) 用户可见体验
- 从“只看到最终回答”升级为“可看到执行过程 + 每一步状态 + 耗时”。
- 在回答生成过程中，用户可实时看到工具调用卡片从 `running` 变为 `success/error`。
- 用户可点击展开工具输入/输出摘要，快速判断结论依据是否充分。
- 当触发调用上限或预算限制时，界面明确显示限制原因，而不是无提示中断。

### 2) 工程与运营效果
- 工程排障效率提升：可直接定位慢调用、失败调用和错误参数。
- 成本与稳定性可控：通过 `tool_calls_limit`、`request_limit`、`total_tokens_limit` 防止失控。
- 审计可追溯：单次 run 的调用链可回放，支持复盘与合规留档。

### 3) 验收时可观察到的“成功信号”
- 同一轮会话中，至少可看到 1 条 `tool.call.started` 和对应 `tool.call.finished`。
- 前端工具面板中的耗时与后端 `duration_ms` 一致或在可接受误差内。
- 触发上限后出现 `run.limited`，同时主回答给出“部分完成 + 下一步建议”。

---

## User-Visible Mock Examples (结合现有 Built-in Tools)

### Mock 1: 文档检索与精读（`docs_search` + `docs_read`）

**User Query**
- “6.3 执行透明化具体要做什么？给我总结并附证据。”

**Tool Panel Preview**
- `10:21:14.102` `builtin:docs_search` `running`
  - input: `{"query":"6.3 Observability & Transparency","root_dir":"docs","mode":"markdown","limit":5}`
- `10:21:14.391` `builtin:docs_search` `success` `289ms`
  - output_preview: `ROADMAP.md 命中 2 处，关键行 274-276`
- `10:21:14.412` `builtin:docs_read` `running`
  - input: `{"path":"ROADMAP.md","root_dir":"docs","target_line":274,"max_lines":30}`
- `10:21:14.676` `builtin:docs_read` `success` `264ms`
  - output_preview: `6.3 包含 tool call panel 与 thought process trace`

**Trace Preview**
- `Task: 回答 6.3 需求`
  - `Subtask A: 定位目标章节` → completed
  - `Subtask B: 读取上下文证据` → completed
  - `Subtask C: 生成结构化总结` → completed

**Assistant Final Answer Preview**
- “6.3 的核心是两点：实时工具调用面板 + 任务思维链可视化。依据来自 ROADMAP.md 第 274-276 行。”

### Mock 2: Excel 数据洞察（`excel_profile` + `excel_query`）

**User Query**
- “分析 `docs/World Indicators.xlsx`，给我人口最高的前 5 个国家。”

**Tool Panel Preview**
- `15:07:33.055` `builtin:excel_profile` `running`
  - input: `{"path":"docs/World Indicators.xlsx"}`
- `15:07:33.522` `builtin:excel_profile` `success` `467ms`
  - output_preview: `sheet=Data, headers_detected=true, approx_rows=266`
- `15:07:33.549` `builtin:excel_query` `running`
  - input: `{"path":"docs/World Indicators.xlsx","sheet_name":"Data","query":"SELECT CountryName, Population FROM excel_data WHERE Population IS NOT NULL ORDER BY Population DESC LIMIT 5"}`
- `15:07:34.138` `builtin:excel_query` `success` `589ms`
  - output_preview: `Top 5 rows returned`

**Trace Preview**
- `Task: 计算人口 Top5`
  - `Subtask A: 识别表结构` → completed
  - `Subtask B: 执行排序查询` → completed
  - `Subtask C: 转换为用户可读结论` → completed

**Assistant Final Answer Preview**
- “已基于 `Data` 工作表完成查询，人口最高前 5 名为：……（并附查询语句与数据来源说明）。”

---

## Screenshot Copy Templates (前端截图文案模板)

### Template A: Tool Call Panel (Normal Flow)

**Panel Title**
- `Execution Transparency`

**Panel Subtitle**
- `Live tool calls, status, latency, and evidence`

**Card Header Format**
- `{timestamp} · {tool_id} · {status_badge} · {duration_ms}`

**Status Badge Copy**
- `running` → `Running`
- `success` → `Completed`
- `error` → `Failed`
- `cancelled` → `Cancelled`

**Expandable Sections**
- `Input (sanitized)`
- `Output (preview)`
- `Metadata`

**Footer Copy**
- `Showing {n} tool calls in this run`

### Template B: Trace Timeline (Normal + Warning + Error)

**Timeline Title**
- `Agent Trace`

**Node Label Format**
- `{node_name} · {state} · {elapsed_ms}`

**State Copy**
- `pending` → `Pending`
- `in_progress` → `In Progress`
- `completed` → `Completed`
- `failed` → `Failed`

**Warning Banner Copy (limit reached)**
- `Run limited by policy: tool call budget reached.`
- `Partial answer returned. You can continue with a narrower request.`

**Error Banner Copy (tool failure)**
- `A tool call failed, but the assistant continued with available evidence.`
- `Open the failed call card to view error details and retry hints.`

### Ready-to-Use UI Text for Existing Built-in Tools

**Docs Flow (`builtin:docs_search`, `builtin:docs_read`)**
- Card title: `Search roadmap evidence`
- Running text: `Searching docs for “6.3 Observability & Transparency”…`
- Success text: `Found 2 matches in ROADMAP.md`
- Read text: `Reading focused lines around L274`
- Evidence chip: `Evidence: ROADMAP.md#L274-L276`

**Excel Flow (`builtin:excel_profile`, `builtin:excel_query`)**
- Card title: `Analyze workbook structure`
- Running text: `Profiling sheet layout and headers…`
- Success text: `Sheet “Data” detected, ~266 rows`
- Query text: `Running SQL on excel_data`
- Result chip: `Result: Top 5 population rows returned`

### Tooltip and Empty-State Copy

**Tooltip Copy**
- `Duration includes tool execution and serialization time.`
- `Input/Output is masked when sensitive patterns are detected.`
- `Click a card to inspect full sanitized payload.`

**Empty State Copy**
- `No tool calls yet.`
- `Tool activity will appear here once the assistant starts execution.`

### Chinese-Only Variant (中文界面文案)

**Panel Title**
- `执行透明化`

**Panel Subtitle**
- `实时展示工具调用、状态、耗时与证据`

**Status Badge Copy**
- `running` → `执行中`
- `success` → `已完成`
- `error` → `失败`
- `cancelled` → `已取消`

**Warning Banner Copy (limit reached)**
- `本轮执行已触达策略上限：工具调用预算已用尽。`
- `系统已返回部分答案，建议缩小问题范围后继续。`

**Error Banner Copy (tool failure)**
- `某次工具调用失败，助手已基于现有证据继续回答。`
- `可展开失败卡片查看错误详情与重试建议。`

**Docs Flow (`builtin:docs_search`, `builtin:docs_read`)**
- 卡片标题：`检索路线图证据`
- 执行中文案：`正在检索“6.3 执行透明化”相关文档…`
- 成功文案：`已在 ROADMAP.md 命中 2 处`
- 证据标签：`证据：ROADMAP.md#L274-L276`

**Excel Flow (`builtin:excel_profile`, `builtin:excel_query`)**
- 卡片标题：`分析工作簿结构`
- 执行中文案：`正在识别表结构与表头…`
- 成功文案：`已识别工作表 “Data”，约 266 行`
- 结果标签：`结果：已返回人口前 5 行数据`

### Chinese Tone Pack Variants (中文语气包)

**Pack 1: 专业版（默认）**
- 面板标题：`执行透明化`
- 面板副标题：`实时展示工具调用、状态、耗时与证据`
- 进行中：`正在执行工具调用，请稍候…`
- 成功：`执行完成，已更新证据与结果。`
- 警告（上限）：`已触达策略上限，系统返回部分结果。`
- 错误：`工具调用失败，请查看详情并重试。`

**Pack 2: 简洁版（高密度信息）**
- 面板标题：`执行记录`
- 面板副标题：`调用 / 状态 / 耗时`
- 进行中：`执行中…`
- 成功：`完成`
- 警告（上限）：`达到上限，已部分返回`
- 错误：`调用失败`

**Pack 3: 产品友好版（新手友好）**
- 面板标题：`助手正在处理`
- 面板副标题：`你可以看到每一步是如何完成的`
- 进行中：`我正在查找和整理信息…`
- 成功：`这一步已完成，我继续下一步。`
- 警告（上限）：`本轮调用次数用完了，我先给你可用结果。`
- 错误：`有一步执行失败了，我会用已有信息继续回答。`

**Usage Guidance**
- 默认推荐 `专业版`，适合大多数 B2B 与开发者场景。
- 若界面空间紧张，优先使用 `简洁版`。
- 面向非技术用户或演示场景，优先使用 `产品友好版`。

**User Segment → Recommended Pack**

| User Segment | Primary Goal | Recommended Pack | Fallback Pack |
| :--- | :--- | :--- | :--- |
| Internal engineering team | Fast debugging and precise status reading | 专业版 | 简洁版 |
| SRE / operations | Rapid incident triage under pressure | 简洁版 | 专业版 |
| Product manager / business stakeholder | Understand progress without technical overload | 产品友好版 | 专业版 |
| Demo audience / new users | Build trust with easy-to-follow wording | 产品友好版 | 简洁版 |
| Power users (frequent tool workflows) | Balance readability and dense run details | 专业版 | 产品友好版 |

**Quick 3-Question Chooser**
- Q1: Is the primary audience technical (engineering/SRE)?
  - Yes → go to Q2
  - No → choose `产品友好版`
- Q2: Is screen space limited or do users prefer dense UI?
  - Yes → choose `简洁版`
  - No → go to Q3
- Q3: Is precise debugging and status interpretation a top priority?
  - Yes → choose `专业版`
  - No → choose `产品友好版`

---

## Delivery Phases

### Milestone A: Foundation
- Define event schema and backend emitter.
- Persist tool call records.
- Stream basic tool start/finish updates.
- Add `usage_limits` policy and `UsageLimitExceeded` handling.

### Milestone B: Trace
- Persist and stream trace node lifecycle.
- Build minimal trace tree UI with status updates.

### Milestone C: Advanced Visibility
- Add tool input/output expandable details.
- Add timeline mode and deep linking between trace and tools.
- Add filtering, replay, and reconnect robustness.

### Milestone D: Hardening
- Add full redaction policy and payload limits.
- Add performance optimization for long-running sessions.

---

## Acceptance Criteria

- Tool panel updates in near real-time during agent execution.
- Each tool call shows duration and terminal status reliably.
- Trace view reflects sub-task hierarchy and state transitions correctly.
- UI remains responsive for at least 500 tool events per run.
- No raw secrets appear in persisted events or rendered UI.

---

## Test Strategy

### Backend
- Unit tests for event emission and schema validation.
- Unit tests for sanitizer and truncation behavior.
- Integration tests for run replay and ordering guarantees.

### Frontend
- Component tests for tool panel rendering and filtering.
- Component tests for trace tree transitions.
- End-to-end test for live run with tool + trace updates.

### Regression
- Verify existing chat streaming remains compatible.
- Verify no performance regression beyond agreed budget.

---

## Risks and Mitigations

- Event volume spikes may degrade UI performance.
  - Mitigation: incremental virtualization and chunked rendering.
- Out-of-order delivery may produce incorrect state.
  - Mitigation: sequence-based ordering and idempotent reducers.
- Incomplete redaction may leak sensitive data.
  - Mitigation: deny-by-default masking policy + test fixtures for secrets.

---

## Implementation Notes

- Reuse existing stream transport where possible.
- Prefer additive schema changes to avoid breaking old runs.
- Keep event contracts versioned for forward compatibility.

---

## Definition of Done

- Backend emits, stores, and serves trace/tool events.
- Frontend shows real-time tool panel and trace visualization.
- Redaction and truncation policies are enforced end to end.
- Automated tests cover core behaviors and pass in CI.
