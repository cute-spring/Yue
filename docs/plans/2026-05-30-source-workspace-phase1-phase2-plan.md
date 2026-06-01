# Source Workspace Phase 1/2 Implementation Plan

Date: 2026-05-30
Status: Phase 1 and Phase 2 MVP implemented and verified
Owner Scope: product architecture, backend data/API, chat runtime context, notebook integration, frontend workspace UX, validation

## 0. Implementation Status

Last updated: 2026-05-30

Phase 1 is implemented as the thin durable workspace layer:

- `workspaces`, `workspace_sources`, `workspace_artifacts`, and `sessions.workspace_id` are persisted through Alembic migrations.
- Workspace CRUD, source CRUD/list, artifact CRUD/list, and workspace-scoped session listing are available through backend APIs.
- Chat submission can carry `workspace_id`, workspace-scoped attachments are registered as sources, and history can be filtered by workspace.
- Chat sidebar exposes workspace switching, source listing, and artifact listing.

Phase 2 MVP is implemented as the source-readiness and evidence workflow slice:

- Workspace sources can be checked individually or in bulk, with readiness status and structured readiness metadata stored on the source.
- Readiness checks respect the global `doc_access` policy for local files and roots; workspace selection does not grant file permissions.
- Chat requests support `workspace_source_mode`, `selected_workspace_source_ids`, and `grounding_mode`.
- Chat prompt assembly includes eligible workspace source context and grounding instructions for `normal`, `prefer_sources`, and `require_sources`.
- Request snapshots preserve workspace source mode, selected source ids, grounding mode, and the generated workspace source context.
- Assistant responses can be saved as workspace notes and research artifacts; research artifacts are stored under `workspace_artifacts`.
- The Chat sidebar exposes readiness check actions, source mode selection, selected-source checkboxes, grounding mode, and artifact visibility.

Deferred beyond the current MVP:

- Workspace memory CRUD and memory review flows remain deferred until grounded source behavior is stable.
- Rich research artifact detail pages, structured finding editors, and export actions remain deferred.
- Full autonomous long-running research jobs, global RAG/indexing, OCR, and universal parser coverage remain out of scope for this phase.

Validation completed on 2026-05-30:

- Backend targeted/related tests: `148 passed`.
- Frontend full Vitest suite: `24 passed`, `206 passed`.
- Frontend production build: passed.
- Fresh SQLite Alembic `upgrade head` and `downgrade base`: passed.
- In-app browser smoke of the Chat page: passed, no visible runtime error.

Phase 4 hardening/productization started on 2026-05-30:

- Added a visible evidence-scope summary in the Chat sidebar so users can see whether the next workspace chat uses all ready sources, selected sources, or no sources, plus the active citation strictness.
- Upgraded workspace artifacts from a thin list into clickable research detail cards showing question, summary, mode, linked sources, open questions, source chat/message, and export paths when available.
- Added source-card capability labels such as `cite-ready`, `PDF read`, `PDF search`, `Excel read`, and `Excel query` so users can see not just that a source is ready, but what Yue can do with it.
- Added real-file readiness coverage for existing PDF uploads, existing Excel uploads, missing uploads, unsupported uploads, and mixed bulk readiness checks.
- Added stream-level workspace grounding metadata so each assistant response can display its evidence contract without exposing the full prompt block.
- Added message-level evidence contract UI showing source mode, grounding strictness, eligible sources, citation count, and a warning when `require_sources` is active but no citations are attached.
- Fixed a manual-QA gap where attachment auto-registration created workspace sources without immediate readiness enrichment; the same chat turn now sees `available_tools` and `citation_capable` without requiring a separate `Check`.
- Added a tooling warning path for `require_sources` turns when no compatible retrieval tools are enabled, so the UI can distinguish "citation required" from "citation-capable execution path actually available".
- Reworked research artifact cards to use native `details`/`summary`; single-artifact workspaces now show the detail body by default, improving click reliability and accessibility.
- Completed a temporary-backend browser smoke with a real seeded workspace containing ready PDF, ready CSV, unsupported MOV, missing PDF, and one research artifact. The Chat sidebar showed readiness states, source capability labels, evidence scope, artifact summary, source labels, open questions, and source chat backlink.
- Added frontend helper coverage for research artifact metadata normalization, source label resolution, and evidence-scope summaries.
- Validation: targeted workspace/sidebar tests passed, full frontend Vitest passed, frontend build passed, and in-app browser smoke passed.

