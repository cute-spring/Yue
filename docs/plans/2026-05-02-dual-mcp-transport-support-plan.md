# Dual MCP Transport Support Execution Plan

## Requirements Summary

Yue currently supports MCP servers through a stdio-only configuration path. The implementation plan below makes `stdio` and `streamable_http` first-class transports in the same config system, while keeping all existing stdio configs working without edits.

Current baseline in the repo:
- `backend/app/api/mcp.py:33-46,60-88,91-145` defines `ServerConfig`, saves configs, validates templates, and reloads the manager, but the request model rejects any `transport` other than `stdio`.
- `backend/app/mcp/models.py:4-19` repeats the same stdio-only validation at the model layer.
- `backend/app/mcp/manager.py:39-47,148-220,293-313` loads the config file, dispatches only the stdio client path, and reports status with transport already included.
- `backend/app/mcp/templates.py:305-397` renders every template to `transport: "stdio"` regardless of template type.
- `frontend/src/pages/Settings.tsx:130-190`, `frontend/src/pages/settings/components/McpSettingsTab.tsx:37-230`, `frontend/src/pages/settings/components/modals/McpManualModal.tsx:1-38`, and `frontend/src/pages/settings/components/modals/McpRawConfigModal.tsx:1-35` expose MCP editing flows, but they all assume the current stdio-shaped config contract.
- `frontend/src/pages/settings/components/modals/McpMarketplaceModal.tsx:20-236` is already data-driven enough to host transport-specific form fields without reworking the modal shell.
- `frontend/src/pages/settings/types.ts:40-83` already carries `transport` through the UI status types, but it is still typed as a generic string.
- `backend/data/mcp_configs.json.example:1-30`, `backend/tests/test_mcp_manager_unit.py:52-340`, `backend/tests/test_api_mcp_unit.py:48-177`, and `frontend/e2e/settings-crud.spec.ts:13-174` still encode stdio as the only supported transport.

This plan is execution-oriented. It specifies the contract, the backend and frontend changes, the secret-handling rules, the test surface, the rollout order, and the definition of done. It does not implement the change.

## Scope

### In scope
- Add `streamable_http` as a supported transport alongside `stdio`.
- Preserve existing stdio configs exactly as valid input.
- Make the backend connection manager load, validate, connect, and report status for both transports.
- Make the template rendering path emit transport-specific configs instead of hardcoding stdio.
- Update the Settings page so users can create, validate, save, and inspect both transport types.
- Keep secrets out of persisted plaintext configs and out of logs.

### Out of scope
- No change to MCP tool semantics beyond transport selection.
- No new auth provider abstraction beyond what is required to configure transport-specific secrets.
- No migration to a different storage backend for MCP config.

## Current State Baseline

The repo currently behaves as follows:
- `backend/app/api/mcp.py`
  - The request model accepts `transport` but only allows `stdio`.
  - Save and delete operations write a JSON array to the config file and reload the manager immediately.
  - Template validation checks that the command exists locally, which only makes sense for stdio configs.
- `backend/app/mcp/models.py`
  - The canonical model also only accepts `stdio`.
  - The model already carries `timeout` and `min_version`, which should continue to apply to both transports.
- `backend/app/mcp/manager.py`
  - The manager loads a list of server dicts from `mcp_configs.json`.
  - It connects only through `stdio_client(...)` and uses `ClientSession` to initialize the session.
  - It already redacts secrets from `env`, which is the right pattern to extend.
  - `get_status()` already returns `transport`, so the status API can expose both transports with no shape change.
- `backend/app/mcp/templates.py`
  - Template renderers hardcode `transport: "stdio"`.
  - Secret handling uses `${ENV_NAME}` placeholders, which is the right persistence pattern to keep.
- `frontend/src/pages/Settings.tsx`
  - The Settings page treats MCP config as raw JSON plus marketplace/manual flows.
  - Save and reload assume the backend will accept the current array shape.
