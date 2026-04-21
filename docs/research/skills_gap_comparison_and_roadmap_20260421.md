# Yue Skill Strategy: Boundary, Scope, and Immediate Gaps

**Date**: 2026-04-21

## 1. Position

Yue will be a **closed internal skill consumption platform**.

This is a deliberate, hard boundary.

Yue is **not** a skill authoring platform, **not** a marketplace, **not** a multi-format compatibility layer, and **not** an enterprise governance platform in the current phase.

Yue will do one thing well:

- **Consume and run skills that follow the Agent Skills open standard**

Everything else is secondary.

## 2. What We Standardize On

Yue will align to exactly one external standard:

- **Agent Skills open standard** (`agentskills.io`)

This means:

- Yue will not build parallel compatibility paths for OpenAI-specific skill formats.
- Yue will not build parallel compatibility paths for Anthropic-specific skill formats.
- Yue will not maintain an internal intermediate format whose purpose is to smooth over multiple external standards.
- Yue will treat **Agent Skills** as the single source of truth for skill package structure and runtime expectations.

The product stance is intentionally sharp:

- **We are not building a universal skill translation layer.**
- **We are building a strong runtime and import path for one widely adopted open standard.**

## 3. What Yue Does

Yue is responsible for:

- importing Agent Skills standard skills into the platform
- parsing and validating those skills
- checking whether those skills are compatible with Yue's runtime and tool surface
- enabling and disabling available skills
- exposing skill metadata to the runtime
- selecting the right skill dynamically for a user task
- injecting and executing the selected skill safely within Yue's runtime

## 4. What Yue Does Not Do

Yue is explicitly **not** responsible for:

- creating new skills inside Yue
- editing or polishing skills inside Yue
- providing a skill IDE or skill authoring workbench
- being the place where teams iterate on prompts, references, or skill package structure
- supporting multiple vendor-specific skill formats in parallel
- providing a skill marketplace
- providing publish / release / rollback / signing workflows
- providing enterprise RBAC in the current phase
- providing compliance logging in the current phase
- providing rich sharing and distribution controls in the current phase

Skill creation and refinement happen **outside Yue**, in tools better suited to authoring, such as VS Code and other compatible IDE / agent environments.

Yue starts **after** a skill is already authored.

## 5. Platform Boundary

### 5.1 Inside Yue

The following capabilities belong inside Yue:

- skill import
- skill static validation
- Yue runtime compatibility checking
- skill registry and activation state
- skill discovery for runtime use
- dynamic skill routing
- runtime prompt injection and action execution

### 5.2 Outside Yue

The following capabilities belong outside Yue:

- skill authoring
- skill editing
- skill prompt tuning
- skill content iteration
- skill package debugging during creation
- skill design workflows
- broader community discovery and curation

In short:

- **Yue consumes skills**
- **External tools create skills**

## 6. Skill Import Gate: Minimum Required Capability Set

If Yue does not provide authoring, then the **import gate** becomes the critical product surface.

This is the smallest set of capabilities Yue must provide in order to safely and usefully consume external Agent Skills.

### 6.1 Import

Yue must be able to ingest a skill package that follows the Agent Skills standard.

Minimum expectation:

- import from a directory or uploaded package
- register the skill in Yue's internal registry

### 6.2 Static Validation

Yue must validate the package structure before activation.

Minimum expectation:

- validate `SKILL.md`
- validate required metadata blocks
- validate referenced files exist
- validate section structure and parseability

### 6.3 Runtime Compatibility Check

Standard-compatible does not automatically mean Yue-compatible.

Yue must check whether the imported skill can actually run on Yue.

Minimum expectation:

- check required tools against Yue-supported tools
- check dependencies and environment requirements
- check unsupported action or resource declarations
- produce a clear compatible / incompatible result

### 6.4 Preview

Before activation, the admin should be able to see what Yue understood.

Minimum expectation:

- skill name
- description
- capabilities
- required tools
- key references and actions
- compatibility warnings

### 6.5 Activation Control

