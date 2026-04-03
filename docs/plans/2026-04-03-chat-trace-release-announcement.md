# Chat Trace Inspection Release Announcement

## Slack Version

Shipped `Trace Inspector` for chat debugging.

What’s included:

- read-only historical request snapshot inspection
- ordered tool-call trace inspection
- gated `raw` mode
- parent/child trace tree
- isolated UI that does not affect normal chat flow

Safety:

- no retry / re-run / edit actions
- default hidden via `chat_trace_ui_enabled=false`
- raw access disabled by default via `chat_trace_raw_enabled=false`

Validation:

- backend tests passed
- frontend tests passed
- build passed
- enabled-state smoke passed
- rollback smoke passed

Status:

- complete and ready for controlled rollout

## GitHub PR Version

### What

Adds a read-only historical trace inspection feature for chat runs.

This PR delivers:

- request snapshot capture for final model-bound inputs
- ordered tool trace capture for each run
- `/api/chat/{chat_id}/trace/bundle` summary/raw bundle retrieval
- isolated `Trace Inspector` UI in chat
- summary view, raw payload inspection, and trace-tree rendering
- rollout gating with `chat_trace_ui_enabled` and `chat_trace_raw_enabled`

### Why

We need a professional debugging surface for historical chat runs that shows:

- what was actually sent to the model
- what tools ran, in what order
- what each tool received and returned
- how nested or chained tool execution unfolded

This helps prompt analysis, tool-chain debugging, and regression diagnosis without changing runtime behavior.

### Safety

- strictly read-only
- no retry / re-run / patch controls
- backend capture is fail-open
- UI is isolated from the normal chat compose/send/stream path
- feature is hidden and raw access is disabled by default

### Testing

Backend:

- trace schema tests passed
- request snapshot capture tests passed
- tool trace capture regression tests passed
- trace bundle API tests passed
- config flag tests passed

Frontend:

- `npm run test -- ChatTraceShell` passed
- `npm run test -- Chat useChatState MessageList` passed
- `npm run build` passed

UI validation:

- `npx playwright test e2e/trace-inspector-smoke.spec.ts` passed
- `npx playwright test e2e/trace-inspector-rollback-smoke.spec.ts` passed

Rollback validation:

- UI entry disappears when flags are disabled
- raw endpoint returns `403 Forbidden` when raw mode is disabled

### Rollout

Recommended default posture:

- `chat_trace_ui_enabled=false`
- `chat_trace_raw_enabled=false`

Recommended rollout order:

1. enable UI only in internal environments
2. keep raw mode disabled unless explicitly needed
3. broaden rollout after operator sign-off

### Docs

- `docs/plans/2026-04-03-chat-request-payload-inspection-plan.md`
- `docs/plans/2026-04-03-chat-trace-inspection-release-checklist.md`
- `docs/plans/2026-04-03-chat-trace-delivery-summary.md`
