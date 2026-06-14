# 2026-06-03 Chat-to-Note / Memory Capture Execution Plan

## Requirements Summary
- Let users save useful chat output as structured notes instead of raw copied text.
- Auto-generate note title, summary, and tags so saved content is easy to scan and search.
- Preserve source backlinks to the originating chat, message, and workspace sources.
- Support later recall so saved notes and approved memories can improve future responses.
- Reuse the existing notebook, session summary, tags, workspace memory, and session-context foundations where practical.

## Current Baseline
### Already Present
- Notebook CRUD exists via `backend/app/services/notebook_service.py` and `backend/app/api/notebook.py`.
- Workspace note capture from chat messages exists via `POST /api/workspaces/{workspace_id}/notes/from-message`.
- Session title and summary generation exists via `backend/app/services/session_meta_service.py`.
- Session tags exist on chats via `sessions.tags_json`.
- Workspace memory candidate and approval flow exists in `backend/app/services/workspace_service.py`.
- Approved workspace memories are already ranked and injected into prompt context.

### Main Gaps
- Notes are stored as flat JSON documents with no durable structured metadata.
- `/note` behaves like "save the last assistant text" instead of "capture reusable knowledge".
- Auto-generated tags are English-regex based and weak for Chinese or mixed-language content.
- Notes are not first-class recall candidates in later chats.
- Users cannot clearly see why a note was captured, how it links back, or whether it was promoted to memory.

## Product Goal
Build a two-layer capture system:
1. `Note` for low-friction capture of useful chat output.
2. `Memory` for reviewed, durable, higher-confidence knowledge.

The end-state user experience should be:
1. User clicks `Save as note` or types `/note`.
2. System saves a structured note with title, summary, tags, source links, and note type.
3. System optionally suggests promotion to memory when content looks stable or highly reusable.
4. Later chats can recall related notes or memories, with visible evidence of what was recalled.

## Scope
### In Scope
- Upgrade note storage from flat JSON to structured database-backed records.
- Add title/summary/tag generation for saved notes.
- Add source backlink metadata for chats, messages, workspace sources, and citations.
- Add note classification and optional memory promotion workflow.
- Add note retrieval and note-assisted recall in later chats.
- Add frontend UX for capture confirmation, note browsing, and memory promotion.
- Add backend, frontend, and E2E verification coverage.

### Out of Scope
- Full cross-user identity and permissions redesign.
- Global semantic search across every artifact type in the product.
- Fully automatic long-term memory writes without user review.
- Major `session-context-manager` package redesign in phase 1.

## Acceptance Criteria
- Saving from chat creates a structured note record, not only a flat content blob.
- Saved notes have `title`, `summary`, `tags`, `note_type`, and source backlink metadata.
- Users can browse notes filtered by workspace, tags, source chat, and capture type.
- Users can promote a note to memory or create a memory candidate from it.
- Later chat turns can recall related notes and display recall evidence.
- Tag generation works for Chinese and mixed-language content at acceptable quality.
- Existing notebook content remains readable after migration.

## Architecture Direction
### Layering
- `Chat Session`: transient conversation and rolling session metadata.
- `Workspace Note`: user-facing structured capture artifact.
- `Workspace Memory Candidate`: proposed durable knowledge.
- `Workspace Memory`: reviewed long-term knowledge injected into prompt context.

### Key Principle
Not every saved note becomes memory. Notes are cheap capture. Memory is curated durable context.

## Phase 0: Schema and Capture Contract
### Objective
Define the durable note model that can support capture, filtering, backlinks, and promotion.

### Tasks
1. Add a database-backed note model or workspace note artifact model.
- Preferred file targets:
  - `backend/app/models/chat.py`
  - `backend/alembic/versions/*_add_workspace_notes.py`
- Suggested fields:
  - `id`
  - `workspace_id`
  - `title`
  - `summary`
  - `content`
  - `tags_json`
  - `note_type`
  - `capture_type`
  - `status`
  - `source_session_id`
  - `source_message_id`
  - `source_message_ids_json` or `source_turn_range_json`
  - `citation_refs_json`
  - `source_metadata_json`
  - `promoted_memory_id`
  - `created_at`
  - `updated_at`

2. Decide migration path for legacy notebook JSON notes.
- Keep legacy notes readable during rollout.
- Provide one-time migration into DB or a compatibility read layer.

