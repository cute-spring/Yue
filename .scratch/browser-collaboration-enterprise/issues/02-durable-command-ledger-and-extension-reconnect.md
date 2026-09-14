# 02 - Build durable command ledger and reconnectable extension channel

**What to build:** Replace interval-only command polling with a reconnectable, idempotent command protocol between Yue and the MV3 extension.

**Blocked by:** 01.

**Status:** ready-for-agent

## Prototype decision

The throwaway MV3 lifecycle prototype is committed on `codex/mv3-reliability-prototype` at `7d41b6d`. It establishes that the production design must keep the command ledger and lease on the server, persist only minimal extension receipts/results, replay terminal results idempotently, reconcile on page-generation mismatch, and require reauthorization after backend restart. It does not select a transport; ticket implementation must compare managed long-polling and a persistent transport against those invariants.

**Scope:**
- Persist redacted command metadata, stable command IDs, sequence numbers, idempotency keys, leases, deadlines, receipt/acknowledgement, and terminal results.
- Add an authenticated managed transport with reconnect/backoff; retain a minimal extension receipt/result queue across service-worker suspension.
- Serialize non-idempotent commands per tab, redeliver only safely after lease expiry, and use idempotent completion.
- Reconcile reconnect reports against tab identity, origin, page generation, and outstanding receipts.
- On mismatch or uncertainty, transition to `needs_reconciliation`; never infer success.
- Backend restart revokes live authority and leaves redacted historical state only.

**Validation:**
- Backend and extension tests/simulations for disconnect before ack, after ack/before completion, duplicate completion, service-worker restart, tab reload, backend restart, and origin change.
- Ensure one irreversible command cannot be executed twice under retries.

**Acceptance Criteria:**
- A transient extension disconnect does not lose or duplicate a command.
- Users see a reconcilable blocked state instead of a false completion.
- No secret material is persisted in the ledger or extension queue.
