# Phase 4B Spec: Structured Chart Artifact Events and History Replay

## Purpose

Phase 4B upgrades Yue charts from the MVP Markdown `yue-chart` fenced block transport to a structured stream artifact transport that can be replayed from chat history.

The frontend remains a renderer and validator. It must not infer when a chart should exist. Scenario owners, tools, agents, skills, or backend workflows decide when to emit a chart artifact.

## Product Rules

- `artifact.chart.created` is the product-grade chart transport for structured chart artifacts.
- A chart artifact renders inline with the assistant turn, alongside normal assistant text.
- Structured chart artifacts are message-level chat renderings, not `WorkspaceArtifact` records.
- Saving a chart into a workspace remains an explicit user action.
- Existing `yue-chart` fenced block support remains supported for backward compatibility and prompt/tool migration.
- Raw ECharts option passthrough is disallowed. Payloads must use `YueChartSpec`.

## Non-Goals

- No frontend chart recommendation or automatic chart creation.
- No raw ECharts `option`, `echartsOption`, `rawOption`, formatter callback, or HTML tooltip passthrough.
- No automatic `WorkspaceArtifact` creation for inline charts.
- No chart editing, BI/dashboard authoring, server-side chart rendering, or PNG/SVG export in Phase 4B.
- No replacement of Mermaid for conceptual diagrams.
- No breaking change to existing chat streaming, Markdown rendering, or history replay behavior.

## Data Contracts

### Stream Event

`artifact.chart.created` uses the existing v2 stream envelope:

```json
{
  "version": "v2",
  "event": "artifact.chart.created",
  "event_id": "evt_...",
  "run_id": "run_...",
  "assistant_turn_id": "turn_...",
  "sequence": 42,
  "ts": "2026-07-24T12:00:00Z",
  "payload": {
    "artifact_id": "chart_...",
    "artifact_type": "chart",
    "display_mode": "inline",
    "message_id": null,
    "chart": {
      "version": 1,
      "kind": "chart",
      "chartType": "line",
      "title": "Monthly Active Users",
      "data": [
        { "month": "Jan", "free": 1200, "paid": 300 },
        { "month": "Feb", "free": 1400, "paid": 380 }
      ],
      "encoding": {
        "x": { "field": "month", "type": "category", "label": "Month" },
        "series": [
          { "field": "free", "label": "Free" },
          { "field": "paid", "label": "Paid" }
        ]
      }
    }
  }
}
```

Required envelope fields:

- `version`: `"v2"`
- `event`: `"artifact.chart.created"`
- `event_id`: globally unique event id
- `run_id`: current run id
- `assistant_turn_id`: current assistant turn id
- `sequence`: monotonic sequence within the run
- `ts`: ISO timestamp
- `payload`: chart artifact payload

Required payload fields:

- `artifact_id`: stable id for this chart artifact, unique within the session
- `artifact_type`: `"chart"`
- `display_mode`: `"inline"` for Phase 4B
- `chart`: a `YueChartSpec` object

Optional payload fields:

- `message_id`: omitted or `null` while streaming if the assistant message row has not been created yet; filled during history replay.
- `placement`: deferred placement hint. If omitted, append after assistant text in `sequence` order.
- `title`: optional artifact-level display label. The renderer should prefer `chart.title` unless a future UI needs an artifact chrome label.

### Binding Rules

- `assistant_turn_id` is the primary live-stream binding key.
- `sequence` defines deterministic ordering among text deltas, tool events, and chart artifacts in the same assistant turn.
- `message_id` is a replay binding key, not required for initial live streaming.
- During streaming, the frontend attaches the chart artifact to the active assistant message whose `assistant_turn_id` matches the event.
- After the assistant message is persisted, the backend stores each accepted structured chart artifact with the saved assistant `message_id`.
- On history replay, chart artifacts are returned as part of the assistant message and render from message state, not from a second event stream fetch.

### Message History Shape

Add a message-level replay field:

```ts
type StructuredChartArtifact = {
  artifact_id: string;
  artifact_type: 'chart';
  display_mode: 'inline';
  assistant_turn_id: string;
  message_id?: number | string | null;
  run_id?: string | null;
  sequence: number;
  ts?: string;
  chart: unknown;
  validation_status?: 'unvalidated' | 'valid' | 'invalid';
  validation_error?: {
    code: string;
    message: string;
    path?: string;
  };
};

type Message = {
  // existing fields...
  chart_artifacts?: StructuredChartArtifact[];
};
```

Backend storage should use a dedicated message-level field:

- Add `messages.chart_artifacts_json` as a JSON text column containing `StructuredChartArtifact[]`.
- Expose it through backend `Message` models and frontend `Message.chart_artifacts`.
- Do not store these records in `workspace_artifacts`.

