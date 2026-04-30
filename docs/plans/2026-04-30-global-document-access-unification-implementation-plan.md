# Global Document Access Unification Implementation Plan

**Date**: 2026-04-30  
**Status**: Draft  
**Owner Scope**: backend config/runtime, builtin file/document tools, agent configuration surface, settings UI, regression verification  
**Primary Goal**: make `settings` the single source of truth for local file/document access control, ensure updates take effect immediately, survive restart, and automatically inform targeted builtin agents/tools which roots are available.

## 1. Requirements Summary

This plan implements a unified local document access model with four hard requirements:

1. `settings` is the only writable control surface for local file access boundaries.
2. Changes to allowed/denied roots take effect immediately after saving settings.
3. Settings persist across process restart and remain authoritative after reload.
4. One or more allowed roots are automatically injected into targeted builtin file/document tool context and prompt guidance so the model knows where to search.

The current system already has a global `doc_access` configuration surface:

- [backend/app/api/config.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/config.py:46)
- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:740)
- [frontend/src/pages/settings/components/GeneralSettingsTab.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/settings/components/GeneralSettingsTab.tsx:487)

But effective access is still mixed with agent-level and tool-level logic:

- agent-level scope fields still exist in [backend/app/api/agents.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/agents.py:23) and [backend/app/services/agent_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py:22)
- runtime still injects agent `doc_roots` in [backend/app/services/chat_runtime.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_runtime.py:116)
- prompt scope summary still depends on agent `doc_roots` in [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py:92) and [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py:412)
- docs/excel tools each fetch roots independently in [backend/app/mcp/builtin/docs.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py:13) and [backend/app/mcp/builtin/excel.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/excel.py:13)
- builtin command execution is implemented separately in [backend/app/mcp/builtin/exec.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/exec.py:160); this initiative does not add new `exec` command restrictions or make `exec` a blocker for file/document scope unification

## 2. Target Architecture

### 2.1 Single Source of Truth

The only authority for local file access boundaries will be:

- `doc_access.allow_roots`
- `doc_access.deny_roots`

Stored in global config and updated through the settings page.

### 2.2 Runtime Rules

1. File access permission is decided only by global `doc_access`.
2. Agent `doc_roots` will no longer participate in access control.
3. `doc_file_patterns` may remain only as a content filtering hint, not a permission boundary.
4. Every targeted builtin file/document tool resolves file scope through one shared policy/lookup contract.
5. Every request that exposes targeted builtin file/document tools receives a dynamically generated scope summary derived from current global config.
6. `exec` keeps its current unrestricted command role and is not part of the new restriction work in this initiative.

### 2.3 Effective Behavior

After the refactor:

- saving settings updates in-memory config and persisted config
- the next tool call reads the new roots immediately
- restarting the service reloads the same roots from disk
- targeted builtin file/document prompts describe the currently allowed roots
- agents no longer have independent directory-level access boundaries

## 3. Acceptance Criteria

The work is complete only when all items below are true:

1. Editing `Document Access` in settings changes effective file access behavior on the very next request without restart.
2. Restarting the backend preserves `allow_roots` and `deny_roots`.
3. No runtime access decision depends on agent `doc_roots`.
4. Docs, Excel, and future targeted builtin file/document tools use the same global scope contract for access guidance and enforcement.
5. Targeted builtin prompts/tool context automatically include one or more currently allowed roots.
6. Frontend agent editing no longer exposes directory-level permission control.
7. Existing regression tests for docs retrieval still pass after the refactor, with updated expectations where agent `doc_roots` previously narrowed scope.
8. Builtin `exec` remains operational without new command-level restrictions from this initiative.

## 4. Design Decisions

### 4.1 Permission Boundary vs Search Hint

We explicitly separate:

- permission boundary: global `allow_roots` / `deny_roots`
- search hint or content preference: file patterns, mode selection, model guidance

This prevents agent-local configuration from silently becoming a second permission system.

### 4.2 Immediate Effect Guarantee

Immediate effect will be guaranteed by design:

1. `config_service.update_doc_access(...)` updates in-memory state and persists to disk.
2. Every targeted file/document tool call reads current roots at execution time.
3. Prompt assembly reads current roots at request assembly time.
4. No access roots are cached in agent objects, request bootstrap state, or tool registry metadata.

### 4.3 Restart Persistence Guarantee

