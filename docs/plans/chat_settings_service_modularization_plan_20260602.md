# Chat / Settings / Service Modularization Plan (2026-06-02)

## Scope

This plan continues the in-progress modularization of the Chat and Settings paths, with focus on the still-heavy modules below:

- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/ChatSidebar.tsx`
- `frontend/src/components/ChatTraceShell.tsx`
- `backend/app/services/chat_service.py`
- `backend/app/api/chat_stream_runner.py`

## Current State

The codebase already completed the first wave of route/page shrinkage:

- `frontend/src/pages/Chat.tsx` is now a thin orchestration shell.
- `frontend/src/components/MessageItem.tsx` has already been split into smaller message-item view modules.
- `backend/app/api/chat.py` has already pushed schemas, helpers, tool-event handling, and stream orchestration into sibling modules.

The remaining problem is concentrated complexity in second-layer orchestrators and state-heavy feature modules.

## Target Boundaries

### Settings frontend

Keep `Settings.tsx` as a page shell and move feature behavior into dedicated hooks:

- `useSettingsGeneral.ts`
  - preferences save
  - feature-flag save
  - doc-access save
- `useSettingsMcp.ts`
  - MCP parse/save/reload/toggle/delete/install flows
  - smart-paste save flow
- `useSettingsLlm.ts`
  - provider refresh/test/edit
  - managed-model modal state and save/undo
  - custom-model delete/test

### Chat frontend

Continue shrinking chat UI modules by moving non-view-heavy logic out of component files:

- `ChatInput`
  - attachment policy and validation helpers
  - upload/preview presentation blocks
- `ChatSidebar`
  - filter persistence and grouping logic
  - workspace panel state defaults
- `ChatTraceShell`
  - trace fetch/load state
  - reusable trace section rendering helpers

### Chat backend

Continue the chat backend refactor as a chain rather than isolated file edits:

- `chat_service.py`
  - split storage, trace replay, action-state persistence, and metrics/reporting responsibilities into helper modules or mixins
- `chat_stream_runner.py`
  - pull request-snapshot, requested-action, and small runtime helper clusters into dedicated modules

## Phased Execution

1. Extract Settings feature hooks and preserve current tab/component API.
2. Extract Chat frontend pure helpers / state hooks from large components.
3. Split `chat_service.py` into mixins or helper modules without changing callers.
4. Split `chat_stream_runner.py` helper clusters while keeping `build_chat_event_generator(...)` stable.
5. Run focused frontend and backend regression checks.

## Risk Controls

- Preserve route/component/service entrypoints.
- Avoid API contract changes.
- Prefer structure-only extraction before deeper cleanup.
- Respect existing in-progress local changes, especially under `frontend/src/components/message-item/`.

## Validation Strategy

- Frontend: targeted Vitest for Settings / chat components plus typecheck if available.
- Backend: targeted pytest suites covering chat API, stream runner, and chat service behavior.

## Execution Update

- 2026-06-02: plan created to continue the second-stage modularization pass after the first wave already shrank `Chat.tsx` and `chat.py`.
