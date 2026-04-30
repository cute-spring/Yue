# Ralph Context Snapshot: Global Document Access Unification

## Task Statement
Implement the first batch from `docs/plans/2026-04-30-global-document-access-unification-implementation-plan.md`, prioritizing Phase 2 and Phase 3 for targeted builtin file/document tools.

## Desired Outcome
- Docs and Excel/CSV builtin tools use global `doc_access.allow_roots` / `doc_access.deny_roots` as the only permission authority.
- Settings updates affect the next tool call immediately.
- `doc_access` persists across service restart.
- `root_dir` is only a query scope selector and invalid `root_dir` returns structured errors.
- Multiple allowed roots are searched/listed by default.
- Relative reads with duplicate files under multiple allowed roots fail with explicit ambiguity.
- Empty `allow_roots` fails closed.
- `exec` behavior is unchanged.

## Known Facts / Evidence
- Current docs builtin helpers still accept request `doc_roots` from context and fallback when `root_dir` is invalid.
- Current `doc_retrieval.resolve_docs_roots_for_search` defaults to project docs if `allow_roots` is absent/empty.
- Current `resolve_docs_root_for_read` chooses first matching relative path instead of reporting ambiguity.
- Current Excel service path resolution already delegates to `doc_retrieval`, but inherits its default/fallback semantics.
- `ConfigService.update_doc_access` updates memory and persists via `update_config`.
- Worktree has many unrelated modified/untracked files; protect them.

## Constraints
- Use TDD: write/adjust tests before production code.
- Keep implementation small and focused on backend docs/Excel/config/doc_retrieval paths.
- Do not modify builtin `exec`.
- Do not inject `deny_roots` into prompts.
- Do not rollback unrelated user changes.

## Unknowns / Open Questions
- Prompt injection coverage may be in chat prompting tests outside this first backend tool slice.
- Full frontend agent directory-control cleanup is outside the stated Phase 2/3 priority unless tests expose a direct blocker.

## Likely Codebase Touchpoints
- `backend/app/services/doc_retrieval.py`
- `backend/app/mcp/builtin/docs.py`
- `backend/app/mcp/builtin/excel.py`
- `backend/app/services/excel_service.py`
- `backend/app/services/config_service.py`
- `backend/tests/test_doc_retrieval.py`
- `backend/tests/test_docs_builtin.py`
- `backend/tests/test_excel_service.py`
- `backend/tests/test_config_service_unit.py`