Persistence will be guaranteed by design:

1. `doc_access` remains part of `global_config.json`.
2. `ConfigService._load_config()` remains the reload path on startup.
3. Tests explicitly verify write-then-reload behavior.

### 4.4 Scope Injection Policy

Allowed roots should be visible to the model whenever targeted builtin file/document tools are enabled.

Injection must:

1. support one or many roots
2. be derived from current global config, not from agent config
3. be generated in one shared place
4. avoid duplicating prompt assembly logic across tools
5. apply to targeted builtin file/document tools only

### 4.5 Target Builtin Tool Coverage

For this initiative, the required target surface is builtin file/document tooling.

Included now:

1. docs tools such as `docs_list`, `docs_search`, `docs_read`, and PDF document helpers
2. Excel/CSV tools such as `excel_profile`, `excel_read`, `excel_query`, `excel_logic_extract`, and `excel_script_scan`
3. future builtin tools whose primary purpose is reading, searching, profiling, or extracting local file/document content

Excluded from this initiative:

1. builtin `exec`
2. terminal-style command execution restriction design
3. shell command semantic parsing

If a future builtin tool is ambiguous, default it into the targeted file/document group only when its product purpose is file/document access rather than general command execution.

### 4.6 Exec Scope Decision

`exec` is explicitly out of scope for additional command restriction in this initiative.

Decision:

1. do not add new command-level restrictions for builtin `exec`
2. do not turn `exec` into a whitelisted or pre-approved command catalog
3. do not spend this initiative on shell-path parsing or command-semantic restriction design
4. keep `exec` behavior as-is unless a separate future initiative explicitly revisits it

This plan focuses on unifying document/file access control for targeted builtin file/document tools and removing scattered directory permission logic.  
`exec` should not become the blocker for that simplification effort.

### 4.7 Runtime Semantics to Implement

These rules remove ambiguity from the implementation:

1. `root_dir` is a query scope selector, not a permission source.
2. `root_dir` must resolve inside one of the configured `allow_roots`.
3. invalid `root_dir` should return a structured permission/root error instead of silently falling back to another root.
4. when `root_dir` is omitted and multiple `allow_roots` exist, search/list tools should search all configured allowed roots unless a tool has a strong reason to require one root.
5. read tools should resolve relative paths against allowed roots and fail with an explicit ambiguity error if the same relative file path exists under multiple roots.
6. `deny_roots` are enforcement-only and should not be injected into prompts.
7. allowed roots should be injected in the same order configured in settings, after normalization.
8. if `allow_roots` is empty, targeted file/document tools should fail closed unless a separate product decision explicitly seeds a default root such as project `docs/`.

## 5. Implementation Plan

### Phase 1: Freeze the Unified Access Contract

**Goal**: define and codify that global config is the only permission source.

#### Changes

- add a short ADR section to this document and reference it in future cleanup PRs
- update doc access policy code comments to reflect that only global roots determine permission boundaries
- mark agent `doc_roots` as deprecated in API/service comments before behavior removal

#### Files

- [backend/app/services/doc_access_policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/doc_access_policy.py:93)
- [backend/app/services/doc_retrieval.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/doc_retrieval.py:92)
- [backend/app/api/agents.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/agents.py:23)
- [backend/app/services/agent_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py:22)

#### Exit Criteria

- code comments and naming no longer imply that agent roots are part of permission authority

### Phase 2: Centralize Path Resolution

**Goal**: make targeted builtin file/document tools depend on one shared access resolution path or scope contract.

#### Changes

- introduce a shared helper or facade for:
  - resolving current effective global roots
  - validating requested roots
  - validating requested file paths
  - returning structured denial reasons
- keep `doc_retrieval` as the core implementation, but reduce per-tool bespoke access assembly
- refactor docs tools to use the shared entrypoint
- refactor Excel service/tools to use the same entrypoint

#### Files

- [backend/app/services/doc_retrieval.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/doc_retrieval.py:120)
- [backend/app/mcp/builtin/docs.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py:13)
- [backend/app/services/excel_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/excel_service.py:36)
- [backend/app/mcp/builtin/excel.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/excel.py:13)

#### Exit Criteria

- docs/excel file access flows call one common policy path
- tool error semantics for denied roots are consistent

### Phase 3: Guarantee Immediate Effect

