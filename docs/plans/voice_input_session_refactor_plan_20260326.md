# Voice Input Session Refactor Plan (2026-03-26)

## Current Responsibilities And Pain Points

The current voice input flow mixes three responsibilities across `frontend/src/hooks/useVoiceInput.ts` and `frontend/src/pages/Chat.tsx`:

1. Speech recognition provider orchestration
2. Session lifecycle and transcript buffering
3. Direct composer mutation during recognition

This creates several stability risks:

- Recognition interim state is written straight into the chat textarea.
- Final commit depends on UI effects observing `isRecording` and `isProcessing`.
- Old transcript state can leak into the next recording session.
- Browser and Azure recognition callbacks can arrive after the UI has conceptually moved on.
- The composer acts as both source text and destination text, which makes cancellation and resume behavior fragile.

## Target Structure

Refactor voice input into a session-oriented model that mirrors Codex-style behavior more closely:

- `useVoiceInput.ts`
  - Owns a single isolated voice session state machine
  - Buffers draft transcript independent from the composer
  - Exposes explicit actions for `start`, `stop`, `cancel`, `commit`, and `clear`
- `Chat.tsx`
  - Treats voice input as a sidecar draft, not live textarea content
  - Commits voice text into the textarea only through an explicit action
- `ChatInput.tsx`
  - Shows session status and preview
  - Offers explicit controls for stop, insert, and cancel when appropriate

## Proposed State Model

Recommended phases:

- `idle`
- `recording`
- `finalizing`
- `ready`
- `error`

Session fields:

- `sessionId`
- `provider`
- `baseText`
- `transcript`
- `interimTranscript`
- `error`
- `fallbackMessage`

Behavior rules:

- A new recording session always creates a new `sessionId`.
- Recognition callbacks are ignored unless they match the active session.
- The textarea is never mutated from interim recognition events.
- Final transcript remains in voice state after stop and becomes `ready`.
- The user explicitly chooses to insert the voice draft into the textarea.
- Starting a new session clears all previous voice draft state first.

## Phased Migration Plan

### Phase 1: Voice Hook Refactor

- Convert boolean recording flags into a single session phase accessor plus compatibility helpers.
- Store `baseText` inside the voice hook rather than `Chat.tsx`.
- Add explicit `hasDraft`, `previewText`, `commitToComposerText`, and `clearDraft` behavior.
- Guard async callbacks with `sessionId`.

### Phase 2: Chat Integration

- Remove composer-syncing effects that mirror recognition text into the textarea.
- Replace them with a single insert action that uses the hook's committed text.
- Keep send behavior safe: if voice is finalizing, stop first; if a draft is ready, let the user insert before sending.

### Phase 3: Composer UX

- Update the voice status card to show a clear draft lifecycle.
- Recording state: show preview and stop/cancel controls.
- Ready state: show final recognized text plus `Insert` and `Discard`.
- Keep the main textarea stable until insert is clicked.

### Phase 4: Regression Coverage

- Add unit tests around session transitions and stale callback dropping.
- Add UI helper tests for draft-ready actions.
- Keep existing speech helper tests passing.

## Risk Assessment

Main risks:

- Browser recognition `onend` timing may differ from mocks.
- Azure callbacks may arrive after stop or cancel.
- Existing submit behavior may unintentionally send stale input if draft handling is unclear.

Mitigations:

- Session id guards on every async callback
- Explicit draft clearing on start and cancel
- Composer mutations only through a single insert path
- Focused tests for repeated recording cycles

## Test And Regression Strategy

- Unit test `useVoiceInput` helpers and session transitions
- Regression test start -> stop -> start again
- Regression test cancel after partial transcript
- Build the frontend after refactor

## Rollout Recommendation

Single PR is reasonable if scoped to frontend voice input only:

1. Hook refactor
2. Chat/composer integration
3. Tests and validation

## Execution Notes

- User approved proceeding with the Codex-style direction on 2026-03-26.
- Implementation and validation results will be appended after execution.

## What Actually Changed

- Refactored `frontend/src/hooks/useVoiceInput.ts` into a session-oriented voice draft controller.
- Added explicit voice phases: `idle`, `recording`, `finalizing`, `ready`, `error`.
- Moved voice draft commit behavior out of reactive textarea sync and into an explicit insert action.
- Updated `frontend/src/pages/Chat.tsx` to keep the composer stable while voice recognition is active.
- Added a short post-insert composer lock to prevent late browser/native input events from overwriting the committed draft.
- Updated `frontend/src/components/ChatInput.tsx` to show voice draft actions (`Insert`, `Discard`) after recognition completes.
- Updated Playwright voice input scenarios to target the new draft-first UX and added a repeated-recording regression case.

## Deviations From The Original Plan

- Kept the browser and Azure provider orchestration inside the existing hook rather than splitting provider adapters into separate modules in this pass.
- Added a defensive composer lock in `Chat.tsx` because browser-level delayed input events still appeared in real-browser testing.

## Final Validation Results

Passed:

- `npm test -- --run src/hooks/useVoiceInput.test.ts src/components/ChatInput.multimodal.test.tsx`
- `npm run build`
- `npx playwright test e2e/voice-input.spec.ts -g "browser speech creates a draft"`

Partial:

- Full `npx playwright test e2e/voice-input.spec.ts` remains flaky when all mocked voice scenarios run sequentially in one session. The browser and Azure insert tests intermittently regress to partial textarea content, which suggests there is still cross-test or delayed input-event timing to stabilize in the test harness or UI lock behavior.

## Follow-Up Suggestions

- Add a dedicated voice session store test harness so we can unit test transition timing without relying only on Playwright.
- Consider increasing isolation around textarea input while a voice draft is active, potentially by rendering the composer in read-only mode during draft-ready transitions.
- If we want to get even closer to Codex behavior, the next step would be a more explicit voice tray or modal instead of reusing the inline composer status strip.
