# API and web services

## SD-API-001

Status: proposed baseline, not corporate approval. Level: MUST for each applicable condition below. Use the [requirement format](../requirement-format.md) for evidence, statuses, and exceptions. This ID groups C01–C06; it cannot pass on evidence for one condition alone.

### SD-API-001.C01 — Enforce the endpoint's access boundary

- **Apply when:** a route reads protected data or performs a protected operation, including webhooks, internal endpoints, and callable server operations. Explicitly public endpoints still need a documented policy.
- **Required / prohibited:** enforce the intended caller policy before protected reads or effects. Do not infer permission from a hidden UI, an internal-looking URL, or CORS configuration.
- **Rationale:** An exposed route without its intended boundary permits unauthorized operations.
- **Implement:** map the route to its policy and invoke the application's authentication and authorization mechanism. For local-only products, document and enforce the intended local request boundary rather than inventing accounts. Use [authorization](authorization-access-control.md) for subject/object decisions and [authentication](authentication-mfa.md) for identity verification.
- **Unsafe → corrected:** illustrative: `POST /admin/export` checks permission only in the page → the server operation checks export permission before selecting records.
- **Positive check:** call the operation as an allowed actor with a valid object; receive only the permitted result.
- **Negative check:** call it directly without the required identity or with a disallowed actor; observe the specified denial, no protected response, and no export job or other side effect.
- **Evidence:** static route-to-policy trace covering middleware bypasses; executed request and state observations. Gateway settings without a demonstrated application path leave reachability assumptions unresolved.
- **Bounds / sources:** S1, Access Control. For machine events load [webhook conditions](webhooks-events.md). Identity and object-policy correctness require their own condition evidence; this check establishes route enforcement coverage. Stack implementation: [Next.js server operations](../stacks/typescript-nextjs.md).

### SD-API-001.C02 — Restrict HTTP methods

- **Apply when:** a route dispatcher accepts HTTP methods or middleware supports method overrides.
- **Required / prohibited:** allow only the operation's documented methods; reject other methods before business logic. Do not let a read method trigger a state-changing operation through a dispatcher fallback.
- **Rationale:** Unexpected methods can reach unintended handlers or side effects.
- **Implement:** declare methods on the route, inspect method-override handling, and distinguish protocol handling such as HEAD/OPTIONS from business operations.
- **Unsafe → corrected:** illustrative: every method on `/records/delete` invokes deletion → deletion is reachable only through its explicitly authorized mutation method.
- **Positive check:** the documented method performs the allowed operation with the expected response.
- **Negative check:** on a mutation-only route, GET and unsupported methods cannot mutate state and follow documented rejection behavior. On a read route, a supported GET succeeds without business mutation; only unsupported methods are expected to be rejected, usually with 405. If overrides exist, test the effective method after middleware processing.
- **Evidence:** route declarations plus dispatch/middleware inspection; executed requests with before/after state. A route decorator alone does not prove proxy behavior.
- **Bounds / sources:** S1, Restrict HTTP Methods. OPTIONS/HEAD behavior is framework-dependent; document intentional handling rather than rejecting all protocol methods indiscriminately.

### SD-API-001.C03 — Enforce the request representation contract

- **Apply when:** an endpoint consumes a request body, content type, or parser-selected representation.
- **Required / prohibited:** use only the declared parsers and validate the decoded input before use. Do not accept an unexpected representation through an automatic fallback or trust client-side schema validation.
- **Rationale:** Ambiguous representations can bypass validation or invoke an unintended parser.
- **Implement:** constrain accepted media types, reject malformed bodies, then apply the [input-validation conditions](input-validation-injection.md). For a supported Python implementation, see [the FastAPI profile](../stacks/python-fastapi.md).
- **Unsafe → corrected:** illustrative: a JSON mutation also accepts a form body because a generic parser tries both → select the declared representation and validate its schema before mutation.
- **Positive check:** a valid body with a supported media type reaches the handler and performs only the documented mutation.
- **Negative check:** unsupported media type, malformed encoding/body, and missing required fields are rejected without mutation; record actual 4xx responses rather than prescribing one status for every framework.
- **Evidence:** parser configuration and handler data flow; executed content-type/body matrix and unchanged state on rejection. Schema generation alone is not runtime validation evidence.
- **Bounds / sources:** S1, Input Validation and Validate Content Types. Multipart and streaming protocols need explicit parser-specific checks; JSON coverage does not establish their behavior.

### SD-API-001.C04 — Bound endpoint resource consumption