Imported does not mean active.

Minimum expectation:

- enable skill
- disable skill
- replace skill with updated package

### 6.6 Smoke Verification

Yue should provide a minimal verification path after import.

Minimum expectation:

- confirm the skill is parseable
- confirm the skill is selectable by the runtime
- confirm the skill can be injected without runtime failure

This is not a full skill authoring testbench.
This is a **platform acceptance check**.

## 7. Current Goal

Given the boundary above, Yue's current goal is narrow and concrete:

- become a reliable **Agent Skills import and runtime platform**

That breaks down into four current workstreams:

1. **Standard-aligned import**
   - Yue should accept Agent Skills standard packages cleanly.

2. **Import gate quality**
   - Yue should reject bad packages early and explain why.

3. **Runtime compatibility clarity**
   - Yue should clearly distinguish:
   - valid standard skill
   - Yue-compatible skill
   - active skill

4. **Better dynamic skill selection**
   - Yue should improve how well it recognizes which imported skill to use for a task.

## 8. Current State vs Target

### 8.1 What We Already Have

Yue already has useful runtime foundations:

- skill loading at service startup from layered directories
- skill listing, detail lookup, reload, and selection APIs
- markdown and package-directory parsing
- support for structured fields such as requirements, compatibility, actions, and resources
- tool restriction via `allowed_tools`
- basic routing based on name / description / capabilities matching

References:

- [backend/app/main.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py:37)
- [backend/app/api/skills.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py:26)
- [backend/app/services/skills/parsing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/parsing.py:103)
- [backend/app/services/skills/routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py:8)

### 8.2 What Is Missing Relative to the New Boundary

The key point is this:

- Yue has a **loader**
- Yue does not yet have a strong **import gate**

The current gaps are:

1. **No explicit import workflow**
   - Current loading is directory-based at startup and reload time.
   - That is not yet the same thing as an admin-facing import path.

2. **No clear distinction between standard validity and Yue runtime compatibility**
   - Parsing exists.
   - Validation exists.
   - But the platform still needs a stronger acceptance layer that answers:
   - is this skill standard-valid?
   - is this skill Yue-compatible?
   - can this skill be activated safely?

3. **No focused activation lifecycle**
   - Skills can be loaded and selected.
   - But imported skill acceptance, activation state, and replacement flow are not yet clearly modeled as a product surface.

4. **Routing is still relatively shallow**
   - Current routing is mostly rule and token matching.
   - That is useful, but still weaker than what we want for dynamic skill recognition.

5. **Boundary is not yet reflected in product design**
   - The codebase still reflects an older “skills platform” direction in some places.
   - The new boundary requires a stronger conceptual reset:
   - no authoring inside Yue
   - no multi-standard ambition
   - no platformization beyond import + runtime

## 9. Immediate Gap List

If we hold ourselves strictly to the new boundary, the near-term gaps are:

- admin-facing skill import flow
- stronger Agent Skills package validation
- explicit Yue compatibility checking
- activation and replacement controls
- import-time preview and warnings
- smoke verification after import
- better skill routing quality

Everything outside this list is currently non-goal work.

That includes:

- skill creation tools
- skill editing UI
- marketplace
- sharing controls
- RBAC
- compliance logs
- signing
- rollback system
- vendor-specific compatibility adapters

## 10. Recommended Execution Order

### P0

Build the **Skill Import Gate**.

- import
- static validation
- compatibility check
- preview
- activation control
- smoke verification

### P1

Strengthen runtime selection.

- better candidate recall
- semantic reranking or lightweight model judgment
- clearer selection reasoning and fallback behavior

### P2

Tighten standard alignment.

- remove old assumptions that imply multi-standard compatibility
- align package expectations more closely with Agent Skills
- reduce platform-specific drift in how skills are loaded and interpreted

## 11. Final Definition

Yue is not where skills are authored.

Yue is where **standard skills are imported, accepted, activated, selected, and run**.

That is the boundary.
That is the product.
That is the current roadmap.
