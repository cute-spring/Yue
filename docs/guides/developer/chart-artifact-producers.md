# Yue Chart Artifact Producers

## Purpose

This guide is for backend workflows, builtin tools, skills, agents, and external MCP tools that decide a data chart should appear in chat.

Yue's frontend does not decide when a chart exists. A scenario owner must explicitly emit a chart-ready `YueChartSpec` through a structured chart artifact path, or fall back to a fenced `yue-chart` block when structured emission is unavailable.

## How It Works

Preferred flow:

```text
scenario owner/tool -> YueChartSpec -> chart_artifact_create -> artifact.chart.created -> frontend validation/render -> message history replay
```

Compatibility flow:

```text
scenario owner/tool -> fenced yue-chart Markdown block -> frontend validation/render from Markdown content
```

Both paths use the same frontend validator and ECharts compiler. Raw ECharts options are never accepted as the product contract.

## Producer Responsibilities

Producers own:

- deciding whether a chart materially improves the answer
- choosing chart type
- organizing chart-ready rows
- providing explicit field encodings
- explaining the chart in nearby prose

Producers must not:

- emit raw ECharts `option`, `echartsOption`, or `rawOption`
- include JavaScript callbacks such as `formatter`
- rely on the frontend to aggregate business data or infer metrics
- create `WorkspaceArtifact` records automatically for inline charts

## Builtin Tool Usage

Use `builtin:chart_artifact_create` when available.

Input:

```json
{
  "chart": {
    "version": 1,
    "kind": "chart",
    "chartType": "bar",
    "title": "Revenue by Region",
    "data": [
      { "region": "APAC", "revenue": 120 },
      { "region": "EMEA", "revenue": 90 }
    ],
    "encoding": {
      "x": { "field": "region", "type": "category", "label": "Region" },
      "y": { "field": "revenue", "type": "number", "label": "Revenue" }
    }
  }
}
```

Optional placement:

```json
{
  "artifact_id": "chart_revenue_region",
  "placement": {
    "type": "replace_marker",
    "marker": "{{chart:chart_revenue_region}}"
  },
  "chart": {
    "version": 1,
    "kind": "chart",
    "chartType": "bar",
    "title": "Revenue by Region",
    "data": [
      { "region": "APAC", "revenue": 120 },
      { "region": "EMEA", "revenue": 90 }
    ],
    "encoding": {
      "x": { "field": "region", "type": "category" },
      "y": { "field": "revenue", "type": "number" }
    }
  }
}
```

When using `replace_marker`, include the exact marker in assistant prose where the chart belongs. If the marker is absent, Yue falls back to appending the chart after assistant text.

Successful result:

```json
{
  "ok": true,
  "artifact_id": "chart_...",
  "artifact_type": "chart",
  "display_mode": "inline",
  "message": "Structured chart artifact emitted. Refer to it in prose; do not repeat the full chart JSON."
}
```

After a successful call, the assistant should summarize what the chart shows. It should not repeat the full chart JSON in normal prose.

## External MCP Guidance

External MCP tools cannot directly control Yue's frontend. They should return chart-ready data and either:

- call a Yue-provided structured chart artifact capability when one is exposed to the tool runtime, or
- return a `YueChartSpec` under a clearly named field such as `chart_spec` for the Yue-side scenario owner to pass into `chart_artifact_create`.

Recommended MCP tool result shape:

```json
{
  "ok": true,
  "summary": "APAC leads revenue, followed by EMEA.",
  "chart_spec": {
    "version": 1,
    "kind": "chart",
    "chartType": "bar",
    "title": "Revenue by Region",
    "data": [
      { "region": "APAC", "revenue": 120 },
      { "region": "EMEA", "revenue": 90 }
    ],
    "encoding": {
      "x": { "field": "region", "type": "category" },
      "y": { "field": "revenue", "type": "number" }
    }
  }
}
```

If the MCP host cannot emit structured artifacts, return prose plus `chart_spec`; Yue can choose to emit it through `chart_artifact_create` or fall back to a fenced `yue-chart` block.

## Producer Integration Matrix

Recommended owner behavior:

| Owner type | Preferred integration | Notes |
| --- | --- | --- |
| Builtin data tools | Return chart-ready rows and call `chart_artifact_create` from the scenario runtime | Use when the tool has enough context to decide the chart is useful. |
| Backend workflows | Build `YueChartSpec`, enqueue `artifact.chart.created`, collect it on `StreamState` | Keep workspace saves as explicit user actions. |
| Generic agents | Use `chart_artifact_create` only when tool results or user intent justify a chart | Do not infer charts from arbitrary prose alone. |
| Skills | Declare `builtin:chart_artifact_create` in tool needs when charts are part of the workflow | Keep fenced `yue-chart` fallback in skill instructions. |
| External MCP tools | Return `chart_spec` and a summary, or call Yue's structured emitter if exposed | Never return raw ECharts options as the integration contract. |

First-party producer candidates beyond Excel:

- SQL/database analysis skills that return grouped or time-series rows.
- Workspace research synthesis when findings include comparable numeric evidence.
- Metrics/observability tools that already produce chart-ready time buckets.
- CSV/dataframe tools that compute explicit aggregations from user-selected files.
- Finance or planning agents when the user explicitly asks for trend, mix, or distribution views.

## Examples

Trend:

```json
{
  "version": 1,
  "kind": "chart",
  "chartType": "line",
  "title": "Monthly Revenue",
  "data": [
    { "month": "Jan", "revenue": 120 },
    { "month": "Feb", "revenue": 150 }
  ],
  "encoding": {
    "x": { "field": "month", "type": "category" },
    "y": { "field": "revenue", "type": "number" }
  }
}
```

Multi-series comparison:

```json
{
  "version": 1,
  "kind": "chart",
  "chartType": "multi-line",
  "title": "Free vs Paid Users",
  "data": [
    { "month": "Jan", "free": 1200, "paid": 300 },
    { "month": "Feb", "free": 1400, "paid": 380 }
  ],
  "encoding": {
    "x": { "field": "month", "type": "category" },
    "series": [
      { "field": "free", "label": "Free" },
      { "field": "paid", "label": "Paid" }
    ]
  }
}
```

Proportion:

```json
{
  "version": 1,
  "kind": "chart",
  "chartType": "pie",
  "title": "Revenue Mix",
  "data": [
    { "segment": "Enterprise", "revenue": 70 },
    { "segment": "SMB", "revenue": 30 }
  ],
  "encoding": {
    "category": { "field": "segment", "type": "category" },
    "value": { "field": "revenue", "type": "number" }
  }
}
```

Distribution/scatter:

```json
{
  "version": 1,
  "kind": "chart",
  "chartType": "scatter",
  "title": "Price vs Quantity",
  "data": [
    { "price": 10, "quantity": 4 },
    { "price": 18, "quantity": 9 }
  ],
  "encoding": {
    "x": { "field": "price", "type": "number" },
    "y": { "field": "quantity", "type": "number" }
  }
}
```

## Failure Handling

- If `chart_artifact_create` returns `INVALID_CHART_ARTIFACT`, fix the `YueChartSpec`; do not retry with raw ECharts.
- If structured emission is unavailable, use a fenced `yue-chart` block as compatibility fallback.
- If chart-ready data is incomplete, answer in prose/table form and state what is missing.
- If the chart is invalid on the frontend, Yue shows a compact error widget and preserves JSON inspection.

## Quality Gates

Before adding a producer, verify:

- the producer emits `YueChartSpec`, not raw ECharts
- chart data is already aggregated and chart-ready
- field references match row keys exactly
- text-only answers still work when no chart is needed
- structured chart artifacts replay from message history
