# Skill Feature Roadmap

*Updated on March 27, 2026*  
*Status: Current-state gap analysis and next-stage roadmap*

## 1. Goal

The product goal is to evolve Yue's current skill feature into a system closer to **Claude Code** or **OpenClaw** style skills:

1. Skills are **package-like capability modules**, not just prompt snippets.
2. Skills support **progressive disclosure** across metadata, instructions, references, scripts, and provider-specific variants.
3. Skills can safely influence both **prompt behavior** and **runtime execution behavior**.
4. Skills are composable enough to support **tooling workflows today** and **delegation/subagents later**.

## 1.1 Boundary Update (2026-03-28)

Yue's current product boundary for skills is now explicit:

1. Skills may **select, constrain, and orchestrate only the tools that Yue already exposes** through built-in tools and MCP.
2. Skills may provide **prompt blocks, references, templates, overlays, and action/workflow metadata**.
3. Skills may use existing platform tools, including `builtin:exec` when it is explicitly exposed and authorized at the platform/tool layer.
4. Skills may **not** introduce a separate skill-owned runtime, custom script runner, or any execution surface beyond the platform's existing tool and MCP surface.

This means the long-term direction in this roadmap should now be interpreted as:

1. **Yes** to package-first, tool-backed skills that stay inside Yue's platform tool boundary.
2. **Yes** to platform-level `builtin:exec` when governed as a normal built-in tool.
3. **No** to building a separate skill script runner or dynamic execution path outside the platform tool surface.

This document replaces the older "big bang" roadmap with a gap-driven roadmap based on the codebase as it exists today.

## 1.2 Current Delivery Snapshot (2026-03-28)

The current implementation has already delivered the highest-value stories for the package/action contract line:

1. package-first skill parsing and registry with legacy markdown compatibility
2. provider/model overlays
3. tool-backed action descriptors, preflight, approval, and runtime lifecycle
4. chat runtime integration for `requested_action`, including approved handoff into platform tools such as `builtin:exec`
5. persisted `skill.action.*` events, direct `action_states`, approval-token lookup, and `invocation_id`-based action identity
6. frontend action history, approval UX, structured detail sections, filters/search/summary, collapsible invocation history, and a first `builtin:exec`-specific result renderer

As a result, the roadmap items below should now be read as:

1. foundational package/action/runtime work is largely complete
2. remaining work is primarily enhancement work on schema breadth, tool-specific presentation, and deeper UX rather than missing core architecture

Recommended handoff interpretation for the next thread:

1. do not reopen the question of a skill-owned runner
2. do not re-scope the current work as incomplete foundation work
3. continue only on enhancement tracks unless product direction changes

## 2. Current Reality

Today Yue already has a meaningful skill foundation:

1. Layered skill discovery exists across `builtin`, `workspace`, and `user` directories via [`backend/app/services/skills/directories.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/directories.py).
2. Skill metadata and markdown parsing exist via [`backend/app/services/skills/models.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py) and [`backend/app/services/skills/parsing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py).
3. Runtime selection exists via [`backend/app/services/skills/routing.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py).
4. Runtime tool gating exists via [`backend/app/services/skills/policy.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py).
5. Prompt assembly already injects the selected skill into chat runtime via [`backend/app/services/chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py).

In other words, Yue already has a **working prompt-time skill system**.

What it does **not** yet have is a fully realized package/runtime system like Claude Code or OpenClaw.

## 3. Current Directories

The current directory picture is:

```text
backend/data/skills/                # builtin skill packages and flat markdown skills
data/skills/                        # workspace skill packages
~/.yue/skills/                      # user skill packages (resolved at runtime)

Examples already present:
- backend/data/skills/ppt-expert/
- backend/data/skills/system-ops-expert/
- backend/data/skills/code-simplifier/
- data/skills/project-status-auditor/
```

Several package directories already include richer structure:

1. `SKILL.md`
2. `scripts/`
3. `references/`
4. `agents/`

That is good news: the directory shape is already moving in the right direction.

## 4. Main Gaps vs Claude Code / OpenClaw Style Skills

### 4.1 Skill packages are not first-class runtime objects yet

Current state:

1. The loader parses frontmatter and markdown sections from `SKILL.md` or flat `.md` files.
2. The runtime mainly consumes `system_prompt`, `instructions`, `examples`, and `constraints.allowed_tools`.

Gap:

1. `scripts/`, `references/`, `assets/`, and `agents/` are mostly just files on disk, not strongly modeled runtime resources.
2. The registry does not expose a normalized resource manifest per skill package.
3. Relative references inside skill content are not resolved as a first-class loading primitive.

Impact:

1. Skills behave mostly like prompt presets.
2. The system cannot reliably perform package-aware resource loading like Claude Code style skills do.