This dedicated field is intentionally narrower than a generic `message_metadata_json` migration.

## Backend Changes

1. Add a lightweight chart artifact model and validator.
2. Add an emitter/helper for `artifact.chart.created`.
3. Persist validated chart artifact payloads into `messages.chart_artifacts_json` after the assistant message is saved.
4. Hydrate `chart_artifacts` in `get_chat` and `list_chats` message responses.
5. Update contracts:
   - `backend/contracts/api/chat_stream_response.json`
   - `backend/contracts/sse/meta.json` only if the generic envelope schema needs a named event example; the existing envelope fields already fit.
6. Keep existing stream event normalization behavior intact.

Backend lightweight validation must check:

- payload is a JSON object
- serialized artifact size is within `CHART_SPEC_LIMITS.maxSerializedBytes`
- `artifact_type === "chart"`
- `display_mode === "inline"`
- `chart.version === 1`
- `chart.kind === "chart"`
- required top-level `YueChartSpec` fields exist
- obvious forbidden keys are absent anywhere in the payload: `echartsOption`, `rawOption`, `option`, `formatter`, `tooltipHtml`, `html`, `unsafeHtml`, `dangerouslySetInnerHTML`

Backend validation must not replace frontend strict validation.

## Frontend Changes

1. Extend `frontend/src/types.ts` with `StructuredChartArtifact` and `Message.chart_artifacts`.
2. Extend `frontend/src/hooks/chat/chatStream.ts` to identify `artifact.chart.created` events.
3. Add an idempotent state updater:
   - key by `artifact_id` when present
   - otherwise key by `assistant_turn_id + sequence`
   - ignore duplicate `event_id`
   - sort by `sequence`, then `ts`
4. Attach live artifacts only to the assistant message with the matching `assistant_turn_id`.
5. Render structured chart artifacts in `MessageAssistantBody` after rendered Markdown content by default.
6. Reuse the same validation and compilation path as fenced blocks:
   - `parseYueChartSpec` / chart validator
   - `compileYueChartOption`
   - existing ECharts module/core renderer path
7. Keep fenced block DOM enhancement working unchanged.

Rendering behavior:

- Normal assistant text streams and renders exactly as today.
- Structured chart artifacts render as inline chart widgets after assistant text unless a future `placement` implementation is explicitly added.
- Multiple structured charts render in ascending `sequence` order.
- Structured charts and fenced charts may coexist in the same message.
- The frontend does not create a chart from text content, tables, or data shape.

## Validation Boundary

Backend:

- catches malformed or obviously unsafe chart artifacts early
- rejects or drops invalid structured artifact events before streaming/persistence
- may emit a diagnostic trace/error event for owners during development

Frontend:

- is the final safety boundary
- fully validates `YueChartSpec`
- enforces row, column, series, label, field, and serialized byte limits
- enforces chart-type-specific encodings
- rejects unsupported chart types and unsafe fields
- compiles only Yue-owned chart options
- never evaluates model/tool-provided JavaScript

## Failure and Fallback

- Invalid structured chart payloads must not crash chat rendering.
- If backend validation fails before streaming, do not emit `artifact.chart.created`; optionally emit a non-user-facing diagnostic event.
- If frontend validation fails, render a compact chart error widget with a JSON inspection panel.
- If the stream disconnects after an artifact event, reconnect/history replay must not duplicate the chart.
- If an artifact arrives before text completion, the frontend may render it as soon as valid or wait for the current render debounce; it must remain bound to the same assistant turn.
- If `message_id` is missing in live events, use `assistant_turn_id`; history replay later supplies message-bound artifacts.
- If structured persistence fails, the assistant text history still works; the chart may be absent on replay and should be logged as a backend persistence error.

## Risk Mitigation Guidance

### Message Persistence Timing

Live streaming and durable history have different identity availability. During streaming, the assistant message row may not exist yet, so `message_id` cannot be required on `artifact.chart.created`.

Mitigation:

- Use `assistant_turn_id` as the only required live binding key.
- Treat `message_id` as a replay binding key that is filled after the assistant message is persisted.
- Collect accepted chart artifact events in the current stream/run context.
- After `add_message()` saves the assistant message, write the collected artifacts into `messages.chart_artifacts_json` with the saved `message_id`.
- If artifact persistence fails, preserve the assistant text message and log the chart replay failure.

Required identity model:

```text
live binding: assistant_turn_id
history binding: message_id + assistant_turn_id
ordering: sequence
```

### Duplicate Replay and Reconnect

