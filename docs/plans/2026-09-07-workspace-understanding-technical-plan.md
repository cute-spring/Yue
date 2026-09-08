# 2026-09-07 Workspace Understanding Technical Plan

## 1. Objective

Implement the Workspace Understanding product model in small, testable slices:

- visible Workspace Understanding summary
- user-level and workspace-level memory separation
- inline memory confirmation
- high-signal memory candidate detection
- conversation-first correction of stale memory

This plan extends the existing workspace source, note, artifact, memory, and memory candidate foundations.

## 2. Current Baseline

Already present:

- Workspace CRUD in `backend/app/services/workspace_service.py`
- workspace memory cards and candidates
- note-to-memory candidate flow
- message-to-note flow
- approved workspace memory injection into prompt context
- chat sidebar Workspace dock and resource panels
- frontend types for Workspace, Source, Artifact, Note, Memory, and Candidate

Main gaps:

- no first-class `Workspace Understanding` summary endpoint
- no cross-workspace `User Memory` surface
- memory cards use engineering-oriented memory types rather than the product-facing 8-group model
- memory candidate creation is mostly explicit action driven, not inline/proactive
- correction/update/replace flows exist partly in backend but are not exposed as a conversational UX
- current Workspace UI starts from resources and controls rather than "what Yue understands"

## 3. Design Direction

### Deep Module Candidate

Introduce a `WorkspaceUnderstanding` module with a small interface:

- build a user-facing summary for a workspace
- classify memory cards and candidates into product groups
- recommend memory scope for candidates
- produce confirmation payloads for the UI
- resolve correction actions against existing memory

The interface should hide ranking, grouping, conflict detection, and source aggregation from callers.

Suggested files:

- `backend/app/services/workspace_understanding_service.py`
- `backend/tests/test_workspace_understanding_service_unit.py`
- `backend/app/api/workspaces.py` for thin route wrappers

Avoid spreading grouping logic across route handlers, frontend components, and prompt assembly.

## 4. Product-Facing Taxonomy

Add product-facing understanding groups:

- `background`
- `goals`
- `decisions`
- `constraints`
- `preferences`
- `terms`
- `open_questions`
- `current_state`

These should be distinct from existing low-level memory types, but mapped from them.

Initial mapping:

- `project_fact` -> `background`
- `decision` -> `decisions`
- `preference` -> `preferences`
- `recurring_instruction` -> `preferences`
- `term` -> `terms`
- `open_question` -> `open_questions`
- `temporary_state` -> `current_state`
- `historical_conclusion` -> `background` or `decisions` depending on metadata

Add metadata override:

- `understanding_group`

This lets existing memory types remain compatible while the UI speaks the new product language.

## 5. Backend Contracts

### Workspace Understanding Summary

Add:

`GET /api/workspaces/{workspace_id}/understanding`

Response shape:

```json
{
  "workspace_id": "ws_1",
  "groups": [
    {
      "group": "background",
      "label": "Background",
      "total_count": 3,
      "active_count": 3,
      "pending_count": 1,
      "representative_items": [
        {
          "id": "mem_1",
          "kind": "memory",
          "title": "Yue is a trusted AI workbench",
          "content": "Yue combines provider-backed agents, MCP tools, skills, and streaming chat.",
          "status": "active",
          "source_session_id": "chat_1",
          "source_message_id": 42
        }
      ]
    }
  ],
  "applied_user_memory_preview": []
}
```

### Memory Candidate Detection

Add a later-phase route:

`POST /api/memory-candidates/analyze-message`

Request:

```json
{
  "workspace_id": "ws_1",
  "chat_id": "chat_1",
  "message_id": 42,
  "content": "I prefer Chinese answers with the conclusion first."
}
```

Response:

```json
{
  "candidate": {
    "title": "Chinese conclusion-first answers",
    "content": "Use Chinese by default and start with the conclusion.",
    "recommended_scope": "user",
    "understanding_group": "preferences",
    "confidence": 0.86,
    "reason": "The user explicitly stated a durable preference."
  }
}
```