### 4.2 Progressive disclosure is only partial

Current state:

1. Yue distinguishes summary loading from full skill loading through `list_summaries()` and `get_full_skill()`.

Gap:

1. Progressive disclosure stops at "summary vs full markdown".
2. There is no separate lazy loading model for references, scripts, examples, templates, or provider-specific overlays.
3. There is no explicit resource budget or loading policy.

Impact:

1. We do not yet get the main context-efficiency advantage of mature skill systems.

### 4.3 Skill schema is too prompt-centric

Current state:

1. [`SkillSpec`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py) models prompts, schemas, constraints, install metadata, and a few runtime fields.

Gap:

1. There is no first-class schema for:
   - bundled scripts
   - references
   - assets/templates
   - model/provider variants
   - delegation hints
   - trigger rules
   - safety levels for executable actions
   - install/check steps with structured validation
2. The `entrypoint` field still assumes markdown section entry, not a broader skill contract.

Impact:

1. The model cannot cleanly represent advanced skill behavior without overloading ad hoc metadata.

### 4.4 Tool-backed workflows are not skill-native enough yet

Current state:

1. Skills can restrict tools through `allowed_tools`.
2. Some skill packages already include workflow metadata and script-like resources on disk.

Gap:

1. Skill actions are not yet cleanly framed as **tool-backed** platform actions.
2. There is no strict contract that skill actions must stay inside existing built-in tools and MCP capabilities.
3. Parameter schema, approval model, and audit trail are still incomplete at the skill-action level.

Impact:

1. Skills cannot yet deliver deterministic, reusable workflows while staying inside the existing platform tool boundary.

### 4.5 Selection is still basic lexical routing

Current state:

1. The router scores by skill name, description, capabilities, and explicit request matching.

Gap:

1. No semantic retrieval.
2. No trigger examples or evaluator-based scoring.
3. No provider/model compatibility ranking.
4. No confidence threshold calibration from production telemetry.
5. No multi-skill composition beyond "selected skill + always skills".

Impact:

1. Routing works for simple cases, but it is still far from robust expert-skill dispatch.

### 4.6 Package format is inconsistent

Current state:

1. Some skills are package directories with `SKILL.md`.
2. Some skills are still flat markdown files such as `backend-api-debugger.md` and `quick-research.md`.

Gap:

1. There is no single preferred packaging standard.
2. There is no migration plan from flat files to package directories.
3. There is no manifest-level validation that a package is complete.

Impact:

1. The loader has to support mixed conventions.
2. Advanced package capabilities become harder to implement consistently.

### 4.7 Skill variants and agent overlays are not integrated

Current state:

1. There is already an example of provider-related config under `backend/data/skills/code-simplifier/agents/openai.yaml`.

Gap:

1. The parser and registry do not surface agent/provider overlays as first-class variants.
2. There is no resolution order for base skill + provider overlay + user override.

Impact:

1. Skills cannot yet adapt cleanly across models/providers without hand-built code paths.

### 4.8 Operational lifecycle is incomplete

Current state:

1. Availability checks cover OS, env vars, and binaries.
2. Layered override and user-directory hot reload exist.

Gap:

1. No install flow.
2. No upgrade/migration lifecycle.
3. No integrity checks for packaged resources.
4. No packaging/export/import format.
5. No version compatibility policy between skills and app/runtime versions.

Impact:

1. The system can load local skills, but it does not yet manage them like reusable installable modules.

### 4.9 Evaluation and observability are too thin for architectural expansion

Current state:

1. The chat runtime records some skill-effectiveness metrics.

Gap:

1. No benchmark set for routing quality.
2. No before/after prompt-token measurement by skill loading tier.
3. No action-level success metrics for tool-backed action flows or references.
4. No regression suite for package resources and variant resolution.

Impact:

1. It is too early to confidently expand into subagents or executable skills without stronger eval coverage.

## 5. Direction Decision

The right direction is:

1. **Yes** to a Claude Code / OpenClaw style skill system.
2. **No** to jumping first into coordinator/subagent orchestration as the main next step.

The current bottleneck is not service modularity anymore.  
The current bottleneck is that Yue's skill model is still closer to **"prompt bundles with routing"** than **"full capability packages"**.

So the next roadmap should prioritize:

1. package model
2. resource loading
3. tool-backed non-executing actions
4. richer routing/evals
5. only then multi-agent delegation

## 6. Recommended Target Package Format

Preferred long-term standard:

```text
<skill-name>/
├── SKILL.md
├── manifest.yaml                 # optional at first, likely required later
├── scripts/                      # optional legacy/package metadata only; not executable by Yue
├── references/
├── assets/
├── templates/
├── agents/
│   ├── openai.yaml
│   ├── anthropic.yaml
│   └── local.yaml
└── tests/
```

