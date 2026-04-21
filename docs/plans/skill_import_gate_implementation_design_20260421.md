# Skill Import Gate Implementation Design

**Date**: 2026-04-21

## 1. Current Stage Judgment

Yue is past the strategy-reset stage and is now in the **implementation design stage**.

The product boundary is already clear:

- Yue only aligns to the **Agent Skills open standard**
- Yue is not a skill authoring platform
- Yue should focus on **import + acceptance + activation + routing + runtime**

The codebase is **not starting from zero**. It already has usable foundations in:

- package parsing and structural validation in [`backend/app/services/skills/parsing.py`](../../backend/app/services/skills/parsing.py)
- in-memory indexing and lazy overlay resolution in [`backend/app/services/skills/registry.py`](../../backend/app/services/skills/registry.py)
- selection and prompt injection in [`backend/app/services/skills/routing.py`](../../backend/app/services/skills/routing.py) and [`backend/app/services/chat_prompting.py`](../../backend/app/services/chat_prompting.py)

But the codebase is still in a transitional shape:

- loader semantics and import semantics are still conflated
- runtime availability and admin acceptance are still conflated
- reusable skill logic and Yue-specific integration are only partially separated

This means the correct next step is **not** broad refactoring and **not** immediate feature coding.

The correct next step is:

- define a concrete Skill Import Gate lifecycle
- carve the module boundary between reusable `skill core` and Yue integration
- choose the first low-risk code seam for Stage 1 and Stage 2

## 2. Highest-Priority Next Step

The highest-priority next step is:

- **Introduce an explicit Skill Import Gate contract without breaking the current runtime path**

This should be done by adding a new import/acceptance path beside the current startup loader, not by rewriting routing first.

Reason:

1. the current runtime already works well enough to continue serving traffic
2. the biggest missing product surface is acceptance lifecycle, not parsing
3. import-gate contracts can be added with lower regression risk than touching runtime routing and prompt assembly first

## 3. Code Facts That Matter

### 3.1 What exists today

The current code already provides these useful building blocks:

- `SkillLoader.parse_package()` parses a package directory and can derive a minimal manifest when `manifest.yaml` is missing. [`backend/app/services/skills/parsing.py:429`](../../backend/app/services/skills/parsing.py)
- `SkillLoader.validate_package()` validates file structure, resources, actions, and overlays. [`backend/app/services/skills/parsing.py:736`](../../backend/app/services/skills/parsing.py)
- `SkillValidator.validate()` validates the resulting `SkillSpec`. [`backend/app/services/skills/parsing.py:860`](../../backend/app/services/skills/parsing.py)
- `SkillRegistry.register_package()` converts a package to runtime skill metadata and indexes it in memory. [`backend/app/services/skills/registry.py:202`](../../backend/app/services/skills/registry.py)
- `SkillRegistry._compute_availability()` checks OS / bins / env presence. [`backend/app/services/skills/registry.py:247`](../../backend/app/services/skills/registry.py)
- `SkillRouter` filters by agent-visible skills and ranks with simple lexical scoring. [`backend/app/services/skills/routing.py:17`](../../backend/app/services/skills/routing.py)
- `chat_prompting.resolve_skill_runtime_state()` binds selection to chat sessions and `assemble_runtime_prompt()` injects the selected skill prompt into the agent persona. [`backend/app/services/chat_prompting.py:190`](../../backend/app/services/chat_prompting.py), [`backend/app/services/chat_prompting.py:331`](../../backend/app/services/chat_prompting.py)
- app startup still loads skills directly from layered directories into a global registry. [`backend/app/main.py:37`](../../backend/app/main.py)

### 3.2 What does not exist yet

The missing pieces are now very specific:

- no explicit import transaction
- no persisted import record
- no admin-facing lifecycle states
- no clear split between:
  - standard-valid
  - Yue-compatible
  - activation-ready
  - active
- no activation persistence independent of source-directory presence
- no replacement flow that preserves lineage between versions or revisions

## 4. Coupling Hotspots

The main implementation risk is not parser complexity. It is **cross-layer coupling**.

