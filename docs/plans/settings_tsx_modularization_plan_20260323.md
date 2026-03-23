# Settings.tsx Modularization Plan

> Status: Draft
> Target: `frontend/src/pages/Settings.tsx`
> Scope: Frontend-only refactor, behavior-preserving

## 1. Why This Refactor

`Settings.tsx` is a large Solid page component with multiple unrelated responsibilities in one file. It currently combines:

- data loading for six API domains
- state for tabs, modals, form fields, toast UX, and confirmation state
- mutation handlers for MCP, LLM, preferences, document access, custom models, and provider model management
- a large render tree with three major tabs and several overlays/modals

The file is about 1,469 lines long and the responsibilities are clustered but not separated. The main pain points are:

- high cognitive load when making any settings change
- risk of accidental regressions because state and UI logic are tightly interleaved
- difficult-to-test mutation flows, especially around model management and MCP parsing
- repeated fetch/reload patterns that should be centralized
- modal logic and tab content are defined inline, which makes future changes harder to isolate

## 2. Current Responsibility Map

### General settings

- user preferences
- document access roots
- save actions for both settings groups

Relevant sections:

- state and data loading: `frontend/src/pages/Settings.tsx:79-125`
- general tab UI: `frontend/src/pages/Settings.tsx:499-588`

### MCP management

- MCP config loading and save
- server enable/disable
- reload and tool refresh
- manual JSON parsing and normalization
- marketplace mock modal
- raw config modal

Relevant sections:

- state and handlers: `frontend/src/pages/Settings.tsx:34-44`, `frontend/src/pages/Settings.tsx:138-202`, `frontend/src/pages/Settings.tsx:329-423`
- MCP UI: `frontend/src/pages/Settings.tsx:592-760`

### LLM / model management

- provider list and refresh
- provider test and edit modal
- custom model CRUD
- provider model manager
- capability overrides and undo flow
- network and session-meta settings

Relevant sections:

- state and handlers: `frontend/src/pages/Settings.tsx:46-77`, `frontend/src/pages/Settings.tsx:205-327`, `frontend/src/pages/Settings.tsx:426-467`
- LLM UI: `frontend/src/pages/Settings.tsx:763-1465`

## 3. Proposed Target Structure

Keep `Settings.tsx` as a thin route shell that only coordinates tab selection and shared page-level concerns. Move feature-specific logic into focused modules.

### Suggested file boundaries

- `frontend/src/pages/settings/SettingsPage.tsx`
  - route shell and page layout
  - tab selection
  - shared toast and delete-confirmation plumbing

- `frontend/src/pages/settings/useSettingsData.ts`
  - initial fetch orchestration
  - refresh helpers
  - loading state and shared data shapes

- `frontend/src/pages/settings/useSettingsMcp.ts`
  - MCP parse/normalize/save/reload/toggle handlers
  - manual JSON conversion helper

- `frontend/src/pages/settings/useSettingsLlm.ts`
  - provider test/edit handlers
  - model manager state and save/undo flow
  - custom model CRUD helpers

- `frontend/src/pages/settings/useSettingsGeneral.ts`
  - preference save
  - document-access save and text normalization helpers

- `frontend/src/pages/settings/components/`
  - `GeneralSettingsTab.tsx`
  - `McpSettingsTab.tsx`
  - `LlmSettingsTab.tsx`
  - `McpManualModal.tsx`
  - `McpMarketplaceModal.tsx`
  - `LlmProviderEditModal.tsx`
  - `LlmModelManagerModal.tsx`
  - `CustomModelModal.tsx`

### Shared utility extraction candidates

- `normalizeMcpConfigInput(...)`
- `buildMcpConfigArray(...)`
- `mergeModelCapabilityOverrides(...)`
- `buildRevertLlmConfig(...)`
- `splitRootsText(...)`

These helpers should live near the feature hooks or in a small `settings-utils.ts` file if they are used by more than one module.

## 4. Phased Migration Plan

### Phase 0: Safety baseline

Goal: establish regression protection before moving code.

- capture current page behavior with a small set of focused tests
- document the public interactions that must remain stable
- keep the page file untouched while the baseline is added

### Phase 1: Extract shared data and helpers

Goal: reduce the size of `Settings.tsx` without changing any UI structure.

- move pure helper logic first
- extract text normalization and MCP parsing helpers
- extract the shared `fetchData` orchestration into `useSettingsData`
- keep the page rendering in place for now

This phase is low risk because it mostly relocates logic without changing component hierarchy.

### Phase 2: Split the tab bodies

Goal: isolate each major settings area into its own component.

- move General tab markup into `GeneralSettingsTab`
- move MCP tab markup into `McpSettingsTab`
- move LLM tab markup into `LlmSettingsTab`
- pass state and actions as explicit props instead of letting child components reach into page internals

This should preserve the existing layout while making each tab independently readable.

### Phase 3: Extract modal islands

