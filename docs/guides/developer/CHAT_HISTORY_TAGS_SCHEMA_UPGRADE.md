# Chat History Tags Schema Upgrade Guide

This guide explains how to move existing environments to the chat-history tags version released on **April 10, 2026**.

## Scope of this upgrade
- Adds `sessions.tags_json` column.
- Enables chat history filters:
  - `tags`
  - `tag_mode` (`any` / `all`)
  - `date_from`
  - `date_to`
- Adds tag generation endpoint:
  - `POST /api/chat/{chat_id}/tags/generate`
- Adds Phase 3 filter preference sync:
  - persisted keys in `/api/config/preferences`:
    - `chat_history_filter_state`
    - `chat_history_filter_presets`

## 1. Pre-upgrade checklist
1. Stop backend writers (or pause traffic).
2. Back up database.
3. Pull latest code and install dependencies.

## 2. Backup
### SQLite (default)
```bash
cp ~/.yue/data/yue.db ~/.yue/data/yue.db.bak-2026-04-10
```

### External DB
Use your standard snapshot tooling before migration (for example `pg_dump` for PostgreSQL).

## 3. Apply schema migration
From repo root:
```bash
cd backend
alembic upgrade head
```

Expected result: latest revision includes `2f9a751c3e1d_add_session_tags_json`.

## 4. Backfill tags for historical sessions
Run once after schema upgrade:
```bash
PYTHONPATH=backend python backend/scripts/backfill_session_tags.py
```

What it does:
- Scans sessions.
- Generates tags for sessions with empty/missing tags.
- Prints updated session IDs and tag sets.

## 5. Verification
### API smoke checks
```bash
curl -s "http://localhost:8000/api/chat/history" | head
curl -s "http://localhost:8000/api/chat/history?tags=api&tag_mode=any" | head
```

### Functional checks
1. Open chat UI sidebar.
2. Confirm tag chips appear on session items.
3. Confirm tag/date filters change visible history.

## 6. Rollback
If you must roll back code:
1. Restore database from backup.
2. Redeploy previous backend/frontend versions.

Note: downgrading DB without restore can drop `tags_json` and lose generated tags.

## 7. Operator notes
- `tags_json` stores normalized tags (lowercase, kebab-case, deduped).
- Tag generation is best-effort and can be re-run safely using:
  - `POST /api/chat/{chat_id}/tags/generate`
  - or the bulk backfill script above.
- Phase 3 preference data is optional UI metadata and does not require schema migrations.