- `frontend/src/pages/settings/components/McpMarketplaceModal.tsx`
  - Template forms are fully data-driven, so transport-specific fields can be added without rewriting the whole modal.

## Target Config Contract

The config file remains a JSON array of server objects. The key change is that `transport` becomes a required discriminator for new configs and a compatibility field for old configs.

### Common fields
- `name` - unique server identifier, required.
- `transport` - `"stdio"` or `"streamable_http"`, required for new writes.
- `enabled` - boolean, defaults to `true`.
- `timeout` - number in seconds, optional, retained for both transports.
- `min_version` - optional semantic version gate, retained for both transports.

### `stdio` transport contract
- Required:
  - `command`: executable to launch.
- Optional:
  - `args`: string array.
  - `env`: string map.
- Runtime behavior:
  - The backend launches a local subprocess with resolved environment variables.
  - `${ENV_NAME}` placeholders remain the supported way to keep secrets out of the config file.

### `streamable_http` transport contract
- Required:
  - `url`: MCP Streamable HTTP endpoint.
- Optional:
  - `headers`: string map for request headers.
  - `env`: allowed only if a template or deployment needs host-side placeholder resolution before header construction.
- Runtime behavior:
  - The backend connects to the remote MCP endpoint over HTTP rather than launching a subprocess.
  - Secrets must be represented as placeholders in persisted config values, never as resolved literals.
  - The transport must be a first-class path in the manager, not a special case hidden behind stdio-shaped fields.

### Backward compatibility rules
- Missing `transport` in an existing config must continue to be interpreted as `stdio`.
- Existing stdio entries in `backend/data/mcp_configs.json.example` and in user config files must continue to load and connect unchanged.
- When a user edits a server, the backend must normalize the saved object to the selected transport schema so stale fields from the previous transport do not linger.

## Backend Design

### 1. Make transport validation model-driven
- Update `backend/app/mcp/models.py` so `ServerConfig` accepts a transport union, not a stdio-only string check.
- Keep `stdio` as the default for omitted transport so legacy config files still validate.
- Add explicit field validation for each transport:
  - `stdio` requires `command`.
  - `streamable_http` requires `url`.
- Keep `timeout`, `enabled`, and `min_version` shared across both transport models.

### 2. Replace the current manager branch with transport dispatch
- Update `backend/app/mcp/manager.py` to route by transport through a small adapter layer.
- Keep the current stdio path behavior intact:
  - command and args resolution.
  - `${PROJECT_ROOT}` substitution.
  - proxy and SSL propagation.
  - retry/backoff and timeout behavior.
- Add a dedicated `streamable_http` connection path that:
  - Builds the HTTP MCP client session from the configured URL and headers.
  - Uses the same retry and timeout envelope as stdio.
  - Registers the session in `self.sessions` and `self.server_info` the same way stdio does.
- Update status handling so a failed `streamable_http` server reports the same fields as stdio, including `transport` and `last_error`.

### 3. Normalize save/update behavior in the API
- Update `backend/app/api/mcp.py` so POST validation accepts both schemas and rejects fields that do not belong to the selected transport.
- Replace the current shallow merge-by-name save path with transport-aware normalization.
  - This avoids keeping stale `command`/`args` fields when a server switches from `stdio` to `streamable_http`.
  - This also prevents accidental retention of `url`/`headers` when switching back to stdio.
- Keep delete and reload behavior unchanged except for schema-aware reload validation.
- Make template validation transport-aware:
  - stdio templates continue to check executable availability.
  - streamable HTTP templates validate the URL shape and required auth/header placeholders instead of command existence.

### 4. Extend template rendering
- Update `backend/app/mcp/templates.py` so the renderers can emit either transport.
- Keep existing template IDs, but make the output shape transport-specific.
- Preserve the current secret placeholder pattern:
  - persisted config stores `${ENV_NAME}` values.
  - rendered previews must never show resolved secrets.
- Emit warnings that are transport-aware:
  - stdio warnings continue to mention missing executables or placeholder env vars.
  - streamable_http warnings should mention URL reachability and required secret placeholders.

