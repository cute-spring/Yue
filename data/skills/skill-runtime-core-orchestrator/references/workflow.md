# Workflow

This skill operates in bounded execution batches.

## Required Batch Sequence

1. Read current source-of-truth docs:
   - externalization plan
   - current task list
   - reuse guide
   - current operation doc
   - status file
2. Determine whether the current batch is:
   - still active
   - finished
   - blocked
   - invalidated
3. If active and still valid:
   - continue that batch
4. Otherwise:
   - choose the next batch from the highest-priority unfinished work
5. Execute the batch.
6. Verify the batch.
7. Update the status file.
8. Report once at the checkpoint.

## Batch Selection Rules

Choose the next batch using this priority order:

1. blocking unfinished work in the current stage
2. tasks that unlock later tasks
3. tasks that reduce ambiguity or coordination cost
4. safe sidecar tasks that can be parallelized with the primary task

## Stop Conditions

Stop and checkpoint when:

1. the current batch is complete
2. a true blocker is found
3. the batch would exceed the locked scope
4. the next step would require changing the accepted plan

Do not stop merely because one subtask completed.
