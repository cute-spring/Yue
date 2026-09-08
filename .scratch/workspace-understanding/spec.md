# Workspace Understanding

Status: ready-for-agent

## Source Specs

This local tracker decomposes the Workspace Understanding product and technical design:

- `docs/specs/2026-09-07-workspace-understanding-product-spec.md`
- `docs/plans/2026-09-07-workspace-understanding-technical-plan.md`
- throwaway prototype route: `frontend/src/pages/WorkspaceUnderstandingPrototype.tsx`

## Product Boundary

Workspace Understanding should make Yue feel smarter with use by showing what Yue knows about the user and the current sustained area of work.

The first implementation should preserve three decisions:

- `About You` and `About This Workspace` are separate layers.
- Workspace opens to fixed Understanding groups, not raw resource lists.
- Durable memory changes require explicit confirmation.

## Selected Prototype Direction

Use `B - Two-Layer Context` as the main direction.

Carry forward:

- left rail: lightweight `About You` preview
- main canvas: `About This Workspace`
- fixed 8 groups: Background, Goals, Decisions, Constraints, Preferences, Terms, Open Questions, Current State
- secondary access to Sources, Notes, Artifacts, and raw Memory management

Borrow from other variants:

- Variant A: compact top-level status metrics
- Variant C: inline memory confirmation card for chat-triggered capture

## Ticket Flow

Work the frontier: any issue whose blockers are complete can be implemented in a fresh context window.

The first frontier is issue 01.

