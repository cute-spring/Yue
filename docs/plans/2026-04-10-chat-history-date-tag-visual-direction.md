# 2026-04-10 Chat History Date + Tag Visual Direction

## Visual Thesis
Calm operator workspace: a precise timeline surface with emerald accents where date groups feel structural and tags feel actionable.

## Content Plan
1. Hero region (sidebar header)
- `Chat History` label and `New Chat` action.

2. Support region (filter band)
- active chips, date presets, clear action.

3. Detail region (timeline groups)
- grouped session rows with sticky date headers.

4. Final action region (empty/recovery states)
- focused call-to-action with one primary button.

## Interaction Thesis
1. Group-header stickiness
- headers glide and pin while scrolling to maintain temporal context.

2. Filter chip transitions
- soft scale and color transition on select/deselect (`160ms`).

3. Session row reveal
- slight lift and accent bar expansion on hover/focus (`140ms`).

## Art Direction Rules
- Avoid card mosaics; prefer flat list planes with clear dividers.
- One accent color (`--primary`) for active and selected states.
- Keep body copy compact and utility-first.
- Limit each row to one dominant signal: title first, then tags, then date.

## Typography and Scale
- Sidebar title: `11px`, uppercase, wide tracking.
- Group header: `12px`, semibold.
- Session title: `13px`, medium, one-line truncate.
- Meta (summary/date/tags): `10-11px`.

## Color System (Light Theme)
```css
--history-bg: #f8fafc;
--history-surface: #ffffff;
--history-divider: #e5e7eb;
--history-text: #111827;
--history-muted: #6b7280;
--history-primary: #10b981;
--history-primary-soft: rgba(16, 185, 129, 0.12);
--history-tag-bg: #ecfeff;
--history-tag-text: #0f766e;
```

## Motion Guidelines
- Use opacity + translate only for list entrance to avoid jank.
- Prefer `transform` over size/position relayout animation.
- Keep all micro-interactions under `200ms`.
- Respect `prefers-reduced-motion`.

## Section-by-Section Notes
### Filter Band
- Compact and always scannable.
- Active filters shown as first-class chips, not hidden in menus.

### Date Headers
- Subtle tinted background strip for contrast.
- Sticky with 1px divider to reinforce section boundary.

### Session Rows
- Left accent bar only on selected row.
- Tags inline below title, max 3 visible to prevent visual noise.

### Empty States
- No illustrations needed.
- One concise sentence + one clear action.

## Do and Do Not
### Do
- Keep rhythm consistent (8px vertical spacing).
- Use contrast to emphasize current chat and active filters.
- Keep control density high but readable.

### Do Not
- Do not introduce extra accent colors for tags.
- Do not wrap each chat row in a card.
- Do not use heavy shadows for routine list items.
- Do not animate layout shifts on every filter update.

## Implementation Notes for Current Code
- Start in `frontend/src/components/ChatSidebar.tsx`.
- Extract filter row into `ChatHistoryFilters.tsx` when JSX density grows.
- Keep class naming aligned with existing Tailwind token usage.