Goal: remove the most nested UI from the page.

- move MCP manual and marketplace overlays into dedicated components
- move LLM custom model, provider edit, and model manager modals into dedicated components
- keep shared toast and confirm modal handling in the page shell

This phase is the best place to catch prop-shape issues with targeted tests.

### Phase 4: Simplify orchestration

Goal: make the page shell thin and predictable.

- replace direct page-local mutation handlers with hook methods
- centralize refresh-after-save behavior where appropriate
- remove dead state and redundant local copies once the extracted modules are stable

## 5. Risk Assessment

### Main risks

- prop drilling can become noisy if the first split is too aggressive
- subtle behavior changes in save/undo flows, especially model-manager revert logic
- MCP JSON parsing supports multiple input shapes, so helper extraction must preserve all accepted formats
- modal behavior depends on click handling and show/hide state, which can regress if moved too quickly
- fetch sequencing matters because some actions expect a refresh immediately after save

### Risk controls

- keep the first phase structure-only and behavior-preserving
- extract pure functions before moving rendering
- preserve the current API calls and response handling order
- prefer explicit props over new context providers for this refactor
- do not change endpoint contracts as part of this work

## 6. Testing Strategy

Start with the narrowest checks that protect the current behavior.

### Recommended baseline tests

- component render smoke test for the page route
- MCP manual JSON normalization cases
  - Claude Desktop-style `mcpServers` object
  - array input
  - single object input
  - invalid JSON
- document-access text splitting and save payload formation
- model-manager save and revert payload construction
- custom model add/test/delete flows at the request-shape level

### Testing layers

1. Unit tests for pure helper functions
2. Component tests for extracted tab sections and modals
3. Page-level smoke test to ensure the route still renders and tab switching still works

### Regression checks

- build the frontend after each phase
- run the focused vitest suite for any extracted helper or component
- if a test is flaky, stabilize it before continuing the refactor

## 7. Rollout / PR Split

Preferred split for low-risk review:

1. PR 1: helper extraction and data hook only
2. PR 2: tab component extraction
3. PR 3: modal extraction and cleanup
4. PR 4: final pruning, dead-state removal, and test updates

If we need fewer PRs, the fallback is two merges:

- PR A: helpers + hooks + general/MCP split
- PR B: LLM modals + cleanup

## 8. Definition of Done

- `Settings.tsx` is reduced to a thin coordinator
- each major tab is isolated in its own component or hook boundary
- modal code is no longer inline inside the page root
- pure parsing/merge logic is covered by unit tests
- the settings page still behaves the same for users

## 9. Next Step Pending Approval

If approved, implementation should start with Phase 1:

- extract pure helpers
- move data loading into a dedicated hook
- add unit tests around the extracted logic before any UI split

## 10. Phase 1 Execution Update (2026-03-24)

### What changed

- Extracted typed settings data loader:
  - `frontend/src/pages/settings/useSettingsData.ts`
- Extracted shared settings types:
  - `frontend/src/pages/settings/types.ts`
- Extracted pure helpers for:
  - document roots text normalization
  - MCP manual JSON parsing/normalization
  - model capability override merge and save/undo config construction
  - file: `frontend/src/pages/settings/settingsUtils.ts`
- Updated `frontend/src/pages/Settings.tsx` to consume extracted hook/helpers while preserving UI and endpoint behavior.
- Added helper unit tests:
  - `frontend/src/pages/settings/settingsUtils.test.ts`

### Deviations from original plan

- No structural deviation from Phase 1 goals.
- `fetchData` remains in `Settings.tsx` as a thin coordinator (expected for low-risk extraction), while network orchestration moved into `useSettingsData`.

### Validation results

- Focused unit tests passed:
  - `npm run test:unit -- src/pages/settings/settingsUtils.test.ts`
- Frontend build passed:
  - `npm run build`

### Follow-up suggestions

- Start Phase 2 by extracting tab bodies (`General`, `MCP`, `LLM`) into dedicated components with prop-based boundaries.

## 11. Phase 2a Execution Update (2026-03-24)

### What changed

- Extracted tab bodies into dedicated components:
  - `frontend/src/pages/settings/components/GeneralSettingsTab.tsx`
  - `frontend/src/pages/settings/components/McpSettingsTab.tsx`
  - `frontend/src/pages/settings/components/LlmSettingsTab.tsx`
- Updated `frontend/src/pages/Settings.tsx` to act as a coordinator that renders the three tab components and passes explicit props/actions.
- Added shared draft type for custom-model editing:
  - `frontend/src/pages/settings/types.ts`

### Deviations from original plan

- No intentional behavior changes.
- Modal UI remains in extracted tab components for now; dedicated modal component extraction is still reserved for Phase 3.

### Validation results

- Focused helper tests passed:
  - `npm run test:unit -- src/pages/settings/settingsUtils.test.ts`
