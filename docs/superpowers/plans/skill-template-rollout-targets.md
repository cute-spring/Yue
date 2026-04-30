# Skill Template Rollout Targets

## Selection Rules

- Prefer skills with existing references plus deterministic scripts.
- Prioritize migration where preflight and action observability already exist.
- Assign clear owner and acceptance criteria before implementation.

## Rollout Targets

| Target Skill | Priority | Owner | Acceptance Criteria |
| --- | --- | --- | --- |
| `json-canvas` | P1 | Runtime Team | Templateized manifest and SKILL docs; one action path covered by unit tests. |
| `ppt-expert` | P2 | DocOps Team | Script-oriented template adoption with release checklist and rollback notes. |
| `pdf-insight-extractor` | P2 | AI Infra Team | Read-only to action migration plan documented and smoke command baseline added. |
| `excel-metric-explorer` | P3 | Data Apps Team | Template structure aligned; required fields and capability levels documented. |

## Batch Plan

1. Batch 1: `json-canvas` pilot with strict RED to GREEN tests.
2. Batch 2: `ppt-expert` and `pdf-insight-extractor` in parallel.
3. Batch 3: `excel-metric-explorer` after Batch 1 and 2 retrospective.
