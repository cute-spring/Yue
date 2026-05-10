# Skill Preflight And Health Panel Guide

## Purpose

This guide explains the new preflight + health workflow for copied skill packages:

- Auto-discover copied packages at startup
- Classify skill status as `available`, `needs_fix`, or `unavailable`
- Show actionable diagnostics in UI
- Import local skill directories from the Skill Health page
- Auto-mount newly imported healthy skills to `Skill Playground`
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

Healthy imports can also be auto-mounted to the default playground agent:

- Agent id: `builtin-action-lab`
- Display name: `Skill Playground`

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

### Import a local skill directory

- `POST /api/skill-imports`
- Request body:

```json
{
  "source_type": "directory",
  "source_path": "/absolute/path/to/skill-directory"
}
```

Successful responses now surface explicit default-agent mount details:

```json
{
  "import": {
    "skill_name": "fireworks-tech-graph",
    "skill_version": "1.0.0",
    "lifecycle_state": "active"
  },
  "report": {
    "activation_eligibility": "compatible",
    "default_agent_mount_status": "mounted",
    "default_agent_mount_target_agent_id": "builtin-action-lab",
    "default_agent_mount_message": "Skill was auto-mounted to Skill Playground (builtin-action-lab)."
  },
  "default_agent_mount": {
    "status": "mounted",
    "target_agent_id": "builtin-action-lab",
    "message": "Skill was auto-mounted to Skill Playground (builtin-action-lab)."
  }
}
```

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
- Import a local skill directory from the `Install Skill` entrypoint
- Show workspace-backed install suggestions without requiring manual path entry
- Render suggestion status badges (`Available`, `Needs Fix`, `Unavailable`)
- Warn when a selected suggestion is not healthy, including the current issue summary
- Let operators jump from the warning notice to the exact preflight record (`Show record`)
- Scroll and briefly highlight the target record after jump
- Display diagnostics (`issues`, `warnings`, `suggestions`)
- Distinguish:
  - Availability (`available|needs_fix|unavailable`)
  - Visibility in default agent (`visible_in_default_agent`)
- Render actionable status copy (`status_message`, `next_action`)
- Show import success notices that include `Skill Playground` auto-mount results
- Execute one-click mount for `available` skills

## Regression Checklist

When changing skill import, preflight serialization, or the Skill Health page, verify:

- `Install Skill` still accepts a local absolute path and posts to `POST /api/skill-imports`
- successful import still shows the `Skill Playground` auto-mount message
- successful import still triggers a rescan and shows the newly imported record
- workspace suggestions still render for workspace preflight records only
- `Needs Fix` and `Unavailable` suggestions still show warning copy before import
- `Show record` still jumps to the matching preflight card
- the jumped-to card still receives temporary highlight styling
- `available` records remain mountable and `needs_fix` records remain blocked

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
npm run test:e2e -- skill-health-visual.spec.ts --grep "workspace suggestion warns and jumps to highlighted record for needs-fix skill"
npm run test:e2e -- skill-health-visual.spec.ts --grep "install flow shows auto-mount success notice and refreshes records"
npm run build
```

## Troubleshooting

- `skill_preflight_not_found`:
  - Check startup preflight scanning and `skill_ref`.
- `skill_preflight_not_mountable`:
  - Resolve preflight issues first, then retry mount.
- `import_source_not_found`:
  - Verify the selected local path exists and points to a skill directory.
- `agent_not_found`:
  - Ensure target agent exists.
- `agent_store_unavailable`:
  - Verify host adapter wiring in runtime bootstrap.
