# 01 - Establish built-in workbench mode contract

**What to build:** A shared Yue product/runtime contract for built-in workbench modes: visible entry points, shortcut metadata, artifact output expectations, safety labels, and tests proving the six capabilities can be represented consistently.

**Blocked by:** None - can start immediately.

**Status:** resolved

- [x] The six built-in capabilities can be represented through one shared workbench mode contract.
- [x] Each mode can declare visible entry points, optional shortcuts, expected outputs, and safety boundaries.
- [x] The contract preserves Yue's product boundary as a trusted AI workbench and skill runtime platform.
- [x] Tests prove all six roadmap capabilities can be loaded or enumerated through the shared contract.
- [x] The contract does not require implementing the individual capability workflows yet.

## Answer

Implemented a contract-only built-in workbench mode catalog for the six Yue roadmap capabilities.

The backend now loads built-in mode definitions from `backend/data/builtin/workbench_modes/` through `WorkbenchModeCatalog`. Each mode declares its visible entry points, shortcut metadata, expected outputs, artifact durability and provenance expectations, safety labels, safety boundaries, runtime routing policy, source spec links, suggested phase, and product boundary. All six definitions use `workflow_status: contract_only`, so issue 01 establishes the representation without implementing the individual workflows.

The contract is exposed through `GET /api/workbench-modes` and `GET /api/workbench-modes/{mode_id}` for future product surfaces.

Validation:

- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_workbench_mode_catalog.py tests/test_api_workbench_modes_unit.py -q` - 8 passed.
- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_builtin_agent_catalog.py tests/test_builtin_jira_agent.py tests/test_api_workbench_modes_unit.py tests/test_workbench_mode_catalog.py -q` - 14 passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q app/services/workbench_mode_catalog.py app/api/workbench_modes.py` - passed.
- `git diff --check` - passed.

Broad backend suite note:

- `PYTHONPATH=. .venv/bin/python -m pytest -q` completed with 1117 passed, 8 skipped, and 14 failures.
- The failures are all in `tests/test_chat_stream_runner_unit.py` and assert older event ordering where skill-effectiveness events appear before the newer `trace.event` payloads. They are not related to the workbench mode catalog or API route.
