# 2026-04-10 Chat History Date + Tag Execution Plan

## Requirements Summary
- Group chat history by date buckets to improve scanability.
- Allow users to filter history by one or more tags.
- Auto-generate tags for each chat so filtering works even without manual labeling.
- Keep interaction responsive with large history lists.

## Scope
### In Scope
- Backend support for session tags and date/tag filtered history query.
- Frontend sidebar support for grouped rendering and tag filtering.
- Automatic tag generation pipeline on new chats and title/summary refresh.
- Unit and E2E test coverage for grouping and filtering behavior.

### Out of Scope
- Full semantic vector retrieval redesign.
- Multi-tenant auth redesign beyond existing owner concept.
- Bulk tag editing across multiple chats.

## Acceptance Criteria
- History endpoint supports `tags`, `date_from`, and `date_to` filters.
- Sidebar renders sessions grouped by `Today`, `Yesterday`, `Last 7 Days`, `Older`.
- Selecting one tag filters results to sessions containing that tag.
- Selecting multiple tags supports both `ANY` and `ALL` modes.
- New chats receive generated tags within 3 seconds of first assistant response.
- Existing chats remain readable even if tags are missing.

## Data Model and API Design
### Backend Data Changes
- Add `tags_json` (`TEXT`) to `sessions` table storing normalized tag arrays.
- Optional follow-up: migrate to dedicated `session_tags` relation if analytics needs grow.

### API Changes
- Extend `GET /api/chat/history` with:
  - `tags` (comma separated)
  - `tag_mode` (`any` or `all`)
  - `date_from` (ISO date)
  - `date_to` (ISO date)
- Response includes `tags: string[]` per session.
- Add `POST /api/chat/{chat_id}/tags/generate` internal endpoint for async/manual regeneration.

## Implementation Steps
1. Backend schema and model updates
- File targets:
  - `backend/app/models/chat.py`
  - `backend/alembic/versions/*_add_session_tags.py`
- Add `tags_json`, defaults, and migration safety for existing rows.

2. Backend service filtering and generation
- File targets:
  - `backend/app/services/chat_service.py`
  - `backend/app/api/chat.py`
- Implement filtering logic and deterministic tag normalization:
  - lowercase
  - kebab-case
  - dedupe
  - controlled vocabulary mapping (`authentication` -> `auth`).

3. Frontend type and state wiring
- File targets:
  - `frontend/src/types.ts`
  - `frontend/src/hooks/useChatState.ts`
- Add `tags` to `ChatSession`.
- Pass filter parameters when loading history.

4. Sidebar grouped rendering and filter controls
- File targets:
  - `frontend/src/components/ChatSidebar.tsx`
  - optional `frontend/src/components/ChatHistoryFilters.tsx`
- Add tag filter chips and date range control.
- Render grouped sections with sticky headers.

5. Auto-tag trigger and refresh behavior
- File targets:
  - `backend/app/services/chat_service.py`
  - `frontend/src/hooks/useChatState.ts`
- Trigger generation after summary/title updates.
- Optimistically refresh session metadata after generation.

6. Verification and rollout
- File targets:
  - `frontend/e2e/chat-history-filtering.spec.ts` (new)
  - backend unit tests for history query.
- Add feature flag if incremental rollout is preferred.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Over-tagging noisy labels | Poor filter quality | Controlled vocabulary + max tag count (8) |
| Slow history query | Sidebar lag | Index `updated_at`, cache parsed tags, cap result count |
| Inconsistent generated tags | User confusion | Stable prompt/rules + normalization + manual regenerate |
| Missing tags in old sessions | Partial filtering | Backfill job and fallback to untagged bucket |

## Verification Steps
1. Backend tests validate `tags` + `date` combinations.
2. Frontend tests validate grouped sections and empty states.
3. E2E validates:
- create chat
- generated tags appear
- filter by tag
- clear filter restores full list.
4. Manual UX check on desktop/mobile breakpoints.

## Delivery Sequence
1. MVP: date grouping + single-tag filter + generated tags.
2. V2: multi-tag mode (`ANY`/`ALL`) + date range filter.
3. V3: starred tags, saved filter presets, keyboard quick filter.
