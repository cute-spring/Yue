# Agent Browser Foundation Plan (2026-03-28)

## 1. Purpose

This document defines the recommended first implementation plan for `agent-browser` in Yue.

`agent-browser` means a browser automation capability that allows the AI runtime to:

1. open pages
2. inspect page structure
3. click elements
4. type into fields
5. capture screenshots
6. report structured evidence back into Yue's action runtime

The goal of this plan is not to deliver a fully autonomous web operator in one step.

The goal is to deliver a safe, inspectable, tool-backed browser MVP that fits the boundaries already established by:

1. [`docs/plans/skill_package_contract_plan_20260327.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md)
2. [`docs/plans/skill_action_runtime_modularization_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_action_runtime_modularization_plan_20260328.md)
3. [`docs/plans/skill_kernel_extraction_plan_20260328.md`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_kernel_extraction_plan_20260328.md)

## 2. Why This Should Be The Next Capability

`agent-browser` is a strong next-step feature because it exercises almost every high-value part of the current skill/action runtime:

1. structured action inputs
2. preflight validation
3. approval gates
4. platform-tool execution
5. action history and invocation drill-down
6. tool-specific result rendering

It is therefore both:

1. a useful end-user capability
2. a high-pressure validation case for the architecture we just cleaned up

If the current skill/action foundation is sound, browser automation should be able to sit on top of it without forcing a redesign.

## 3. Current Baseline And Gap

Current platform baseline:

1. tool-backed requested actions already run through Yue's action lifecycle
2. requested-action orchestration has now been separated from the main stream runner
3. action event persistence and invocation history already exist
4. the frontend action panel already supports focused trace inspection and tool-specific renderers

Current gap:

1. there is no dedicated browser automation builtin tool in [`backend/app/mcp/builtin`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin)
2. there is no browser-specific action payload contract
3. there is no browser-specific result renderer in the intelligence panel
4. there is no safety/approval policy yet tailored to web automation risk

## 4. Product Boundary

The browser capability should follow the same product boundary as the rest of the skill system:

1. skills may orchestrate browser actions only through Yue platform tools
2. skills must not introduce a separate skill-owned browser runtime
3. browser execution must remain observable via Yue action lifecycle events
4. browser actions should reuse the existing approval, action-state, and trace mechanisms

This means:

1. the browser engine should be a Yue builtin tool or builtin tool family
2. skills should target those tools through action metadata
3. the frontend should render browser results as tool-backed action output, not as a separate ad hoc feature

## 5. Recommended MVP Scope

### 5.1 Include In MVP

The first version should support only a narrow, inspectable browser command set:

1. `open`
2. `snapshot`
3. `click`
4. `type`
5. `press`
6. `screenshot`
7. optional `tab-list` / `tab-select` if they come naturally from the tool wrapper

These are enough to support:

1. page navigation
2. basic form workflows
3. evidence capture
4. UI debugging
5. step-by-step agent browser demos

### 5.2 Explicitly Exclude From MVP

Do not include these in the first version:

1. automatic login persistence
2. CAPTCHA solving
3. unrestricted cross-site autonomous browsing
4. automatic purchases or destructive submissions
5. invisible background browsing without approval
6. long-horizon planner/executor loops that hide intermediate steps

This keeps the first version safe and debuggable.

## 6. Recommended Tool Strategy

The cleanest path is to add a Yue builtin browser tool backed by Playwright-style automation.

Recommended shape:

