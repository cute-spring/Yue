# Yue Browser Collaboration: Local-Owner Enterprise Execution Specification

**Status:** confirmed; staged implementation with a controlled-write Beta exception
**Date:** 2026-09-09
**Extends:** `2026-09-08-browser-collaboration-product-spec.md` (currently in the primary worktree)

## Purpose and boundary

This specification turns the existing browser-extension foundation into a reliable execution channel for a locally administered Yue installation. It does not change the established limits: Yue never stores or exports passwords, cookies, tokens, MFA/verification codes, or authentication-page content; the user completes authentication in the browser; and browser authority is explicitly granted per session.

The existing `BrowserSessionService` is an in-memory P1 foundation. It is not a production execution protocol: its polling command channel can lose work across extension/service-worker interruption, action completion is not connected to a recoverable chat run, and it has no durable approval or audit model.

## Controlled-write Beta exception

The current mainline milestone is a local-owner controlled-write Beta, not completion of this enterprise execution specification. It may share an explicitly authorized tab, fill or select a form field, and invoke a save or submit only after the local owner confirms **each command**. This stricter per-command rule overrides the routine-execution auto modes for the Beta.

The Beta must retain a local redacted command-state record, bind a command to the current page snapshot, allow only one command in flight per tab, and enter Reconciliation on a lost response, lease expiry, or missing post-command snapshot. It must never automatically retry an uncertain command. Form values must not be written to the local record.

The following enterprise requirements are explicitly deferred and must be completed before a production or generally available execution release: append-only hash-linked audit events; semantic page contracts and verified postconditions; sensitive-value classification and dedicated paste/upload consent; a managed reconnect transport with durable receipt queues, sequence numbers, and idempotency/deadline metadata; chat-run recovery; batch Approval Envelopes; and reusable form templates. The Beta must not enable batch execution, scheduling, background execution, or automatic write approval.

## Confirmed governance decisions

| Concern | Decision |
| --- | --- |
| Administration | Each local Yue owner is the administrator by default. This phase has no separate enterprise-admin or delegated-user roles. |
| Trusted business origins | Only exact HTTPS origins can be trusted. The local owner manages a simple local policy UI/API and may add an origin through a clear request-and-approve flow. Trust never implies a wildcard or subdomain match. |
| SSO/IdP origins | An exact trusted IdP origin is `sso_handoff` only: it permits the browser to traverse the login flow, but Yue captures no text, screenshot, control metadata, action target, or audit payload from it. The browser pauses for password, MFA, CAPTCHA, QR, or verification-code work. |
| Routine execution | Users may choose per-step, session-auto, or exact-site-auto within their own policy. Crossing to a new origin always leaves auto mode. |
| Irreversible work | Submit, send, publish, comment, approve, pay, order, sign, delete, overwrite, bulk modify, revoke, upload, paste sensitive content, change permissions/security, download executable/environment-changing files, and cross-origin navigation require approval regardless of auto mode. |
| Batch approval | The default approval form for very similar irreversible work is a session-scoped approval envelope. It can cover only one exact origin and action class, a previewed record set or maximum count, an explicit consequence summary, and a short expiry. A changed origin, action class, sensitive-value class, consequence, record outside the preview, or expiry requires fresh approval. |
| Audit retention | Retain redacted local audit records until the owner manually deletes them. Session artifacts (screenshots, downloaded-file metadata, DOM evidence) expire with the session unless explicitly retained. |
| Sensitive data | Never capture/log/replay authentication secrets or IdP page content. Redact likely personal and financial identifiers in UI and audit output. A dedicated confirmation is required before Yue pastes or uploads sensitive values. Users may enter sensitive values directly in the browser. |

## Architecture requirements

### Reliable browser execution channel

Replace interval-only MV3 polling with a managed extension transport that can reconnect after service-worker suspension, tab reload, backend restart, or a transient network failure. The server owns a durable command ledger; the extension owns no durable credential beyond an installation/session proof that can be revoked.

Each command must have a stable command ID, session ID, monotonically increasing sequence number, idempotency key, lease/acknowledgement, deadline, and terminal result. The extension must persist a minimal command receipt/result queue suitable for retry, acknowledge only after receipt, and send idempotent completion. The server must safely redispatch an unacknowledged command after lease expiry, never execute two non-idempotent commands concurrently in one tab, and mark uncertain commands as `needs_reconciliation` rather than assuming success.

On reconnect, the extension reports tab identity, current exact origin, page-generation/navigation marker, and outstanding command receipts. A mismatched tab, changed origin, or changed page generation blocks the command and asks the user to reconcile it. Backend restart invalidates live browser authority; durable records retain only redacted state and must never allow automatic reconnection or execution.

### Recoverable action and chat state

Persist redacted execution state separately from live authority. Model an execution as a state machine: `planned`, `awaiting_approval`, `queued`, `leased`, `running`, `succeeded`, `failed`, `blocked`, `needs_reconciliation`, `cancelled`, or `expired`. State transitions are append-only and correlated to a chat run/event stream.

The chat client must render live execution events and restore a completed, blocked, or reconcilable execution after refresh. It must never claim that an action completed until the command ledger has a terminal result and a fresh post-action semantic snapshot/evidence record where applicable.

### Semantic page contract

Replace best-effort text matching with versioned semantic snapshots: page generation, exact origin, title, accessible landmarks, visible controls, labels, roles, stable business keys, table row identities, validation messages, and redacted field classifications. Resolve an action against a snapshot version and verify the expected postcondition. Locator fallback must be bounded and explainable; a mismatch blocks/reconciles instead of guessing.

### Approval and audit

Approval is a server-side, immutable decision attached to an execution action or batch envelope. It records the redacted preview, origin, policy basis, expiry, approver (the local owner), decision, and the action IDs consumed by it. An approval may not be reused outside its envelope.

The audit trail records policy/configuration changes, session lifecycle, authorization changes, commands, approvals, state transitions, redacted outcome/evidence references, and manual deletion. Use a hash-linked event chain to make accidental or unauthorized local changes detectable; document that local-owner storage cannot guarantee tamper-proof evidence. Provide export and selective/manual deletion, preserving a redacted deletion event.

## Form-skill product boundary

Deliver reusable, versioned form templates before general workflow recording. Each template declares parameter schema, allowed exact origins, semantic page contract, required user-entered sensitive fields, validation/preconditions, draft/save/submit boundary, approval class, evidence schema, and recovery guidance. Templates cannot contain secrets, raw selectors as their primary contract, or an implicit cross-origin hop.

Initial templates are:

1. Expense report — collect and validate line items/receipts, populate a draft, show totals and policy warnings, then submit only through an approval envelope.
2. Timesheet — populate previewed date/project/hour rows, detect conflicts, save draft where supported, and batch-submit only matching rows in the approved session scope.
3. Daily report — fill a draft from supplied structured inputs, present the rendered summary, then submit with approval.
4. Approval query — read/filter/search approval queues and present structured results; it is read-only and cannot approve/reject items.

## Delivery gates

1. No durable policy/approval/audit code may store browser secrets or raw sensitive field values.
2. No irreversible action may dispatch without a valid, unexpired action approval or matching unconsumed batch envelope.
3. A reconnect, reload, timeout, or crash cannot silently duplicate a command or report an uncertain command as successful.
4. The four initial templates must demonstrate safe recovery and evidence on representative enterprise pages before workflow recording or scheduling is enabled.
