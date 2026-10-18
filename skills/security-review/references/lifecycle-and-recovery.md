# Lifecycle and recovery scenarios

Load for cached/derived data, ownership or permission changes, delayed work, retries and external effects. Select only paths present in the target. This guide synthesizes investigation cases; the product contract defines when a transition becomes effective.

## Access over time

Record actor/object/scope, authoritative version, derived copies and permitted in-flight behavior. Exercise: allowed access → warm cache/index/export or capture job → revoke access, transfer ownership, unpublish or delete → read/execute/replay → restart and repeat. Inspect payloads, snippets, counts, downloadable files and durable effects, not only response status. Check newly authorized access after transfer as an allowed control.

Distinguish authorization at enqueue, execution, artifact creation and artifact download; each can have a different contract. Check whether old signed links or captured events remain valid by design, for how long, and for whom. Do not invent instantaneous revocation guarantees. Test stale/out-of-order updates after deletion to ensure the declared policy cannot be bypassed by resurrection. Sequential revocation tests do not establish concurrent linearizability.

## Recovery across effect boundaries

List independent commits: intent/reservation, recipient effect, caller completion. For each relevant boundary, interrupt before and after commit, reopen durable state and retry with the same scoped operation identity. Observe both caller outcome and independently counted recipient effects. Test concurrent duplicates, payload mismatch, another actor/operation using the same key, cancellation, timeout and retry exhaustion where supported.

A database rollback cannot undo an independently committed recipient action. An outbox can still redeliver; deduplication/reconciliation belongs at the appropriate effect boundary. If an outcome cannot be reconciled safely, preserve an explicit unresolved/pending state rather than silently retrying. Compensation is itself an effect whose authorization, identity and failure behavior need inspection.

Document the expected invariant, crash mechanism (exception/process death/network loss), restart mechanism, actual persisted state and effects. Mocks establish only their modeled protocol. Do not infer provider correctness from SQLite or an in-memory fixture. Apply the current engine/provider's primary documentation before choosing locking, isolation, idempotency retention or compensation.

## Sources

- [OWASP Authorization Testing Automation](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Testing_Automation_Cheat_Sheet.html), authorization matrix and integration tests; living document verified 2026-10-18.
- [AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html), issues and considerations, duplicate delivery and rollback; verified 2026-10-18. Pattern guidance, not a requirement to use AWS or an outbox.
