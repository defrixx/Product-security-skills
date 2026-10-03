# Authorization and access control

## SD-AUTHZ-001

Status: proposed baseline; C01–C05 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for exceptions and evidence. Establish actual actors and resources first; do not add tenants or accounts to a local-only product merely to satisfy this checklist. Examples are synthetic pseudocode.

### SD-AUTHZ-001.C01 — Require an explicit grant for the operation

- **Apply when:** an operation is restricted by role, permission, relationship, or environmental policy.
- **Required / prohibited:** an explicit applicable policy must grant the operation; unknown or unavailable policy must not silently allow it. Authentication alone is not an operation grant.
- **Rationale:** Implicit grants expose operations to principals outside the intended policy.
- **Implement:** define an actor/action matrix and enforce it at the server operation boundary, including alternate entry points. See [Next.js server operations](../stacks/typescript-nextjs.md); [API access enforcement](api-web-services.md) addresses route coverage.
- **Unsafe → corrected:** `if logged_in: export_all()` → authorize the export permission before creating the export.
- **Positive check:** an actor with the documented grant completes the operation.
- **Negative check:** a logged-in actor without that grant, an unknown role, and a policy lookup failure cannot trigger it; no job or mutation is created.
- **Evidence:** inspect grant/default/error branches and execute direct operation calls with state observations. A hidden UI control is not evidence.
- **Bounds / sources:** S1, Deny by Default and Exit Safely. Explicit public access is a policy decision, not an exception; document it. Object access remains C02.

### SD-AUTHZ-001.C02 — Authorize the requested object

- **Apply when:** a caller supplies an object identifier, relationship, nested resource, attachment, or bulk list.
- **Required / prohibited:** authorize the actor's requested action on each selected object. Do not treat an unguessable identifier or a general role as proof of access.
- **Rationale:** Knowing an object identifier does not establish permission to access it.
- **Implement:** select through an actor-scoped query or check the loaded object's relationships before response construction or mutation. Apply the same decision to downloads, exports, and nested/bulk routes. Treat cached/search/vector results as candidates: establish current object scope and permitted output before disclosure, including snippets and counts.
- **Unsafe → corrected:** `records.get(request.id)` followed by serialization → select from `records.visible_to(actor)` using that ID, or enforce equivalent object policy before disclosure.
- **Positive check:** the owner or explicitly delegated actor reads/updates the allowed synthetic record.
- **Negative check:** replace the ID with another actor's record, including one item in a bulk request; no unauthorized data or side effects result. Specify atomic rejection or permitted-item processing explicitly.
- **Evidence:** inspect lookup-to-use flow and execute a two-actor/two-object matrix. Test both read and mutation when supported; one does not prove the other. Identify each distinct guard path and record returned data and side effects, not just status codes.
- **Bounds / sources:** S1, Lookup IDs and Right Location. Cross-tenant boundaries are additionally C03; response denial alone does not prove that a mutation did not occur.

### SD-AUTHZ-001.C03 — Derive and enforce the tenant boundary

- **Apply when:** the application hosts data for distinct organizations, accounts, or workspaces that are intended isolation boundaries.
- **Required / prohibited:** use an authorized tenant context for every tenant-scoped operation. An arbitrary client-supplied tenant selector must not establish membership or access.
- **Rationale:** Caller-selected tenant context can cross an isolation boundary.
- **Implement:** validate tenant selection against trusted membership and carry the resulting scope through queries, jobs, storage keys, and caches. Centralized context is useful only if every consumer enforces it.
- **Unsafe → corrected:** query with `tenant_id=request.header` → resolve the actor's permitted tenant, then scope the query with that trusted context.
- **Positive check:** an actor in synthetic tenant A accesses its permitted record in A.
- **Negative check:** changing a header, route parameter, job payload, or cache key to tenant B cannot return or modify B's data. Exercise each applicable storage path separately.
- **Evidence:** trace membership resolution to persistence and cache use; execute two-tenant requests with distinct sentinels. A database filter does not prove blob-store or search-index isolation.
- **Bounds / sources:** S1, Least Privileges and Every Request. Tenant switching may be legitimate for multi-membership actors; validate it. Mark N/A with architecture evidence when no such boundary exists.

### SD-AUTHZ-001.C04 — Protect privilege-bearing fields

- **Apply when:** updates can affect role, owner, tenant, ACL, approval state, or another field that changes access.
- **Required / prohibited:** ordinary updates must not modify privilege-bearing fields without the specific grant for that transition. A valid field type is not authorization to set its value.
- **Rationale:** Writable ownership or privilege fields can bypass operation-level checks.
- **Implement:** separate ordinary DTOs from privileged commands; derive ownership from trusted context; check permission on approved privilege transitions. See [input schema checks](input-validation-injection.md).
- **Unsafe → corrected:** assign all supplied fields to a record, including `owner_id` → allowlist ordinary fields and expose ownership transfer only through an authorized operation.
- **Positive check:** a permitted ordinary update preserves ownership; an explicitly authorized transfer follows its documented policy.
- **Negative check:** inject `role`, `owner_id`, or `tenant_id` into the ordinary update; observe rejection or documented ignoring and unchanged privileged state.
- **Evidence:** field-to-model assignment trace and before/after database observations. Request validation alone is insufficient if another update path bypasses it.
- **Bounds / sources:** S1, Least Privileges and Every Request. Enumerate actual protected fields; do not rely only on the illustrative names above.

### SD-AUTHZ-001.C05 — Apply policy changes to deferred and cached access

- **Apply when:** jobs, cached decisions, signed links, or long-lived operations may outlive the grant on which they rely.
- **Required / prohibited:** enforce a documented authorization lifetime and revocation policy. Do not silently treat an indefinitely cached grant as current permission.
- **Rationale:** Stale grants in queues and caches can outlive revoked authority.
- **Implement:** choose and document execution-time checks, bounded delegated capabilities, or versioned policy/cache invalidation appropriate to the operation. Bind delegation to the intended actor, action, and resource scope.
- **Unsafe → corrected:** a queued export runs forever with the submitter's old role → reauthorize at execution, or use an explicitly approved bounded delegation with defined revocation semantics.
- **Positive check:** a job with a valid current grant/delegation completes within its allowed lifetime.
- **Negative check:** remove the grant before execution or expire the delegation; the operation follows its documented denial/revocation behavior without unauthorized output. Warm the cache and capture queued work before changing rights, ownership, publication state or resource existence; test subsequent use and delayed refresh events. Test cache expiry and invalidation separately if both matter.
- **Evidence:** inspect authorization timing and lifetime enforcement; run a controlled policy-change sequence. A submission-time permission check cannot prove execution-time behavior.
- **Bounds / sources:** S1, Every Request and Review Chosen Technologies. Some workflows intentionally preserve an approved transaction; record that policy rather than universally demanding cancellation. Signed bearer links need explicit expiry/revocation limits. Declare when a change becomes effective and which in-flight work may finish; sequential before/after observations do not establish race safety.

## Sources

- **S1:** [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) — Least Privileges; Deny by Default; Validate Permissions on Every Request; Lookup IDs; Right Location; Exit Safely; Testing. Living documentation, checked 2026-10-03. These are project acceptance conditions; implementation and lifetime choices require the target's policy and stack documentation.
