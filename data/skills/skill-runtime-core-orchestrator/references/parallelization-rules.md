# Parallelization Rules

The goal is to accelerate delivery without creating hidden coupling or rework.

## Classify Work

Every candidate task must be classified as one of:

- `blocking`
- `parallelizable`
- `deferred`
- `risky`

## Safe To Parallelize

Tasks are safe to parallelize when all of these are true:

1. they do not edit the same file set
2. they do not depend on a not-yet-written interface from another task in the same batch
3. they can be verified independently
4. failure in the sidecar task does not invalidate the primary task

Typical safe parallel pairs:

- boundary manifest creation + boundary test skeleton
- docs alignment + low-risk helper script
- status file refresh + non-invasive reference updates

## Keep Serial

Tasks must stay serial when any of these are true:

1. they touch the same core runtime file
2. one task decides the public shape that the other task depends on
3. they change the same acceptance criteria
4. they are both high-risk runtime-path edits

## Batch Shape

Preferred batch shape:

- 1 primary task group
- 1-3 sidecar tasks
- 1 consolidated verification pass

Avoid:

- many tiny batches
- many unrelated tasks in one batch
- sidecar tasks that require frequent human re-approval