### 5. Update example data and redaction
- Update `backend/data/mcp_configs.json.example` to include at least one `stdio` example and one `streamable_http` example.
- Extend redaction in `backend/app/mcp/manager.py` so any future header/secret maps are masked in logs and status traces the same way env secrets are masked today.
- Keep the redaction rules deterministic and conservative. If a key looks like a secret, it should be masked.

## Frontend Design

### 1. Keep raw JSON as the authoritative advanced path
- `Settings.tsx` can keep the current raw-config and manual-config flows, but those flows must validate against the new union schema.
- The raw editor should surface transport-specific validation errors from the backend instead of assuming all configs are stdio-shaped.

### 2. Add transport-aware template editing
- Update `McpMarketplaceModal.tsx` to include a transport selector or transport-specific template metadata so users can choose stdio or streamable HTTP before install.
- For stdio templates, keep the current command/args/env fields.
- For streamable HTTP templates, render URL and headers/auth fields instead of command/args.
- Keep the onboarding notes system, but make the notes dependent on both template and transport.

### 3. Improve MCP status visibility
- Update `frontend/src/pages/settings/types.ts` so `McpStatus.transport` is a real union type, not a free-form string.
- Show the transport explicitly in the MCP server list so users can tell which path is in use.
- Keep the existing connected/failed state model, but make the failure copy transport-neutral.

### 4. Preserve current workflows
- `McpManualModal.tsx` and `McpRawConfigModal.tsx` can remain simple editors, but their help text should explain that both transport shapes are accepted.
- The existing add/edit/delete flows in `McpSettingsTab.tsx` should keep working for stdio users with no extra clicks.
- The default experience should still land on stdio unless the user explicitly selects `streamable_http`.

## Secret Handling

Secret handling is part of the transport contract, not an afterthought.

- Persist secrets only as `${ENV_NAME}` placeholders in stored config objects.
- Resolve placeholders as late as possible, at connection time.
- Never log resolved secret values.
- Redact any value that is likely to contain a token, password, key, or bearer credential.
- Treat `headers` in `streamable_http` configs as secret-capable data, not as plain display text.
- Keep validation feedback helpful:
  - warn when required env vars are missing.
  - do not echo actual secret contents back to the UI.

## Implementation Steps

### Step 1: Define the union schema and compatibility rules
- Update `backend/app/mcp/models.py` and `backend/app/api/mcp.py` to validate by transport.
- Encode the backward-compatibility rule that missing `transport` means `stdio`.
- Add explicit per-transport required fields and schema errors.

### Step 2: Implement transport dispatch in the manager
- Refactor `backend/app/mcp/manager.py` so the connection code selects a transport adapter.
- Keep stdio behavior stable.
- Add streamable HTTP connection, retry, timeout, session registration, and status reporting.

### Step 3: Make save/validate/reload transport-aware
- Update `backend/app/api/mcp.py` so POST save, template validation, and delete/reload all use the same transport-aware normalization path.
- Remove stale fields when a server changes transports.

### Step 4: Update template rendering
- Teach `backend/app/mcp/templates.py` to render both transports.
- Update template warnings, defaults, and preview output.

### Step 5: Update the Settings UI contract
- Update `frontend/src/pages/Settings.tsx`, `frontend/src/pages/settings/types.ts`, and `frontend/src/pages/settings/components/McpSettingsTab.tsx`.
- Add transport-aware form presentation in `frontend/src/pages/settings/components/modals/McpMarketplaceModal.tsx`.
- Keep raw-config editing intact for advanced users.

### Step 6: Refresh examples, docs, and tests
- Update `backend/data/mcp_configs.json.example`.
- Update onboarding docs that describe the example config shape if they reference stdio-only assumptions.
- Add backend unit and API tests for both transport types.
- Add frontend unit and e2e coverage for transport selection and transport-aware config previews.

### Step 7: Verify and gate rollout
- Run the targeted test matrix.
- Perform a manual smoke test for one stdio server and one streamable HTTP server.
- Only ship after both transports load, connect, report status, and survive reload without regression.