SSE reconnects, repeated event handling, and history replay can otherwise render the same chart more than once.

Mitigation:

- Frontend chart artifact state must be idempotent.
- Deduplicate first by `event_id` when processing stream events.
- Deduplicate chart artifacts by `artifact_id` when present.
- If `artifact_id` is absent, fall back to `${assistant_turn_id}:${sequence}`.
- Sort artifacts deterministically by `sequence`, then `ts`, then `artifact_id`.
- History hydration should replace or initialize message `chart_artifacts`; it should not append on top of already-replayed stream artifacts for the same message.

### Storage Shape Creep

Chart artifacts are message-scoped renderable state, not durable workspace records and not arbitrary message metadata.

Mitigation:

- Use a dedicated `messages.chart_artifacts_json` field for Phase 4B.
- Do not introduce a broad `message_metadata_json` bag just for charts.
- Do not reuse `workspace_artifacts` for inline chart replay.
- Keep workspace save/export as a future explicit user action with its own API path.

This keeps the migration narrow and avoids mixing transient inline renderings with user-saved workspace artifacts.

### Renderer Split-Brain

The Markdown fenced transport and structured event transport must not evolve into two incompatible chart implementations.

Mitigation:

- Allow transport-specific extraction only.
- Reuse one validation and rendering path for both transports.
- Fenced block path produces a raw `YueChartSpec` string.
- Structured event path produces a raw `YueChartSpec` object.
- Both paths then flow through the same normalizer, strict validator, compiler, and ECharts renderer.

Target pipeline:

```text
yue-chart fenced block -> raw YueChartSpec string
artifact.chart.created -> raw YueChartSpec object
both -> normalize/validate -> compileYueChartOption -> Yue-controlled ECharts renderer
```

### Validation Boundary Drift

Backend and frontend validation can drift if both layers attempt to fully own chart schema rules.

Mitigation:

- Backend owns lightweight contract hygiene only.
- Frontend owns strict render safety.
- Backend validation should reject clearly malformed, oversized, or obviously unsafe artifacts before streaming/persistence.
- Frontend validation remains authoritative for chart-type-specific encodings, field references, dataset limits, type compatibility, unsafe display fields, and ECharts option safety.
- Do not copy the full frontend chart compiler rules into backend code unless a shared schema package is introduced later.

### Backward Compatibility

Existing `yue-chart` fenced blocks are already a replayable transport because the chart payload lives in Markdown content.

Mitigation:

- Do not migrate old fenced blocks into structured artifacts for Phase 4B.
- Keep fenced block rendering enabled.
- Allow structured charts and fenced charts to coexist in the same assistant message.
- Add regression tests for all three cases: fenced-only, structured-only, and mixed.

## Migration and Backward Compatibility

- Existing assistant messages with `yue-chart` fenced blocks continue replaying from Markdown content.
- Existing messages without `chart_artifacts` behave unchanged.
- Phase 4B does not require migrating fenced blocks into structured artifacts.
- Agents/tools may migrate gradually from fenced blocks to `artifact.chart.created`.
- During the migration window, both transports are valid.
- The same `YueChartSpec` schema and frontend validation rules apply to both transports.

## Testing Plan

Backend unit/contract tests:

- `artifact.chart.created` envelope contains `event_id`, `run_id`, `assistant_turn_id`, `sequence`, `ts`, and `payload`.
- valid chart artifact passes lightweight validation.
- forbidden raw ECharts fields are rejected.
- oversized payload is rejected.
- persisted assistant message includes `chart_artifacts_json`.
- `get_chat` hydrates `Message.chart_artifacts`.
- structured chart artifacts do not create `WorkspaceArtifact` rows.

Frontend unit tests:

- stream normalizer preserves `artifact.chart.created`.
- artifact reducer attaches charts by `assistant_turn_id`.
- duplicate event ids/artifact ids are idempotent.
- multiple artifacts sort by `sequence`.
- invalid structured chart renders fallback using existing validator.
- fenced `yue-chart` Markdown rendering still works.

Frontend integration/e2e tests:

- text plus one structured chart renders in one assistant message.
- two structured charts render in deterministic order.
- structured chart survives history reload.
- structured and fenced charts can coexist.
- malformed chart shows error UI and does not break Markdown content.

Acceptance criteria:

- A backend workflow can emit `artifact.chart.created` and see the chart render inline in the matching assistant turn.
- Reloading the chat shows the same structured chart from message history.
- No chart is created unless an owner emitted a structured artifact or fenced block.
- Raw ECharts options are rejected.
- No automatic workspace artifact is created.
- Existing tests and frontend build continue passing.

## Open Questions

None blocking for Phase 4B.
