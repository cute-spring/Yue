# Smart Visibility for Evidence Panels

## Purpose
Improve the UI/UX of the chat interface by reducing visual noise and cognitive load. The "Used context" and "Evidence contract" panels currently display for every message, even when they contain no meaningful information (e.g., "no_context_needed", "0 eligible sources"). This design implements "smart visibility" to hide these panels when empty, ensuring they only draw attention when actual traceability data is present.

## Constraints
- Must not remove the data from the underlying message object, only hide the UI representation.
- Must ensure that any actual context, sources, warnings, or errors are still clearly visible to the user.
- The UI should not bounce or jitter unnecessarily; the panels should simply not render if conditions are met.

## Success Criteria
- The "Used context" panel is hidden when `msg.session_used_context.reason` indicates no context was needed or when it's otherwise empty.
- The "Evidence contract" panel is hidden when `msg.workspace_grounding` has 0 eligible sources, 0 unavailable sources, and no warnings/errors.
- Messages with actual context or sources continue to display the panels exactly as before.

## Component Changes: `MessageEvidencePanel.tsx`

### 1. "Used Context" Visibility Logic
Currently:
```tsx
<Show when={props.msg.session_used_context}>
```
Change to:
```tsx
<Show when={
  props.msg.session_used_context && 
  props.msg.session_used_context.reason !== 'no_context_needed' &&
  props.msg.session_used_context.reason !== 'no_reference_signal'
}>
```
*(We will verify the exact strings used by the backend for empty context states, but `no_context_needed` and `no_reference_signal` are the targets based on the user request).*

### 2. "Evidence Contract" Visibility Logic
Currently:
```tsx
<Show when={props.msg.workspace_grounding}>
```
Change to:
```tsx
<Show when={
  props.msg.workspace_grounding && 
  (
    (props.msg.workspace_grounding.eligible_sources?.length ?? 0) > 0 ||
    (props.msg.workspace_grounding.unavailable_sources?.length ?? 0) > 0 ||
    getWorkspaceCitationWarning(props.msg) !== undefined ||
    getWorkspaceToolingWarning(props.msg) !== undefined
  )
}>
```

## Data Flow & Architecture
- No changes to backend API or data structures.
- No changes to state management.
- Purely a presentation layer logic update in `frontend/src/components/message-item/MessageEvidencePanel.tsx`.

## Testing
- Verify rendering with a message containing no context/sources (panels should be hidden).
- Verify rendering with a message containing context/sources (panels should be visible).
- Run existing UI tests (e.g., `workspace-grounded-answer.spec.ts`) to ensure no regressions.
