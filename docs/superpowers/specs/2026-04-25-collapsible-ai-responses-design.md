# Collapsible AI Responses Design

## Intent
Improve the navigability of multi-turn chat sessions by implementing a feature that automatically collapses historical AI responses into concise summaries. This prevents long AI responses from overwhelming the visual space and obscuring important context.

## Design

### 1. Behavior
- **Default State**: All AI responses are collapsed by default.
- **Exception (Generating)**: When an AI message is actively being generated (`isTyping === true`), it remains fully expanded so the user can read the response in real-time.
- **Transition**: The moment generation completes, the message automatically collapses.
- **User Override**: Users can manually click to expand any collapsed message or click a button to collapse any expanded message. Manual states persist and override the default behavior.

### 2. Components

**MessageItem.tsx**
- Introduce `isManuallyExpanded` and `isManuallyCollapsed` SolidJS signals.
- Introduce `isCollapsed` memoized state:
  ```tsx
  const isCollapsed = createMemo(() => {
    if (props.msg.role === 'user') return false;
    if (isManuallyExpanded()) return false;
    if (isManuallyCollapsed()) return true;
    return !props.isTyping; // Smart collapse
  });
  ```
- **Collapsed UI**: Renders the first 100 characters of the AI's response text alongside an "Expand" chevron button. Clickable area covers the summary row.
- **Expanded UI**: Existing message content rendering, plus an added "Collapse" button in the action bar (next to copy, regenerate, etc.).

**MessageList.tsx**
- `isLatest` logic removed, as all AI responses share the same rule based on `isTyping`.

## Trade-offs Considered
- **Length-based vs. Uniform Collapse**: Chose uniform collapse for all AI responses (regardless of length) to maintain a consistent UI rhythm and avoid arbitrary length thresholds.
- **Collapse on Complete vs. Always Collapse History**: Chose "Collapse on Complete" so that the user's active reading experience isn't abruptly interrupted, but as soon as the turn is over, space is reclaimed.

## Status
Approved and implemented.
