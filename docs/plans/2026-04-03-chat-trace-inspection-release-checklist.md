# Chat Trace Inspection Release Checklist

## Purpose

This checklist is for operators and release owners who want to enable the read-only chat trace inspection feature safely, without affecting the normal chat experience.

The feature is intentionally additive and read-only:

- it does not retry or re-run tools
- it does not mutate chat history
- it does not alter the normal send/stream/reply path

## Current Implementation Boundary

Implemented:

- request snapshot capture
- tool trace capture
- read-only summary endpoint
- backend raw-mode gating
- isolated frontend trace drawer
- summary-mode request and tool-trace rendering
- default-hidden UI flag

Not fully completed yet:

- deeper raw-mode UI polish and validation
- broader nested call-tree UX refinement beyond the current read-only tree view

## Feature Flags

### `chat_trace_ui_enabled`

- default: `false`
- purpose: shows or hides the Trace Inspector UI entry point
- recommended rollout: enable first in internal environments only

### `chat_trace_raw_enabled`

- default: `false`
- purpose: allows backend raw trace bundle access
- recommended rollout: keep disabled unless an explicitly authorized debug workflow needs it

## Pre-Release Checklist

- [ ] Confirm backend tests are green for trace-related changes.
- [ ] Confirm summary endpoint access works in the target environment.
- [ ] Confirm `chat_trace_ui_enabled` remains `false` by default before rollout.
- [ ] Confirm `chat_trace_raw_enabled` remains `false` by default before rollout.
- [ ] Confirm no operator or product expectation includes retry, re-run, or edit behavior.
- [ ] Confirm frontend JS toolchain is available if frontend validation is required in this environment.

## Recommended Rollout Order

### Stage 1: backend-only readiness

- [ ] Deploy backend capture and summary endpoint with UI flag still disabled.
- [ ] Verify normal chat send and stream behavior on a smoke-test chat.
- [ ] Verify no user-visible UI change appears while `chat_trace_ui_enabled=false`.

### Stage 2: internal UI exposure

- [ ] Enable `chat_trace_ui_enabled=true` in an internal or development environment.
- [ ] Keep `chat_trace_raw_enabled=false`.
- [ ] Verify the Trace Inspector opens as an isolated drawer.
- [ ] Verify opening and closing the drawer does not affect chat input, streaming, or message history interactions.

### Stage 3: internal trace validation

- [ ] Verify a chat with no tool calls shows a valid empty tool-trace state.
- [ ] Verify a chat with tool calls shows ordered tool records.
- [ ] Verify request metadata, message history summary, attachments, and field policies render correctly.
- [ ] Verify 404 handling shows the expected “no saved trace summary” message.
- [ ] Verify the feature remains read-only and exposes no action controls.

### Stage 4: optional raw-mode validation

- [ ] Enable `chat_trace_raw_enabled=true` only in an authorized debug environment.
- [ ] Verify the backend raw endpoint is accessible only when the flag is enabled.
- [ ] Verify the Raw mode toggle appears only when the raw flag is enabled.
- [ ] Verify switching between Summary and Raw refreshes the bundle without affecting the main chat page.
- [ ] Verify raw payload blocks show tool inputs, outputs, and error details in read-only form.
- [ ] Verify summary mode still behaves as the default safe path.
- [ ] Verify no UI path attempts to mutate or re-execute anything.

## Regression Checklist

### Backend

- [ ] `cd backend && .venv/bin/python -m pytest tests/test_chat_trace_schemas_unit.py -q`
- [ ] `cd backend && .venv/bin/python -m pytest tests/test_chat_stream_runner_unit.py tests/test_api_chat_modularization_regression.py -q`
- [ ] `cd backend && .venv/bin/python -m pytest tests/test_chat_service_unit.py tests/test_api_chat_unit.py -k "trace_bundle or chat_trace_raw" -q`
- [ ] `cd backend && .venv/bin/python -m pytest tests/test_api_config_unit.py tests/test_config_service_unit.py -q`

### Frontend

- [ ] `cd frontend && npm run test -- Chat`
- [ ] `cd frontend && npm run test -- useChatState MessageList Chat`
- [ ] `cd frontend && npm run build`
- [ ] `cd frontend && npx playwright test e2e/trace-inspector-smoke.spec.ts`

Note:

- Frontend validation has been executed successfully in this workspace using `/opt/homebrew/bin/node` and `/opt/homebrew/bin/npm`.
- The current build still emits a chunk-size warning from Vite, but the production build completes successfully.

## Smoke Test Script

Use this manual smoke sequence after enabling `chat_trace_ui_enabled`:

1. Open an existing chat with known history.
2. Confirm the normal chat page loads without layout regressions.
3. Open Trace Inspector.
4. Confirm the drawer appears independently of the main message area.
5. Confirm request summary data is visible.
6. Confirm tool trace summary is visible or an empty-state message appears.
7. Close the drawer.
8. Send a normal chat message.
9. Confirm send, stream, and response rendering still behave normally.

Smoke evidence completed in this workspace:

- [x] Seeded smoke chat loaded from an isolated temporary `YUE_DATA_DIR`
- [x] Trace Inspector opened from the independent chat header entry point
- [x] Summary mode rendered request snapshot and tool trace content
- [x] Raw mode rendered gated raw payload content
- [x] Read-only trace tree rendered parent-child call structure
- [x] Playwright smoke spec passed: `frontend/e2e/trace-inspector-smoke.spec.ts`
- [x] Rollback smoke spec passed: `frontend/e2e/trace-inspector-rollback-smoke.spec.ts`
- [x] Raw trace endpoint returned `403 Forbidden` after rollback flags were disabled

## Rollback Procedure

### Fast rollback

- Set `chat_trace_ui_enabled=false`
- Set `chat_trace_raw_enabled=false`

Expected result:

- Trace Inspector UI entry disappears
- raw trace access is blocked
- normal chat behavior continues unchanged

### When to rollback immediately

- The chat header or main layout becomes unstable after enabling the UI flag
- Opening the drawer interferes with input, send, stream, or history behavior
- Trace loading causes visible regressions in normal chat usage
- Raw mode is exposed in an environment where it should remain disabled

## Operator Notes

- This feature is safe to keep deployed but hidden.
- The preferred production posture is:
  - `chat_trace_ui_enabled=false`
  - `chat_trace_raw_enabled=false`
- If internal teams need summary inspection, enable only the UI flag first.
- Enable raw mode only for trusted debug workflows with explicit awareness of exposure risk.

## Exit Criteria For Broader Rollout

- [x] Frontend automated tests executed successfully in a JS-capable environment
- [x] Frontend build executed successfully in a JS-capable environment
- [x] Internal smoke test completed without regression
- [x] Summary-mode inspection confirmed useful on at least one multi-tool historical chat
- [x] Raw-mode inspection confirmed useful on at least one internal debug chat with gated access
- [x] Rollback path verified by disabling the flags without affecting normal chat flows