## 1. Purpose

This document turns the `Source Workspace` opportunity from the AI Workbench roadmap into an executable two-phase plan.

The product goal is to make Yue feel less like a generic chat shell and more like a trusted AI workbench where a project, research question, client case, sprint, or report has one durable place for:

- source files and local document references
- chats and chat history
- notes
- generated artifacts and exports
- default agent choice
- citations and traceable evidence
- tool/action outputs

The first phase should stay intentionally thin. It should create a durable workspace identity and attach existing Yue objects to it. The second phase should make the attached sources usable, inspectable, selectable, and evidence-backed.

## 2. Current Baseline

Yue already has strong pieces of the Source Workspace shape:

- chat sessions, messages, tags, summaries, tool calls, action events, and action states in `backend/app/models/chat.py`
- generic message attachments via `messages.attachments`
- upload API and upload metadata via `backend/app/api/files.py`
- document access configuration through `doc_access.allow_roots` and `doc_access.deny_roots`
- docs/PDF/Excel/PPT built-in tools and agents
- action observability fields, including artifact paths
- Notebook CRUD through `backend/app/services/notebook_service.py`
- chat trace and request attachment snapshots

The missing object is the durable project-level container that binds these pieces together.

## 3. Guiding Decisions

### 3.1 Workspace Is A Container, Not A Permission System

`Workspace` may store selected sources, preferred local roots, and default source scope. It must not become an independent file permission boundary.

Local file access authority remains:

- `doc_access.allow_roots`
- `doc_access.deny_roots`

Workspace source selection narrows what the user and agent intend to use. It does not grant access to anything outside the global document access policy.

### 3.2 Start With Registry, Not Full RAG

Phase 1 should create a durable registry of workspace objects. It should not require vector indexing, OCR, background ingestion, or long-running research orchestration.

Phase 2 can add readiness states and evidence behavior without forcing all sources into a single indexing system.

### 3.3 Reuse Shipped Attachment Work

The codebase already has:

- `ChatRequest.attachments`
- `Message.attachments`
- `/api/files`
- frontend upload-before-submit behavior

Phase 1 should attach existing uploaded file metadata to a workspace. It should not redesign the attachment model.

### 3.4 Keep The MVP Product Shape Coherent

The first visible product should answer four user questions:

- Which workspace am I in?
- Which chats, notes, files, and outputs belong here?
- Which agent is the default for this workspace?
- Which sources will Yue consider for this task?

## 4. Phase 1: Thin Source Workspace

### 4.1 Goal

Create the minimal durable workspace layer that binds chats, notes, uploaded files, local document references, and generated artifacts into one product object.

Phase 1 is successful when a user can create a workspace, work inside it, upload or reference sources, create notes, chat with a default agent, and later return to the same workspace with those objects still organized together.

### 4.2 Non-Goals

Phase 1 does not include:

- vector search over all workspace sources
- full document ingestion pipelines
- OCR
- source quality scoring
- multi-user permissions
- cloud storage
- deep research job orchestration
- automatic workflow/runbook generation
- a new file permission model

### 4.3 Data Model

Add a `workspaces` table.

Suggested fields:

```text
id: string primary key
name: string not null
description: text nullable
default_agent_id: string nullable
source_policy_json: text not null default "{}"
created_at: datetime
updated_at: datetime
```

`source_policy_json` is not a permission boundary. It can store workspace-level preferences such as default source inclusion mode, preferred source types, or citation strictness.

Add `workspace_id` to `sessions`.

Suggested behavior:

- nullable for backward compatibility
- indexed for workspace chat listing
- existing sessions remain unassigned until explicitly moved
- new sessions created from an active workspace inherit that workspace id

Add `workspace_sources`.

Suggested fields:

```text
id: string primary key
workspace_id: string not null
source_type: string not null
source_ref: string not null
display_name: string not null
metadata_json: text not null default "{}"
status: string not null default "registered"
created_at: datetime
updated_at: datetime
```

Initial `source_type` values:

- `upload`
- `local_doc_root`
- `local_file`
- `note`
- `chat`

Initial `status` values:

- `registered`
- `ready`
- `unavailable`
- `error`

Phase 1 only needs coarse status. Phase 2 will expand readiness semantics.

Add `workspace_artifacts`.

Suggested fields:

```text
id: string primary key
workspace_id: string not null
artifact_type: string not null
title: string not null
source_session_id: string nullable
source_message_id: integer nullable
action_state_id: integer nullable
artifact_path: string nullable
content_ref: string nullable
metadata_json: text not null default "{}"
created_at: datetime
updated_at: datetime
```

Initial `artifact_type` values:

- `export`
- `tool_output`
- `research_report`
- `generated_file`
- `preview`

Migrate Notebook storage to support workspace association.

Recommended implementation:

- introduce a database-backed `notes` table
- include `workspace_id` as nullable for backward compatibility
- keep a one-time import path from existing `notes.json`
- preserve the existing `/api/notebook` behavior for global listing during transition

Suggested note fields:

```text
id: string primary key
workspace_id: string nullable
title: string not null
content: text not null
source_session_id: string nullable
source_message_id: integer nullable
source_refs_json: text not null default "[]"
created_at: datetime
updated_at: datetime
```

### 4.4 Backend API

Add workspace CRUD endpoints.

```text
GET /api/workspaces
POST /api/workspaces
GET /api/workspaces/{workspace_id}
PUT /api/workspaces/{workspace_id}
DELETE /api/workspaces/{workspace_id}
```

Delete behavior for Phase 1:

- soft-delete is preferred if the project already has a pattern for it
- otherwise block deletion when the workspace still has chats/sources/artifacts unless `force=true`
- do not delete physical uploaded files in Phase 1 unless a clear lifecycle rule is implemented

Add workspace object listing endpoints.

```text
GET /api/workspaces/{workspace_id}/sessions
GET /api/workspaces/{workspace_id}/sources
POST /api/workspaces/{workspace_id}/sources
DELETE /api/workspaces/{workspace_id}/sources/{source_id}
GET /api/workspaces/{workspace_id}/artifacts
POST /api/workspaces/{workspace_id}/artifacts
GET /api/workspaces/{workspace_id}/notes
```

Extend chat creation and streaming request flow.

Required behavior:

- allow `workspace_id` on chat creation or first chat stream request
- persist `workspace_id` on the `Session`
- if the request has attachments and a workspace id, register those attachments as workspace sources
- if the workspace has `default_agent_id` and no request-level agent is selected, use the workspace default agent
- include active workspace source summary in the prompt context only when the request is workspace-scoped

Extend upload flow minimally.

Options:

- add optional `workspace_id` to `/api/files`
- or keep `/api/files` unchanged and register uploaded attachments as workspace sources during chat submission

Recommended Phase 1 choice:

- register during chat submission first, because the current upload API is already stable and chat submission already knows whether the message belongs to a workspace

### 4.5 Runtime And Prompt Behavior

Phase 1 prompt context should be small and structured.

Include:

- active workspace name
- active workspace description if present
- default agent id/name if present
- count and type summary of registered sources
- current turn attachments
- clear instruction that local file access still follows global `doc_access`

Do not include:

- full file trees
- full PDF text
- full Excel data
- all note bodies
- all chat transcripts

The model should be told that workspace sources are available through tools or explicit references, not pasted wholesale into context.

### 4.6 Frontend UX

Add a workspace switcher.

Minimum behavior:

- visible from Chat and Notebook
- supports create, rename, switch
- shows current workspace name
- supports "No workspace" or "General" fallback for old/global chats

Update chat history.

Minimum behavior:

- filter chats by current workspace
- show unassigned chats in a global or legacy area
- allow starting a new chat inside current workspace
- optionally allow moving a chat into a workspace

Add workspace source panel.

Minimum behavior:

