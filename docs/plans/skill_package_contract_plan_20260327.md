# Skill Package Contract Plan (2026-03-27)

## 1. Purpose

This document defines the next implementation target for Yue's skill system:

1. establish a **package-first skill contract**
2. keep current markdown skills working during migration
3. create a stable foundation for resource loading, tool-backed action metadata, provider overlays, and later delegation

This plan follows the updated roadmap in [`docs/plans/Skill_Feature_Roadmap.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/Skill_Feature_Roadmap.md).

## 1.1 Boundary Update (2026-03-28)

This plan now operates under an explicit product boundary:

1. Skills may only orchestrate Yue's already-available built-in tools and MCP tools.
2. Skills may expose structured action/workflow metadata and may target platform tools, including `builtin:exec`, when those tools are explicitly available to the agent/runtime.
3. Skill packages must not introduce a separate skill-owned runtime, dynamic code creation path, or custom script execution surface outside Yue's platform tools.
4. `scripts/` may remain in the package contract as compatibility/resource metadata, but not as an execution surface Yue will run.

## 2. Why This Is The Next Step

The current skill runtime already supports:

1. layered discovery
2. markdown parsing
3. skill routing
4. tool gating
5. prompt injection

The biggest current gap is that Yue does not yet have a formal package contract for the richer skill directories already appearing in:

1. [`backend/data/skills/ppt-expert/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert)
2. [`backend/data/skills/system-ops-expert/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/system-ops-expert)
3. [`backend/data/skills/code-simplifier/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/code-simplifier)
4. [`data/skills/project-status-auditor/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/data/skills/project-status-auditor)

Without a stable package contract, the loader and registry cannot safely grow beyond prompt-only skills.

## 3. Design Goals

The contract should:

1. preserve the simplicity of `SKILL.md`
2. make bundled resources first-class
3. support provider-specific overlays without custom code
4. enable progressive disclosure by loading tier
5. support safe tool-backed action metadata without redesigning the package shape
6. preserve backward compatibility with flat `.md` skills during migration

## 4. Recommended Canonical Package Structure

Preferred long-term structure:

```text
<skill-name>/
├── SKILL.md
├── manifest.yaml
├── scripts/                      # optional compatibility metadata, not executed by Yue
├── references/
├── assets/
├── templates/
├── agents/
│   ├── openai.yaml
│   ├── anthropic.yaml
│   └── local.yaml
└── tests/
```

Rules:

1. `SKILL.md` remains the human-authored source of core instructions.
2. `manifest.yaml` becomes the machine-readable package contract.
3. `scripts/` contains compatibility metadata or externally managed resources, not code Yue executes.
4. `references/` contains files that may be lazily mounted or summarized.
5. `assets/` and `templates/` contain reusable output resources.
6. `agents/` contains provider/model/agent overlays.
7. `tests/` is optional but strongly recommended for mature built-in skills.

## 5. Contract Levels

### 5.1 Level 0: Legacy Flat Markdown Skill

Example:

1. `backend/data/skills/backend-api-debugger.md`

Behavior:

1. Still supported during migration.
2. Parsed into a synthetic package with no bundled resources.
3. Marked internally as `format = "legacy_markdown"`.

### 5.2 Level 1: Basic Package Skill

Required:

1. package directory
2. `SKILL.md`

Optional:

1. `manifest.yaml`
2. `scripts/`
3. `references/`
4. `assets/`
5. `templates/`
6. `agents/`

Behavior:

1. If `manifest.yaml` is absent, the loader derives a minimal manifest from `SKILL.md` plus discovered files.

### 5.3 Level 2: Fully Declared Package Skill

Required:

1. package directory
2. `SKILL.md`
3. `manifest.yaml`

Behavior:

1. Loader validates declared resources against on-disk files.
2. Registry exposes the normalized package manifest.
3. Provider overlays and action definitions are enabled.

## 6. Division Of Responsibility Between `SKILL.md` And `manifest.yaml`

### `SKILL.md` should own

1. human-readable skill instructions
2. prompt sections like system prompt, instructions, examples, failure handling
3. author-oriented narrative guidance

### `manifest.yaml` should own

1. package metadata and format version
2. declared resources
3. action definitions
4. provider overlay declarations
5. compatibility and install requirements
6. loading policy hints
7. tool/MCP binding hints for non-executing actions

This split keeps authored instructions readable while keeping runtime structure machine-safe.

## 7. Proposed Manifest Schema

Minimum target shape:

```yaml
format_version: 1
name: ppt-expert
version: 1.0.0
description: Generate professional PPTX decks from structured slide JSON.
entrypoint: system_prompt

capabilities:
  - pptx-generation
  - presentation-design

loading:
  summary_fields:
    - name
    - description
    - capabilities
  default_tier: prompt

requirements:
  os: [darwin, linux]
  bins: []
  env: []

resources:
  references:
    - path: references/guide.md
      kind: markdown
      load_tier: reference
  scripts:
    - id: generate
      path: scripts/generate_pptx.py
      runtime: python
      load_tier: action
      safety: workspace_write
      metadata:
        executable_by_yue: false
  templates: []
  assets: []

overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml

actions:
  - id: generate
    resource: scripts/generate_pptx.py
    input_schema: {}
    output_schema: {}
    approval_policy: tool:builtin:ppt_generate
```

## 8. Proposed Runtime Models

Recommended additions to the backend model layer:

1. `SkillPackageSpec`
2. `SkillResourceSpec`
3. `SkillReferenceSpec`
4. `SkillScriptSpec`
5. `SkillTemplateSpec`
6. `SkillOverlaySpec`
7. `SkillActionSpec`
8. `SkillLoadingPolicy`

Recommended relationship:

1. keep `SkillSpec` as the prompt-facing normalized view for the current runtime

## 9. Implementation Status Snapshot (2026-03-28)

Completed high-value stories in the current implementation:

1. package-first skill contract with legacy markdown compatibility
2. parser, registry, and provider/model overlays
3. tool-backed action descriptor, preflight, approval, and runtime lifecycle
4. `requested_action` chat runtime integration with platform-tool continuation, including `builtin:exec`
5. action event persistence, `action_states`, and state lookup APIs
6. stable `invocation_id` support so repeated invocations of the same action no longer overwrite each other
7. frontend action history grouped by `skill.action`, with invocation history visible per group
8. frontend approval controls, structured action detail sections, search, filtering, summary stats, and collapsible invocation history
9. action argument validation extended beyond the original flat subset to include nested objects, arrays, defaults, and path-aware validation errors
10. first tool-specific result renderer shipped for `builtin:exec`, including stdout/stderr/exit-code sectioning

Still remaining after these stories:

1. richer JSON Schema semantics such as bounds, patterns, nullable handling, and combinators like `oneOf/allOf`
2. additional tool-specific result renderers beyond `builtin:exec`
3. deeper action detail UX such as dedicated drill-down views, pinning, or exportable action traces

Current recommendation:

1. treat the current contract/runtime/UI baseline as the primary high-value milestone
2. treat further schema breadth and additional tool-specific renderers as enhancement follow-ups rather than blockers for this plan
3. introduce `SkillPackageSpec` as the package-level source of truth
4. derive `SkillSpec` from `SkillPackageSpec` during normalization

This avoids breaking current prompt/runtime call sites too early.

## 9.1 Enhancement Backlog For Follow-Up Work

The remaining work is no longer about making the package/action contract viable. The current contract is already usable. The follow-up work should therefore be treated as **enhancement delivery**, with each enhancement scoped as an independent track.

Recommended follow-up order:

1. broaden action argument schema support
2. add more tool-specific result renderers
3. deepen action trace/detail UX

The goal of this section is to let a new thread continue implementation without needing to reconstruct intent from chat history.

### Enhancement Track A: Broader Action Argument Schema Support

#### Why it still matters

The current validator already supports:

1. nested objects
2. arrays
3. defaults
4. path-aware validation errors
5. basic `type`, `enum`, `required`, and `additionalProperties`

That is enough for a stable baseline, but it still leaves out several schema features that real tool-backed workflows often need.

#### Desired product outcome

Skills should be able to describe richer tool parameter contracts without resorting to ad hoc validation in custom code. When a schema fails, the user-facing error should remain:

1. deterministic
2. path-aware
3. stream-safe
4. approval/runtime compatible

#### Suggested scope

Add support incrementally for:

1. `nullable` / explicit null handling
2. string constraints
   - `minLength`
   - `maxLength`
   - `pattern`
3. numeric constraints
   - `minimum`
   - `maximum`
4. array constraints
   - `minItems`
   - `maxItems`
5. schema combinators only if needed after the simpler constraints land
   - `oneOf`
   - `allOf`
   - `anyOf`

#### Suggested implementation locations

- [backend/app/services/skills/policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
- [backend/tests/test_skill_foundation_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
- [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py)

#### Suggested implementation rules

1. keep the validator as a **bounded subset**, not a full JSON Schema engine
2. add each constraint only when its runtime and UX behavior is clear
3. keep `validated_arguments` as the single normalized payload that later runtime stages use
4. keep all validation failures expressible as flat string messages, even if richer internal structure is introduced

#### Acceptance criteria

1. nested path-aware errors still work after new constraints land
2. blocked requested-action flows still stop before tool invocation
3. SSE/user-visible errors remain readable and stable
4. existing simple-schema tests continue to pass unchanged

#### Risks

1. validator complexity could grow into an accidental full schema engine
2. inconsistent precedence between defaults and combinators could create confusing behavior
3. error messaging could become too verbose for SSE if not kept concise

### Enhancement Track B: Additional Tool-Specific Result Renderers

#### Why it still matters

The current UI now has:

1. grouped invocation history
2. structured detail sections
3. a first dedicated renderer for `builtin:exec`

That proves the rendering pattern works, but only one tool currently benefits from it.

#### Desired product outcome

For common platform tools, the action panel should present results in a way that matches the tool's actual semantics, instead of always falling back to generic text or generic JSON blocks.

#### Suggested next renderer candidates

1. document retrieval / docs read style tools
   - render matched path
   - render excerpts separately from metadata
2. search-style tools
   - render result list / result count / top hits
3. PPT or artifact-generation tools
   - render output path, generation status, summary metadata

#### Suggested implementation locations

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/components/IntelligencePanel.actions.test.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.actions.test.ts)

If result shape normalization is needed later, consider also:

- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

#### Suggested renderer architecture

1. keep a generic fallback renderer
2. add a per-tool mapping layer keyed by `mapped_tool`
3. keep renderers display-only at first
4. avoid changing backend payload shapes unless a tool result is impossible to render reliably from the current result string/object

#### Acceptance criteria

1. generic tools still render safely
2. tool-specific rendering never hides raw information needed for debugging
3. result rendering remains compatible with replayed historical events
4. tests cover both success and failure payloads where relevant

#### Risks

1. overfitting renderers to test data instead of real tool outputs
2. backend payload drift if frontend has to guess too much
3. too many bespoke renderers could become hard to maintain without a small shared abstraction

### Enhancement Track C: Deeper Action Trace / Detail UX

#### Why it still matters

The current panel is now strong enough for day-to-day inspection, but longer-running sessions may still outgrow a compact side panel.

#### Desired product outcome

Users should be able to inspect action history as a real trace, not just as a dense stack of invocation cards. The main next step is better drill-down, not more summary chips.

#### Suggested scope

1. dedicated invocation detail drill-down
   - open/close within panel, or modal/drawer
2. pinned focus state for one invocation while keeping list context
3. export/copy trace payload for debugging or support handoff
4. improved timestamp / ordering cues for long sessions

#### Suggested implementation locations

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/pages/Chat.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/Chat.tsx)
- [frontend/src/hooks/useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts)

#### Suggested implementation rules

1. do not replace the current compact grouped list
2. add drill-down as a second-level interaction
3. keep approval actions accessible from both compact and expanded views
4. preserve compatibility with historical events that only have partial metadata

#### Acceptance criteria

1. a user can inspect one invocation in depth without losing the broader group context
2. action arguments, validation errors, requirements, result sections, and approval metadata all remain visible
3. long sessions remain performant and readable

#### Risks

1. too much UI complexity inside the side panel
2. duplicated state if drill-down is implemented separately from grouped list state
3. making the panel powerful but visually noisy

### Enhancement Track D: Optional Cleanup And Normalization

This track is optional and should only be taken if the team wants extra polish after Tracks A-C.

Potential work:

1. normalize more result payloads before they hit the frontend
2. reduce duplicated helper logic inside `IntelligencePanel.tsx`
3. split action rendering helpers into a dedicated module if the file grows further
4. add small benchmark/regression coverage for large action histories

#### Suggested implementation locations

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/hooks/chat/chatStream.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/chat/chatStream.ts)
- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

## 9.2 Suggested Execution Checklist For New Threads

This section turns the enhancement backlog into concrete rounds of work so a new thread can start implementation immediately.

### Round 1: Broaden Schema Support

#### Primary objective

Extend the current argument validator from the existing nested-object baseline to cover the most practical missing constraints without turning it into a full JSON Schema engine.

#### Recommended scope

1. add nullable/null handling
2. add string constraints
   - `minLength`
   - `maxLength`
   - `pattern`
3. add numeric constraints
   - `minimum`
   - `maximum`
4. add array constraints
   - `minItems`
   - `maxItems`

#### Files to start with

- [backend/app/services/skills/policy.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py)
- [backend/tests/test_skill_foundation_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py)
- [backend/tests/test_api_chat_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py)

#### Deliverables

1. validator support for the listed constraints
2. path-aware validation messages for new constraints
3. blocked requested-action API coverage for at least one nested failure path
4. regression coverage proving existing validator behavior still passes

#### Acceptance criteria

1. invalid requests still stop before tool invocation
2. `validated_arguments` remains the normalized handoff payload
3. new validation errors remain readable in SSE and UI

### Round 2: Add More Tool-Specific Renderers

#### Primary objective

Move beyond the current `builtin:exec` renderer and make the action panel better at presenting results from other common platform tools.

#### Recommended scope

1. pick one additional high-traffic tool family first
   - doc/search style tool is the best next candidate
2. add one renderer for success payloads
3. add one renderer for failure or partial-result payloads
4. keep generic fallback intact

#### Files to start with

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/components/IntelligencePanel.actions.test.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.actions.test.ts)

Possible backend touchpoint only if rendering is impossible with the current payload:

- [backend/app/api/chat_stream_runner.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_stream_runner.py)

#### Deliverables

1. one new renderer beyond `builtin:exec`
2. helper tests for both renderer selection and output formatting
3. no regression to generic section rendering

#### Acceptance criteria

1. raw information remains accessible for debugging
2. replayed historical events still render correctly
3. generic fallback still handles unknown tools safely

### Round 3: Add Invocation Drill-Down

#### Primary objective

Give one invocation a deeper inspection view without sacrificing the compact grouped list already built into the side panel.

#### Recommended scope

1. add an invocation drill-down entry point
   - inline expansion, side drawer, or modal
2. show the full invocation detail payload
   - args
   - validation errors
   - requirements
   - tool result/error sections
   - approval metadata
3. keep approve/reject accessible from the focused view

#### Files to start with

- [frontend/src/components/IntelligencePanel.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/IntelligencePanel.tsx)
- [frontend/src/pages/Chat.tsx](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/pages/Chat.tsx)
- [frontend/src/hooks/useChatState.ts](/Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/hooks/useChatState.ts)

#### Deliverables

1. second-level invocation view
2. tests covering invocation selection and visible detail behavior
3. no regression to compact grouped browsing

#### Acceptance criteria

1. users can inspect one invocation deeply without losing group context
2. approval flow still works from the detailed view
3. long-session readability remains acceptable

### Round 4: Optional Follow-Up Round

Only take this round after Rounds 1-3 are complete or explicitly deprioritized.

#### Candidate items

1. combinator support such as `oneOf/allOf/anyOf`
2. more renderer coverage for artifact-generation or search-like tools
3. export/copy trace payloads
4. helper extraction / component cleanup
5. large-history regression coverage

#### Recommendation

Treat Round 4 as enhancement polish, not as a blocker for closing the current package/action contract line.

## 10. Loading Tiers

To support progressive disclosure, every normalized skill package should expose loading tiers:

### Tier 1: Summary

Contains:

1. name
2. description
3. capabilities
4. availability
5. source metadata
6. lightweight trigger metadata

### Tier 2: Prompt

Contains:

1. Tier 1 fields
2. prompt sections from `SKILL.md`
3. allowed tools
4. high-level action/reference summaries

### Tier 3: Reference

Contains:

1. selected reference file contents or summaries
2. selected examples/templates

### Tier 4: Action

Contains:

1. structured action definitions
2. tool-binding metadata
3. compatibility path/runtime/policy metadata

The current implementation roughly supports Tier 1 and Tier 2.  
This plan formalizes Tiers 3 and 4.

## 10. Overlay Resolution Rules

Provider overlays should merge in this order:

1. base package from `SKILL.md` and `manifest.yaml`
2. provider overlay from `agents/<provider>.yaml`
3. workspace layer override
4. user layer override

Rules:

1. overlays may add or replace prompt blocks
2. overlays may narrow tool policies
3. overlays may not silently broaden dangerous action permissions
4. effective package config should record its resolution chain for debugging

## 11. Legacy Compatibility Rules

During migration:

1. flat `.md` skills remain loadable
2. package directories without `manifest.yaml` remain loadable
3. the registry should expose `format` and `package_completeness` so the UI and tests can distinguish:
   - legacy markdown
   - basic package
   - full package

Suggested compatibility window:

1. keep flat `.md` support for at least one full refactor cycle
2. stop adding new built-in skills as flat `.md`
3. migrate built-ins first, workspace/user skills second

## 12. Validation Rules

### Phase 1 validation

Validate:

1. `SKILL.md` exists for package skills
2. frontmatter fields are valid
3. declared resource paths stay inside the package root
4. overlay files exist if declared
5. duplicate action ids are rejected

### Phase 2 validation

Validate:

1. action runtime types are supported
2. input/output schema shape is valid
3. loading tiers are valid
4. references and templates have known kinds
5. incompatible manifest/runtime versions are flagged

## 13. API And Registry Changes

Recommended registry additions:

1. `list_packages()`
2. `get_package(name, version=None)`
3. `get_package_manifest(name, version=None)`
4. `get_package_resources(name, version=None)`
5. `resolve_reference(name, relative_path, version=None)`
6. `resolve_overlay(name, provider, version=None)`

Recommended API additions later:

1. package detail endpoint
2. package resource endpoint
3. package validation endpoint

The existing `SkillSpec` endpoints can remain for prompt/runtime compatibility.

## 14. Migration Plan

### Phase 1. Schema and parsing

1. add package models
2. add manifest parser
3. detect package format level
4. keep existing `SkillSpec` output stable

### Phase 2. Registry normalization

1. store package manifest alongside current prompt-facing skill spec
2. expose normalized resource manifest
3. add tests for package discovery and overlays

### Phase 3. Built-in migration

1. convert built-in flat markdown skills to package directories where valuable
2. add `manifest.yaml` to richer built-in packages first
3. leave simple skills on legacy path until there is clear benefit

### Phase 4. Runtime adoption

1. upgrade prompt assembly to use loading tiers
2. resolve provider overlays at runtime
3. surface resource and package status in the UI

### Phase 5. Action adoption

1. add structured action definitions
2. integrate policy-aware action execution
3. add audit logging

## 15. Testing Strategy

High-value tests:

1. package discovery with `SKILL.md` and `manifest.yaml`
2. package discovery without `manifest.yaml`
3. legacy flat markdown fallback
4. resource path validation
5. provider overlay merge behavior
6. layer override resolution across builtin/workspace/user
7. manifest-to-`SkillSpec` normalization
8. loading-tier visibility

## 16. Non-Goals For This Plan

This document does not yet define:

1. final subagent orchestration behavior
2. final script sandbox implementation
3. full package marketplace/distribution design

Those should build on this contract, not be mixed into it.

## 17. Recommended Immediate Implementation Order

The best next implementation sequence is:

1. add the package models and manifest parser
2. add registry support for normalized package manifests
3. add tests for package format detection and resource discovery
4. migrate one rich built-in skill as the reference implementation

Suggested pilot skill:

1. [`backend/data/skills/ppt-expert/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/ppt-expert)

Why:

1. it already has `SKILL.md`
2. it already has scripts
3. it has a narrow and concrete workflow
4. it is a strong candidate for later action-based execution

## 18. Bottom Line

If the goal is a Claude Code or OpenClaw grade skill system, the next correct move is not to add more prompt logic first.

The next correct move is to define and implement a **real skill package contract** that the rest of the system can trust.
