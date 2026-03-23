---
name: refactor-with-plan
description: Analyze a code file or module for modularization, cohesion, coupling, and refactor risk. Use when the user wants to enhance, split, simplify, or restructure existing code, and especially when the work should start with a dedicated change plan under docs/plans before any code changes.
---

# Refactor With Plan

Follow a plan-first refactor workflow. Treat this skill as the default approach for medium or large refactors where behavior stability matters.

## Core Workflow

1. Inspect the target code and surrounding call sites before proposing structure changes.
2. Identify current responsibilities, dependency directions, hidden state, test seams, and likely regression risks.
3. Before editing code, create a dedicated plan document under `docs/plans/`.
4. In that document, capture:
   - current responsibilities and pain points
   - proposed target structure and file boundaries
   - phased migration plan
   - risk assessment
   - test and regression strategy
   - rollout or PR split recommendation
5. Summarize the recommendation for the user and wait for approval before changing code.
6. After approval, implement in low-risk phases:
   - start with structure-only extraction
   - preserve public behavior and imports when practical
   - run focused regression checks after each phase
   - add tests around newly exposed seams before deeper refactors
7. After implementation, update the same plan document with:
   - what actually changed
   - deviations from the original plan
   - final validation results
   - follow-up suggestions

## Refactor Principles

- Prefer incremental refactoring over big-bang rewrites.
- Optimize for higher cohesion and lower coupling, not just smaller files.
- Preserve external behavior unless the user explicitly approves behavior changes.
- Keep entrypoints thin and push orchestration into well-bounded modules.
- Remove thin wrapper helpers only when doing so improves clarity without increasing coupling.
- Call out global state, singleton dependencies, and import stability risks explicitly.

## Plan Document Pattern

Use a dedicated file in `docs/plans/` named after the target and date, such as:

- `docs/plans/<target>_modularization_plan_YYYYMMDD.md`
- `docs/plans/<target>_refactor_plan_YYYYMMDD.md`

Keep the plan practical. It should help execution, review, and rollback.

## Testing Pattern

- Start with the narrowest regression checks that protect existing behavior.
- Add unit tests for newly extracted helpers, state objects, or runners.
- Expand to broader integration coverage before riskier internal restructuring.
- If an existing test is flaky or blocked by environment issues, isolate and fix that before trusting it as regression protection.

## Response Pattern

When this skill is triggered:

1. Begin by explaining that you will inspect the target and write a dedicated plan first.
2. Do not jump straight into code edits.
3. After writing the plan, give the user a concise recommendation and ask for approval.
4. During execution, provide short progress updates and explain each migration phase.
5. Close by summarizing outcome, verification, and remaining risks.

## Typical Triggers

Examples of requests that should trigger this skill:

- "Please refactor this file into smaller modules."
- "Can we make this code more cohesive and less coupled?"
- "Analyze this service and propose a safer restructuring plan."
- "Enhance this module, but write a dedicated change plan first."
- "Use the same approach we used for chat.py on this file."