1. add a new builtin module such as:
   - [`backend/app/mcp/builtin/browser.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)
2. register one or more builtin tools such as:
   - `builtin:browser_open`
   - `builtin:browser_snapshot`
   - `builtin:browser_click`
   - `builtin:browser_type`
   - `builtin:browser_press`
   - `builtin:browser_screenshot`

Alternative:

1. provide one `builtin:browser` tool with an explicit `operation` field

Recommendation:

1. prefer operation-specific tools or a thin command family over a single opaque mega-tool

Why:

1. action schemas stay clearer
2. approval policies can differ per operation
3. renderer logic can stay operation-aware
4. future skill contracts remain easier to validate and explain

## 7. Skill Contract Recommendation

Browser automation should be modeled as regular tool-backed skill actions.

Recommended skill package examples:

1. `browser-operator`
2. `web-form-runner`
3. `site-verification-agent`

Example action families:

1. `open_page`
2. `inspect_page`
3. `click_element`
4. `fill_field`
5. `capture_screenshot`

Example action schema directions:

### `open_page`

Input:

1. `url: string`
2. `new_tab?: boolean`
3. `wait_until?: string`

### `inspect_page`

Input:

1. `include_text?: boolean`
2. `include_interactive_elements?: boolean`
3. `max_nodes?: integer`

### `click_element`

Input:

1. `element_ref: string`
2. `wait_after?: boolean`

### `fill_field`

Input:

1. `element_ref: string`
2. `text: string`

### `capture_screenshot`

Input:

1. `full_page?: boolean`
2. `label?: string`

The schema style should stay narrow and explicit, not attempt to expose the entire browser engine surface in the first round.

## 8. Approval And Safety Model

Browser automation has higher interaction risk than many existing builtins, so approval policy needs to be deliberate.

Recommended default policy:

1. `open_page` may be allowed without approval for low-risk environments if desired
2. `snapshot` and `screenshot` can generally be lower-risk
3. `click`, `type`, and `press` should default to approval-required
4. actions that may submit forms or navigate to external domains should remain approval-gated

Recommended policy dimensions:

1. domain allowlist / denylist
2. operation type
3. whether text input is being sent
4. whether a click target appears submit-like or destructive

The first version does not need full semantic intent detection.

It does need:

1. explicit operation-aware approval policy
2. visible action trace showing what page and what element was targeted
3. clear user control before mutating steps

## 9. Runtime Contract Recommendation

Browser actions should reuse the current requested-action lifecycle:

1. preflight
2. approval-required or ready
3. queued
4. running
5. succeeded / failed

Recommended metadata to preserve in action payloads:

1. `operation`
2. `url`
3. `tab_id`
4. `element_ref`
5. `screenshot_path` or artifact path
6. `page_title`
7. `status_text`
8. structured result payload

This will make browser steps visible in both:

1. backend action history
2. frontend focused trace

## 10. Renderer Recommendation

The intelligence panel should get browser-specific result renderers after the tool contract is stable.

Recommended browser renderer sections:

### Snapshot Result

1. `Page`
2. `Interactive Elements`
3. `Visible Text Summary`

### Screenshot Result

1. `Screenshot`
2. `Artifact Path`
3. `Download`

### Navigation Result

1. `URL`
2. `Title`
3. `Status`

### Interaction Result

1. `Operation`
2. `Target`
3. `Post-Action State`

The browser renderer should fit into the same renderer path currently used for:

1. `builtin:exec`
2. docs search/read
3. PPT artifact generation

## 11. Proposed Builtin Agent

Once the tool contract exists, add a dedicated builtin agent such as:

1. `builtin-agent-browser`

Recommended prompt behavior:

1. prefer stepwise browsing over hidden chains
2. surface intermediate observations
3. stop for approval before mutation steps
4. keep final prose short and rely on the Actions panel for detailed trace

Recommended enabled tools:

1. browser builtin tools
2. optionally docs tools for combining local-doc analysis with live browser verification

Recommended visible skills:

1. a dedicated browser operator skill package
2. optionally docs or reporting skills later

## 12. Suggested Implementation Order

### Phase 1: Foundation Contract

Scope:

1. define the browser builtin tool family
2. define browser action schemas for a minimal skill package
3. keep the backend runtime path identical to other requested actions

Success condition:

1. a browser action can preflight cleanly
2. approval-required browser actions show up in action history
3. approved browser actions execute through the same runtime seam as existing tool-backed actions

### Phase 1 Status Update (Current Branch)

Phase 1 foundation work is now materially in place on the current branch.

Delivered scope:

1. a dedicated builtin browser tool family now exists in [`backend/app/mcp/builtin/browser.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py)
2. operation-specific tool contracts are defined for:
   - `builtin:browser_open`
   - `builtin:browser_snapshot`
   - `builtin:browser_click`
   - `builtin:browser_type`
   - `builtin:browser_press`
   - `builtin:browser_screenshot`
