# Evidence Panels Smart Visibility Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement smart visibility for the "Used context" and "Evidence contract" panels in the chat interface so they hide when empty, reducing visual noise.

**Architecture:** Pure presentation logic change in `MessageEvidencePanel.tsx`. The underlying data structure and state management remain untouched.

**Tech Stack:** React/SolidJS (TSX), Tailwind CSS.

---

### Task 1: Update "Used Context" Visibility Logic

**Files:**
- Modify: `frontend/src/components/message-item/MessageEvidencePanel.tsx`

- [ ] **Step 1: Update the `<Show>` condition for `session_used_context`**

```tsx
// Find this line (approx line 20):
// <Show when={props.msg.session_used_context}>

// Replace with:
      <Show when={
        props.msg.session_used_context && 
        props.msg.session_used_context.reason !== 'no_context_needed' &&
        props.msg.session_used_context.reason !== 'no_reference_signal'
      }>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/message-item/MessageEvidencePanel.tsx
git commit -m "feat(ui): hide used context panel when reason indicates no context needed"
```

---

### Task 2: Update "Evidence Contract" Visibility Logic

**Files:**
- Modify: `frontend/src/components/message-item/MessageEvidencePanel.tsx`

- [ ] **Step 1: Update the `<Show>` condition for `workspace_grounding`**

```tsx
// Find this line (approx line 63):
// <Show when={props.msg.workspace_grounding}>

// Replace with:
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

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/message-item/MessageEvidencePanel.tsx
git commit -m "feat(ui): hide evidence contract panel when empty and no warnings exist"
```

---

### Task 3: Run E2E Tests to Verify No Regressions

**Files:**
- Test: `frontend/e2e/workspace-grounded-answer.spec.ts` (and potentially others if applicable)

- [ ] **Step 1: Run frontend tests**

```bash
cd frontend
npm run test # or appropriate test command, e.g., vitest, playwright
```
Expected: PASS

- [ ] **Step 2: Fix tests if broken (only if UI tests explicitly check for the presence of the empty panel)**
If tests fail because they explicitly assert the visibility of the *empty* evidence panel (e.g., checking for "0 eligible sources"), update the test assertions to reflect the new design (i.e., assert that the panel is *not* visible).

- [ ] **Step 3: Commit (if tests changed)**

```bash
git add frontend/e2e/
git commit -m "test(ui): update e2e tests for evidence panel smart visibility"
```