### Hotspot 1: `skill_service.py` is a global compatibility hub

[`backend/app/services/skill_service.py`](../../backend/app/services/skill_service.py) exports:

- global `skill_registry`
- global `skill_router`
- global `skill_action_execution_service`
- a compatibility wrapper around `SkillRouter`

This keeps the app simple to wire, but it also hides dependencies and makes extraction harder.

Impact:

- API, startup, and chat runtime all depend on shared global instances
- the future import gate cannot be isolated cleanly while everything routes through one global facade

### Hotspot 2: `SkillRegistry` mixes too many responsibilities

[`backend/app/services/skills/registry.py`](../../backend/app/services/skills/registry.py) currently owns:

- source directory scanning
- watch-loop reload
- package registration
- runtime indexing
- overlay resolution
- availability checking
- action invocation validation

This is the largest cohesion issue inside the current skill subsystem.

Impact:

- import-gate behavior cannot be added cleanly without either bloating the registry further or introducing side channels
- extraction into a small reusable library will remain awkward if source discovery, runtime indexing, and app policy stay fused

### Hotspot 3: routing depends on Yue agent visibility and skill groups

[`backend/app/services/skills/routing.py`](../../backend/app/services/skills/routing.py) depends on:

- agent fields like `visible_skills`, `skill_groups`, `extra_visible_skills`, `resolved_visible_skills`
- `skill_group_store`

This means routing is not a pure skill concern today. It is partly a Yue agent configuration concern.

Impact:

- routing primitives are reusable
- agent visibility resolution is not

These two concerns should be separated.

### Hotspot 4: prompt assembly mixes runtime routing state with chat/session policy

[`backend/app/services/chat_prompting.py`](../../backend/app/services/chat_prompting.py) currently:

- resolves visible skills
- mutates `agent_config.resolved_visible_skills`
- reads and writes bound session skill through `chat_service`
- injects prompts and always-on skills

Impact:

- the runtime selection pipeline is partially embedded in chat-specific code
- this should stay in Yue adapter land, not inside future reusable skill core

### Hotspot 5: startup loading equals acceptance today

App startup directly does:

- resolve directories
- create directories
- set layered dirs on the registry
- call `load_all()`
- start watch reload

in [`backend/app/main.py:37`](../../backend/app/main.py)

Impact:

- a package being physically present in a watched folder is effectively treated as accepted by the platform
- this is the key product-level mismatch with the new direction

## 5. Recommended Module Boundary

The cleanest future split is:

## 5.1 Reusable Skill Core

These modules belong in future reusable `skill core`.

### Data models

- package/resource/action/validation models
- import report and compatibility report models
- lifecycle enums and result types

Current base:

- [`backend/app/services/skills/models.py`](../../backend/app/services/skills/models.py)

### Standard parsing and structural validation

- package parsing
- markdown/frontmatter parsing
- manifest normalization
- overlay parsing
- structural validation

Current base:

- [`backend/app/services/skills/parsing.py`](../../backend/app/services/skills/parsing.py)

### Skill catalog/index primitives

- in-memory skill/package index
- overlay resolution
- package-to-runtime projection

Current base:

- parts of [`backend/app/services/skills/registry.py`](../../backend/app/services/skills/registry.py)

### Compatibility evaluation contract

This should become its own focused module.

It should answer:

- is the package structurally valid
- does it require unsupported tools
- does it require missing env/bins/os
- is it activation-eligible in this runtime

Current base:

- `SkillRegistry._compute_availability()` in [`backend/app/services/skills/registry.py:247`](../../backend/app/services/skills/registry.py)
- tool policy checks in [`backend/app/services/skills/policy.py`](../../backend/app/services/skills/policy.py)

### Routing primitives

- lexical scoring
- candidate ranking contracts
- routing explanations

Current base:

- scoring methods in [`backend/app/services/skills/routing.py:59`](../../backend/app/services/skills/routing.py)

### Action policy / preflight

- action binding validation
- approval requirement logic
- argument schema validation

Current base:

- [`backend/app/services/skills/policy.py`](../../backend/app/services/skills/policy.py)
- [`backend/app/services/skills/actions.py`](../../backend/app/services/skills/actions.py)

