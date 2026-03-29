# Skill Kernel Extraction Plan (2026-03-28)

## 1. Purpose

This document proposes a path to make Yue's current skill implementation more cohesive and more reusable across other AI projects.

The goal is not to export the current Yue skill system as-is.

The goal is to:

1. identify the parts that already behave like a reusable skill kernel
2. separate those parts from Yue-specific chat/runtime/UI adapters
3. define a safe extraction sequence that preserves the current Yue product behavior

This plan should be read together with:

1. [`docs/plans/skill_package_contract_plan_20260327.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [`docs/plans/skill_action_runtime_modularization_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_action_runtime_modularization_plan_20260328.md)
3. [`docs/plans/skill_service_modularization_plan_20260323.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_service_modularization_plan_20260323.md)

## 2. Why Extraction Is Worth Considering

Yue's current skill implementation already contains several capabilities that are broadly useful beyond Yue itself:

1. package-first skill contracts
2. legacy markdown compatibility
3. manifest, resource, and overlay normalization
4. action descriptors with structured input schemas
5. action preflight validation and approval gating
6. normalized action payload handoff to tools/runtime bridges

These are not inherently tied to one chat UI or one AI product.

That means Yue is now close to having a reusable `skill kernel`, but not quite there yet.

The main remaining gap is boundary clarity.

Today, the reusable parts and the Yue-specific parts are still interleaved across backend runtime orchestration, persistence, and frontend inspection flows.

## 3. Extraction Goal

The target is a layered architecture where:

1. the skill contract and runtime decision logic are framework-neutral
2. Yue-specific integrations live behind adapter interfaces
3. frontend trace/history UX remains product-specific and outside the reusable kernel

The kernel should be reusable by another AI project even if that project has:

1. a different chat runtime
2. a different tool registry
3. a different approval model
4. a different event transport
5. no React frontend at all

## 4. What Should Become The Reusable Kernel

### 4.1 Contract Models

Good kernel candidates:

1. skill package models
2. manifest models
3. resource models
4. overlay models
5. action descriptor and schema models

Current source areas:

1. [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py)
2. parts of [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)

Why reusable:

1. these models describe the skill package contract itself
2. they do not need to know about Yue chats, SSE, or React UI

### 4.2 Loader / Normalization Layer

Good kernel candidates:

1. package loading
2. markdown compatibility loading
3. manifest parsing
4. resource discovery
5. overlay normalization
6. package normalization into stable internal models

Current source area:

1. [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py)

Why reusable:

1. many AI projects need a way to load and normalize skill packages
2. this logic can remain independent from how a project executes tools

### 4.3 Validation / Policy Evaluation

Good kernel candidates:

1. action argument validation
2. nested/default-aware payload normalization
3. preflight blocking decisions
4. approval requirement evaluation

Current source area:

1. [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)

Why reusable:

1. these rules operate on contracts and input payloads
2. they are useful regardless of whether the host app is Yue or another AI product

### 4.4 Registry And Descriptor Resolution

Good kernel candidates:

1. normalized package registry
2. skill/action lookup
3. version and visibility-independent descriptor resolution

Current source area:

1. [`backend/app/services/skills/registry.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/registry.py)

Why reusable:

1. most host projects need a registry of installed/available skills
2. the registry can be made generic if Yue-specific visibility concerns are pushed outward

### 4.5 Runtime State Machine Logic

Good kernel candidates:

1. invocation identity generation
2. action lifecycle status transitions
3. normalized execution request creation
4. blocked / awaiting approval / executable decision logic

Current source areas:

