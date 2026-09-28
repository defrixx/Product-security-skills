# Webhooks and asynchronous events

## SD-EVENT-001

Status: proposed baseline; C01–C03 are MUST when applicable. Use the [requirement format](../requirement-format.md). Load for inbound machine events and their workers. Identify provider/protocol/API version, identity mechanism, and delivery contract first. Examples are synthetic; Stripe is a source example, not a required provider or universal signing protocol.

### SD-EVENT-001.C01 — Verify the intended message before effects

- **Apply when:** an external event can change trusted application state.
- **Required / prohibited:** authenticate the sender/message through the intended mechanism before protected effects. Validate the exact representation required by that protocol, not an unrelated reserialized body.
- **Rationale:** parser transformations or a permissive fallback can invalidate the authenticity boundary.
- **Implement:** use the provider's maintained verifier and trusted key/endpoint context; preserve raw bytes where its signature scheme requires them. Bound intake before buffering. Browser CSRF tokens are not webhook sender authentication; exempt only the correctly authenticated machine route where appropriate.
- **Unsafe → corrected:** parse JSON and trust its `verified` field → verify the required signed representation then validate its schema before scheduling trusted work.
- **Positive check:** a valid fixture message reaches its intended operation once.
- **Negative check:** altered bytes, wrong key/endpoint, missing required proof, and unsupported event structure produce no trusted job or mutation.
- **Evidence:** actual verifier and parser ordering, captured worker/storage effects; mocked verifier success is not provider integration.
- **Bounds / sources:** S1, signature verification and raw-body guidance; S2, primitive verification. Another provider may authenticate through a different mechanism; document it.

### SD-EVENT-001.C02 — Bind event scope and freshness

- **Apply when:** an authenticated event identifies an account/object, or replay outside a permitted lifetime changes a protected outcome.
- **Required / prohibited:** accept the event only for its intended integration, account, resource, and declared freshness policy. A valid signature alone does not authorize an arbitrary target identifier.
- **Rationale:** a real event from one integration can otherwise be applied to another object or accepted after authority expires.
- **Implement:** map verified sender context to local scope; cross-check event type/object/account relationships. Apply protocol-defined authenticated time/nonce checks where available, with bounded skew and explicit failure behavior. Separate delivery freshness from duplicate-event identity.
- **Unsafe → corrected:** apply a signed event to a URL-supplied account → derive or verify the account against the trusted integration and event binding.
- **Positive check:** a legitimate current event updates only its bound object.
- **Negative check:** wrong account/object/type, stale proof, and an unacceptable future timestamp cause no unauthorized effect; a legitimate provider retry with renewed proof follows its contract.
- **Evidence:** verified-context-to-object trace and controlled-clock tests; do not rely on unverified payload timestamps.
- **Bounds / sources:** S1, replay protection and event versions; project account/object binding refines [authorization](authorization-access-control.md). No universal timestamp window or global event-order guarantee.

### SD-EVENT-001.C03 — Preserve effects across duplicate and reordered delivery

- **Apply when:** the delivery contract permits duplicates, retries, reordering, or interrupted workers.
- **Required / prohibited:** preserve the business invariant under those delivery modes and define acknowledgment/durability behavior. Do not equate receiving a 2xx response with committed processing.
- **Rationale:** valid duplicate events can issue duplicate benefits or regress current state.
- **Implement:** use [business C01–C03](business-logic.md), scoped durable event identities, bounded retries, and reconciliation where needed. Handle pending/error states explicitly; do not assume arrival order or timestamp uniqueness.
- **Unsafe → corrected:** issue one entitlement for each delivery → deduplicate the intended logical effect and enforce its state transition even when deliveries reorder.
- **Positive check:** a normal event and valid retry reach the documented completed state without duplicate effect.
- **Negative check:** simultaneous duplicates, older-after-newer delivery, and crash before/after acknowledgment cannot violate the invariant; recover pending work after restart.
- **Evidence:** durable state and counted effects across actual worker restarts; label simulated queues/providers and untested distributed behavior.
- **Bounds / sources:** S1, event ordering, duplicates, asynchronous handling; S3, idempotency. This is conditional processing guidance, not universal exactly-once delivery.

## Sources

- **S1:** [Stripe webhooks](https://docs.stripe.com/webhooks) — verification, replay, event ordering/versioning, duplicates, asynchronous processing; checked 2026-09-28. Provider-specific behavior must not be generalized to all event systems.
- **S2:** [RFC 2104](https://www.rfc-editor.org/rfc/rfc2104.html) — February 1997, HMAC construction; checked 2026-09-28. HMAC examples illustrate authenticating exact bytes; algorithm/profile choice requires current cryptographic guidance.
- **S3:** [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests) — key/payload semantics, checked 2026-09-28. Recovery design follows the application's actual contract.