## 5.2 Yue Adapter Layer

These modules must stay in Yue.

### App lifecycle and storage wiring

- layered directory resolution
- startup load / watch config
- data-dir persistence strategy

Current files:

- [`backend/app/main.py`](../../backend/app/main.py)
- [`backend/app/services/skills/directories.py`](../../backend/app/services/skills/directories.py)

### Admin/API surface

- FastAPI endpoints
- request/response models for import, preview, activate, replace

Current file:

- [`backend/app/api/skills.py`](../../backend/app/api/skills.py)

### Yue-specific persistence

- imported package storage
- activation state storage
- replacement lineage
- admin-visible import records

Current reusable persistence pattern to follow:

- [`backend/app/services/agent_store.py`](../../backend/app/services/agent_store.py)
- [`backend/app/services/skill_group_store.py`](../../backend/app/services/skill_group_store.py)

### Agent visibility resolution

- mapping active skills to `agent.visible_skills` / `skill_groups`
- resolving effective visible skills per agent

Current files:

- [`backend/app/services/agent_store.py`](../../backend/app/services/agent_store.py)
- [`backend/app/services/skill_group_store.py`](../../backend/app/services/skill_group_store.py)
- [`backend/app/services/skills/routing.py`](../../backend/app/services/skills/routing.py)

### Chat/session binding and prompt assembly

- chat session remembered skill
- skill prompt injection into agent persona
- feature-flag-driven runtime behavior

Current files:

- [`backend/app/services/chat_prompting.py`](../../backend/app/services/chat_prompting.py)
- [`backend/app/api/chat.py`](../../backend/app/api/chat.py)

## 6. Skill Import Gate Lifecycle Model

The lifecycle should be explicit and stateful.

### 6.1 Proposed persistent states

Each imported package should move through these states:

1. `imported`
   - package bytes or directory snapshot accepted by Yue
   - source recorded
   - no parse guarantee yet

2. `parsed`
   - `SKILL.md` and package structure parsed into normalized package model

3. `standard_valid`
   - passes Agent Skills structural validation

4. `yue_compatible`
   - passes Yue runtime compatibility checks
   - does not imply active

5. `activation_ready`
   - valid, compatible, and eligible for activation in Yue

6. `active`
   - selected as an active package revision in the runtime catalog

7. `inactive`
   - previously accepted but currently not active

8. `rejected`
   - import failed parsing, standard validation, or compatibility gate

9. `superseded`
   - accepted earlier revision replaced by a newer imported revision

### 6.2 Lifecycle rules

Rules should be strict:

- `imported -> parsed` only if normalization succeeds
- `parsed -> standard_valid` only if package validation succeeds
- `standard_valid -> yue_compatible` only if compatibility evaluation succeeds
- `yue_compatible -> activation_ready` only if Yue policy says activation is allowed
- `activation_ready -> active` only via explicit admin action
- `active -> inactive` only via explicit admin action
- any failed gate moves to `rejected`
- replacement of an active revision marks the prior revision as `superseded`, not deleted

### 6.3 Why `availability` is not enough

Current `availability` on `SkillSpec` is runtime-focused and derived from OS/bin/env checks. [`backend/app/services/skills/models.py:193`](../../backend/app/services/skills/models.py), [`backend/app/services/skills/registry.py:247`](../../backend/app/services/skills/registry.py)

That is not enough because:

- it is not persisted as an import decision
- it does not represent admin intent
- it does not capture rejected vs inactive vs superseded
- it is computed only after registration, not as an import lifecycle event

So `availability` should remain a runtime convenience field, while the import gate introduces a separate acceptance lifecycle.

## 7. First Recommended Refactoring Cut

The first cut should be small, reversible, and low-risk.

### Recommended first cut

- **Add new import-gate modules without changing runtime routing behavior**

Specifically:

1. introduce import record models
2. introduce a compatibility evaluator
3. introduce import persistence
4. introduce an import service that uses current parser/validator/registry pieces
5. keep current startup loading path temporarily intact

This gives Yue a parallel acceptance path before any major runtime rewiring.