3. Introduce a service boundary for notes.
- Preferred file targets:
  - `backend/app/services/notebook_service.py`
  - optional new `backend/app/services/workspace_note_service.py`
- Separate note persistence from note-enrichment logic.

### Exit Criteria
- Schema exists.
- Old notes still load.
- New notes can store structured metadata.

## Phase 1: Structured Note Capture
### Objective
Turn "save to note" into a structured capture flow with meaningful metadata.

### Tasks
1. Replace current raw note assembly in:
- `backend/app/api/workspaces.py`
- Current behavior appends lines like `Source chat` into the note body.
- New behavior should store backlinks as structured fields and keep note body clean.

2. Add enrichment pipeline for note save.
- Reuse `backend/app/services/session_meta_service.py` patterns.
- Create generation tasks for:
  - note title
  - note summary
  - note tags
  - note type classification

3. Expand note capture request/response contract.
- Add response fields needed by frontend:
  - generated title
  - generated summary
  - tags
  - note_type
  - backlink metadata
  - promotion suggestion

4. Update slash command behavior.
- File targets:
  - `frontend/src/pages/chat/utils/chatCommands.ts`
  - `frontend/src/pages/chat/hooks/useChatWorkspace.ts`
- `/note` should create a structured note and confirm what was saved.

5. Add richer confirmation UI.
- Show:
  - saved title
  - tags
  - note type
  - source link
  - quick action to open note

### Exit Criteria
- Chat save produces structured notes.
- User sees clear save confirmation.
- Notes have machine-usable metadata.

## Phase 2: Tagging and Classification Quality
### Objective
Make saved notes searchable and understandable across Chinese and mixed-language sessions.

### Tasks
1. Replace or augment regex-based tag derivation.
- Current implementation in `backend/app/services/chat_service_schema.py` is English-token centric.
- Add note-specific tag generation using LLM or hybrid rules.

2. Add normalization rules.
- lowercase where appropriate
- dedupe
- stable display form
- optional controlled vocabulary mapping
- Chinese tag preservation without forced transliteration

3. Add note type taxonomy.
- Suggested types:
  - `decision`
  - `fact`
  - `preference`
  - `todo`
  - `summary`
  - `insight`
  - `reference`

4. Add confidence and fallback behavior.
- If generation fails:
  - fallback title from content prefix
  - fallback summary from trimmed content
  - fallback tags empty rather than noisy

### Exit Criteria
- Generated titles and tags are visibly better than prefix-based save.
- Chinese sessions produce useful labels.
- Note type is available for filtering and promotion.

## Phase 3: Notebook UX Upgrade
### Objective
Turn the notebook page into a true capture surface instead of a plain text list.

### Tasks
1. Upgrade notebook list and editor UI.
- File target:
  - `frontend/src/pages/Notebook.tsx`
- Add:
  - tag chips
  - note type badge
  - workspace/source metadata
  - summary preview
  - promotion status

2. Add filters and sorting.
- Filter by:
  - workspace
  - tag
  - note type
  - capture type
  - source chat
- Sort by:
  - updated time
  - recently recalled
  - recently promoted

3. Add note detail backlinks.
- Open originating chat/session.
- Jump to source message when possible.
- Show associated workspace sources and citations.

4. Add quick actions.
- `Promote to memory`
- `Create memory candidate`
- `Copy summary`
- `Open source chat`

### Exit Criteria
- Notebook becomes a usable knowledge surface.
- Users can understand where each note came from and what it is for.

## Phase 4: Note-to-Memory Promotion
### Objective
Connect note capture with durable memory governance without auto-polluting memory.

### Tasks
1. Add note-driven memory candidate creation.
- Reuse existing memory candidate flow in `backend/app/services/workspace_service.py`.
- Allow memory suggestion from note, not only from assistant message.

2. Add promotion heuristics.
- High-signal candidates include:
  - stable user preference
  - confirmed project rule
  - repeated decision
  - reusable domain fact

3. Preserve lineage.
- Store:
  - source note id
  - source candidate id
  - approval mode
  - superseded memory id if replaced

4. Add frontend review UI.
- Candidate preview
- conflict explanation
- approve / reject / update existing

### Exit Criteria
- Notes can become governed memory through a clear review step.
- Memory lineage is inspectable.

