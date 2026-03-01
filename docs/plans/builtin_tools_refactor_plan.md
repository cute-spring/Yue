# Built-in Tools Refactor Plan

## 1) Goal
- Refactor the current built-in tools implementation to decouple them from `McpManager`, improve directory structure, and provide a scalable registry for future tools.

## 2) Contract (Public)
- Entry points:
    - `backend/app/mcp/builtin/registry.py`: Main entry point for discovering and getting built-in tools.
    - `McpManager.get_available_tools()`: Will now call the new registry.
    - `ToolRegistry.get_tools_for_agent()`: Will now call the new registry.
- Inputs/schema: No changes to existing tool schemas to maintain compatibility.
- Outputs (success): Same as before (strings or JSON strings).
- Outputs (error, protocol shape): Standardized error payload `{error_code, message, hint}`.

## 3) Invariants
- Compatibility: Tool names (`exec`, `docs_list`, etc.) and their parameters must remain identical.
- Ordering/IDs: Tool IDs must remain `builtin:<name>`.
- Security boundaries: Existing guards (path checks, command patterns) must be preserved or strengthened.

## 4) Risks & Mitigations
- Security: Moving `ExecTool` and `doc_retrieval` logic must not accidentally bypass existing path/command guards.
    - Mitigation: Reuse existing guard logic and add unit tests specifically for these guards in the new structure.
- Performance/timeouts: Refactoring shouldn't introduce overhead.
    - Mitigation: Ensure logic remains as direct as possible.
- Rollback:
    - Mitigation: Keep the refactor in atomic steps. Can revert to previous `McpManager` implementation if needed.

## 5) Step Plan (Test-Gated)
- [ ] Step 1: Infrastructure Setup
    - Create `backend/app/mcp/builtin/` directory.
    - Create `backend/app/mcp/builtin/base.py` (inheriting from `mcp/base.py`).
    - Create `backend/app/mcp/builtin/registry.py`.
    - Tests: `pytest backend/tests/test_mcp_builtin_registry.py` (new test).
- [ ] Step 2: Migrate `ExecTool`
    - Move `backend/app/mcp/exec_tool.py` logic to `backend/app/mcp/builtin/exec.py`.
    - Update to use new base class and registry.
    - Tests: `pytest backend/tests/test_exec_tool.py`.
- [ ] Step 3: Migrate `doc_retrieval` tools
    - Create `backend/app/mcp/builtin/docs.py`.
    - Move `docs_list`, `docs_search`, etc. implementations from `McpManager` to `docs.py`.
    - Tests: `pytest backend/tests/test_doc_retrieval.py`.
- [ ] Step 4: Migrate other tools
    - Create `backend/app/mcp/builtin/system.py` (`get_current_time`).
    - Create `backend/app/mcp/builtin/ppt.py` (`generate_pptx`).
    - Tests: `pytest backend/tests/test_mcp_manager_unit.py`.
- [ ] Step 5: Integration & Cleanup
    - Update `McpManager` to delegate to `BuiltinToolRegistry`.
    - Update `backend/app/mcp/registry.py`.
    - Remove old implementations from `McpManager`.
    - Tests: Full regression suite.

## 6) Status Log
### 2026-03-01
- Initial plan created.
- Goal: Decouple built-in tools from `McpManager`.
- Step 1: Infrastructure Setup (completed)
- Step 2: Migrate `ExecTool` (completed)
- Step 3: Migrate `doc_retrieval` tools (completed)
- Step 4: Migrate other tools (completed)
- Step 5: Integration & Cleanup (completed)
- All tests passed. Refactor complete.
 
## 7) Phase 2 Improvements (Test-Gated)
- [ ] Step A: ExecTool allowlist enforcement
  - Tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_base_tool_unit.py`
  - Rollback: Revert `ExecTool._guard_command` allowlist logic.
- [ ] Step B: Built-in registry deterministic order
  - Tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_mcp_builtin_registry.py`
  - Rollback: Revert registry ordering change.
- [ ] Step C: Update tests for new module path
  - Tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_base_tool_unit.py`
  - Rollback: Revert test updates.

## 8) Status Log (Phase 2)
### 2026-03-01
- Step A: completed | change: allowlist enforced in ExecTool | tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_base_tool_unit.py backend/tests/test_mcp_builtin_registry.py` ✅
- Step B: completed | change: deterministic builtin registry ordering | tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_mcp_builtin_registry.py` ✅
- Step C: completed | change: update tests for builtin exec module path | tests: `export PYTHONPATH=$PYTHONPATH:$(pwd)/backend && pytest backend/tests/test_base_tool_unit.py` ✅
