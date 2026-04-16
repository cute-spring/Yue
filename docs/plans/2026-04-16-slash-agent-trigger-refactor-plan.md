# Slash Agent Trigger Refactor Plan (2026-04-16)

## Scope

Replace the current `@`-based agent picker trigger in chat composer with a `/`-first flow while preserving existing keyboard navigation, accessibility, chat submission, and voice-input behavior.

Primary files in scope:

- `frontend/src/pages/Chat.tsx`
- `frontend/src/hooks/useAgents.ts`
- `frontend/src/components/AgentSelector.tsx`
- `frontend/src/hooks/useAgents.slash-trigger.test.ts` (new)

Out of scope:

- Backend agent APIs
- Agent model/skill selection behavior after selection
- General chat slash command handling (for submit-time commands)

## Current State

- Input parsing in `Chat.tsx` detects `@` near cursor and toggles the agent picker.
- Agent selection logic in `useAgents.ts` removes `@mention` token and sets selected agent.
- Picker header in `AgentSelector.tsx` communicates `@` mention semantics.
- No dedicated test coverage for trigger parsing and mention-token replacement.

## Target Behavior

### Trigger Rules

1. Show agent picker when the cursor is in a leading slash token at input start.
2. A valid leading slash token means:
   - Text before cursor starts with `/`
   - Text after `/` and before cursor contains no whitespace
3. Real-time filter string is the substring after the leading `/` up to cursor.
4. Hide picker when:
   - Cursor is not inside the leading slash token
   - Input does not start with `/`
   - Whitespace appears inside the prefix segment before cursor

### Selection Rules

1. On agent selection, set selected agent ID as today.
2. Remove the leading slash token from input.
3. Preserve remaining text after the token and normalize away leading whitespace introduced by token removal.

### Keyboard/Accessibility

- Keep existing arrow key navigation, Enter to select, Escape to dismiss.
- Keep current picker rendering and role semantics; only trigger language/indicator text changes from `@` to `/`.

## Refactor Strategy

### Step 1: Extract testable helper seams in `useAgents.ts`

Add pure helper functions:

- derive picker visibility/filter from `(input, cursorPos)`
- compute input rewrite after slash-agent selection
- optional pure filter helper for agent-name narrowing

Reason: isolate parser/rewrite behavior for focused unit tests and reduce risk in `Chat.tsx`.

### Step 2: TDD Red Phase

Add focused unit tests that fail initially:

- Trigger detection:
  - `/` at beginning shows picker
  - `/abc` narrows filter to `abc`
  - non-leading slash does not trigger
  - whitespace in leading segment hides picker
- Selection replacement:
  - removes slash token when selected
  - keeps trailing user text
  - no-op if input is not slash-token form
- Filtering:
  - narrows by case-insensitive substring

### Step 3: Green Phase

Implement minimal behavior changes:

- `Chat.tsx` uses new helper for parsing trigger/filter state.
- `useAgents.ts` selection path uses slash-token rewrite helper.
- `AgentSelector.tsx` visual affordance updates from `@` to `/`.

### Step 4: Refactor Phase

- Keep naming and function boundaries concise.
- Avoid unrelated styling/behavior refactors.
- Retain existing event and keyboard flow.

## Verification Plan

1. Run targeted new tests:
   - `npm run test -- useAgents.slash-trigger.test.ts`
2. Run adjacent existing chat input helper tests:
   - `npm run test -- ChatInput.multimodal.test.tsx`
3. Optional broader frontend tests if fast enough:
   - `npm run test`

Success criteria:

- New slash-trigger tests pass.
- Existing related tests remain green.
- No regression in keyboard selection behavior in code path.

## Risks And Mitigations

1. Risk: slash trigger collides with submit-time slash commands.
   - Mitigation: trigger only while cursor is in leading slash token during typing; submission logic unchanged.
2. Risk: input rewrite removes unintended text.
   - Mitigation: isolate and test rewrite helper with no-op scenarios.
3. Risk: keyboard behavior regression.
   - Mitigation: avoid changes to keydown branch logic except trigger source.

## Implementation Notes

- Keep diff small and localized.
- Do not change backend contracts.
- Preserve all existing dirty-worktree edits outside these files.
