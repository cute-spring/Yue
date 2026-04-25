# Skill Import Gate API Contract

**Date**: 2026-04-21

## 1. Purpose

This document defines the minimum API contract for Yue's `Skill Import Gate`.

It is designed to support:

- Stage 1 implementation scaffolding
- Stage 2 admin-facing import and activation flows
- future separation between reusable `skill core` and Yue-specific adapter code

This contract is intentionally narrow.

It does **not** define:

- skill authoring APIs
- marketplace APIs
- RBAC APIs
- release/signing/rollback workflows

For current execution, Stage 3/4/5 follow a **Lite-first** policy:

- keep API surface stable
- reserve extension contracts first
- avoid scope expansion in the current cycle

## 2. API Position

The `Skill Import Gate` is the **admin acceptance surface** for skills.

Its responsibility is to answer:

- what was imported
- whether it is structurally valid
- whether it is Yue-compatible
- whether it can be activated
- whether it is active now

It is separate from runtime skill selection.

So Yue should have two API planes:

### Plane A: import and acceptance

Admin-facing, lifecycle-oriented:

- import
- inspect
- activate
- deactivate
- replace

### Plane B: runtime consumption

Runtime-facing, selection-oriented:

- list routable active skills
- inspect active skill metadata
- select skill for an agent/task

Current runtime selection entrypoint is `POST /api/skills/tool/select_runtime_skill`. [`backend/app/api/skills.py`](../../backend/app/api/skills.py)

For Stage 3 Lite, runtime routing improvements should be API-neutral:

- no new public endpoints are required
- no endpoint-level contract should assume vector retrieval, LLM rerank, or multi-source federation
- no new pluggable routing abstraction is introduced in this phase
- explanation fields may be added in response payloads in a backward-compatible way

Current usability policy for small-skill-count deployment:

- keep directory loading available
- allow compatible imports to auto-activate by default
- expose a config switch `skill_import_auto_activate_enabled` so operators can fall back to explicit activation
- keep explicit deactivate/replace controls
- keep runtime routing scoped to active skills only

## 3. Resource Model

The API should revolve around three resources.

### 3.1 `SkillImportRecord`

Represents one imported package revision.

Suggested fields:

- `id: string`
- `skill_name: string`
- `skill_version: string`
- `display_name: string | null`
- `source_type: "directory"`
- `source_ref: string | null`
- `package_format: "package_directory" | "legacy_markdown"`
- `lifecycle_state: string`
- `reason_code: string | null`
- `created_at: datetime`
- `updated_at: datetime`
- `supersedes_import_id: string | null`
- `superseded_by_import_id: string | null`

### 3.2 `SkillImportReport`

Represents the evaluation result of a single import attempt.

Suggested fields:

- `import_id: string`
- `parse_status: "passed" | "failed"`
- `standard_validation_status: "passed" | "failed"`
- `compatibility_status: "compatible" | "incompatible" | "unknown"`
- `activation_eligibility: "eligible" | "ineligible"`
- `errors: string[]`
- `warnings: string[]`
- `compatibility_issues: string[]`

### 3.3 `SkillPreview`

Represents what Yue understood from the package.

Suggested fields:

- `skill_name: string`
- `skill_version: string`
- `description: string`
- `capabilities: string[]`
- `entrypoint: string`
- `required_tools: string[]`
- `requires_bins: string[]`
- `requires_env: string[]`
- `resources: {id, path, kind}[]`
- `actions: {id, tool, path, runtime, approval_policy}[]`
- `overlays: {provider, model, path}[]`
- `always: boolean | null`

## 4. Lifecycle Vocabulary

The API should expose a minimal persisted lifecycle vocabulary:

- `active`
- `inactive`
- `rejected`
- `superseded`

The key rule is:

- `availability` is a runtime convenience field
- `lifecycle_state` is an admin acceptance state

These must not be merged in the API.

## 5. Endpoint Design

Recommended path structure:

- keep existing runtime endpoints under `/api/skills`
- add import-gate endpoints under `/api/skill-imports`

This is cleaner than overloading current `skills.py` with mixed semantics.

## 5.1 Import a skill

`POST /api/skill-imports`

Creates a new import record and evaluates the package.

### Request

Supported request mode:

#### Import from staged server path

```json
{
  "source_type": "directory",
  "source_path": "/absolute/path/to/unpacked/skill"
}
```

### Response

`201 Created`

