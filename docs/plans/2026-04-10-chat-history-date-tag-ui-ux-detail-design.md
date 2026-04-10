# 2026-04-10 Chat History Date + Tag UI/UX Detail Design

## Product Goal
Help users find previous chats quickly by combining:
- chronological grouping (scan by time)
- tag filtering (jump by topic)

## Information Architecture
### Sidebar Structure (top to bottom)
1. Header
- title: `Chat History`
- action: `New Chat`

2. Filter Zone
- search input (existing keyword)
- tag filter row (multi-select chips)
- date quick filters (`Today`, `7d`, `30d`, `Custom`)
- active filter summary and clear action

3. Grouped Session List
- sections:
  - `Today`
  - `Yesterday`
  - `Last 7 Days`
  - `Older`
- each section collapsible

4. Empty and Recovery States
- no chats at all
- no results for filter
- loading skeleton

## Interaction Spec
### Tag Filtering
- Click a tag chip to toggle selection.
- Selected chips stay pinned at top in "Active filters".
- Default mode: `ANY` for reduced friction.
- Advanced mode switch: `ANY` <-> `ALL`.
- Clearing filters keeps current scroll position.

### Date Grouping
- Group headers are sticky while scrolling.
- Group headers show count, e.g., `Yesterday (6)`.
- Collapsing a group preserves state during session.

### Session Item
- Keep current controls: generate summary, delete.
- Add visible tag pills (max 3, rest as `+N`).
- Keep current selected-row highlight behavior.

## Component-Level Design
### `ChatSidebar.tsx`
- Own layout shell, grouped list, section collapse states.
- Receives:
  - filtered sessions
  - active filters
  - callbacks for filter updates.

### `ChatHistoryFilters.tsx` (new)
- Owns filter input controls and filter summary bar.
- Emits normalized filter state:
  - `selectedTags: string[]`
  - `tagMode: 'any' | 'all'`
  - `datePreset: 'today' | '7d' | '30d' | 'custom' | null`
  - `customRange`.

### `useChatState.ts`
- Source of truth for:
  - raw sessions
  - filter state
  - derived grouped sessions.

## State Model
```ts
type ChatHistoryFilterState = {
  query: string;
  selectedTags: string[];
  tagMode: 'any' | 'all';
  datePreset: 'today' | '7d' | '30d' | 'custom' | null;
  dateFrom?: string;
  dateTo?: string;
};
```

## UX Copy
- Empty global:
  - "No chats yet. Start a new conversation."
- Empty filtered:
  - "No chats match these filters."
  - secondary action: "Clear filters"
- Tag generation pending:
  - "Tagging..."

## Accessibility Requirements
- All filter controls keyboard reachable.
- Tag chips use `aria-pressed` toggle semantics.
- Group collapse buttons expose `aria-expanded`.
- Announce result count changes via polite live region.

## Responsive Behavior
- Desktop:
  - full filter zone always visible.
- Tablet/mobile:
  - compact filter bar with `Filters` drawer button.
  - chips horizontally scrollable with snap behavior.

## Edge Cases
- Untagged sessions:
  - still shown with subtle `Untagged` badge.
- Invalid historical timestamps:
  - fall into `Older`.
- Too many tags:
  - show top relevance tags + `More` popover.

## Testing Checklist
- Component tests:
  - tag toggle
  - `ANY`/`ALL` logic
  - grouped rendering counts.
- E2E:
  - date presets update list correctly
  - mobile drawer filter workflow
  - keyboard navigation for chips and group toggles.
