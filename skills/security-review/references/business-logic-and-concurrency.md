# Business logic and concurrency discovery

Load for security-relevant values, workflows, entitlements, quotas, shared state or repeated effects. These are investigation prompts, not requirements to add payments, tenants or distributed infrastructure.

## Establish the invariant

For each sensitive operation, identify the authoritative state, allowed actor, prerequisites, permitted transition and durable effect. Label the invariant as specified (cite document and section), inferred (give domain/code evidence), or unresolved. Tests and comments are evidence of intent, not proof that the intent is secure. A specification mismatch becomes a vulnerability only with an attacker-reachable security impact; record policy-only deviations separately.

Synthetic examples: a refund cannot exceed the settled amount; one entitlement can be consumed once; a revoked grant cannot authorize a later export. Check the same invariant across UI/API, create/update, bulk/import, background and administrative paths where present.

## Abuse prompts

| Surface | Try to invalidate | Inspect the decisive control |
| --- | --- | --- |
| Derived values | Client price, discount, currency, role or approval flag overrides authoritative state | Recalculation and binding to actor/object at execution |
| Quantities and time | Negative/zero quantity, overflow, unit mismatch, client clock, expired quote | Domain ranges, arithmetic semantics and trusted expiry |
| Workflow | Skip, reverse or repeat a step; invoke a later API directly | Server-side transition prerequisites on every route |
| Partial updates | PATCH or update sets a field forbidden during creation | Effective merged object and field-level authorization |
| Replay | Same request twice, different payload under one key, another actor's key | Scoped durable deduplication and recorded outcome |
| Failure | Fraud/policy dependency fails; cancellation arrives after a write | Fail behavior and actual durable/external effects |
| Derived state | Cache, replica, index or job retains old permissions | Authority at delayed consumption and revocation semantics |

## Distinguish concurrency defects

- Data race: identify the shared memory location, reader/writer pair and language memory semantics. Do not infer undefined behavior uniformly across languages.
- Logic race: individually synchronized operations still permit an invalid sequence. Identify the shared invariant and atomicity boundary.
- TOCTOU: external state changes between validation and use; inspect filesystem identity, storage predicates and alternate writers.

Look for lazy initialization, different lock instances for one resource, a lock covering only part of an invariant, conflicting lock order, shutdown/cancellation writes, and attacker-triggered unbounded tasks. Establish a realistic trigger and security impact; an arbitrary scheduling concern is not automatically a vulnerability.

For storage/distributed paths, inspect conditional updates, unique constraints, actual isolation, concurrent callbacks, cache refresh, idempotency reservation and result persistence. A transaction or process-local mutex alone does not establish cross-worker correctness. For multi-step external actions, inspect compensation and ambiguous outcomes after a lost acknowledgment.

## Evidence example

Synthetic unsafe case: A and B both read one remaining redemption; A records its credit; B records another credit. Show the actual read, decision, write and effect locations, all relevant constraints, and why both paths can commit. A useful repair might be an atomic conditional consumption with a checked result, but the actual storage and effect boundaries determine the repair.

State the interleaving explicitly. For execution, use barriers or observable states at the contested boundary and inspect final state plus independent effects; arbitrary sleeps do not establish the interleaving. Pair the adversarial case with an allowed operation. Apply [analysis and validation](analysis-and-validation.md) for crash boundaries, original-code evidence and mocked effects.

## Source

[OWASP Business Logic Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html), living document, sections on authoritative values, state machines, races and testing; verified 2026-10-18. The prompts above are review synthesis; the target supplies its actual invariants and concurrency semantics.
