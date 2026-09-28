# Business invariants and concurrent operations

## SD-BUSINESS-001

Status: proposed baseline; C01–C03 are MUST when applicable. Use the [requirement format](../requirement-format.md). Apply only to actual security-relevant workflows, entitlements, balances, quotas, or external effects. Examples are synthetic; no payment system or multi-user architecture is required merely to use this skill.

### SD-BUSINESS-001.C01 — Enforce authoritative values and transitions

- **Apply when:** a sequence or derived value controls a sensitive outcome.
- **Required / prohibited:** derive security-relevant values from trusted state and allow only the intended state transitions. Valid field types and actor permissions alone do not authorize an impossible transition.
- **Rationale:** reordered steps or manipulated totals can violate the product's invariant.
- **Implement:** define allowed states, transition prerequisites, value derivation, and expiry where necessary; enforce them at every operation entry point. Reuse [authorization](authorization-access-control.md) for actor/object grants.
- **Unsafe → corrected:** accept `approved=true` from the final form → derive approval from the authoritative workflow state before issuing the entitlement.
- **Positive check:** a valid sequence reaches exactly its permitted outcome with the expected derived value.
- **Negative check:** skip, reverse, replay, or expire a required step; no protected outcome occurs. Tampering with a client-supplied total cannot change the authoritative amount.
- **Evidence:** transition/value trace and persisted state before/after each case; UI ordering is not enforcement.
- **Bounds / sources:** S1, server-derived values and state machines. The product supplies its invariant; unknown business rules remain unresolved rather than invented.

### SD-BUSINESS-001.C02 — Preserve invariants under concurrency

- **Apply when:** multiple requests/workers can check and consume a shared right or update a constrained value.
- **Required / prohibited:** enforce the check and protected update atomically under the actual storage/concurrency model. Do not assume sequential tests or the presence of a transaction prevents races.
- **Rationale:** concurrent valid requests can each observe the same available capacity.
- **Implement:** use an appropriate conditional write, unique constraint, lock, or isolation strategy; handle conflicts and bounded retries. Define which resource and actors share the invariant. Inspect every alternate write path.
- **Unsafe → corrected:** read one remaining slot then independently decrement it → use an atomic conditional update and require a successful affected-row result.
- **Positive check:** one permitted consumer succeeds and leaves the expected state.
- **Negative check:** synchronize competing consumers at the decision boundary; at most the allowed number succeeds and the stored invariant remains true. A rejected/conflicted attempt emits no protected effect.
- **Evidence:** real storage-engine concurrency observations, isolation settings, and all update paths. An in-process lock test does not establish multi-process or distributed correctness.
- **Bounds / sources:** S1, race conditions; S2, concurrency and isolation. Select the actual engine's semantics; SERIALIZABLE or a row lock is an option, not a universal required implementation.

### SD-BUSINESS-001.C03 — Bound repeated effects and partial failure

- **Apply when:** retries, duplicate delivery, or restart can repeat an operation whose protected effect must not duplicate.
- **Required / prohibited:** bind replay handling to the actor, operation, and equivalent payload; persist the decision/result at the necessary boundary. Do not silently reuse a key for a different operation or assume database rollback undoes an external effect.
- **Rationale:** retry ambiguity can issue the same entitlement twice or return another actor's result.
- **Implement:** document idempotency scope/lifetime, pending/completed states, and recovery or compensation for every crash boundary. Use durable uniqueness and provider-supported idempotency/outbox/reconciliation where appropriate; constrain retry work.
- **Unsafe → corrected:** repeat a timed-out issue request with no identity → replay its scoped operation identity and reconcile the recorded effect before another attempt.
- **Positive check:** a legitimate retry returns the documented result without another sensitive effect.
- **Negative check:** concurrent duplicates, a different payload under the same key, another actor's key, and failure between state commit and effect follow the declared policy. Restart and observe recovery rather than assuming it.
- **Evidence:** durable records plus actual effect counts and injected-failure observations. Label simulated external effects; do not claim universal exactly-once delivery.
- **Bounds / sources:** S1, idempotency; S3, example provider semantics. The failure-state design is project synthesis. Key lifetime and compensation depend on the business contract; no universal retention interval.

## Sources

- **S1:** [OWASP Business Logic Security](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html) — authoritative values, state machines, races, idempotency; checked 2026-09-28.
- **S2:** [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — isolation levels, conflicts and retries; living vendor documentation checked 2026-09-28. Match the installed release; SQLite fixtures do not verify PostgreSQL behavior.
- **S3:** [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests) — request keys and parameter comparison; checked 2026-09-28. Provider example only; do not transfer its retention/error rules to another service.