### Why this is the right cut

It avoids the riskiest sequence:

- rewriting registry
- rewriting routing
- rewriting prompt assembly

all at once.

Instead, it creates a new seam:

- `skill core` can grow around import/validation/compatibility contracts
- Yue runtime can continue to consume activated skills from the current registry

## 8. Stage 1 Detailed Plan: Define the Acceptance Boundary

### Goal

Create the code contracts and persisted state model for the Skill Import Gate.

### Scope

- add lifecycle enums and result models
- add compatibility evaluation contract
- add import record persistence
- add non-invasive import service
- do not change selection/routing behavior yet

### Stage 1 deliverables

#### Deliverable A: import lifecycle models

Add models for:

- `SkillImportSource`
- `SkillImportRecord`
- `SkillImportLifecycleState`
- `SkillImportReport`
- `SkillCompatibilityReport`
- `SkillActivationStatus`

#### Deliverable B: compatibility evaluator

Extract Yue compatibility checks from generic registry behavior into a dedicated component.

Suggested responsibility:

- evaluate package against Yue-supported tool names
- evaluate OS / bins / env
- produce structured reasons, not only boolean availability

#### Deliverable C: import persistence

Persist import records under `YUE_DATA_DIR`, following the same atomic JSON pattern already used by:

- [`backend/app/services/agent_store.py`](../../backend/app/services/agent_store.py)
- [`backend/app/services/skill_group_store.py`](../../backend/app/services/skill_group_store.py)

Suggested files:

- `~/.yue/data/skill_imports.json`
- `~/.yue/data/skill_activation.json`

#### Deliverable D: import service contract

Add a service that accepts a package path or extracted upload path and returns:

- normalized package preview
- validation report
- compatibility report
- lifecycle result
- stored import record id

### Stage 1 file-level change map

#### New files

- `backend/app/services/skills/import_models.py`
- `backend/app/services/skills/compatibility.py`
- `backend/app/services/skills/import_store.py`
- `backend/app/services/skills/import_service.py`

#### Existing files to update lightly

- `backend/app/services/skills/models.py`
  - only if shared enums/types should live here
- `backend/app/services/skills/registry.py`
  - extract or delegate compatibility logic
- `backend/app/services/skills/__init__.py`
  - export new contracts
- `backend/app/services/skill_service.py`
  - expose import service as temporary compatibility seam

### Stage 1 acceptance criteria

1. a package can be evaluated through an explicit import path without being auto-activated
2. the system can distinguish:
   - parse failure
   - standard validation failure
   - Yue compatibility failure
   - activation-ready success
3. every import attempt produces a persisted record
4. `SkillRegistry` is no longer the only place where compatibility semantics live
5. no change in current chat runtime behavior is required for Stage 1 to pass

### Stage 1 verification

- unit tests for lifecycle transitions
- unit tests for compatibility evaluator
- unit tests for import-store persistence/recovery
- integration test: import valid package -> activation-ready record
- integration test: import standard-valid but Yue-incompatible package -> rejected record with reasons

## 9. Stage 2 Detailed Plan: Implement Admin-Facing Import Gate

### Goal

Turn the Stage 1 contracts into a minimal usable product surface.

### Scope

- explicit import endpoint
- preview endpoint
- activate / deactivate / replace endpoints
- runtime catalog should consume only active accepted packages from the new path
- startup directory scanning should be demoted from primary acceptance path

### Stage 2 deliverables

#### Deliverable A: API surface

Add APIs for:

- import skill package
- preview import result
- list imported records
- activate record
- deactivate record
- replace active skill revision

#### Deliverable B: activation persistence

Add persisted activation state separate from import record state.

Reason:

- one imported revision may exist but remain inactive
- runtime should build its active catalog from activation state, not just package presence

#### Deliverable C: runtime catalog projection

Introduce a projection step:

- active import records -> runtime `SkillRegistry`

This should become the bridge between admin acceptance and runtime use.

#### Deliverable D: startup mode split

After Stage 2, startup should support two concepts:

- source discovery for legacy/dev mode
- accepted active catalog for import-gate mode