- **Apply when:** input size, pagination, batch size, concurrency, or downstream duration can increase the operation's work.
- **Required / prohibited:** enforce a documented resource budget at the layer where that work occurs. Do not rely on a request-count limit alone to bound the cost of one accepted request.
- **Rationale:** Unbounded work lets a small request exhaust shared resources.
- **Implement:** identify the expensive stage and set justified limits for it: bytes before buffering, items before iteration, deadlines for downstream work, or concurrency before scheduling. Record actual workload-specific values and overload behavior; do not invent universal thresholds.
- **Unsafe → corrected:** illustrative: `limit` from a query string is passed directly to a database fetch → enforce a configured maximum and reject or explicitly cap larger requests.
- **Positive check:** a request at the documented supported boundary completes with bounded output/work.
- **Negative check:** a request above the boundary or a deliberately stalled dependency triggers the documented rejection/timeout; inspect that excessive work is not scheduled and abandoned work is released. Test each budget selected for the route separately.
- **Evidence:** configuration values and their enforcement locations; executed boundary/load probes with observed work, duration, or queue size. A timeout response without cancellation evidence leaves ongoing work unverified.
- **Bounds / sources:** S1, Input Validation and HTTP Return Code 429. This is an application-specific resource invariant; report each selected budget as a separate evidence row under this condition. Production load testing needs its own authorized scope.

### SD-API-001.C05 — Return non-sensitive failures

- **Apply when:** parsing, validation, downstream calls, or unexpected exceptions can produce a response.
- **Required / prohibited:** return a controlled failure without credentials, request secrets, internal traces, or sensitive implementation details. Do not serialize raw exception objects to callers.
- **Rationale:** Detailed failures can disclose secrets and internal implementation data.
- **Implement:** map errors to public error DTOs and stable identifiers; preserve necessary diagnostics only through a separately controlled logging path. See [Python error handling](../stacks/python-fastapi.md) and [logging](logging-monitoring.md).
- **Unsafe → corrected:** illustrative: `return {error: str(exc), input: request_body}` → return a public error code and a non-sensitive correlation identifier.
- **Positive check:** a normal successful request retains the intended public response contract.
- **Negative check:** submit `SYNTHETIC_ERROR_CANARY` in a rejected field and trigger a controlled dependency failure; responses contain neither the canary nor a stack trace. Inspect logs separately instead of assuming response redaction protects them.
- **Evidence:** exception-handler and serializer inspection; captured validation and unexpected-error responses from executed tests. One validation-error test does not prove every failure path.
- **Bounds / sources:** S1, Error Handling. Correlation identifiers must not encode sensitive input. Logging and successful-response filtering require separate evidence.

### SD-API-001.C06 — Preserve response isolation through caches

- **Apply when:** browser, proxy/CDN, framework, or application caches can retain a protected response.
- **Required / prohibited:** cache reuse must preserve the response's recipient, variant, and authorization policy. Do not let a cache hit bypass access checks or treat tenant separation as sufficient for different users within one tenant.
- **Rationale:** caching can disclose an authorized response to a later unauthorized reader.
- **Implement:** define cacheability, key dimensions, freshness, and invalidation per layer. Distinguish private/no-store/shared-cache HTTP semantics from application memoization. Derive identity/context from trusted state; authorize before returning cached data. Apply [authorization C03/C05](authorization-access-control.md) to tenant scope and grant changes.
- **Unsafe → corrected:** cache a private profile solely by URL → enforce access on hits and partition or disable reuse according to its recipient contract.
- **Positive check:** an authorized repeat request obtains its correct response and intended cache behavior; deliberately public content remains shareable.
- **Negative check:** warm as actor A, then read as same-tenant B and anonymously; neither receives A's private fields. Test other tenant, request variants, expiry, and role revocation independently where applicable.
- **Evidence:** effective headers, actual cache keys/configuration, and two-actor observations through each claimed cache layer. A handler-only test does not verify CDN behavior.
- **Bounds / sources:** S2 sections 3.5, 4.1, 5.2.2; application-key/authorization design is project synthesis. No universal ban on caching or assumption that Cookie implies private caching.

## Sources

- **S1:** [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) — Access Control; Restrict HTTP Methods; Input Validation; Validate Content Types; HTTP Return Codes; Error Handling. Living documentation, checked 2026-09-24. Conditions are this project's engineering synthesis, not a claim of OWASP certification.
- **S2:** [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) — June 2022, authenticated response storage, Vary matching, Cache-Control directives; checked 2026-09-28. HTTP semantics do not certify framework cache APIs.
