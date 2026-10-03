# Privacy and data protection

## SD-PRIVACY-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Examples are synthetic design sketches, not production implementations. Legal basis, jurisdiction, and retention periods require supplied policy and separate authoritative verification; this baseline does not determine legal compliance.

### SD-PRIVACY-001.C01 — Collect only fields needed for a declared purpose

- **Apply when:** request schemas, forms, device permissions, imports, or SDKs collect personal information.
- **Required / prohibited:** associate collected fields with the feature's documented purpose and omit fields without a justified need. Do not collect an entire source object merely because it is available.
- **Rationale:** unnecessary collection expands the data exposed by a breach.
- **Implement:** maintain a field-to-purpose map and explicit input projections; select only required SDK permissions and fields. Use the [Python profile](../stacks/python-fastapi.md) or [TypeScript profile](../stacks/typescript-nextjs.md) for schema implementation, then inspect downstream persistence separately.
- **Unsafe → corrected:** a delivery-status form requires date of birth → accept the synthetic shipment identifier alone when that is sufficient for the feature.
- **Positive check:** a request containing the necessary fields completes the documented feature.
- **Negative check:** an extra synthetic birth-date field is rejected or discarded according to the contract and never persisted or forwarded.
- **Evidence:** static field/purpose mapping and input-to-storage trace; executed request plus inspected stored record and outbound payload. An unused UI field does not prove the server omits it.
- **Bounds / sources:** S1, data minimization, adapted from mobile to this proposed general baseline. Unclear business necessity remains an open decision, not an invented purpose.

### SD-PRIVACY-001.C02 — Limit each recipient to its approved projection

- **Apply when:** personal data enters responses, exports, logs, analytics, third-party SDKs, or other recipients.
- **Required / prohibited:** send only the fields approved for that recipient and purpose. Do not serialize a full database entity into every destination.
- **Rationale:** authorization to use a feature does not justify disclosure of every field to every connected service.
- **Implement:** define destination-specific output schemas and event payloads. Apply [authorization](authorization-access-control.md) to recipient access and [logging](logging-monitoring.md) to diagnostics; encryption does not establish recipient need.
- **Unsafe → corrected:** send the full synthetic customer profile to an event collector → send only the documented event type and the minimum justified identifier.
- **Positive check:** an approved recipient receives the required fields for the operation.
- **Negative check:** a seeded field excluded from that recipient's contract is absent from the actual response/export/event, including errors and retry payloads.
- **Evidence:** destination inventory and serializer/call-site inspection; captured synthetic outbound payloads for each assessed path. A mocked SDK call does not establish what the real SDK adds.
- **Bounds / sources:** S1, necessary sharing and SDK data flows. Pseudonymous identifiers remain potentially linkable; do not label them anonymous without a separate assessment.

### SD-PRIVACY-001.C03 — Enforce configured collection choices at the processing boundary

- **Apply when:** a feature or SDK processes data subject to an explicit user privacy choice under the project's policy.
- **Required / prohibited:** enforce the recorded choice before the governed processing starts and after it changes. A disabled UI toggle must not leave the corresponding collection active.
- **Rationale:** presentation-only choices misrepresent actual data use.
- **Implement:** gate initialization and processing at the responsible service or SDK adapter; propagate changes to active sessions and queued work according to the documented policy. Keep required service processing distinct from optional collection.
- **Unsafe → corrected:** start optional analytics before reading its disabled preference → resolve the preference before initialization and stop governed collection when revoked.
- **Positive check:** an enabled synthetic preference permits the intended governed event.
- **Negative check:** a disabled or revoked preference prevents subsequent governed events from reaching the collector, including after reload and worker retry.
- **Evidence:** choice-to-processing control flow; executed event capture before and after the choice changes. UI screenshots alone do not establish enforcement.
- **Bounds / sources:** S1, SDK collection controls; S2, user control. Whether a particular operation requires consent is a policy/legal question, not inferred from the presence of an SDK.

### SD-PRIVACY-001.C04 — Execute the defined retention and deletion lifecycle

- **Apply when:** stored personal data has a project-defined expiry, deletion request, or lifecycle transition.
- **Required / prohibited:** enforce the documented disposition across identified stores and copies. Do not report complete deletion when a live index, replica, or scheduled restore can silently reintroduce the record.
- **Rationale:** hidden copies can retain or restore information after the intended lifecycle ends.
- **Implement:** inventory authoritative storage, caches, indexes, exports, and backups; implement idempotent deletion/expiry jobs and explicit handling of policy exclusions. Define how restricted backups expire and how deletions are reapplied on restoration.
- **Unsafe → corrected:** delete a synthetic account row while leaving its searchable profile active → propagate its deletion identifier through the documented stores and verify the search result disappears.
- **Positive check:** a synthetic record remains available before its configured expiry; an authorized deletion completes with the policy's stated outcome.
- **Negative check:** after the completion boundary, normal reads and a tested restore/reindex cannot resurrect data outside the documented exclusions. Replay an older indexing/publication event after deletion and verify it cannot reintroduce accessible output. Failed deletion work must not be reported as completed.
- **Evidence:** lifecycle inventory, configured policy and job inspection; executed deletion/expiry and recovery observations per store. Distinguish removal from serving paths from physical disposition of retained copies; record the completion boundary and each store separately.
- **Bounds / sources:** S2 supports user data management; lifecycle propagation is this baseline's engineering application. Do not invent retention durations, legal holds, or guarantees of physical media erasure. Disclose policy-authorized retained copies and their access/expiry limits.

## Sources

- **S1:** [OWASP MASVS-PRIVACY-1](https://mas.owasp.org/MASVS/controls/MASVS-PRIVACY-1/) — minimization, necessary third-party sharing, and SDK collection controls. Living documentation; checked 2026-09-24. Mobile guidance adapted as a proposed general engineering baseline.
- **S2:** [OWASP MASVS-PRIVACY-4](https://mas.owasp.org/MASVS/controls/MASVS-PRIVACY-4/) — user control over data and privacy settings. Living documentation; checked 2026-10-03. Project-specific lifecycle mechanisms, including stale-event rejection, are engineering synthesis, not prescribed legal obligations.
