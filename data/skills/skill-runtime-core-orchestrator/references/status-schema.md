# Status Schema

The status file is the continuity layer for this skill.

Default path:

- `docs/execution/skill-runtime-core-orchestrator-status.md`

## Required Sections

The file should contain these sections:

1. `Objective`
2. `Locked Scope`
3. `Source Docs`
4. `Current Stage`
5. `Current Batch`
6. `Completed`
7. `Pending`
8. `Parallelizable Candidates`
9. `Blockers`
10. `Latest Verification`
11. `Scope Drift Check`
12. `Recommended Next Batch`
13. `Decision Log`

## Update Rules

On every successful batch:

- move completed items from `Current Batch` or `Pending` into `Completed`
- keep unfinished items in `Pending`
- rewrite `Current Batch` to match the next in-progress batch, or mark it complete
- update `Latest Verification`
- update `Scope Drift Check`
- append a short line to `Decision Log`

On blocked runs:

- leave unfinished work in `Pending`
- add the blocker to `Blockers`
- update `Current Batch` to show blocked status
- append a short blocker note to `Decision Log`

## Style Rules

- keep items short and executable
- prefer task ids like `A1`, `A3`, `B1`
- do not replace historical notes with prose summaries
- preserve prior completion evidence unless it becomes wrong