1. [`backend/app/services/skills/actions.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py)
2. parts of [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

Why reusable:

1. the decision model for action execution should not depend on Yue chat transport
2. other AI products can reuse the same lifecycle semantics with different integrations

## 5. What Should Stay In Yue Adapters

These concerns should not be part of the reusable kernel.

### 5.1 Chat Runtime Integration

Keep Yue-specific:

1. mapping action lifecycle to Yue chat stream behavior
2. requested-action handling inside the current chat request flow
3. assistant message mutation and stream coordination

Current source areas:

1. [`backend/app/api/chat.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat.py)
2. [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

### 5.2 Tool Bridge Integration

Keep Yue-specific:

1. platform tool resolution
2. `builtin:*` tool invocation wiring
3. Yue-specific MCP/tool availability checks

Current source areas:

1. [`backend/app/api/chat_stream_runner.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)
2. any built-in tool bridge/runtime modules used by chat execution

### 5.3 Persistence And Event Storage

Keep Yue-specific:

1. action event persistence
2. action state projections
3. session-scoped lookup APIs
4. approval token storage if tied to Yue session/data models

Current source area:

1. [`backend/app/services/chat_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_service.py)

### 5.4 Frontend Trace And History UX

Keep Yue-specific:

1. action history grouping UX
2. focused trace drill-down
3. tool-specific result rendering cards
4. approval controls in the intelligence panel

Current source area:

1. [`frontend/src/components/IntelligencePanel.tsx`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)

## 6. Recommended Layered Architecture

Recommended end state:

### Layer A: `skill_kernel.contracts`

Responsibilities:

1. package, manifest, resource, overlay, and action models
2. compatibility-level metadata
3. stable normalized data contracts

Must not depend on:

1. FastAPI
2. chat sessions
3. persistence stores
4. React

### Layer B: `skill_kernel.loader`

Responsibilities:

1. load package directories
2. load legacy markdown skills
3. parse manifests and overlays
4. normalize discovered resources

Must not depend on:

1. tool execution
2. SSE
3. Yue chat runtime

### Layer C: `skill_kernel.validation`

Responsibilities:

1. validate action arguments
2. apply defaults and normalized payload shaping
3. evaluate preflight blocking and approval needs

Must not depend on:

1. persistence
2. frontend rendering
3. Yue-specific event payloads

### Layer D: `skill_kernel.runtime`

Responsibilities:

1. action invocation planning
2. lifecycle state transitions
3. execution request modeling
4. event model generation in a framework-neutral shape

Must not depend on:

1. FastAPI response streaming
2. Yue session ids
3. React trace UX

### Layer E: `yue_skill_adapters`

Responsibilities:

1. bridge kernel decisions into Yue chat runtime
2. map execution requests into Yue platform tools
3. persist events and state into Yue stores
4. expose Yue API and frontend views

This is where Yue-specific behavior should remain.

## 7. Required Interfaces For Reuse

To make the kernel reusable, the main work is not just moving files. The main work is defining interfaces.

Recommended interfaces:

### 7.1 `ToolExecutor`

Purpose:

1. accept a normalized execution request from the kernel
2. execute it in the host application's tool environment
3. return a normalized result or execution error

Why needed:

1. the kernel should not know how Yue invokes `builtin:exec` or any other tool

### 7.2 `ApprovalStore`

Purpose:

1. record approval requests
2. read approval decisions
3. expose approval tokens or handles back to the host app

Why needed:

1. approval persistence differs across projects

### 7.3 `ActionEventSink`

Purpose:

1. receive lifecycle events from the kernel runtime
2. let the host project decide whether to persist them, stream them, or both

Why needed:

1. the kernel should not hardcode SSE, DB writes, or chat event models

### 7.4 `SkillPackageRepository`

Purpose:

1. enumerate skill packages
2. load package contents from local disk or other sources
3. support project-specific installation/discovery strategies

Why needed:

1. not every host project stores skills exactly like Yue

### 7.5 `VisibilityResolver`

Purpose:

1. decide which normalized skills are visible to a given host runtime context

Why needed:

1. Yue agent visibility rules are product-specific and should not be pushed into the kernel core

## 8. Proposed Extraction Sequence

### Phase 1: Internal Boundary Cleanup Inside Yue

Goal:

1. clarify kernel-like boundaries before any package extraction

Work:

1. follow [`docs/plans/skill_action_runtime_modularization_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_action_runtime_modularization_plan_20260328.md)
2. extract requested-action orchestration out of chat streaming
3. split parsing/loading/validation boundaries
4. isolate chat persistence seams

Success condition:

1. Yue still behaves the same
2. kernel-shaped responsibilities become visible in the codebase

### Phase 2: Introduce Framework-Neutral Internal Interfaces

Goal:

1. convert implicit Yue assumptions into explicit interfaces

Work:

1. add `ToolExecutor`
2. add `ApprovalStore`
3. add `ActionEventSink`
4. add `SkillPackageRepository`
5. add `VisibilityResolver`

Success condition:

1. core skill logic depends on interfaces, not Yue runtime details

### Phase 3: Create A Kernel Namespace Inside The Same Repo

Goal:

1. test extraction without cross-repo churn

Work:

1. move reusable modules under an internal namespace such as:
   - `backend/app/skill_kernel/...`
   - or `backend/app/services/skill_kernel/...`
2. leave Yue adapters under:
   - `backend/app/services/yue_skill_adapters/...`

Success condition:

1. internal imports reflect the intended architecture
2. behavior remains unchanged

### Phase 4: Optional Standalone Package Extraction

Goal:

1. make the kernel consumable by other AI projects

Work:

1. only after the internal namespace stabilizes
2. define a minimal public API
3. publish or vendor as a separate package only if there is a concrete second consumer

Success condition:

1. another project can adopt the kernel without importing Yue chat/persistence/frontend code

## 9. Risks And Non-Goals

### Risks

1. extracting too early could freeze the wrong abstractions
2. moving files before interfaces are clear may just relocate coupling instead of reducing it
3. approval/event semantics may be more Yue-shaped than they initially appear

### Non-goals

1. do not make frontend intelligence UI part of the kernel
2. do not make Yue's exact SSE schema the kernel's required event transport
3. do not force all host projects to adopt Yue's session or storage model
4. do not expand feature scope while performing the extraction

## 10. Suggested Directory Shape

Illustrative target only:

```text
backend/app/
├── skill_kernel/
│   ├── contracts/
│   ├── loader/
│   ├── validation/
│   ├── runtime/
│   └── interfaces/
├── services/
│   ├── yue_skill_adapters/
│   ├── chat_action_events.py
│   ├── chat_action_states.py
│   └── ...
├── api/
│   ├── chat.py
│   └── chat_stream_runner.py
└── ...
```

This keeps the kernel and Yue adapters in one repo until the design is proven.

## 11. Regression Strategy

Before any extraction beyond internal cleanup, preserve the current Yue behavior as the freeze baseline:

1. package-first and legacy-markdown skill loading
2. action descriptor lookup
3. schema validation and defaults
4. `requested_action` blocked / approval / execution paths
5. `invocation_id` stability
6. action event persistence and state lookup APIs
7. current intelligence panel rendering for supported tool families

Recommended rule:

1. if an extraction changes one of those behaviors, treat it as a product change rather than a pure modularization step

## 12. Recommendation

Yes, Yue's current skill implementation can become meaningfully more cohesive and reusable.

The best path is:

1. first modularize the current Yue implementation into kernel-shaped boundaries
2. then introduce explicit host interfaces
3. only then consider extracting a standalone reusable package

That path gives us the benefits of reuse without destabilizing the current product branch or prematurely hardening Yue-specific assumptions into a shared library.