- list workspace sources grouped by type
- show display name, type, status, and last updated time
- allow removing a source registration
- allow adding a local document root reference from already-authorized `doc_access` roots
- show uploaded attachments that were registered from chat

Update Notebook.

Minimum behavior:

- show workspace notes when a workspace is active
- allow creating notes inside the active workspace
- preserve access to existing global notes during migration

Add artifact list.

Minimum behavior:

- show generated outputs and export records attached to workspace
- link back to originating chat or action when possible
- show artifact path/download link when available

### 4.7 Acceptance Criteria

Phase 1 is complete when:

- a user can create, rename, list, and switch workspaces
- new chats started inside a workspace persist `workspace_id`
- chat history can be filtered by workspace
- a workspace can define a default agent and new workspace chats use it when no explicit agent is selected
- uploaded attachments from workspace-scoped chats are registered as workspace sources
- notes can be created and listed within a workspace
- generated/exported artifacts can be listed under a workspace
- active workspace context is included in prompt assembly without injecting large source contents
- workspace source references cannot bypass global `doc_access`
- existing chats and notes remain accessible after migration

### 4.8 Verification

Backend unit tests:

- workspace CRUD service tests
- session `workspace_id` persistence tests
- source registration tests for uploaded attachments
- note migration and workspace note listing tests
- artifact registration tests

Backend API tests:

- workspace CRUD endpoints
- workspace-scoped chat creation
- workspace-scoped source listing
- default agent fallback behavior

Frontend tests:

- workspace switcher create/switch flow
- chat history filtering
- workspace note creation
- source panel renders uploaded attachment registration

Manual smoke test:

1. Create workspace "Client Research".
2. Set default agent to PDF Research.
3. Upload a PDF in a new chat inside the workspace.
4. Confirm the chat appears under the workspace.
5. Confirm the PDF appears in workspace sources.
6. Create a workspace note.
7. Generate or export an answer.
8. Confirm the output appears in workspace artifacts.
9. Restart backend and confirm all objects still appear.

### 4.9 Phase 1 Risks

Data model sprawl:

Keep `workspace_sources` and `workspace_artifacts` generic but not abstract to the point of meaninglessness. Store stable type fields and structured metadata.

Permission confusion:

Never describe workspace roots as authorization. They are source preferences only.

Notebook migration risk:

Preserve existing `notes.json` import and avoid destructive migration in the first pass.

Attachment lifecycle ambiguity:

Phase 1 may register files without deleting them. Document that file garbage collection is a later lifecycle task.

## 5. Phase 2: Source Readiness And Evidence Workflows

### 5.1 Goal

Upgrade Source Workspace from "objects are grouped together" to "sources are reliably usable, selectable, traceable, and evidence-backed."

Phase 2 is successful when users can see whether sources are ready, choose which sources to use for a task, ask grounded questions with citations, and save structured research outputs back into the workspace.

### 5.2 Non-Goals

Phase 2 does not include:

- full autonomous long-running background agent board
- arbitrary web research
- full multi-user ACLs
- global long-term memory across all workspaces
- automatic runbook extraction
- universal document parser coverage

### 5.3 Source Readiness Model

Expand `workspace_sources.status`.

Recommended statuses:

- `registered`
- `checking`
- `ready`
- `needs_permission`
- `unsupported_type`
- `parse_failed`
- `too_large`
- `missing`
- `stale`

Add readiness metadata.

Suggested `metadata_json` fields:

```json
{
  "mime_type": "application/pdf",
  "extension": ".pdf",
  "size_bytes": 12345,
  "storage_path": "uploads/chat/...",
  "doc_access_checked_at": "2026-05-30T00:00:00Z",
  "last_ready_at": "2026-05-30T00:00:00Z",
  "readiness_error_code": null,
  "readiness_error_message": null,
  "available_tools": ["docs_read", "docs_search"],
  "citation_capable": true
}
```

Add a readiness checker service.

Responsibilities:

- validate source type
- validate storage path or local path shape
- validate global `doc_access` for local documents
- detect whether existing tools can read the source
- return structured readiness result
- avoid reading large source contents unless a tool requires a lightweight probe

### 5.4 Source Picker

