# 2026-09-07 Workspace Understanding Product Spec

## 1. Product Thesis

Workspace should make Yue feel like it gets smarter the more the user works with it.

The core promise is not file management, chat filtering, or raw retrieval configuration. The promise is:

> Yue should remember enough about the user and the current area of work that the user does not need to re-explain background, goals, constraints, preferences, terminology, decisions, and current state every time.

Workspace is therefore the user-facing home for `About This Workspace`, while `About You` remains a lightweight cross-workspace layer that can be previewed when relevant.

## 2. User Problem

Users repeatedly spend time re-establishing context:

- what this effort is about
- what has already been decided
- what constraints matter
- what language, style, or workflow they prefer
- what terms mean in this context
- what is still open or unresolved
- what the current state is

This repetition makes Yue feel stateless even when chat history, notes, sources, and memory records exist technically.

## 3. Product Goals

- Make Yue's current understanding visible and reviewable.
- Let users confirm durable understanding at the moment it emerges in conversation.
- Separate user-level memory from workspace-level memory without hiding either layer.
- Keep the Workspace first screen simple, predictable, and non-technical.
- Avoid turning memory into another manual database maintenance chore.

## 4. Non-Goals

- Do not make the first version scenario-adaptive by workspace type.
- Do not silently write durable memories without user confirmation.
- Do not make Sources, Notes, Memory, and Artifacts the primary first-screen mental model.
- Do not require users to classify every memory candidate manually.
- Do not solve global semantic search, identity sync, or external connector memory in this phase.

## 5. Core Model

### Yue Understanding

Yue Understanding has two layers:

- `About You`: durable understanding that applies across workspaces.
- `About This Workspace`: durable understanding that applies only inside the selected Workspace.

### About You

Examples:

- default language
- preferred answer structure
- collaboration style
- stable workflow habits
- recurring technical or product preferences

### About This Workspace

Examples:

- background of this effort
- goals
- decisions
- constraints
- preferences specific to this area of work
- terms
- open questions
- current state

## 6. Workspace Understanding Groups

The Workspace first screen should use a fixed, simple grouping model:

1. Background
2. Goals
3. Decisions
4. Constraints
5. Preferences
6. Terms
7. Open Questions
8. Current State

The UI should not reorder or rename these groups based on inferred workspace type in the first version. Predictability matters more than clever adaptation.

## 7. First-Screen Experience

The Workspace panel/home should open on `Workspace Understanding`, not raw resource lists.

The selected visual direction is `B - Two-Layer Context` from the throwaway prototype at
`/workspace-understanding-prototype?variant=B`.

The final design should use:

- the primary structure from Variant B: `About You` as a visible left rail and `About This Workspace` as the main canvas
- the status summary idea from Variant A: compact counts for saved understanding, pending confirmations, ready sources, and fixed groups
- the inline confirmation treatment from Variant C: memory confirmation appears in conversation and refreshes the Workspace Understanding view

Each group should show:

- group name
- count
- one or two representative items
- visible stale/conflict/pending markers when relevant
- a `Review` or `Manage` action

The top of the screen should show:

- selected Workspace name
- one-line purpose or description when present
- current understanding health, such as pending confirmations or stale items
- lightweight `Also using About You` preview

`Sources`, `Notes`, `Artifacts`, and raw `Memory` management should remain available as secondary tabs or lower-priority sections.

## 8. Applied User Memory Preview

Inside a Workspace, Yue should show a small preview of relevant user-level preferences currently influencing answers.

Example:

- Default to Chinese
- Start with the conclusion
- Prefer productized, implementation-ready design

This preview should not duplicate those memories into the Workspace. It should link to the global `About You` memory surface later.

## 9. Inline Memory Confirmation

When Yue detects high-signal durable information in conversation, it should show a non-blocking confirmation after the assistant response.

Confirmation UI should include:

- plain-language summary of what Yue proposes to remember
- recommended destination: `About You` or `This Workspace`
- ability to switch destination
- actions: `Remember`, `Just this time`, `Edit`

Examples:

User: "I prefer answers in Chinese, with the conclusion first."

Inline confirmation:

> Remember this preference?
> Use Chinese by default and start with the conclusion.
> Save to: About You

User: "For Yue, Workspace means a project workbench, not a file folder."

Inline confirmation:

> Save this workspace context?
> Workspace should be treated as a project workbench, not just a file folder or chat filter.
> Save to: This Workspace

## 10. Memory Capture Policy

Yue should proactively suggest memory only for high-signal content:

- explicit defaults or preferences
- user corrections to Yue's understanding
- clear decisions
- term definitions
- long-lived constraints

Yue should avoid prompts for:

- ordinary chat content
- assistant-only inferences
- one-off task state
- vague or unstable statements
- sensitive content without clear user intent

Suggested limits:

- at most one inline memory confirmation per assistant turn
- lower prompt frequency after repeated `Just this time`
- never block the primary task flow

## 11. Scope Recommendation

Yue should recommend where each Memory Candidate belongs:

- `About You` for stable cross-workspace user preferences and habits
- `This Workspace` for facts, goals, constraints, decisions, terms, and current state tied to the selected Workspace
- `Just this time` for temporary context

The user can switch the destination before saving.

## 12. Correction Flow

When the user corrects Yue in conversation, Yue should treat the correction as a high-signal Memory Candidate.

The inline confirmation should support:

- `Update`: enrich an existing memory
- `Replace`: supersede an outdated memory
- `Archive`: deactivate a memory that no longer applies

Example:

User: "Not LangChain anymore. This project is now using Pydantic AI."

Inline confirmation:

> Update project memory?
> Replace "uses LangChain" with "uses Pydantic AI."
> Save to: This Workspace

Workspace management screens should support review and cleanup, but the primary correction path should be conversational.

## 13. Relationship To Existing Objects

Sources, Notes, Memory, and Artifacts should support Workspace Understanding rather than define the first-screen experience.

- Sources provide evidence and grounding.
- Notes are intermediate captures that may later become memory.
- Memory is reviewed durable understanding that can affect future answers.
- Artifacts are outputs created during work.
- Memory Candidates are proposed changes awaiting confirmation.

## 14. Key User Journeys

### First Use

1. User creates or selects a Workspace.
2. Yue shows empty Workspace Understanding groups.
3. User chats normally.
4. Yue detects high-signal background, goals, constraints, or preferences.
5. Yue asks inline whether to remember them.
6. Confirmed items appear in Workspace Understanding.

### Returning Use

1. User selects a Workspace.
2. Yue shows the Workspace Understanding summary.
3. User sees what Yue already knows.
4. User starts a chat without re-explaining the basics.
5. The answer is influenced by active User Memory and Workspace Memory.

### Correction

1. User says Yue has remembered something wrong or outdated.
2. Yue proposes an update, replacement, or archive action inline.
3. User confirms or edits.
4. Future workspace chats use the corrected understanding.

## 15. Acceptance Criteria

- A returning user can understand what Yue knows about a Workspace within one screen.
- The user can see which user-level preferences are also affecting the Workspace.
- High-signal preferences, corrections, decisions, terms, and constraints produce inline confirmation prompts.
- Durable memory writes require explicit confirmation.
- Workspace Understanding remains useful for non-IT domains such as travel, writing, renovation, research, health planning, and family planning.
- The first-screen grouping stays simple and predictable.
