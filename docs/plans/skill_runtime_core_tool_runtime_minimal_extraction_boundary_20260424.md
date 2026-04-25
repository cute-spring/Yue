# Skill Runtime Core + Tool Runtime Minimal Extraction Boundary

**Date**: 2026-04-24  
**Status**: Draft (next-batch baseline)  
**Scope**: define the smallest practical file boundary for reusing runtime core with MCP/builtin tools in another project.

## 1. Goal

Keep extraction low-risk and incremental:

1. split reusable runtime logic from tool execution infrastructure
2. preserve current `builtin:*` authorization model
3. avoid forcing host projects to copy Yue app startup/API internals

This draft is intentionally minimal and optimized for copy-first reuse.

## 2. Package Split (Minimal)

### 2.1 Package A: `skill-runtime-core`

Owns skill-domain runtime behavior and host contracts.  
No direct dependency on Yue API modules or app startup wiring.

**Include now**

- `backend/app/services/skills/models.py`
- `backend/app/services/skills/parsing.py`
- `backend/app/services/skills/import_models.py`
- `backend/app/services/skills/import_store.py`
- `backend/app/services/skills/import_service.py`
- `backend/app/services/skills/policy.py`
- `backend/app/services/skills/directories.py`
- `backend/app/services/skills/registry.py`
- `backend/app/services/skills/runtime_catalog.py`
- `backend/app/services/skills/runtime_seams.py`
- `backend/app/services/skills/actions.py`
- `backend/app/services/skills/routing.py`

**Include with small cleanup**

- `backend/app/services/skills/host_adapters.py`
- `backend/app/services/skills/compatibility.py`

Cleanup target for `compatibility.py`:
- replace implicit `app.mcp.builtin` lookup with injected tool-id provider or explicit supported-tool list.

### 2.2 Package B: `skill-tool-runtime`

Owns tool transport/execution and tool metadata registry.

**Include now**

- `backend/app/mcp/base.py`
- `backend/app/mcp/models.py`
- `backend/app/mcp/schema_translator.py`
- `backend/app/mcp/manager.py`
- `backend/app/mcp/registry.py`
- `backend/app/mcp/builtin/registry.py`
- `backend/app/mcp/builtin/exec.py`
- `backend/app/mcp/builtin/docs.py`
- `backend/app/mcp/builtin/system.py`
- `backend/app/mcp/builtin/ppt.py`
- `backend/app/mcp/builtin/excel.py`
- `backend/app/mcp/builtin/__init__.py`

## 3. Host/Adapter Layer (Do Not Put in Either Core Package)

Host-specific composition and APIs stay outside the two reusable packages.

**Keep host-local**

- `backend/app/main.py`
- `backend/app/api/skills.py`
- `backend/app/api/skill_imports.py`
- `backend/app/api/skill_groups.py`
- `backend/app/services/skill_service.py`
- `backend/app/services/skills/bootstrap.py` (transitional today; keep host-owned until route strategy is fully packageized)
- `backend/app/services/skills/adapters.py`
- `backend/app/services/skills/__init__.py` (current mixed barrel)

## 4. Bridge Contract Between A and B

Minimal stable integration contract:

1. runtime core consumes tool ids (`builtin:*`, `server:tool`) as opaque strings
2. runtime core does not import concrete MCP/builtin modules
3. host wiring provides:
   - tool metadata provider (`list_available_tool_ids` / equivalent)
   - tool execution registry for chat/runtime invocation path

Practical near-term bridge in Yue:

- keep `builtin:*` ids unchanged
- inject supported tool ids into `SkillCompatibilityEvaluator(...)`
- keep authorization intersection in runtime policy (`enabled_tools` ∩ `allowed_tools`) unchanged

## 5. Migration Sequence (Minimal Batchable)

1. freeze the file boundary in docs (this draft)
2. decouple `compatibility.py` from `app.mcp.builtin` by dependency injection
3. add a thin composition module in host layer that wires:
   - `skill-runtime-core`
   - `skill-tool-runtime`
4. move `bootstrap.py` from transitional host module to package-level reusable bootstrap only after route strategy cleanup

## 6. Non-Goals (for this boundary draft)

- no runtime hot-import
- no per-user dynamic tool visibility model
- no plugin marketplace/runtime dynamic loading
- no rewrite of current `builtin:*` tool naming scheme

## 7. Acceptance for This Draft

This boundary is considered usable when:

1. another project can copy Package A + Package B + host adapters and boot without importing Yue `app.main`
2. `compatibility.py` no longer hard-imports `app.mcp.builtin`
3. skill/tool authorization behavior remains backward-compatible for existing `builtin:*`-based agents/skills