## Phase 5: Recall and Prompt Injection
### Objective
Make saved knowledge useful in future conversations.

### Tasks
1. Add note retrieval layer.
- Start simple:
  - title/tag/content keyword match
  - workspace scoping
  - note type boost
- Later add embeddings if needed.

2. Inject relevant note context into chat preparation.
- File targets:
  - `backend/app/api/chat_stream_runner_preparation.py`
  - possible helper in workspace or note service
- Keep notes separate from reviewed memories in prompt formatting.

3. Define prompt block structure.
- Example sections:
  - `### Relevant Workspace Notes`
  - `### Workspace Memory Cards`
- Notes should be lower authority than approved memory.

4. Expose recall evidence to frontend.
- Similar to existing workspace memory evidence path.
- Show:
  - recalled note count
  - recalled note titles
  - why they matched

5. Add freshness rules.
- Newer user corrections should outrank old notes.
- Reviewed memory outranks plain note.

### Exit Criteria
- Later chats can use captured notes.
- Users can see when recall happened.

## Phase 6: Suggestive Capture and Passive Memory Capture
### Objective
Increase capture rate without making the product feel noisy or intrusive.

### Tasks
1. Add suggestion triggers after assistant messages.
- Trigger when content resembles:
  - multi-step plan
  - final recommendation
  - confirmed decision
  - reusable explanation

2. Add non-blocking capture prompts.
- Examples:
  - `Save as note`
  - `Keep as memory candidate`

3. Add user controls.
- Allow disable:
  - auto-suggestions
  - memory suggestions
  - note recall

4. Add suggestion quality telemetry.
- track shown
- accepted
- dismissed
- promoted

### Exit Criteria
- Capture becomes discoverable.
- Suggestion rate is high-value, not spammy.

## API and Service Work Items
### Backend
- `backend/app/models/chat.py`
- `backend/alembic/versions/*`
- `backend/app/api/notebook.py`
- `backend/app/api/workspaces.py`
- `backend/app/services/notebook_service.py`
- optional `backend/app/services/workspace_note_service.py`
- `backend/app/services/session_meta_service.py`
- `backend/app/services/workspace_service.py`
- `backend/app/api/chat_stream_runner_preparation.py`

### Frontend
- `frontend/src/pages/Notebook.tsx`
- `frontend/src/pages/chat/utils/chatCommands.ts`
- `frontend/src/pages/chat/hooks/useChatWorkspace.ts`
- `frontend/src/types.ts`
- possible new note list/detail/filter components
- message evidence components for recalled notes

## Testing Plan
### Backend Unit Tests
- structured note CRUD
- note creation from message
- title/summary/tag generation fallback behavior
- note-to-memory candidate creation
- recall ranking and filtering

### Frontend Unit Tests
- `/note` command behavior
- note save confirmation state
- notebook filters and badges
- recall evidence rendering

### E2E
1. Create workspace chat.
2. Save last assistant response as note.
3. Verify notebook entry shows generated metadata.
4. Promote note to memory candidate.
5. Approve candidate.
6. Ask a related follow-up.
7. Verify note or memory recall evidence appears.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Saving too much raw text | Notes become cluttered and low-value | Generate clean summary + note type + filters |
| Wrong auto-tagging in Chinese | Search and browse quality drops | LLM-assisted tags + normalization + fallback rules |
| Unreviewed note injected as fact | Model may over-trust weak content | Keep notes lower-authority than approved memory |
| Memory pollution | Durable context becomes noisy | Candidate review flow and conflict checks |
| Migration complexity from JSON notes | Existing users lose access | Compatibility read path and staged migration |

## Delivery Sequence
1. MVP
- DB-backed structured notes
- save from chat
- generated title/summary/tags
- clean backlinks
- notebook UI badges

2. V2
- note filters
- note-to-memory candidate flow
- recall evidence in chat

3. V3
- retrieval ranking improvements
- capture suggestions
- settings and telemetry

## Recommended Build Order for This Repo
1. Phase 0
2. Phase 1
3. Phase 3 basic UI shell
4. Phase 2 quality pass
5. Phase 4 promotion
6. Phase 5 recall
7. Phase 6 suggestions

This order reduces migration risk, gets visible user value early, and reuses the existing workspace memory injection path before attempting a broader memory architecture rewrite.