Add a workspace source picker for chat and research flows.

Minimum behavior:

- default to all ready workspace sources
- allow selecting a subset for the current request
- allow excluding unsupported or failed sources
- show readiness badges
- persist the selected source ids in request trace metadata

Backend request extension:

```text
selected_workspace_source_ids: list[string] | null
workspace_source_mode: "all_ready" | "selected" | "none"
```

Runtime behavior:

- when `selected`, only selected sources are included in the source summary
- when `all_ready`, all ready sources are eligible
- when `none`, workspace identity remains active but sources are not used

### 5.5 Grounded Answer Mode

Add workspace-level and request-level grounded answer settings.

Suggested modes:

- `normal`: workspace context is helpful but not mandatory
- `prefer_sources`: answer should use workspace sources when relevant
- `require_sources`: answer must cite workspace sources or state that evidence is insufficient

Prompt behavior:

- in `prefer_sources`, prioritize workspace sources and cite when used
- in `require_sources`, do not answer unsupported factual claims from general model knowledge when the user asks about workspace materials
- if selected sources are insufficient, produce an insufficiency response with missing evidence needs

Output behavior:

- citations should identify source id, display name, locator, and snippet when available
- unsupported claims should be minimized in grounded modes

### 5.6 Research Artifact

Introduce a first-class research artifact type under `workspace_artifacts`.

Suggested artifact payload:

```json
{
  "question": "What are the main risks in these contracts?",
  "source_ids": ["src_1", "src_2"],
  "mode": "require_sources",
  "summary": "...",
  "findings": [
    {
      "claim": "...",
      "evidence": [
        {
          "source_id": "src_1",
          "locator": "page 4",
          "snippet": "..."
        }
      ],
      "confidence": "medium"
    }
  ],
  "open_questions": ["..."],
  "export_paths": []
}
```

Phase 2 can generate research artifacts from a normal chat action before adding a full long-running job system.

Minimum UX:

- "Save as research artifact" action on assistant responses
- artifact detail view in workspace
- link back to source chat and selected sources
- export to Markdown or DOCX when export support is available

### 5.7 Source-To-Note

Add structured note capture from workspace sources and assistant responses.

Minimum behavior:

- save selected assistant response as workspace note
- include source chat backlink
- include source ids and citation refs
- optionally generate title and tags using existing meta model settings

This is the bridge between workspace evidence and durable knowledge capture.

### 5.8 Workspace Memory

Add workspace-scoped memory only after source readiness and grounded answer behavior are stable.

Initial memory card types:

- `project_fact`
- `decision`
- `preference`
- `term`
- `open_question`

Rules:

- memory is scoped to one workspace
- memory writes require explicit user action or visible review
- memory cards retain source refs when derived from chat or documents
- memory cards can be disabled per workspace

This avoids prematurely introducing global memory behavior while still making each workspace improve over time.

### 5.9 API Additions

Readiness:

```text
POST /api/workspaces/{workspace_id}/sources/{source_id}/check
POST /api/workspaces/{workspace_id}/sources/check
```

Grounded chat request extensions:

```text
workspace_source_mode
selected_workspace_source_ids
grounding_mode
```

Artifacts:

```text
POST /api/workspaces/{workspace_id}/research-artifacts
GET /api/workspaces/{workspace_id}/research-artifacts
GET /api/workspaces/{workspace_id}/research-artifacts/{artifact_id}
```

Notes:

```text
POST /api/workspaces/{workspace_id}/notes/from-message
POST /api/workspaces/{workspace_id}/notes/from-source
```

Memory:

```text
GET /api/workspaces/{workspace_id}/memory
POST /api/workspaces/{workspace_id}/memory
PUT /api/workspaces/{workspace_id}/memory/{memory_id}
DELETE /api/workspaces/{workspace_id}/memory/{memory_id}
```

Memory endpoints may be deferred until the end of Phase 2.

### 5.10 Frontend UX

Source readiness panel:

- show status per source
- allow retry readiness check
- show concise error reason
- show tool capability labels such as PDF, Excel, citation-capable, searchable

Source picker:

- accessible from chat composer
- supports all ready, selected, and none
- warns when selected sources are not ready
- keeps selection visible as a small source strip

Grounded mode control:

- workspace setting for default grounding mode
- request-level override in composer or research panel
- visible citation requirement state in responses

Research artifact view:

- list research artifacts in workspace
- detail view with findings, evidence, open questions, source list, and export actions
- link back to originating chat

Source-to-note:

- message action to save as note
- optional generated title
- note includes source refs and backlinks

### 5.11 Acceptance Criteria

Phase 2 is complete when:

- each workspace source has a visible readiness status
- failed sources show actionable reasons
- users can choose all ready sources, selected sources, or no sources for a chat request
- selected source ids are preserved in request trace metadata
- grounded answer mode can require citations from workspace sources
- insufficient evidence is surfaced instead of unsupported confident answers in require-sources mode
- assistant responses can be saved as research artifacts with source ids and citations
- assistant responses can be saved as workspace notes with backlinks
- readiness checks respect global `doc_access`
- source status survives backend restart

### 5.12 Verification

Backend tests:

- readiness checker for upload, local file, local root, note, and unsupported type
- doc access denial maps to `needs_permission`
- selected source ids are accepted and persisted in trace/request snapshot
- grounded mode prompt assembly differs across `normal`, `prefer_sources`, and `require_sources`
- research artifact creation validates workspace and source ids
- source-to-note preserves backlinks and source refs

Frontend tests:

- source readiness panel renders statuses and retry action
- source picker updates request payload
- grounded mode control updates request payload
- research artifact list and detail render evidence
- save-to-note from message creates workspace note

Manual smoke test:

1. Open a workspace with one PDF, one Excel file, and one unsupported file.
2. Run readiness check.
3. Confirm PDF/Excel become ready and unsupported file shows a reason.
4. Select only the PDF and ask a grounded question requiring citations.
5. Confirm the answer cites the PDF or reports insufficient evidence.
6. Save the answer as a research artifact.
7. Save a paragraph as a workspace note.
8. Restart backend and confirm statuses, artifact, and note remain.

### 5.13 Phase 2 Risks

Citation quality:

Different tools return different evidence shapes. Phase 2 should normalize citation display enough for UX consistency without forcing every tool into a perfect citation model.

Over-promising grounded behavior:

The product should distinguish "requires workspace evidence" from "guaranteed exhaustive truth." The UI and prompt should use evidence language carefully.

Readiness cost:

Readiness checks should be lightweight. Heavy parsing or indexing belongs behind explicit actions or later background jobs.

Memory write quality:

Workspace memory should stay reviewed and source-linked. Avoid silent memory writes in Phase 2.

## 6. Recommended Sequencing

Recommended delivery order:

1. Phase 1 data model and migrations
2. workspace CRUD API
3. session workspace association
4. source and artifact registries
5. notebook workspace migration
6. workspace switcher and chat filtering
7. source panel and artifact list
8. prompt summary for active workspace
9. Phase 2 readiness checker
10. source picker
11. grounded answer mode
12. research artifact capture
13. source-to-note
14. workspace-scoped memory cards

## 7. Open Questions

- Should old unassigned chats appear under a built-in "General" workspace or remain outside all workspaces?
- Should workspace deletion be soft-delete from the start?
- Should uploaded files be registered to a workspace at upload time or only when sent in a workspace chat?
- Should workspace default agent override global preference only for new chats, or also for existing workspace chats with no agent selected?
- Should Phase 2 readiness checks run automatically after registration or only when the user opens the source panel?

## 8. Dependencies

Primary dependencies:

- global document access behavior must remain authoritative
- attachment upload and message persistence must stay stable
- chat prompt assembly must accept compact workspace context
- notebook storage needs a migration path from JSON to database
- artifact registration should reuse action observability where possible

Related docs:

- `docs/plans/2026-05-30-ai-workbench-opportunity-roadmap.md`
- `docs/plans/2026-04-19-chat-attachment-file-support-execution-plan.md`
- `docs/plans/2026-04-30-global-document-access-unification-implementation-plan.md`
- `docs/plans/File_Management_Improvement_Review.md`
