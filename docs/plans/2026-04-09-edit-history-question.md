# Edit History Question Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to edit a history question and send it again, which truncates the chat at that point and overrides the old question.

**Architecture:** Add a robust `handleEditQuestion` flow in `useChatState` that (1) validates edited content, (2) truncates server history at a deterministic boundary, and (3) only mutates local state and resubmits after truncate succeeds. Pass this async handler through `Chat.tsx` and `MessageList.tsx` into `MessageItem.tsx`. In `MessageItem.tsx`, add edit mode with pending/error-safe UX (disable save while submitting, keep editor open on failure, close only on success).

**Tech Stack:** React/SolidJS (Frontend), TypeScript

---

### Task 1: Harden Truncate-and-Resubmit State Logic

**Files:**
- Modify: `frontend/src/hooks/useChatState.ts`
- Reference: `backend/app/api/chat_schemas.py` (`TruncateRequest.keep_count`)

- [ ] **Step 1: Add boundary resolver for truncate payload**

Add a helper near other chat-state helpers that derives truncate boundary from message metadata:
- **Use the current backend contract**: `/api/chat/{chat_id}/truncate` accepts only `{ keep_count: number }`.
- Normalize boundary with guard checks before calling API:
  - `index >= 0`
  - `index < messages().length`
  - target message is a `user` message
  - computed `keep_count` keeps all messages before the edited question.
- Keep a TODO comment for future backend enhancement to support message-id truncation.

- [ ] **Step 2: Implement `handleEditQuestion(index, newContent): Promise<void>`**

Define `handleEditQuestion` below `handleRegenerate` with strict flow:
1. Return early if `isTyping()` is true.
2. `const trimmed = newContent.trim()`; return if empty.
3. Validate index range; throw or return with error if invalid.
4. If `currentChatId()` exists, call truncate API and `await` response.
5. If truncate fails (`!response.ok` or exception), surface error and **do not** call `setMessages`, `setInput`, or `handleSubmit`.
6. On success only: truncate local messages, set input to `trimmed`, and `await handleSubmit()`.

- [ ] **Step 3: Add explicit error signal/return contract**

Choose one consistent pattern used in this codebase:
- Use `throw` for failure and `Promise<void>` for success (consistent with existing async handlers + caller-side toast/error handling).

Document this in the function JSDoc and keep all call sites aligned.

- [ ] **Step 4: Export `handleEditQuestion`**

Ensure `handleEditQuestion` is included in the returned object at the end of `useChatState`.

---

### Task 2: Propagate Async Handler Types Through Components

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`
- Modify: `frontend/src/components/MessageList.tsx`

- [ ] **Step 1: Extract and pass handler in `Chat.tsx`**

In `Chat.tsx`, extract `handleEditQuestion` from `chatState` destructuring, and pass it to `<MessageList ... handleEditQuestion={handleEditQuestion} />`.

- [ ] **Step 2: Update `MessageListProps`**

In `MessageList.tsx`, set:
```ts
handleEditQuestion: (index: number, newContent: string) => Promise<void>;
```

- [ ] **Step 3: Pass handler to `MessageItem`**

In `MessageList.tsx`, pass `handleEditQuestion={props.handleEditQuestion}` to the `<MessageItem />` component.

---

### Task 3: Implement Resilient Edit UX in MessageItem

**Files:**
- Modify: `frontend/src/components/MessageItem.tsx`

- [ ] **Step 1: Update `MessageItemProps`**

Add:
```ts
handleEditQuestion: (index: number, newContent: string) => Promise<void>;
```

- [ ] **Step 2: Add local edit/pending/error state**

Inside the `MessageItem` component, add state variables for editing:
```tsx
  const [isEditing, setIsEditing] = createSignal(false);
  const [editContent, setEditContent] = createSignal("");
  const [isSavingEdit, setIsSavingEdit] = createSignal(false);
  const [editError, setEditError] = createSignal<string | null>(null);
