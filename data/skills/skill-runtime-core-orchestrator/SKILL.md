---
name: skill-runtime-core-orchestrator
description: Use when continuing the Yue Skill Runtime Core externalization and Stage A/B execution line. This skill reads the locked plan and status files, selects the next highest-value batch, evaluates safe parallelization opportunities, executes a bounded batch without expanding scope, updates project status artifacts, and reports only at batch-level checkpoints or when blocked.
---

# Skill Runtime Core Orchestrator

Use this skill when the task is to continue the Yue `Skill Runtime Core` externalization roadmap without drifting from the defined plan.

This skill is not a generic planner.
It is a bounded execution orchestrator for the current repository's `Skill Runtime Core` workstream.

## Default Scope

By default, this skill is locked to these source documents:

- `docs/plans/skill_runtime_core_externalization_plan_20260423.md`
- `docs/plans/skill_runtime_core_stage_ab_task_list_20260424.md`
- `docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md`
- `docs/architecture/Skill_Runtime_Current_Operation.md`

Default state file:

- `docs/execution/skill-runtime-core-orchestrator-status.md`

If the user explicitly redirects the workstream to another plan, switch to that plan and update the status file accordingly. Otherwise stay on this line.

## Operating Contract

Every run must follow this sequence:

1. Read the locked plan docs and the current status file.
2. Recompute remaining work.
3. Classify remaining work into:
   - `blocking`
   - `parallelizable`
   - `deferred`
   - `risky`
4. Select one bounded execution batch.
5. Execute the full batch, including validation where practical.
6. Update the status file.
7. Report only at the batch checkpoint, or earlier if blocked.

Do not re-plan the entire roadmap every run unless the current batch is completed, blocked, or invalidated.

## Batch Rules

Read `references/workflow.md` and `references/parallelization-rules.md` before selecting a batch.

Hard limits for one batch:

- Prefer 1 primary task group plus 1-3 safe parallel sidecar tasks.
- Do not cross into a later stage when the current stage still has blocking work.
- Do not expand scope because something is "nearby" or "easy to fix".
- Do not pause after every small step; pause at batch completion, true blocker, or scope-change need.

## Status Discipline

Read `references/status-schema.md` before editing the status file.

On each run:

- preserve prior completion history
- update current batch, completed items, pending items, blockers, and next batch
- record verification evidence briefly
- record any scope-drift check result

If the status file does not exist, initialize it from `assets/status-template.md`.

## Parallelization Policy

Default stance:

- be conservative about scope
- be aggressive about safe parallelization

You should actively look for parallel work each run.

Good parallel candidates:

- doc sync that does not change runtime behavior
- tests for a manifest or boundary that depends on a stable interface
- host-simulator scaffolding separate from core runtime edits
- sample files, templates, or low-risk helper scripts

Bad parallel candidates:

- multiple tasks editing the same runtime core file
- a task whose acceptance depends on another unfinished task in the same batch
- work that would force rework if the primary task changes shape

## Allowed Behavior

You may:

- execute multiple related subtasks in one batch
- edit status artifacts
- update task progress
- tighten docs when required to keep execution aligned

You must not:

- invent new stages
- silently widen the roadmap
- jump ahead to later stages because they look cleaner
- replace the locked objective with a broader refactor goal

## Recommended Helpers

If needed, use:

- `scripts/validate_status.py` to validate status structure
- `scripts/select_next_batch.py` to summarize the next candidate batch from the current status

For reusable invocation text, read:

- `references/startup-command-template.md`
- `references/standard-prompts.md`

Use the startup command template when bootstrapping a new run or re-entering context.
Use the standard prompts when continuing execution, asking for acceleration, or forcing a checkpoint.

## Batch Output Format

At the end of a successful batch, report:

1. `Completed in this batch`
2. `Verification`
3. `Updated status`
4. `Recommended next batch`

If blocked, report:

1. `Blocked by`
2. `Impact`
3. `Smallest unblock`
4. `Status updated`