```json
{
  "import": {
    "id": "imp_01",
    "skill_name": "pdf-insight-extractor",
    "skill_version": "1.0.0",
    "source_type": "directory",
    "package_format": "package_directory",
    "lifecycle_state": "inactive",
    "reason_code": "manual_activation_required",
    "created_at": "2026-04-21T10:00:00Z",
    "updated_at": "2026-04-21T10:00:00Z",
    "supersedes_import_id": null,
    "superseded_by_import_id": null
  },
  "report": {
    "import_id": "imp_01",
    "parse_status": "passed",
    "standard_validation_status": "passed",
    "compatibility_status": "compatible",
    "activation_eligibility": "eligible",
    "errors": [],
    "warnings": [],
    "compatibility_issues": []
  },
  "preview": {
    "skill_name": "pdf-insight-extractor",
    "skill_version": "1.0.0",
    "description": "Extract evidence from PDFs",
    "capabilities": ["pdf analysis", "evidence extraction"],
    "entrypoint": "system_prompt",
    "required_tools": ["builtin:pdf_keyword_page_search", "builtin:pdf_page_text_read"],
    "requires_bins": [],
    "requires_env": [],
    "resources": [],
    "actions": [],
    "overlays": [],
    "always": false
  }
}
```

### Behavior notes

- import should be idempotent only by explicit future policy, not by default
- repeated imports of the same package may create different import records
- default policy may auto-activate when evaluation is compatible and activation-eligible
- explicit activation endpoint remains available for controlled/manual activation policy

## 5.2 List imports

`GET /api/skill-imports`

Lists imported records.

### Query params

- `skill_name`
- `lifecycle_state`
- `latest_only=true|false`

### Response

`200 OK`

```json
{
  "items": [
    {
      "id": "imp_01",
      "skill_name": "pdf-insight-extractor",
      "skill_version": "1.0.0",
      "source_type": "directory",
      "package_format": "package_directory",
      "lifecycle_state": "active",
      "created_at": "2026-04-21T10:00:00Z",
      "updated_at": "2026-04-21T10:10:00Z",
      "supersedes_import_id": null,
      "superseded_by_import_id": null
    }
  ]
}
```

## 5.3 Get one import

`GET /api/skill-imports/{import_id}`

Returns the import record, report, and preview.

### Response

`200 OK`

```json
{
  "import": {},
  "report": {},
  "preview": {}
}
```

## 5.4 Activate import

`POST /api/skill-imports/{import_id}/activate`

Activates an accepted import record.

### Request

```json
{}
```

### Response

`200 OK`

```json
{
  "import_id": "imp_01",
  "skill_name": "pdf-insight-extractor",
  "skill_version": "1.0.0",
  "lifecycle_state": "active"
}
```

### Rules

- `inactive` and activation-eligible imports may be activated
- `inactive` imports may be re-activated after an explicit deactivate
- activation should update persisted activation state
- if another import for the same `skill_name` is active, activation policy must be explicit:
  - default recommendation: allow only one active import per `skill_name`
- if import has already been auto-activated by policy, API may return conflict/idempotent semantics based on implementation choice

## 5.5 Deactivate import

`POST /api/skill-imports/{import_id}/deactivate`

Deactivates an active import.

### Response

`200 OK`

```json
{
  "import_id": "imp_01",
  "skill_name": "pdf-insight-extractor",
  "skill_version": "1.0.0",
  "lifecycle_state": "inactive"
}
```

## 5.6 Replace active skill with a new import

`POST /api/skill-imports/{import_id}/replace`

Promotes a compatible imported revision and supersedes the current active revision for the same skill.

### Request

```json
{
  "target_skill_name": "pdf-insight-extractor"
}
```

### Response

`200 OK`

```json
{
  "activated_import_id": "imp_02",
  "superseded_import_id": "imp_01",
  "skill_name": "pdf-insight-extractor",
  "active_version": "1.1.0"
}
```

### Rules

- replacement should only be allowed when the new import is `inactive` and activation-eligible
- the previous active revision becomes `superseded`
- replacement should preserve lineage through:
  - `supersedes_import_id`
  - `superseded_by_import_id`
- if `target_skill_name` does not match the import record's `skill_name`, return:
  - `400` with `detail: "invalid_request"`
- if `target_skill_name` is missing or empty, return:
  - `400` with `detail: "invalid_request"`

## 5.7 List active runtime skills

This remains in the runtime plane.

Two possible paths:

- keep `GET /api/skills`
- or add `GET /api/skills/active`

Recommendation:

- Stage 1 keeps current `GET /api/skills`
- Stage 2 keeps runtime listing aligned to active runtime skills
- imported but inactive records stay under `/api/skill-imports`
- directory-loaded compatible skills may be auto-activated into active runtime set by policy

## 6. Error Contract

The API should return stable machine-readable `detail` codes.

### Recommended error codes

- `invalid_request`
- `import_source_missing`
- `import_source_not_found`
- `skill_parse_failed`
- `skill_standard_validation_failed`
- `skill_yue_compatibility_failed`
- `skill_activation_ineligible`
- `skill_import_not_found`
- `skill_import_already_active`
- `skill_import_not_active`
- `skill_replacement_conflict`

### Status code guidance

- `400` for malformed request or illegal transition
- `404` for missing import record
- `409` for activation/replacement conflicts
- `422` for accepted request body but failed import-gate evaluation
- for `GET /api/skill-imports` query filters:
  - invalid `lifecycle_state` values return `400` with `detail: "invalid_request"`

