# `skill_service.py` Modularization Plan (2026-03-23)

## 1. Purpose

This document analyzes [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) and proposes a safe modularization plan that improves cohesion, lowers coupling, and preserves current runtime behavior.

The immediate goal is not a behavior rewrite. The goal is to split the current 711-line service into clearer modules while keeping the current public import surface stable for:

1. [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py)
2. [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
3. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
4. [`backend/app/services/chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py)
5. the existing skill-related test suite under [`backend/tests`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests)

## 1.1 Phase 1 Execution Update

Phase 1 of this plan has now been implemented.

What actually changed:

1. Added [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py) for shared pydantic contracts.
2. Added [`backend/app/services/skills/directories.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/directories.py) for layer priority and directory resolution.
3. Added [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py) for markdown parsing and validation.
4. Added [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to re-export the extracted Phase 1 symbols.
5. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) to import and reuse those extracted modules while preserving the existing registry, router, adapters, policy gate, and global exports.

What did not change:

1. `SkillRegistry` and its runtime watch behavior remain in [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) for this phase.
2. `SkillRouter`, adapters, and `SkillPolicyGate` also remain in the compatibility module for now.
3. Existing import paths such as `from app.services.skill_service import ...` were preserved.

Validation results:

1. `python -m compileall backend/app/services/skill_service.py backend/app/services/skills`
2. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_foundation_unit.py`
3. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_api_skills.py`
4. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_runtime_integration.py`

Observed outcome:

1. `14 passed` in `test_skill_foundation_unit.py`
2. `12 passed` in `test_api_skills.py`
3. `8 passed` in `test_skill_runtime_integration.py`

Deviation from the original plan:

1. The Phase 1 implementation kept `skill_service.py` as a partially extracted compatibility module rather than reducing it all the way to a thin facade in the same step. This was intentional to keep watch-thread and routing behavior isolated from the first extraction.

## 1.2 Phase 2 Execution Update

Phase 2 of this plan has now been implemented.

What actually changed:

1. Added [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py) for `SkillRouter`.
2. Added [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py) for `SkillPolicyGate`.
3. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export the new routing and policy symbols.
4. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) so it now reuses the extracted router and policy modules.
5. Added a constructor-injection test in [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py) for the new `skill_group_store` seam.

Compatibility handling:

1. [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) keeps a thin compatibility wrapper class named `SkillRouter`.
2. That wrapper preserves the historical `app.services.skill_service.skill_group_store` patch seam used by existing tests and callers.
3. The public imports `SkillRouter`, `SkillPolicyGate`, and `skill_router` remain stable.

Validation results:

1. `python -m compileall backend/app/services/skill_service.py backend/app/services/skills backend/tests/test_skill_foundation_unit.py`
2. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_foundation_unit.py`
3. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_api_skills.py`
4. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_runtime_integration.py`

Observed outcome:

1. `15 passed` in `test_skill_foundation_unit.py`
2. `12 passed` in `test_api_skills.py`
3. `8 passed` in `test_skill_runtime_integration.py`

Deviation from the original plan:

1. Instead of replacing `SkillRouter` in [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) with a direct re-export, a small compatibility subclass was kept to preserve module-level patch behavior.

## 1.3 Phase 3 Execution Update

Phase 3 of this plan has now been implemented.

What actually changed:

1. Added [`backend/app/services/skills/adapters.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/adapters.py) for `LegacyAgentAdapter` and `MarkdownSkillAdapter`.
2. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export the adapter symbols.
3. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) so the compatibility module now reuses the extracted adapters instead of defining them inline.
4. Added a direct adapter coverage test to [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py).

Compatibility handling:

1. The public imports `LegacyAgentAdapter` and `MarkdownSkillAdapter` remain available from [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py).
2. Downstream chat prompt assembly code in [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py) continues to receive the same `MarkdownSkillAdapter` interface and behavior.

Validation results:

1. `python -m compileall backend/app/services/skill_service.py backend/app/services/skills backend/tests/test_skill_foundation_unit.py`
2. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_foundation_unit.py`
3. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_api_skills.py`
4. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_runtime_integration.py`

Observed outcome:

1. `16 passed` in `test_skill_foundation_unit.py`
2. `12 passed` in `test_api_skills.py`
3. `8 passed` in `test_skill_runtime_integration.py`

Deviation from the original plan:

1. No material deviation was needed in this phase because the adapter boundary was already narrow and only lightly coupled.

## 1.4 Phase 4 Execution Update

Phase 4 of this plan has now been implemented.

What actually changed:

1. Added [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py) for `SkillRegistry`.
2. Updated [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) to export `SkillRegistry`.
3. Updated [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) so `SkillRegistry` is now imported from the package rather than defined inline.
4. Reduced [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) to a compatibility-oriented module that primarily re-exports extracted symbols and retains the small `SkillRouter` compatibility wrapper plus the global `skill_registry` and `skill_router`.

Compatibility handling:

1. `skill_registry = SkillRegistry()` still lives in [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py), so imports used by [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py), [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py), and [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py) remain stable.
2. Runtime watch behavior, load/reload semantics, and registry public methods were preserved unchanged during extraction.
3. The router compatibility wrapper remained in place so module-level patch behavior for `skill_group_store` still works.

Validation results:

1. `python -m compileall backend/app/services/skill_service.py backend/app/services/skills`
2. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_foundation_unit.py`
3. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_api_skills.py`
4. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_runtime_integration.py`

Observed outcome:

1. `16 passed` in `test_skill_foundation_unit.py`
2. `12 passed` in `test_api_skills.py`
3. `8 passed` in `test_skill_runtime_integration.py`

Deviation from the original plan:

1. The global `skill_registry` instance was intentionally kept in [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) rather than moving instance construction into the package entrypoint. This keeps import and patch behavior maximally stable while still extracting the class implementation.

## 1.5 Cleanup Update

A final cleanup pass was completed after the planned modularization phases.

What actually changed:

1. Added an explicit `__all__` export list to [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) to make the compatibility surface intentional and easier to audit.
2. Updated [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py) to import `SkillDirectoryResolver` directly from [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py) while still importing the global `skill_registry` from [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py).
3. Updated [`backend/app/api/skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py) to import `SkillPolicyGate`, `SkillSpec`, and `SkillSummary` directly from [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py), while keeping `skill_registry` and `skill_router` from the compatibility module.
4. Updated [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py) to import `SkillPolicyGate` and `MarkdownSkillAdapter` directly from [`backend/app/services/skills/__init__.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/__init__.py), while keeping the global registry/router imports unchanged.

Why this cleanup was safe:

1. Pure contracts and helper classes now come from the new package directly.
2. Mutable globals and compatibility seams still come from [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py).
3. This reduces accidental dependence on the compatibility layer without forcing a broad import migration.

Final validation results:

1. `python -m compileall backend/app/main.py backend/app/api/skills.py backend/app/api/chat.py backend/app/services/skill_service.py backend/app/services/skills`
2. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_foundation_unit.py`
3. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_api_skills.py`
4. `PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend pytest tests/test_skill_runtime_integration.py`

Observed outcome:

1. `16 passed` in `test_skill_foundation_unit.py`
2. `12 passed` in `test_api_skills.py`
3. `8 passed` in `test_skill_runtime_integration.py`

## 2. Current Responsibilities

As written today, [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) mixes at least six distinct responsibilities:

1. Data contracts and pydantic models for skills, summaries, validation results, runtime descriptors, and directory specs at [`skill_service.py:22`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L22), [`skill_service.py:26`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L26), [`skill_service.py:31`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L31), [`skill_service.py:63`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L63), [`skill_service.py:93`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L93), and [`skill_service.py:101`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L101).
2. Filesystem directory resolution for builtin, workspace, and user skill layers at [`skill_service.py:72`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L72).
3. Markdown parsing and schema validation at [`skill_service.py:106`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L106) and [`skill_service.py:196`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L196).
4. Registry lifecycle, load/reload, version resolution, availability checks, and file watching at [`skill_service.py:239`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L239).
5. Runtime descriptor adapters for legacy agents and markdown skills at [`skill_service.py:499`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L499) and [`skill_service.py:516`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L516).
6. Agent-scoped selection, ranking, and tool gating at [`skill_service.py:538`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L538) and [`skill_service.py:692`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py#L692).

## 3. Why The File Is Hard To Change

The main issue is not just size. It is responsibility mixing.

### 3.1 Cohesion problems

[`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) currently groups together:

1. pure data models
2. pure parsing logic
3. filesystem I/O
4. background watch-thread management
5. ranking heuristics
6. runtime policy checks

These areas change for different reasons and have different test seams.

### 3.2 Coupling problems

There are a few notable coupling hotspots:

1. `SkillRouter.resolve_visible_skill_refs()` directly depends on the global [`skill_group_store`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_group_store.py), which makes routing logic less self-contained and a little harder to test in isolation.
2. `SkillRegistry` owns both indexing concerns and runtime watch concerns, so small registry changes can accidentally affect background reload behavior.
3. The module exports concrete globals, `skill_registry` and `skill_router`, that are used directly by app startup and APIs, which raises import-stability risk during refactor.
4. `LegacyAgentAdapter.to_descriptor()` imports `AgentConfig` inside the method to avoid circular imports, which is a signal that runtime descriptor logic is living close to a dependency seam.

### 3.3 Hidden state and operational risk

The registry keeps mutable in-memory state plus watcher state:

1. `_skills`
2. `_latest_versions`
3. `_watch_thread`
4. `_watch_stop_event`
5. `_watch_snapshot`

That state is safe enough today, but it makes the class broader than a normal repository/index abstraction. Refactors that touch `load_all()` or watch behavior need stronger regression protection than parser-only changes.

## 4. Surrounding Usage And Constraints

The modularization has to respect these call patterns:

1. [`backend/app/main.py:35`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py#L35) constructs layered directories, loads the registry, and starts the runtime watch on startup.
2. [`backend/app/api/skills.py:4`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py#L4) imports `skill_registry`, `skill_router`, `SkillPolicyGate`, `SkillSpec`, and `SkillSummary` directly from the module.
3. [`backend/app/services/chat_prompting.py:209`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py#L209) through [`chat_prompting.py:347`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py#L347) uses the router and registry repeatedly during runtime selection and prompt assembly.
4. The unit and integration tests currently import classes from the same file, especially [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py) and [`backend/tests/test_skill_runtime_integration.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_integration.py).

This means the first safe step is internal extraction with a compatibility facade, not immediate breaking import-path changes.

## 5. Recommended Target Structure

I recommend converting the single file into a small package while keeping a compatibility export layer:

```text
backend/app/services/skills/
├── __init__.py
├── models.py
├── directories.py
├── parsing.py
├── registry.py
├── adapters.py
├── routing.py
└── policy.py
```

Recommended responsibility split:

### 5.1 `models.py`

Owns:

1. `SkillDirectorySpec`
2. `SkillConstraints`
3. `SkillSpec`
4. `SkillSummary`
5. `RuntimeCapabilityDescriptor`
6. `SkillValidationResult`

Why:

1. These are shared contracts.
2. They are the least risky to extract first.
3. Multiple downstream modules depend on them.

### 5.2 `directories.py`

Owns:

1. `SKILL_LAYER_PRIORITY`
2. `SkillDirectoryResolver`

Why:

1. Directory-layer resolution is conceptually separate from parsing and routing.
2. It is startup-facing logic used by [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py).

### 5.3 `parsing.py`

Owns:

1. `SkillLoader`
2. `SkillValidator`
3. small internal helpers such as list normalization and section extraction

Why:

1. Markdown-to-model parsing is a cohesive unit.
2. This area already has focused tests in [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py).

### 5.4 `registry.py`

Owns:

1. `SkillRegistry`
2. load/reload behavior
3. availability computation
4. full-skill lazy reload
5. runtime watch behavior

Why:

1. Registry and watch behavior are tightly coupled today.
2. Keeping them together in phase 1 avoids premature splitting of mutable runtime state.

Phase-2 optional refinement:

1. If the registry still feels too broad after extraction, split watch behavior into a `SkillRegistryWatcher` collaborator.
2. I would not do that in the first pass.

### 5.5 `adapters.py`

Owns:

1. `LegacyAgentAdapter`
2. `MarkdownSkillAdapter`

Why:

1. These are translation utilities from domain objects into runtime descriptor objects.
2. They change for prompt/runtime concerns, not for discovery or selection concerns.

### 5.6 `routing.py`

Owns:

1. `SkillRouter`
2. tokenization helpers
3. ranking heuristics
4. visible-skill resolution

Recommended improvement:

1. Accept a `skill_group_store` dependency in the constructor, defaulting to the current global store for compatibility.
2. This makes routing logic easier to unit-test and less coupled to global module state.

### 5.7 `policy.py`

Owns:

1. `SkillPolicyGate`

Why:

1. It is tiny, but separating it keeps runtime policy logic out of the routing module.
2. It also creates a clean seam if tool-policy logic grows later.

## 6. Compatibility Strategy

To reduce breakage, keep [`backend/app/services/skill_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py) as a compatibility facade for at least one refactor cycle.

Recommended facade behavior:

1. Re-export all public classes from the new `app.services.skills` package.
2. Instantiate and export `skill_registry` and `skill_router` from the facade or package entrypoint.
3. Do not change existing import sites in the same phase unless there is a compelling reason.

This avoids a broad multi-file rename while still gaining modular internals.

## 7. Phased Migration Plan

### Phase 0. Lock in baseline coverage

Before structural edits:

1. Run the focused skill test set:
   - [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
   - [`backend/tests/test_api_skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skills.py)
   - [`backend/tests/test_skill_runtime_integration.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_integration.py)
2. Add any missing tests around import compatibility if needed.

### Phase 1. Extract data contracts and pure logic

Move without changing behavior:

1. extract pydantic models into `models.py`
2. extract `SkillDirectoryResolver` into `directories.py`
3. extract `SkillLoader` and `SkillValidator` into `parsing.py`
4. update imports inside the old module or compatibility facade

Expected benefit:

1. The riskiest mutable runtime class, `SkillRegistry`, stays untouched while pure logic moves first.

### Phase 2. Extract routing and policy

Move next:

1. extract `SkillRouter` into `routing.py`
2. extract `SkillPolicyGate` into `policy.py`
3. inject or default `skill_group_store` instead of hard-coding it in routing
4. keep the global `skill_router` export stable

Expected benefit:

1. runtime selection logic becomes independently testable
2. registry concerns are no longer mixed with ranking concerns

### Phase 3. Extract adapters

Move:

1. `LegacyAgentAdapter`
2. `MarkdownSkillAdapter`

Expected benefit:

1. runtime descriptor logic is isolated from discovery/indexing logic
2. the remaining registry module becomes easier to reason about

### Phase 4. Move registry into package module

Move:

1. `SkillRegistry`
2. global `skill_registry`
3. runtime watch support

Rules for this phase:

1. keep public methods and semantics unchanged
2. preserve the existing startup call sequence in [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py)
3. keep `skill_service.py` as a thin re-export wrapper

### Phase 5. Optional cleanup

After the package split is stable:

1. migrate imports from `app.services.skill_service` to `app.services.skills` only if that improves clarity
2. consider splitting watch logic from registry only if registry complexity still feels high
3. consider adding a small shared parser utility if markdown parsing expands further

## 8. Risks And Mitigations

### 8.1 Import stability risk

Risk:

1. many files and tests import directly from `app.services.skill_service`

Mitigation:

1. keep `skill_service.py` as a compatibility layer
2. preserve symbol names and globals

### 8.2 Watch-thread lifecycle risk

Risk:

1. moving `SkillRegistry` and its watcher behavior can accidentally change startup/shutdown semantics

Mitigation:

1. do not redesign watch behavior during the first extraction
2. preserve `start_runtime_watch()` and `stop_runtime_watch()` signatures
3. re-run runtime integration coverage after registry extraction

### 8.3 Behavior drift in routing heuristics

Risk:

1. small refactors to tokenization or scoring can subtly change auto-selection behavior

Mitigation:

1. keep routing code behavior-identical during extraction
2. retain the replay-style routing test in [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
3. add one or two explicit tests for constructor-based dependency injection if introduced

### 8.4 Circular import risk

Risk:

1. moving adapters and registry code may expose or create circular imports, especially around `AgentConfig`

Mitigation:

1. keep lazy import behavior in `LegacyAgentAdapter`
2. keep runtime globals instantiated from a single top-level package entrypoint
3. move modules in small phases, not all at once

## 9. Test And Regression Strategy

Minimum regression set per phase:

1. [`backend/tests/test_skill_foundation_unit.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
2. [`backend/tests/test_api_skills.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skills.py)
3. [`backend/tests/test_skill_runtime_integration.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_integration.py)

Recommended additional spot-checks:

1. startup path exercised via [`backend/app/main.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py)
2. chat runtime paths that call skill routing and lazy full-skill loads via [`backend/app/services/chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py)

If we add new tests during the refactor, highest-value additions are:

1. a test that `app.services.skill_service` still re-exports the expected symbols
2. a test that `SkillRouter` works with an injected mock group store
3. a test that registry watcher start/stop still behaves safely after extraction

## 10. PR Split Recommendation

The safest PR sequence is:

1. PR 1: extract `models.py`, `directories.py`, and `parsing.py` with compatibility exports
2. PR 2: extract `routing.py`, `policy.py`, and `adapters.py`
3. PR 3: extract `registry.py`, keep facade, and run the full skill regression set
4. PR 4: optional cleanup and import-path simplification

## 11. Recommendation Summary

Recommended approach:

1. modularize `skill_service.py` into a `services/skills/` package
2. keep `skill_service.py` as a compatibility facade initially
3. extract pure contracts and parsing first
4. leave `SkillRegistry` plus watcher behavior for a later, more protected phase
5. inject `skill_group_store` into routing for lower coupling once the routing extraction happens

This gives a clear cohesion win without forcing a risky all-at-once rewrite.