First version can keep this endpoint backend-only or call it after assistant completion.

## 6. Data Model

### Minimal First Version

Reuse `workspace_memory_cards.memory_metadata_json` and `workspace_memory_candidates.candidate_metadata_json`.

Store:

- `understanding_group`
- `recommended_scope`
- `capture_signal`
- `correction_action`
- `replaces_memory_id`

This avoids immediate migrations while proving the product loop.

### Later Version

If query volume grows, add explicit columns:

- `understanding_group`
- `scope_type`
- `scope_ref`
- `capture_signal`

Existing `scope_type` and `scope_ref` already support part of this shape.

## 7. User Memory

Current code has workspace-scoped memory but no clear global `About You` surface.

Implementation options:

1. Reuse `workspace_memory_cards` with `scope_type = "user"` and a global workspace/null convention.
2. Add a separate `user_memory_cards` table.

Recommendation for first version:

Use existing memory card model with `scope_type = "user"` and `scope_ref = null`, but expose it through a clear `UserMemory` interface so the storage choice can change later.

Suggested module:

- `backend/app/services/user_memory_service.py`

Small interface:

- `list_applied_preview(workspace_id, current_query=None)`
- `create_candidate_from_message(...)`
- `approve_candidate(...)`

## 8. Frontend Changes

### Selected Layout

Use the `B - Two-Layer Context` prototype as the production design direction.

Implementation should preserve the prototype's information hierarchy:

- `About You` appears as a lightweight applied-memory rail or top section.
- `About This Workspace` owns the main Workspace canvas.
- fixed Workspace Understanding groups are the primary first-screen content.
- Sources, Notes, Artifacts, and raw Memory management remain secondary.

Borrow the compact status metrics from Variant A and the inline confirmation style from Variant C.

### Types

Add types in `frontend/src/types.ts`:

- `WorkspaceUnderstandingGroup`
- `WorkspaceUnderstandingItem`
- `WorkspaceUnderstandingSummary`
- `MemoryCandidateAnalysis`
- `InlineMemoryConfirmation`

### Hook

Extend or split `useChatWorkspace`.

Recommendation:

Create a new hook:

- `frontend/src/pages/chat/hooks/useWorkspaceUnderstanding.ts`

It should own:

- loading `/understanding`
- optimistic refresh after memory approvals
- inline confirmation state
- grouping summary state

Keep `useChatWorkspace` focused on existing Workspace resources until the new hook proves stable.

### UI

Add:

- `frontend/src/components/workspace/WorkspaceUnderstandingPanel.tsx`
- `frontend/src/components/workspace/WorkspaceUnderstandingGroupCard.tsx`
- `frontend/src/components/memory/InlineMemoryConfirmation.tsx`

Update:

- `frontend/src/components/chat-sidebar/ChatWorkspaceDock.tsx`
- `frontend/src/components/ChatSidebarResources.tsx`
- `frontend/src/pages/chat/components/ChatPageContent.tsx`

First screen should become:

- Workspace header
- Applied User Memory preview
- fixed 8-group Workspace Understanding summary
- secondary tabs/sections for Sources, Notes, Artifacts, and Memory management

## 9. Prompt/Runtime Integration

Existing prompt context already injects active workspace memories.

Add:

- product-group labels to loaded memory metadata
- applied user memory preview in message metadata when user memory exists
- correction-sensitive retrieval, so contradicted/superseded memories are not loaded

Do not inject pending candidates into normal answers unless explicitly framed as pending/unconfirmed.

## 10. Phased Implementation

### Phase 0: Contract and Summary

Goal: make Yue's Workspace Understanding visible without changing capture behavior.

Tasks:

1. Add taxonomy constants and mapping helpers.
2. Add `WorkspaceUnderstandingService`.
3. Add `GET /api/workspaces/{workspace_id}/understanding`.
4. Add frontend types.
5. Add fixed 8-group summary UI.
6. Keep existing resource lists accessible below or behind a tab.