**Goal**: ensure a settings save affects the next request with no restart and no agent recreation.

#### Changes

- verify every targeted builtin file/document path reads current scope information at call time
- verify prompt assembly reads current global roots at request assembly time
- remove any access-root caching outside `ConfigService`
- add integration tests that update settings twice in the same process and assert behavior changes immediately

#### Files

- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:780)
- [backend/app/mcp/builtin/docs.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py:13)
- [backend/app/mcp/builtin/excel.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/excel.py:13)
- [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py:88)

#### Verification

1. save roots = `A`
2. call file tool and observe access only within `A`
3. save roots = `B`
4. call file tool again in the same process
5. observe access only within `B`

#### Exit Criteria

- immediate effect test passes without backend restart

### Phase 4: Guarantee Restart Persistence

**Goal**: ensure doc access configuration survives process restart.

#### Changes

- keep `doc_access` persisted through `update_config`
- add tests that instantiate a fresh `ConfigService` after write
- optionally harden logging/error handling for malformed config recovery

#### Files

- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:187)
- [backend/app/services/config_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py:780)
- [frontend/src/pages/settings/useSettingsData.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/settings/useSettingsData.ts:64)

#### Verification

1. update doc access
2. assert config file content changed
3. construct a fresh config service
4. assert roots reloaded correctly

#### Exit Criteria

- restart persistence test passes

### Phase 5: Replace Agent-Level Scope Injection with Global Scope Injection

**Goal**: inject current allowed roots into targeted builtin prompt/tool context from one shared source.

#### Changes

- add a shared scope summary builder for requests with targeted builtin file/document tools
- determine scope injection by builtin tool availability, not by agent `doc_roots`
- inject current allowed roots into prompt assembly
- support one or many roots in a stable, predictable format
- remove prompt text that currently derives from agent `doc_roots`
- treat builtin document/file-oriented tools as the required injection target for this initiative

#### Suggested Prompt Shape

```text
### File Access Scope
You may access local files only within these allowed roots:
- /path/a
- /path/b

If the user does not specify a path, inspect these roots first.
Prefer listing or searching within the allowed roots before reading files directly.
```

#### Files

- [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py:88)
- [backend/app/services/chat_prompting.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py:408)
- [backend/app/services/chat_runtime.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_runtime.py:116)

#### Exit Criteria

- one-root and multi-root prompt injection tests pass
- prompt assembly no longer references agent `doc_roots`

### Phase 6: Remove Agent-Level Directory Permission Surface

**Goal**: delete the old per-agent directory permission model.

#### Changes

- stop using `doc_roots` in runtime deps
- stop exposing `doc_roots` in agent editing UX
- remove `doc_roots` badges/cards in agent list
- deprecate and then remove `doc_roots` from public agent schema
- keep `doc_file_patterns` only if still valuable as a search filter

#### Files

- [backend/app/api/agents.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/agents.py:23)
- [backend/app/services/agent_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py:22)
- [frontend/src/hooks/useAgentsState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useAgentsState.ts:60)
- [frontend/src/components/AgentForm.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/AgentForm.tsx:49)
- [frontend/src/components/AgentCard.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/AgentCard.tsx:110)

#### Exit Criteria

- settings is the only visible directory permission UI
- agent create/edit flow no longer changes directory access boundaries

### Phase 7: Data Migration and Compatibility Cleanup

**Goal**: safely retire historical agent-level roots without silently expanding access.

#### Migration Strategy

1. scan stored agents for non-empty `doc_roots`
2. generate a migration report listing affected agents and values
3. do not auto-merge all historical roots into global `allow_roots`
4. require an explicit admin decision to widen global access in settings
5. clear or ignore historical `doc_roots` after migration

#### Why No Auto-Merge

Auto-merging all historical agent roots into global roots could silently widen file access and violate least privilege.

#### Files

- [backend/app/services/agent_store.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py:47)
- [backend/data/agents.json](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/agents.json:1)

#### Exit Criteria

- migration report is generated
- historical agents no longer influence permission boundaries

## 6. Test and Verification Plan

### 6.1 Unit Tests

#### Doc access policy

- path normalization for relative and absolute roots
- deny-overrides-allow behavior
- multiple allow roots
- overlapping roots dedupe and normalization

Primary files:

- [backend/tests/test_doc_retrieval.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_doc_retrieval.py:368)