- Frontend build passed:
  - `npm run build`
- Playwright browser coverage passed:
  - `frontend/e2e/settings-general.spec.ts`
  - `frontend/e2e/settings-crud.spec.ts`

### Residual risk

- Keep the General tab manual smoke checklist around as a quick browser sanity check, but the automated save path is now covered by `frontend/e2e/settings-general.spec.ts`.

### Next step

- Proceed to Phase 3: extract modal islands (`MCP` overlays, `LLM` add/edit/manage modals) from tab components into dedicated modal components.

## 12. General Tab Manual Smoke Checklist

Use this checklist in the browser when you want to verify the General tab without relying on the flaky automated save path.

1. Open `/settings` and click `General`.
2. Change `Theme` from `Light` to `Dark`, then back to `Light`.
3. Change `Language` from `English` to `Chinese`, then back to `English`.
4. Change `Default Agent` to another agent if one is available.
5. Save `Preferences` and confirm the success toast appears.
6. Edit `Allow Roots` with a multi-line value and save.
7. Edit `Deny Roots` with a multi-line value and save.
8. Reload the page and confirm the saved values still render.

If the save does not stick visually after a reload, treat that as a regression in the General tab update path and inspect the network request for `/api/config/preferences` or `/api/config/doc_access`.

## 13. General Tab Stabilization Update (2026-03-24)

The General tab preferences flow was simplified to a plain form-submit path so browser interactions are easier to reason about and test.

### What changed

- Converted the preferences section to submit as a form instead of relying on an inline click handler.
- Kept the browser-owned select state visible in the form and read the submitted values directly at save time.
- Added a focused browser spec for the General tab:
  - `frontend/e2e/settings-general.spec.ts`

### Validation results

- `npm run build`
- `npx playwright test e2e/settings-general.spec.ts`
- `npx playwright test e2e/settings-crud.spec.ts`

### Follow-up

- Phase 3 can now focus on modal extraction without carrying forward a known General-tab automation gap.

## 14. Phase 3 Execution Update (2026-03-24)

### What changed

- Extracted MCP modal islands into dedicated components:
  - `frontend/src/pages/settings/components/modals/McpManualModal.tsx`
  - `frontend/src/pages/settings/components/modals/McpMarketplaceModal.tsx`
  - `frontend/src/pages/settings/components/modals/McpRawConfigModal.tsx`
- Extracted LLM modal islands into dedicated components:
  - `frontend/src/pages/settings/components/modals/LlmCustomModelModal.tsx`
  - `frontend/src/pages/settings/components/modals/LlmModelManagerModal.tsx`
  - `frontend/src/pages/settings/components/modals/LlmProviderEditModal.tsx`
- Updated the settings tab components to render the modal components instead of inline modal JSX.

### Behavior notes

- No endpoint contracts changed.
- The existing page-level state and handlers remain in `Settings.tsx`.
- The modal extraction is a structural split only; save/delete/test flows continue to use the same APIs.

### Validation results

- Frontend build passed:
  - `npm run build`
- Browser specs passed:
  - `npx playwright test e2e/settings-general.spec.ts`
  - `npx playwright test e2e/settings-crud.spec.ts`

### Broader frontend validation

- Full unit suite passed:
  - `npm run test`
- Full Playwright suite was run, and two unrelated pre-existing specs failed outside the settings area:
  - `e2e/agents-smart-generate.spec.ts`
  - `e2e/comprehensive-workflow.spec.ts`
- Observed failures were agent-flow related, not settings-related:
  - one click was intercepted by an overlay in the smart-generate flow
  - one workflow timed out waiting for an agent form submit control

### Scope note

- These broader E2E failures were left untouched so the settings refactor stays focused and low-risk.

### Next step

- Proceed to Phase 4: simplify orchestration and remove any remaining dead state or redundant local copies once the modal components settle in.

## 15. Phase 4 Execution Update (2026-03-24)

### What changed

- Simplified the LLM save orchestration in `frontend/src/pages/Settings.tsx` by introducing a shared `postLlmConfig(...)` helper.
- Reused that helper for:
  - saving the global LLM configuration
  - saving provider editor changes
  - saving managed-model changes
  - undoing managed-model changes
- Kept the shell behavior the same:
  - the page still owns the state
  - the same endpoints are called
  - refresh behavior still happens after each save

### What did not change

- No endpoint contract changes.
- No user-facing layout changes.
- No tab or modal behavior changes.

### Validation results

- Frontend build passed:
  - `npm run build`
- Browser specs passed:
  - `npx playwright test e2e/settings-general.spec.ts`
  - `npx playwright test e2e/settings-crud.spec.ts`

### Residual state

- The page shell still owns cross-tab state such as toast, delete confirmation, and tab selection, which is intentional.
- There was no safe dead state to remove beyond the config-posting duplication, so Phase 4 focused on collapsing orchestration instead of reshaping the whole shell.
