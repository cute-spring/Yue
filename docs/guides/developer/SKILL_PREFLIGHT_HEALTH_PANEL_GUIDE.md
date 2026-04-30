# Skill Preflight And Health Panel Guide

## Purpose

This guide explains the new preflight + health workflow for copied skill packages:

- Auto-discover copied packages at startup
- Classify skill status as `available`, `needs_fix`, or `unavailable`
- Show actionable diagnostics in UI
- Mount available skills to default agent with one click

## Backend Flow

At startup, runtime preflight scans layered skill directories:

- Builtin
- Workspace
- User

Each discovered package generates a preflight record in `SkillImportStore`.

Preflight records include:

- Skill identity (`skill_name`, `skill_version`, `skill_ref`)
- Source metadata (`source_path`, `source_layer`)
- Health status (`status`)
- Diagnostics (`issues`, `warnings`, `suggestions`)
- Actionability (`mountable`, `status_message`, `next_action`)
- Visibility (`visible_in_default_agent`)

## API Endpoints

### List preflight records

- `GET /api/skill-preflight`
- Query params:
  - `status` (`available|needs_fix|unavailable`)
  - `skill_name`
  - `source_layer`

### Get one preflight record

- `GET /api/skill-preflight/{skill_ref}`

### Mount a preflighted skill

- `POST /api/skill-preflight/{skill_ref}/mount`
- Request body:

```json
{
  "agent_id": "builtin-action-lab"
}
```

If `agent_id` is omitted, backend mounts to `builtin-action-lab`.

### Mount error payload

Non-2xx mount responses now return actionable structured detail:

```json
{
  "detail": {
    "code": "skill_preflight_not_mountable",
    "message": "Skill is not mountable until preflight issues are resolved.",
    "next_action": "Resolve listed issues, then rerun preflight."
  }
}
```

## Frontend Integration

A dedicated page is available at:

- `/skill-health`

Current UI behavior:

- Filter by status, source layer, and keyword
- Display diagnostics (`issues`, `warnings`, `suggestions`)
- Distinguish:
  - Availability (`available|needs_fix|unavailable`)
  - Visibility in default agent (`visible_in_default_agent`)
- Render actionable status copy (`status_message`, `next_action`)
- Execute one-click mount for `available` skills

## Action Observability (Excalidraw)

For skill action troubleshooting, `/api/chat/{chat_id}/actions/states` now exposes
stable observability fields (besides raw `payload` passthrough):

- `observability.started_at`
- `observability.finished_at`
- `observability.duration_ms`
- `observability.error_kind`
- `observability.retryable`
- `observability.artifact_path`

For Excalidraw-related failures, UI action detail cards prioritize this structured
`observability` block so operators can quickly identify retryability and artifact location.

## Verification Commands

Backend:

```bash
cd backend
PYTHONPATH=. pytest tests/test_api_skill_preflight.py -q
```

Frontend:

```bash
cd frontend
npm run test -- src/pages/SkillHealth.test.ts
npm run build
```

## Troubleshooting

- `skill_preflight_not_found`:
  - Check startup preflight scanning and `skill_ref`.
- `skill_preflight_not_mountable`:
  - Resolve preflight issues first, then retry mount.
- `agent_not_found`:
  - Ensure target agent exists.
- `agent_store_unavailable`:
  - Verify host adapter wiring in runtime bootstrap.