3. builtin registry metadata now exposes optional `output_schema` and contract `metadata`, in addition to existing `input_schema`
4. the current branch now has a split execution posture:
   - `builtin:browser_open` executes through a minimal Playwright-backed single-use flow
   - `builtin:browser_snapshot` executes through a minimal Playwright-backed single-use flow
   - `builtin:browser_screenshot` executes through a minimal Playwright-backed single-use flow
   - `builtin:browser_press` executes through a minimal Playwright-backed single-use flow
   - `builtin:browser_click` executes through a minimal Playwright-backed single-use flow using authoritative snapshot-minted targets
   - `builtin:browser_type` executes through a minimal Playwright-backed single-use flow using authoritative snapshot-minted targets
5. a minimal builtin browser skill package now exists in [`backend/data/skills/browser-operator/`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/skills/browser-operator)
6. browser action safety is now contractually separated into:
   - lower-risk operations using `approval_policy: auto`
   - mutating operations using `browser_write` or `browser_mutation`
7. stable runtime metadata now flows through invocation/preflight/execution payloads using:
   - `tool_family`
   - `operation`
   - `runtime_metadata_expectations`
   - `runtime_metadata`
8. intelligence panel action details now surface browser contract summary/context via the existing generic action detail renderer path

Still intentionally not implemented:

1. a real browser execution engine
2. Playwright runtime/session management
3. login persistence
4. CAPTCHA handling
5. autonomous browser planning or hidden loops
6. browser-specific persistence outside the existing action lifecycle

Current Phase 2 interpretation on this branch:

1. read-only browser operations can execute as single-use URL-scoped actions without introducing new persistent browser state
2. `press` can also execute in a constrained single-use mode because a page-level key event does not require stable cross-call element targeting
3. `click` and `type` can now execute in a constrained single-use authoritative-target mode
4. session continuity and resumed target validity remain the next explicit design boundary

### Phase 2: Backend Tool Integration

Scope:

1. implement the builtin browser tool(s)
2. return structured results, not free-form strings only
3. surface useful metadata for frontend traces

Success condition:

1. open / snapshot / screenshot work in a controlled environment
2. press can work in a controlled page-level mode without requiring stable element reuse
3. click / type can work in a controlled authoritative-target mode without selector fallback
4. failures are visible and structured

### Phase 2 Boundary Clarification

Phase 2 should now be treated as a narrow backend integration pass rather than a broader browser platform build-out.

Allowed scope:

1. replace placeholder execution in the existing builtin browser tool family with a controlled real backend implementation
2. preserve existing operation-specific tool ids and input schemas where practical
3. return structured result payloads that fit the already-declared output/result contract
4. surface page metadata, element references, screenshot artifact paths, and structured failure details through the existing action lifecycle
5. add focused regression coverage and only minimal frontend renderer refinements if backend payloads require it
6. allow single-use URL-scoped execution for operations that do not require stable cross-call element identity

Explicitly out of scope unless re-approved:

1. login/account persistence
2. CAPTCHA solving
3. hidden multi-step autonomous browser loops
4. cross-session browser state as a new subsystem
5. browser-specific chat runtime redesign
6. browser-specific frontend panel redesign beyond incremental renderer work
7. silently changing `click` or `type` into best-effort selectors that bypass the declared `element_ref` contract

Guiding rule:

1. if a change cannot stay inside Yue's current tool-backed action lifecycle, it should be deferred

Additional guardrail for mutation operations:

1. `press` may proceed first because it can be modeled as a page-level mutation in a single-use browser context
2. `click` and `type` may proceed only when they consume platform-minted targets without selector fallback
3. resumable continuity for `click` and `type` still should not proceed until Yue decides how `element_ref` is persisted and validated across action boundaries
4. if strengthening `click` or `type` would force ad hoc selector parsing or hidden page state reuse, the work should stop at the current single-use boundary

### Phase 2.5: Session Continuity And Stable Target Identity Contract

Purpose:

1. define the minimum contract Yue needs before `click` or `type` can move from placeholder to real execution
2. keep the design future-kernel-friendly by separating reusable action/runtime semantics from Yue-specific persistence and chat UX

Recommended minimum contract:

1. `session_id`
   - platform-owned browser session identity
   - nullable for single-use operations such as the current `open`, `snapshot`, `screenshot`, and constrained `press`
   - required for any operation that claims to reuse prior browser state
2. `tab_id`
   - platform-owned tab identity scoped to one `session_id`
   - optional for single-use operations
   - required when a follow-up operation depends on an existing tab rather than a fresh page
