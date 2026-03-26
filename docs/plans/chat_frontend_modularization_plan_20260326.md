# Chat Frontend Modularization Plan (2026-03-26)

## Scope

This plan covers the frontend chat surface with special focus on the recently stabilized voice-input flow:

- `frontend/src/hooks/useChatState.ts`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/hooks/useVoiceInput.ts`

The goal is to improve cohesion, reduce file size, and make future changes safer without changing user-visible behavior.

## Current Responsibilities And Pain Points

### 1. `useChatState.ts`

Current responsibilities:

- chat history loading and deletion
- chat submission orchestration
- image serialization
- SSE stream parsing and assistant message mutation
- generation stop/regenerate behavior
- message-level utility actions

Pain points:

- Submission and stream parsing are tightly coupled in one large function.
- History concerns and live-run concerns live in the same hook.
- The hook has grown into a "god object" and is now the hardest place to test in isolation.
- Voice-input direct send now depends on a low-level `submitText(...)` seam that deserves a clearer API boundary.

### 2. `Chat.tsx`

Current responsibilities:

- page layout and responsive orchestration
- chat sidebar and content composition
- global event listeners
- mention picker orchestration
- mermaid preview logic
- speech playback wiring
- voice composer integration, focus behavior, and commit lock handling

Pain points:

- Page-level layout code is mixed with input-controller logic.
- Voice draft shortcut handling and composer lock behavior are embedded in the page component.
- This makes the file hard to scan and increases the risk of regressions when touching unrelated UI areas.

### 3. `ChatInput.tsx`

Current responsibilities:

- composer textarea
- model/tool bar
- image attachment preview row
- voice input button
- voice draft status card
- submit button rendering

Pain points:

- The component is visually coherent, but functionally overloaded.
- Voice draft UI now has enough complexity to deserve its own component.
- Image attachment UI and voice status UI are independent concerns but are rendered inline in one large block.

### 4. `useVoiceInput.ts`

Current responsibilities:

- voice session state machine
- browser dictation provider
- Azure provider integration
- Azure SDK lazy loading
- transcript normalization and commit semantics

Pain points:

- State-machine logic and provider implementations are coupled.
- Browser and Azure callback flows are long and hard to compare.
- The hook is stable now, but provider-specific debugging or extension will get harder as it grows.

## Existing Regression Protection

The current baseline is strong enough to support incremental refactoring:

- Unit tests:
  - `frontend/src/hooks/useVoiceInput.test.ts`
- Component/helper tests:
  - `frontend/src/components/ChatInput.multimodal.test.tsx`
  - `frontend/src/pages/settings/types.test.ts`
- E2E voice regression:
  - `frontend/e2e/voice-input.spec.ts`

Protected voice scenarios currently include:

- browser draft creation
- Enter insert
- direct Send button
- Cmd/Ctrl+Enter send
- Escape discard
- focus staying on the voice button
- Azure STT path
- Azure fallback to browser
- repeated recording after discard

## Target Structure

### A. Chat State Layer

Refactor `useChatState.ts` into smaller units:

- `frontend/src/hooks/chat/useChatHistory.ts`
  - history loading
  - delete
  - summary refresh
  - chat meta refresh
- `frontend/src/hooks/chat/useChatSubmission.ts`
  - `submitText`
  - `handleSubmit`
  - stop generation
  - regenerate
- `frontend/src/hooks/chat/chatStreamProcessor.ts`
  - parse SSE lines
  - normalize stream events
  - update assistant message state

Design intent:

- `useChatState` remains as a thin composition layer and compatibility facade.
- Existing consumers should not need to change all at once.

### B. Chat Page Integration Layer

Extract page-specific orchestration from `Chat.tsx`:

- `frontend/src/hooks/chat/useVoiceComposerIntegration.ts`
  - voice insert/send/cancel actions
  - composer lock/replay behavior
  - focus restoration
  - voice draft keyboard shortcuts
- `frontend/src/hooks/chat/useChatGlobalInteractions.ts`
  - global click / keydown listeners
  - mermaid overlay cleanup

Design intent:

- `Chat.tsx` becomes mostly layout and prop wiring.
- Voice behavior gets its own narrow seam and dedicated tests later.

### C. Chat Input View Layer

Split `ChatInput.tsx` into view-focused pieces:

- `frontend/src/components/chat-input/VoiceDraftCard.tsx`
- `frontend/src/components/chat-input/ImageAttachmentTray.tsx`
- `frontend/src/components/chat-input/ComposerToolbar.tsx`

Design intent:

- keep `ChatInput.tsx` as the top-level shell
- move dense conditional UI blocks into small, focused components

### D. Voice Provider Layer

Refactor `useVoiceInput.ts` incrementally:

- `frontend/src/hooks/voice/voiceSessionMachine.ts`
  - phase transitions
  - draft lifecycle
  - session guards
- `frontend/src/hooks/voice/browserVoiceProvider.ts`
  - browser recognition start/stop wiring
- `frontend/src/hooks/voice/azureVoiceProvider.ts`
  - Azure SDK loading and recognizer wiring

Design intent:

- keep `useVoiceInput` as public entrypoint
- move provider mechanics behind internal helpers first

## Phased Migration Plan

### Phase 1: Stabilize Public Seams

- Keep existing exports and prop shapes intact.
- Document internal seams that already exist:
  - `submitText(...)`
  - voice insert/send/cancel handlers
  - stream processing paths
- Add a small amount of test coverage only where a new extraction seam needs protection.

Success condition:

- no behavior change
- no new user-visible copy change
- all current tests stay green

### Phase 2: Extract Chat Submission And Stream Processing

- Move stream parsing logic out of `useChatState.ts`.
- Move submission orchestration into `useChatSubmission.ts`.
- Keep `useChatState` returning the same public API for now.

Success condition:

- same tests still pass
- `useChatState.ts` shrinks materially
- stream parsing becomes directly testable

### Phase 3: Extract Voice Composer Integration From `Chat.tsx`

- Move voice draft shortcut handling, composer lock logic, and focus restoration into a dedicated hook.
- Keep `Chat.tsx` responsible only for wiring returned handlers and signals.

Success condition:

- keyboard shortcuts still work
- direct Send/Insert/Discard still work
- focus regression tests remain green

### Phase 4: Split `ChatInput.tsx` Presentation Blocks

- Extract `VoiceDraftCard`
- Extract image attachment tray
- Extract toolbar where beneficial

Success condition:

- no interaction change
- easier visual diff review
- `ChatInput.tsx` becomes a composition component rather than a large render block

### Phase 5: Internal Voice Provider Extraction

- Move browser and Azure provider logic behind internal modules.
- Keep `useVoiceInput` as the single public hook.

Success condition:

- provider behavior unchanged
- Azure fallback tests remain green
- session semantics unchanged

## Risk Assessment

### Highest-Risk Areas

- stream parsing extraction from `useChatState.ts`
- voice composer lock behavior in `Chat.tsx`
- Azure fallback timing in `useVoiceInput.ts`

### Main Regression Modes

- assistant stream content no longer applies incrementally
- voice Send path regresses back to textarea timing dependence
- direct Insert path reintroduces stale browser callback overwrite
- shortcut listeners conflict with composer submit behavior

### Mitigations

- preserve current outward API during early phases
- refactor one concern at a time
- run focused regressions after each phase
- prefer structure-only extraction before semantic cleanup

## Test And Regression Strategy

### Keep As Gate Checks For Every Phase

- `npm test -- --run src/hooks/useVoiceInput.test.ts src/components/ChatInput.multimodal.test.tsx src/pages/settings/types.test.ts`
- `npx playwright test e2e/voice-input.spec.ts`
- `npm run build`

### Add Later If Needed During Refactor

- unit tests for extracted stream processor
- unit tests for voice composer lock/replay helper
- component tests for `VoiceDraftCard`

## PR / Change Split Recommendation

Recommended sequence:

1. PR 1: Extract chat submission and stream processor
2. PR 2: Extract voice composer integration from `Chat.tsx`
3. PR 3: Split `ChatInput.tsx` presentation components
4. PR 4: Internal provider extraction from `useVoiceInput.ts`

If done in one working branch, still keep the same phase boundaries and validate after each phase.

## Approval Checkpoint

Recommended first implementation target:

- Start with `frontend/src/hooks/useChatState.ts`

Why first:

- it has the biggest responsibility overlap
- it already exposes the new `submitText(...)` seam used by voice draft send
- shrinking it will make later `Chat.tsx` and `ChatInput.tsx` cleanup easier

## Expected Outcome

After this refactor sequence:

- page-level files should become easier to scan
- voice-specific behavior should be isolated and easier to reason about
- stream submission and parsing should be testable without touching page layout
- future voice and composer changes should require edits in fewer places

## Phase 2 Progress Update

### What Actually Changed

- Extracted stream helpers into `frontend/src/hooks/chat/chatStream.ts`
- Extracted chat submission and SSE application flow into `frontend/src/hooks/chat/chatSubmission.ts`
- Updated `frontend/src/hooks/useChatState.ts` to become a thinner orchestrator that composes those internal modules
- Preserved existing public exports from `useChatState.ts` so current imports and tests did not need to change

### Deviations From The Original Plan

- This pass kept history loading inside `useChatState.ts`; only the submission/stream path was extracted
- Helper re-exports were intentionally preserved from `useChatState.ts` to avoid a broad import migration in the same step

### Validation Results

Passed:

- `npm test -- --run src/hooks/useChatState.events.test.ts src/hooks/useChatState.multimodal.test.ts src/hooks/useVoiceInput.test.ts src/components/ChatInput.multimodal.test.tsx src/pages/settings/types.test.ts`
- `npx playwright test e2e/voice-input.spec.ts`
- `npm run build`

### Follow-Up Recommendation

- Next extraction should target the voice composer integration currently embedded in `frontend/src/pages/Chat.tsx`
- After that, split `frontend/src/components/ChatInput.tsx` presentation blocks, starting with the voice draft card