#### Config persistence

- update doc access writes config
- fresh config load restores the same values

Primary files:

- [backend/tests/test_config_service_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_config_service_unit.py:1)

#### Prompt injection

- builtin document/file tools plus one root means one-root scope block
- builtin document/file tools plus many roots means multi-root scope block
- injection always reflects latest saved config
- injected roots preserve settings order after normalization
- deny roots are not injected into prompt text

Primary files:

- [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py:1688)

### 6.2 Integration Tests

1. update `doc_access` through API
2. invoke `docs_search` / `docs_read`
3. verify access within allowed roots only
4. update `doc_access` again
5. re-run request without restart
6. verify immediate behavior change

Repeat the same flow for Excel file tools.

### 6.3 UI Tests

- settings loads saved doc access roots
- settings saves new doc access roots
- agents UI no longer exposes directory access controls
- document access description clearly states the setting is global

Possible coverage points:

- [frontend/e2e/settings-general.spec.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/e2e/settings-general.spec.ts:1)
- [frontend/src/pages/settings/useSettingsData.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/settings/useSettingsData.ts:64)

## 7. Risks and Mitigations

### Risk 1: Existing agents lose narrowed scope behavior

Some agents may currently rely on `doc_roots` as a narrower scope than global config.

**Mitigation**

- remove `doc_roots` only after migration reporting
- communicate the behavior change explicitly
- keep temporary compatibility tests during rollout

### Risk 2: Silent widening of access during migration

Automatically copying historical `doc_roots` into global allow roots would broaden access unexpectedly.

**Mitigation**

- do not auto-merge
- require explicit admin action in settings

### Risk 3: Tool descriptions and prompts drift apart

If prompt scope injection and tool execution use different sources, the model could be told one scope while execution enforces another.

**Mitigation**

- use the same global config read path for prompt assembly and tool execution
- add tests that compare injected roots with effective tool roots

### Risk 4: Immediate effect is accidentally broken by caching

Future optimizations might cache roots in tool registry or chat runtime state.

**Mitigation**

- add regression tests for same-process reconfiguration
- document "no root caching" as an invariant

## 8. Rollout Strategy

Recommended rollout order:

1. lock runtime semantics for `root_dir`, empty allow roots, and multi-root behavior
2. unify policy resolution and tests
3. verify immediate effect and restart persistence
4. switch prompt injection to global roots
5. remove agent runtime dependency on `doc_roots`
6. remove agent UI/schema fields
7. run migration report and cleanup

This ordering keeps the system safe while progressively shrinking the old surface area.

## 9. Definition of Done

This initiative is done when:

1. global settings are the only writable directory permission surface
2. changing settings affects the next request immediately
3. restarting the backend preserves the same effective roots
4. all targeted builtin prompts/tool contexts display the current allowed roots
5. agent-local directory permissions no longer influence execution
6. docs, Excel, and other targeted builtin file/document tools share the same access scope semantics
7. regression and acceptance tests pass

## 10. ADR Summary

**Decision**

Use global `doc_access` as the single source of truth for local file access boundaries for the targeted builtin file/document tool surface, without expanding this initiative into extra `exec` command restrictions.

**Drivers**

- reduce scattered permission logic
- guarantee immediate and predictable behavior
- simplify user mental model
- avoid tool/agent-specific boundary drift

**Alternatives Considered**

- keep global roots plus agent-level narrowing
- move all boundaries into each tool independently
- auto-merge agent roots into global settings during migration

**Why Chosen**

Single-source global configuration is the simplest model that satisfies immediate effect, restart persistence, and consistent scope injection for the targeted builtin file/document surface.

**Consequences**

- simpler control plane
- smaller chance of permission drift
- migration work required for legacy agent scope configuration

**Follow-Ups**

- implement unified builtin file access scope injection
- remove deprecated agent scope fields
- add explicit regression gates for same-process config updates

## 11. Pre-Implementation Checklist

Before implementation starts, confirm these assumptions in the first PR description:

1. `exec` is not changed by this initiative.
2. empty `allow_roots` means targeted file/document tools fail closed.
3. invalid `root_dir` returns a structured error and does not silently fall back.
4. omitted `root_dir` searches all configured roots for search/list operations.
5. prompt injection lists allowed roots only, not denied roots.
6. historical agent `doc_roots` are reported but not automatically merged into global settings.