```

- [ ] **Step 3: Add Edit Button**

In the user message render block (where `props.msg.role === 'user'`), find the action buttons (copy, etc.) and add an Edit button next to them. When clicked, set `isEditing(true)` and `setEditContent(props.msg.content)`. Wrap the existing content and buttons in a `<Show when={!isEditing()}>`.

- [ ] **Step 4: Add Edit Textarea, keyboard behavior, and controls**

Below the read-only view, add a `<Show when={isEditing()}>` block containing:
- A `textarea` bound to `editContent()`.
- Keyboard shortcuts:
  - `Escape` => cancel edit.
  - `Cmd/Ctrl+Enter` => submit.
- A "Cancel" button that sets `isEditing(false)` and clears `editError`.
- A "Save & Submit" button that:
  1. Trims content and validates non-empty.
  2. Sets `isSavingEdit(true)`.
  3. `await props.handleEditQuestion(...)`.
  4. Closes editor only on success.
  5. On failure, shows inline error and keeps editor open.
  6. Finally sets `isSavingEdit(false)`.
- Disable buttons/textarea while `isSavingEdit()` is true.

- [ ] **Step 5: Replace optimistic close with success-based close**

Use structure similar to:
```tsx
<Show when={isEditing()}>
  <div class="flex flex-col gap-2 mt-2 w-full min-w-[250px] relative z-20">
    <textarea
      class="w-full bg-background/80 backdrop-blur-md border border-primary/30 rounded-xl p-3 text-[15px] text-text-primary focus:outline-none focus:border-primary/60 resize-y min-h-[100px]"
      value={editContent()}
      onInput={(e) => setEditContent(e.currentTarget.value)}
    />
    <Show when={editError()}>
      <div class="text-xs text-danger">{editError()}</div>
    </Show>
    <div class="flex justify-end gap-2 mt-1">
      <button
        disabled={isSavingEdit()}
        onClick={() => {
          setIsEditing(false);
          setEditError(null);
        }}
      >
        Cancel
      </button>
      <button disabled={isSavingEdit()} onClick={onSubmitEditedQuestion}>
        Save & Submit
      </button>
    </div>
  </div>
</Show>
```

---

### Task 4: Add User-Facing Error Feedback Consistency

**Files:**
- Modify: `frontend/src/hooks/useChatState.ts`
- Modify: `frontend/src/components/MessageItem.tsx`
- Reference only: `frontend/src/context/ToastContext.tsx`

- [ ] **Step 1: Reuse existing app error mechanism**

Use the existing `useToast()` API:
- In `useChatState.ts`, call `toast.error("Failed to update question")` for truncate/submit failures.
- In `MessageItem.tsx`, keep inline `editError` text for local context.
- Do not add a new notification framework.

- [ ] **Step 2: Ensure no silent failures remain**

Replace `console.error`-only behavior with user-visible feedback and a typed failure path.

---

### Task 5: Add Focused Test Coverage

**Files:**
- Modify: `frontend/src/hooks/useChatState.events.test.ts`
- Create: `frontend/src/components/MessageItem.edit.test.tsx`
- Create: `frontend/e2e/chat-edit-history.spec.ts`

- [ ] **Step 1: Add unit tests for `handleEditQuestion` success path**

Validate:
- Truncate API called with expected boundary payload.
- Local messages are truncated only after successful API response.
- `handleSubmit` is triggered with edited content.
- Add as a focused `describe('handleEditQuestion')` block in `useChatState.events.test.ts`.

- [ ] **Step 2: Add unit tests for `handleEditQuestion` failure path**

Validate:
- On API error/non-OK response, local messages remain unchanged.
- Submit is not triggered.
- Failure is propagated (throw/return contract).
- Add case for non-OK HTTP response and case for rejected fetch.

- [ ] **Step 3: Add component test for edit UI behavior**

Validate:
- Enter edit mode from user message.
- Save button disabled while submitting.
- Editor stays open and shows error on failure.
- Editor closes on success.
- Include keyboard coverage: `Escape` cancels, `Cmd/Ctrl+Enter` submits.

- [ ] **Step 4: Add integration/e2e regression test**

Validate end-to-end scenario:
1. Send Q1 -> A1, send Q2 -> A2.
2. Edit Q1 and resubmit.
3. History after Q1 is replaced (old Q2/A2 removed).
4. New assistant response corresponds to edited Q1.

---

### Task 6: Verification and Delivery

**Files:**
- No source changes (verification only)

- [ ] **Step 1: Run targeted frontend tests**

Run:
- `npm run test:unit -- src/hooks/useChatState.events.test.ts`
- `npm run test:unit -- src/components/MessageItem.edit.test.tsx`
- `npm run test:e2e -- e2e/chat-edit-history.spec.ts`

Expected:
- Unit tests pass with no failed assertions.
- E2E spec passes locally against `http://localhost:3000`.

- [ ] **Step 2: Run typecheck/lint for frontend package**

Run:
- `npm run build`

Notes:
- This project currently has no dedicated `lint` script in `frontend/package.json`.
- `npm run build` runs `tsc && vite build`, which validates type drift from prop signature changes.

- [ ] **Step 3: Manual smoke check in chat UI**

Verify in browser:
- Edit latest and earlier user questions.
- Empty edit is blocked.
- Network failure shows error and does not corrupt history.
- Success path truncates and resubmits correctly.

- [ ] **Step 4: Prepare commit**

Commit with a focused message, for example:
`feat(chat): support editing prior user question with safe truncate and resubmit`