3. `element_ref`
   - opaque platform-issued target reference
   - must not be a raw CSS selector or XPath in the public action/tool contract
   - should be minted from a snapshot result or equivalent platform-owned inspection step
   - should be treated as invalid once the underlying page/navigation context has changed beyond the rules declared by the platform

Recommended target-binding metadata:

1. `binding_source`
   - identifies the snapshot or inspection result that minted the target
2. `binding_session_id`
   - session identity expected by the target
3. `binding_tab_id`
   - tab identity expected by the target
4. `binding_url`
   - URL observed when the target was minted
5. `binding_dom_version`
   - optional monotonic or hash-like page-structure marker for future stronger validation

Recommended snapshot output additions:

1. each interactive element returned by `snapshot` may carry a `target_binding` object
2. the snapshot payload may also carry a snapshot-level `target_binding_context`
3. both shapes should use the same binding vocabulary so target minting remains consistent across tools and host adapters

Minimum validity rules:

1. a runtime may execute `click` or `type` only when:
   - `session_id` is present
   - `tab_id` is present
   - `element_ref` is present
   - the runtime can confirm the target belongs to the same active tab context
2. if target validation cannot be performed, the operation should fail as a structured contract/runtime error rather than silently falling back to selector guesses
3. a new navigation may invalidate previously minted targets unless the runtime can explicitly prove continuity

Recommended structured failure categories:

1. `browser_session_required`
2. `browser_tab_required`
3. `browser_target_required`
4. `browser_target_stale`
5. `browser_target_context_mismatch`

Recommended contract metadata for reuse-sensitive operations:

1. `click` and `type` should publish `structured_failure_codes` in tool/action metadata
2. those codes should be treated as contract vocabulary first, even before a full validation engine exists
3. the first required set should include:
   - `browser_session_required`
   - `browser_tab_required`
   - `browser_target_required`
   - `browser_target_stale`
   - `browser_target_context_mismatch`

Kernel-friendly boundary:

1. reusable/kernel candidate:
   - target identity vocabulary
   - minimum validation rules
   - structured failure categories
   - runtime metadata expectations for reuse-sensitive operations
2. Yue-adapter-specific:
   - where session/tab state is persisted
   - how action history or SSE wording describes the mismatch
   - how the intelligence panel visualizes stale-target failures

Recommendation for next implementation step after this contract:

1. do not implement `click` or `type` until Yue first chooses a platform-owned target minting path
2. the smallest acceptable next step is:
   - add session-aware snapshot result metadata
   - define how `element_ref` is minted and invalidated
   - keep `click` and `type` placeholder until that path is proven by tests

### Phase 3: Frontend Browser Renderer

Scope:

1. add browser-specific renderer sections
2. reuse current action detail infrastructure
3. avoid a separate browser-only panel

Success condition:

1. browser results are readable without opening raw payloads
2. screenshots and page metadata are clearly visible

### Phase 4: Builtin Agent And Manual QA Flows

Scope:

1. add `builtin-agent-browser`
2. provide a manual smoke-test script
3. verify approval and trace flows in the intelligence panel

Success condition:

1. users can test browser automation without custom setup
2. the feature is demonstrable end to end

## 13. Manual Test Scenarios For MVP

Recommended initial manual tests:

1. open a public page and capture a snapshot
2. send a harmless page-level key press after approval
3. take a screenshot and verify artifact rendering
4. inspect grouped action history for a multi-step browser flow

Deferred until session/targeting policy is explicit:

1. click a harmless navigation element
2. type into a search field after approval

These scenarios should verify:

1. preflight and approval behavior
2. structured browser result payloads
3. focused trace usefulness
4. renderer readability

## 14. Risks

Main risks:

1. letting the browser tool grow too broad before the contract is stable
2. hiding too much state inside the browser execution layer
3. making browser results unstructured and hard to render
4. weakening approval boundaries for mutating actions

Most of these risks can be reduced by keeping MVP small and action contracts explicit.

## 15. Recommendation

The right next move is not to build a full autonomous browser operator immediately.

The right next move is:

1. define a narrow browser builtin tool family
2. route it through the current tool-backed action runtime
3. keep mutation steps approval-gated
4. add browser-specific renderer support only after the result payload shape is clear

That approach lets `agent-browser` validate the current architecture while still shipping a genuinely useful first version.