Tests:

- backend unit tests for grouping/mapping
- API test for summary response
- frontend component test for fixed group rendering

Local tracker tickets:

- `.scratch/workspace-understanding/issues/01-build-workspace-understanding-summary-service.md`
- `.scratch/workspace-understanding/issues/02-add-workspace-understanding-api-contract.md`
- `.scratch/workspace-understanding/issues/03-add-frontend-understanding-types-and-hook.md`
- `.scratch/workspace-understanding/issues/04-implement-two-layer-workspace-first-screen.md`

### Phase 1: Inline Confirmation From Explicit Actions

Goal: reuse existing memory candidate creation, but show a better confirmation experience.

Tasks:

1. Convert explicit `Review as memory` results into inline confirmation cards.
2. Show recommended destination and understanding group.
3. Support edit before save.
4. Refresh Workspace Understanding after approval.

Tests:

- frontend test for inline confirmation actions
- backend test for metadata preservation
- Playwright test for chat -> candidate -> approve -> summary update

Local tracker ticket:

- `.scratch/workspace-understanding/issues/05-inline-confirmation-for-existing-memory-candidates.md`

### Phase 2: High-Signal Detection

Goal: Yue proactively detects likely memory candidates after high-signal user statements.

Tasks:

1. Add high-signal classifier.
2. Start rule-based for explicit markers: "以后", "默认", "我喜欢", "我不喜欢", "remember", "always", "don't".
3. Add optional LLM classifier later for ambiguous cases.
4. Enforce one prompt per assistant turn.
5. Track dismissals to reduce prompt frequency.

Tests:

- classifier unit tests in Chinese and English
- no-prompt tests for ordinary chat
- UI frequency cap tests

Local tracker ticket:

- `.scratch/workspace-understanding/issues/07-high-signal-memory-capture-mvp.md`

### Phase 3: User Memory Preview

Goal: make `About You` visible inside Workspace without mixing it into Workspace Memory.

Tasks:

1. Add `UserMemoryService` interface over existing storage.
2. Add applied user memory preview to `/understanding`.
3. Render `Also using About You`.
4. Add a global memory management route later.

Tests:

- user memory preview selection tests
- workspace summary tests verifying user memory is not duplicated into workspace groups

Local tracker ticket:

- `.scratch/workspace-understanding/issues/06-add-applied-user-memory-preview.md`

### Phase 4: Conversation-First Correction

Goal: user corrections propose update, replace, or archive actions inline.

Tasks:

1. Detect correction phrases and contradiction candidates.
2. Match correction to existing memory cards.
3. Produce action payloads: `update`, `replace`, `archive`.
4. Expose `View conflict`.
5. Ensure replaced/superseded memory does not load into future prompt context.

Tests:

- correction matching unit tests
- prompt context excludes superseded items
- Playwright correction flow

Local tracker ticket:

- `.scratch/workspace-understanding/issues/08-conversation-first-memory-correction.md`

## 11. Acceptance Criteria

- Workspace opens to a fixed 8-group Understanding summary.
- Summary can be loaded with one backend request.
- User-level preview is visibly separate from workspace-level understanding.
- Existing Sources, Notes, Artifacts, and Memory management remain available.
- Explicit memory capture can be approved through inline confirmation.
- High-signal user preferences and corrections can become candidates without silent durable writes.
- Tests cover grouping, API contract, UI rendering, and at least one end-to-end confirmation path.

## 12. Rollout Risks

- Too many memory prompts can make Yue feel needy.
- Too little prompting fails the "越用越聪明" promise.
- Mixing User Memory and Workspace Memory can create cross-project contamination.
- Treating raw notes as durable memory can persist unreviewed assistant claims.
- Expanding `useChatWorkspace` further may make the frontend harder to change.

Mitigations:

- high-signal-only capture policy
- explicit confirmation
- separate User Memory preview
- new `WorkspaceUnderstandingService` and `useWorkspaceUnderstanding` module
- focused browser regression for the main loop
