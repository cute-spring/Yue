task statement: Lane B Stage 4-Lite final convergence gap fill for hybrid import mutation gate behavior consistency.
desired outcome: Add one minimal valuable TDD-covered matrix case in allowed files only, with failing test first and minimal fix only if needed.
known facts/evidence:
- User restricted writes to 4 files.
- runtime_catalog.py exposes runtime mode/convergence strategy helpers.
- Existing tests cover some legacy/import-gate strict paths and hybrid refresh behavior.
- Worktree is dirty; must not revert or disturb unrelated changes.
constraints:
- Strict TDD RED->GREEN->REFACTOR.
- Minimal change.
- No edits outside allowed files.
- Focus on legacy/import-gate + strict/default hybrid combinations for import mutation gate consistency.
unknowns/open questions:
- Exact uncovered matrix cell.
- Whether gap can be filled test-only or needs runtime_catalog change.
likely codebase touchpoints:
- backend/tests/test_api_skill_imports.py
- backend/tests/test_import_gate_lifespan_smoke.py
- backend/tests/test_skill_runtime_catalog_unit.py
- backend/app/services/skills/runtime_catalog.py