### Example failure

`422 Unprocessable Entity`

```json
{
  "detail": "skill_yue_compatibility_failed",
  "report": {
    "import_id": "imp_03",
    "parse_status": "passed",
    "standard_validation_status": "passed",
    "compatibility_status": "incompatible",
    "activation_eligibility": "ineligible",
    "errors": [],
    "warnings": [],
    "compatibility_issues": [
      "Unsupported tool required: builtin:exec"
    ]
  }
}
```

## 7. State Transition Rules

The API should enforce these transitions:

- `inactive -> active`
- `active -> inactive`
- `active -> superseded`
- any failed evaluation path -> `rejected`

Illegal transitions should be rejected with `400` or `409`.

Examples:

- `rejected -> active` is illegal
- `inactive -> superseded` is legal only through replace policy
- `active -> active` should return `skill_import_already_active`

## 8. Persistence Contract

The API contract requires durable persistence across restart for:

- import records
- activation semantics

Current Lite implementation keeps minimal activation semantics in import records via `lifecycle_state`.

Suggested persistence options:

- minimal/current: `~/.yue/data/skill_imports.json`

The API should not expose raw file layout, but the lifecycle contract depends on durable persistence across restart.

## 9. Relationship to Current Endpoints

Current [`backend/app/api/skills.py`](../../backend/app/api/skills.py) should evolve like this:

### Keep

- `GET /api/skills`
- `GET /api/skills/summary`
- `GET /api/skills/{name}`
- `POST /api/skills/tool/select_runtime_skill`

### Runtime Selection Response Profile

For `POST /api/skills/tool/select_runtime_skill`, the default response must stay minimal in the current stage:

- `selected_skill`
- `reason_code`
- `fallback_used`

Detailed explanation fields are treated as debug-only surfaces:

- `selected`
- `candidates`
- `scores`
- `reason`
- `stage_trace`
- `selection_mode`
- `effective_tools`

Debug fields are allowed only under debug logging/diagnostics mode, and should not be treated as stable frontend/user-facing contract in this MVP phase.

Current regression guard:

- `backend/tests/test_api_skills.py` enforces default response profile to remain minimal (only `selected_skill`, `reason_code`, `fallback_used`).
- debug/diagnostics fields are not returned by default response contract.

### Demote or gate

- `POST /api/skills/reload`

Reason:

- reload is an operator tool and should not be the primary user workflow
- hybrid mode can keep directory watch/reload behavior while runtime routing still consumes active set semantics

### Add separately

- all import/acceptance endpoints under `/api/skill-imports`

## 10. Stage Mapping

## Stage 1

API contract can be partially scaffolded with service-level tests:

- internal import service returns `import + report + preview`
- persistence contracts exist
- no full admin endpoint set required yet

## Stage 2

Minimum endpoint set should exist:

- `POST /api/skill-imports`
- `GET /api/skill-imports`
- `GET /api/skill-imports/{id}`
- `POST /api/skill-imports/{id}/activate`
- `POST /api/skill-imports/{id}/deactivate`
- `POST /api/skill-imports/{id}/replace`

Policy note:

- compatible imports may auto-activate by default in the current lightweight deployment policy
- manual deactivate/replace must remain available for control

## Stage 3 (Routing Lite)

API contract remains stable. No new mandatory endpoints.

Contract expectations:

- runtime routing remains visibility-scoped
- fallback semantics remain deterministic
- contract focuses on deterministic routing behavior and explanation-ready fields only

## Stage 4 (Decouple Lite)

No immediate public API expansion is required.

Reserve adapter-level seams behind existing API handlers:

- `ToolCapabilityProvider`
- `ActivationStateStore`
- `RuntimeCatalogProjector`
- `PromptInjectionAdapter`
- `VisibilityResolver`

These are internal integration contracts and should not be exposed as standalone HTTP resources in this phase.

## Stage 5 (Externalization Prep Lite, Deferred)

Stage 5 externalization work is deferred for the current MVP cycle.

Only keep minimal compatibility notes; do not introduce extraction-driven API work in this stage.

## 11. Acceptance Criteria

This contract is acceptable when:

1. imported-but-inactive skills are represented separately from active runtime skills
2. standard-valid but Yue-incompatible imports have a stable API representation
3. activation and replacement are explicit state transitions, not hidden side effects
4. API semantics do not require runtime routing changes to be designed first
5. API scope remains minimal and internal-dev oriented in the current cycle
6. Stage 3/4/5 Lite can proceed without adding broad new endpoint surface area
7. reserved interface seams can evolve internally without breaking current admin/runtime API consumers
8. default auto-activation policy can coexist with explicit deactivation/replacement controls

## 12. Recommendation

For implementation, the safest order is:

1. define import models and reports in service code
2. implement import store and import service
3. add API handlers under a new `/api/skill-imports` router
4. keep runtime consumption aligned to active-set semantics while preserving directory-loading usability in hybrid mode