## Test Plan

### Backend unit tests
- Extend `backend/tests/test_mcp_manager_unit.py` with:
  - stdio happy path remains unchanged.
  - streamable HTTP connection path creates a session and reports status.
  - missing `transport` still defaults to stdio.
  - switching transports does not keep stale fields.
  - redaction covers new secret-bearing fields.
- Extend `backend/tests/test_api_mcp_unit.py` with:
  - valid streamable HTTP save and validation cases.
  - invalid URL or missing endpoint cases.
  - config normalization for transport switches.
  - template rendering that emits the correct transport schema.

### Frontend unit tests
- Extend `frontend/src/pages/settings/settingsUtils.test.ts` and `frontend/src/pages/settings/components/modals/McpMarketplaceModal.logic.test.ts` to cover transport-aware template defaults and onboarding notes.
- Add tests for union-typed status display and transport-specific validation messages.

### E2E tests
- Extend `frontend/e2e/settings-crud.spec.ts` so it covers:
  - saving a stdio config.
  - saving a streamable HTTP config.
  - viewing the transport in the status list.
  - validating that the rendered preview matches the selected transport.

### Manual verification
- Confirm that existing stdio configs in `backend/data/mcp_configs.json.example` still load.
- Confirm that a sample streamable HTTP config can be saved, reloaded, and connected.
- Confirm that no secret values appear in logs, previews, or status payloads.

## Rollout Order

1. Land schema and validation changes in `backend/app/mcp/models.py` and `backend/app/api/mcp.py`.
2. Land manager transport dispatch in `backend/app/mcp/manager.py`.
3. Update template rendering in `backend/app/mcp/templates.py`.
4. Update frontend types and MCP settings UI.
5. Refresh example config and developer-facing docs.
6. Land unit tests, integration tests, and e2e coverage.
7. Verify stdio regression first, then streamable HTTP smoke tests, then merge.

## Risks and Mitigations

### Risk: transport switch leaves stale fields behind
- Mitigation: normalize saved configs by transport schema instead of shallow-merging dictionaries.

### Risk: streamable HTTP secrets leak into logs or previews
- Mitigation: treat headers as secret-capable, resolve placeholders only at connect time, and redact aggressively.

### Risk: stdio regression during the transport refactor
- Mitigation: preserve the existing stdio branch behavior first, add streamable HTTP next, and keep stdio tests green before widening the rollout.

### Risk: UI becomes ambiguous about which transport is active
- Mitigation: show transport in the status list and make template forms transport-aware.

### Risk: validation rules diverge between backend and frontend
- Mitigation: keep the backend as the source of truth and have the frontend surface backend validation responses rather than re-implementing schema logic.

## Verification Steps

- `backend/tests/test_mcp_manager_unit.py` passes with both transports covered.
- `backend/tests/test_api_mcp_unit.py` passes with streamable HTTP validation and save coverage added.
- `frontend/src/pages/settings/settingsUtils.test.ts` and `frontend/src/pages/settings/components/modals/McpMarketplaceModal.logic.test.ts` pass with transport-aware fixtures.
- `frontend/e2e/settings-crud.spec.ts` passes with both transport flows.
- A manual smoke run confirms:
  - an existing stdio config still connects.
  - a sample streamable HTTP config connects and reports status.
  - reload does not lose or corrupt either config type.
  - secret placeholders remain placeholders in persisted config.

## Definition of Done

- `stdio` and `streamable_http` are both accepted by the backend, persisted in config, connected at runtime, and shown in status.
- Existing stdio configs continue to work without edits.
- Transport changes do not leave stale fields in saved configs.
- Template validation and rendered previews are transport-aware.
- Secrets are not persisted in plaintext and are not exposed in logs or previews.
- Backend unit tests, frontend unit tests, and the Settings e2e test cover both transports.
- The example config and any MCP onboarding notes no longer imply stdio is the only supported path.