The import-gate mode should become the preferred path.

### Stage 2 file-level change map

#### New files

- `backend/app/services/skills/runtime_catalog.py`
- `backend/app/api/skill_imports.py` or extend `backend/app/api/skills.py`

#### Existing files to update

- `backend/app/api/skills.py`
  - add import/preview/activate/deactivate/replace endpoints, or split cleanly
- `backend/app/main.py`
  - initialize import store / activation store
  - build runtime catalog from active imports
- `backend/app/services/skill_service.py`
  - wire runtime catalog and import service
- `backend/app/services/skills/registry.py`
  - narrow role to runtime index
- `backend/app/services/skills/directories.py`
  - keep only source-discovery responsibilities

### Stage 2 acceptance criteria

1. admins can import a package without manually placing files into watched runtime directories
2. a standard-valid but Yue-incompatible package is visible but cannot be activated
3. runtime uses only active accepted skill revisions in import-gate mode
4. replacing an active skill preserves lineage and marks the old revision `superseded`
5. restart does not lose import records or activation state

### Stage 2 verification

- API integration test: import -> preview -> activate -> list active
- API integration test: replace active revision -> old becomes superseded
- app restart test: activation state is restored
- smoke runtime test: active imported skill appears in routing candidates

## 10. Recommended Structure for Future Extraction

The idea of extracting this into a tiny open-source project is **feasible**, but only if the right boundary is enforced now.

### Feasibility assessment

The idea is technically plausible because the repo already has a partial skill subsystem:

- parsing is already relatively self-contained
- action policy is already relatively self-contained
- some routing logic is already generic

The blockers are not conceptual. They are structural:

- global singleton wiring in `skill_service.py`
- registry overreach
- Yue-specific agent visibility logic inside routing
- chat/session integration directly touching runtime selection state

### What makes the idea realistic

If we keep the future open-source core focused on:

- package parsing
- structural validation
- compatibility contract
- import report models
- runtime catalog primitives
- generic routing primitives

then extraction is realistic.

### What must not be dragged into the future OSS core

- FastAPI routes
- Yue startup and file watching
- `agent_store`
- `skill_group_store`
- chat session binding
- prompt composition
- feature-flag policy

### Recommended extraction sequence

1. Stage 1: define lifecycle and import contracts
2. Stage 2: make Yue consume accepted active imports
3. Stage 3: isolate runtime catalog and compatibility seams
4. Stage 4: move generic code behind a package-style API
5. Stage 5: run extraction spike

This is feasible.

Trying to extract before Stage 1 and Stage 2 is not recommended.

## 11. Risks and Rollback Strategy

### Risk 1: dual path confusion

During transition, both:

- directory-based auto-load
- import-gate activation

may coexist.

Mitigation:

- add an explicit feature flag for import-gate runtime mode
- keep legacy directory loading as fallback until Stage 2 stabilizes

### Risk 2: registry bloat gets worse before it gets better

If import logic is added directly into `SkillRegistry`, coupling will increase.

Mitigation:

- treat `SkillRegistry` as runtime catalog only
- put import lifecycle and persistence in separate modules from the start

### Risk 3: routing regressions caused by early activation rewiring

If runtime selection is changed before import-state modeling is stable, regressions will be hard to diagnose.

Mitigation:

- do not touch routing heuristics in Stage 1
- only switch the source of routable skills after activation persistence is stable

### Risk 4: extraction goal distorts near-term delivery

Optimizing too early for a future open-source package may slow product progress.

Mitigation:

- extract boundaries in code, not in repo layout yet
- prefer interface seams over large file moves in Stage 1

## 12. Final Recommendation

The project is ready for a **conservative, low-risk Stage 1 implementation**.

The most important design choice is:

- **treat Skill Import Gate as a new acceptance subsystem, not as a small extension of the current loader**

The most important code choice is:

- **keep reusable skill logic inside `backend/app/services/skills/`, but stop letting `SkillRegistry` own every skill-related concern**

The first concrete move should be:

- add import lifecycle models
- add compatibility evaluator
- add import persistence
- add import service

without rewriting routing or prompt assembly yet.