Notes:

1. `SKILL.md` should remain the human-authored core instructions file.
2. `manifest.yaml` should become the machine-readable package contract once the schema expands.
3. Flat markdown skills may remain supported temporarily as a backward-compatible legacy format.

## 7. Gap-Driven Roadmap

### Phase A. Standardize the package contract

Goal:

1. Move from mixed markdown/package conventions to a clear package-first model.

Work:

1. Define a canonical package format with required and optional files.
2. Extend `SkillSpec` into a broader package model or introduce `SkillPackageSpec`.
3. Add structured resource descriptors for scripts, references, assets, templates, and agent overlays.
4. Keep flat `.md` skills as legacy-compatible input only.

Deliverables:

1. updated skill schema
2. package validator
3. migration guide from flat markdown skills to package directories

### Phase B. Make bundled resources first-class

Goal:

1. Treat package resources as loadable runtime objects, not opaque files.

Work:

1. Add resource manifest generation in the registry.
2. Add APIs/helpers for resolving bundled references by skill and relative path.
3. Add lazy loading tiers:
   - metadata
   - core prompt sections
   - selected references/examples
   - executable actions/assets
4. Add prompt assembly rules for when references should be mounted or summarized.

Deliverables:

1. skill resource manifest model
2. resource resolver service
3. progressive disclosure policy implementation

### Phase C. Introduce tool-backed skill actions safely

Goal:

1. Let skills provide deterministic workflows without introducing arbitrary code execution.

Work:

1. Add first-class `actions` schema with parameters and policies.
2. Define safety classes:
   - read-only
   - workspace-write
   - approval-required
3. Bind skill actions only to existing built-in tools or MCP tools.
4. Persist audit logs for skill action usage.

Deliverables:

1. `SkillActionSpec`
2. tool-backed action contract with policy checks
3. integration tests for action state, approvals, and tool-binding validation

### Phase D. Upgrade routing from lexical match to skill retrieval

Goal:

1. Make skill selection more reliable and scalable.

Work:

1. Add trigger examples and richer metadata to skills.
2. Add semantic matching on top of lexical scoring.
3. Rank by availability, provider compatibility, tool compatibility, and confidence.
4. Support multi-skill plans where appropriate, not just one selected skill.

Deliverables:

1. improved router
2. routing eval dataset
3. production telemetry dashboard for match quality

### Phase E. Add provider and agent overlays

Goal:

1. Allow one skill package to adapt to different models and agent styles cleanly.

Work:

1. Load `agents/*.yaml` overlays.
2. Define merge order:
   - base package
   - provider overlay
   - workspace override
   - user override
3. Support provider-specific prompt blocks, tool preferences, and action policies.

Deliverables:

1. overlay resolution system
2. provider-aware packaging tests

### Phase F. Package management and UX

Goal:

1. Make skills installable and maintainable as reusable modules.

Work:

1. Add install/upgrade/remove flows.
2. Add integrity checks and compatibility warnings.
3. Surface package health, requirements, and available actions in the UI.
4. Add authoring docs and skill templates.

Deliverables:

1. package lifecycle commands/APIs
2. UI for package inspection and management

### Phase G. Delegation and multi-agent composition

Goal:

1. Introduce subagents only after the package/runtime model is mature enough.

Work:

1. Add delegation hints to skills.
2. Define coordinator policy and result-merging contracts.
3. Allow some skills to be "worker skills" and others to be "coordinator skills".

Deliverables:

1. delegation-ready skill contracts
2. limited-scope subagent orchestration prototype

## 8. Immediate Next 4 Tasks

If we want the fastest path toward the target system, the best next tasks are:

1. Add a new doc that defines the canonical **skill package contract** and legacy compatibility rules.
2. Extend the skill schema to model **bundled resources** explicitly instead of leaving them implicit on disk.
3. Update the loader/registry so every skill exposes a **resource manifest**.
4. Add tests covering:
   - package resource discovery
   - provider overlay resolution
   - progressive loading tiers
   - action policy validation

## 9. Success Criteria

We should evaluate the roadmap against measurable outcomes:

1. A skill package can declare and expose scripts, references, assets, and overlays without custom app code.
2. Prompt assembly can load only the needed tier of a skill package.
3. The router selects the right skill with improved confidence on a maintained eval set.
4. Skill-provided actions run through explicit policy gates and audit logs.
5. A new skill package can be added mostly by authoring files, not by modifying backend code.

## 10. Bottom Line

Yue is already on the right path, but it is only at the **prompt-skill foundation** stage.

The biggest gaps are not in file modularization anymore.  
The biggest gaps are:

1. package contract
2. resource modeling
3. executable actions
4. richer routing
5. provider overlays

That is the right next direction if the goal is to approach a Claude Code or OpenClaw level skill system.
