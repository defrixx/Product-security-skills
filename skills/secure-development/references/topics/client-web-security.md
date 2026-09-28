# Client-side web security

## SD-WEB-001

Status: proposed baseline; C01–C08 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Examples are synthetic sketches. The [TypeScript profile](../stacks/typescript-nextjs.md) supplies framework implementation details; browser/version assumptions must be recorded.

### SD-WEB-001.C01 — Render untrusted text as data

- **Apply when:** API, URL, storage, or message values reach templates or DOM operations.
- **Required / prohibited:** preserve text as inert data in its destination context; do not route it through HTML parsing or code evaluation.
- **Rationale:** a rendering sink can turn an ordinary field into code executing with the application's origin.
- **Implement:** use framework text interpolation or `textContent` for text nodes. Avoid dynamic script, event-handler, and style-code contexts; encoding for HTML is not a universal encoder.
- **Unsafe → corrected:** `node.innerHTML = label` → `node.textContent = label` when the feature displays a plain label.
- **Positive check:** a synthetic label containing angle brackets displays literally without losing its intended text.
- **Negative check:** an injected element with an event handler creates no executable node and does not set a local test marker in the browser.
- **Evidence:** source-to-sink trace identifying the rendering context; executed browser DOM and marker observations. Server response text alone does not establish browser behavior.
- **Bounds / sources:** S1, Output Encoding and Safe Sinks. CSP is defense in depth, not evidence that an unsafe sink is acceptable.

### SD-WEB-001.C02 — Constrain intentionally supported HTML and URLs

- **Apply when:** rich text, user-authored HTML, or dynamic navigation/resource URLs are supported.
- **Required / prohibited:** admit only the documented markup and URL schemes for the destination. Do not treat escaping an attribute as validation of its URL scheme.
- **Rationale:** permitted formatting can hide executable attributes or navigation.
- **Implement:** use a maintained sanitizer with an explicit feature policy for HTML; validate parsed URLs against allowed schemes and any destination restrictions. Avoid transformations after sanitization that reintroduce unsafe markup.
- **Unsafe → corrected:** put arbitrary rich text into an HTML sink → sanitize at the final rendering boundary; reject a `javascript:` link rather than merely escaping its quotes.
- **Positive check:** an allowed formatting element and an approved HTTPS link work as specified.
- **Negative check:** event attributes, forbidden elements, and disallowed URL schemes cannot execute or navigate to the prohibited destination; test each supported sink separately.
- **Evidence:** sanitizer version/configuration and URL validation trace; browser tests against the actual rendering component. A sanitizer dependency without an invoked policy is insufficient.
- **Bounds / sources:** S1, HTML Sanitization and URL Contexts. Select vendor guidance for the installed sanitizer; support for SVG, MathML, or embedded content needs explicit assessment.

### SD-WEB-001.C03 — Reject forged state-changing browser requests

- **Apply when:** a browser automatically attaches credentials, such as cookies, to a state-changing operation.
- **Required / prohibited:** verify a suitable anti-CSRF mechanism before mutation. Do not rely on CORS or the presence of a session cookie as proof of user intent.
- **Rationale:** another site can cause the browser to submit requests with ambient credentials.
- **Implement:** use the framework's supported CSRF protection with its required token/origin checks. Assess every mutation route, including login and alternate content types; apply [session cookie](sessions-cookies.md) controls independently.
- **Unsafe → corrected:** accept a cookie-authenticated form POST from any page → verify the configured CSRF mechanism before updating the synthetic profile.
- **Positive check:** an authorized same-application request with valid CSRF context updates exactly the intended record.
- **Negative check:** a forged request from an unapproved origin cannot change state. Where the selected defense requires a token, missing/invalid tokens also fail. For tokenless framework defenses, exercise their documented rejection predicates instead of inventing a token requirement. Observe persisted state, not only the status code.
- **Evidence:** route/middleware coverage and credential model; executed browser-origin scenarios. A unit test calling the handler without middleware does not prove deployed coverage.
- **Bounds / sources:** S2, framework protection, token defenses, and SameSite limitations. Explicit non-ambient bearer credentials change applicability; establish their actual transport first.

### SD-WEB-001.C04 — Grant cross-origin response access only to intended origins

- **Apply when:** CORS permits browser clients from another origin to read application responses.
- **Required / prohibited:** allow only the origins and credential mode required by the endpoint contract. Do not reflect arbitrary origins into a credentialed policy.
- **Rationale:** an excessive grant can disclose authenticated responses to another site's scripts.
- **Implement:** configure exact origin matching, including scheme and port, and deliberate credential handling. Public noncredentialed resources may intentionally permit all origins. Keep server authorization independent of CORS.
- **Unsafe → corrected:** echo every request Origin with credentials enabled → grant the documented `https://portal.example.test` origin only.
- **Positive check:** the approved browser origin can read its authorized response.
- **Negative check:** an unapproved origin, including a suffix lookalike, cannot read the protected response in a browser; direct unauthenticated requests still fail authorization.
- **Evidence:** effective CORS configuration plus actual/preflight browser observations. A missing allow-origin header does not mean the request was never sent.
- **Bounds / sources:** S3, Cross Origin Resource Sharing. CORS is a browser read boundary, not authentication or a general network firewall.

### SD-WEB-001.C05 — Bind window messages to the intended peer and schema

- **Apply when:** `postMessage` or message event handlers exchange data or trigger actions across windows/frames.
- **Required / prohibited:** validate the expected sender origin and peer where relevant, then validate the payload before acting. Send sensitive messages only to the intended target origin.
- **Rationale:** an unexpected window can impersonate a trusted integration or receive misdirected data.
- **Implement:** compare complete origins, check `event.source` against the expected window, and use an explicit message schema/action allowlist. Treat payload strings as data, applying C01 at rendering sinks.
- **Unsafe → corrected:** any message with `action: 'save'` triggers a write → accept that action only from the registered peer at its exact origin with valid fields.
- **Positive check:** the intended peer's valid synthetic message completes the allowed action.
- **Negative check:** wrong-origin, wrong-peer, and malformed messages each cause no action or sensitive response; test them independently. Navigate the target window to an unapproved origin before an outbound sensitive message and verify it receives no payload.
- **Evidence:** sender/receiver call sites and peer lifecycle; executed multi-window tests with state observations. A payload-only validator does not establish peer identity.
- **Bounds / sources:** S3, Web Messaging. Sandboxed opaque origins and navigated windows require a separately justified protocol; do not broadly accept `null` origins.

### SD-WEB-001.C06 — Avoid unnecessary persistent browser credentials

- **Apply when:** authentication material or sensitive records are considered for localStorage, sessionStorage, IndexedDB, or other script-readable persistence.
- **Required / prohibited:** choose storage according to an explicit exposure/lifetime model; do not persist session identifiers in localStorage as a convenience default.
- **Rationale:** script-readable storage expands the impact and lifetime of same-origin script compromise.
- **Implement:** prefer a server session with appropriately protected cookies when compatible with the architecture; minimize client-held data and define removal on logout/expiry. Cookie-backed designs also require C03.
- **Unsafe → corrected:** retain a synthetic session credential indefinitely in localStorage → use the chosen bounded session transport and remove obsolete persisted credentials.
- **Positive check:** normal sign-in and authorized operation work using the selected transport.
- **Negative check:** inspecting browser persistence after sign-in/logout finds no prohibited credential copies; expired credentials cannot authorize a server request.
- **Evidence:** all storage write/read sites and lifecycle policy; browser storage observations and server rejection test. HttpOnly does not prevent an injected script from issuing authenticated actions.
- **Bounds / sources:** S3, Local Storage; [sessions](sessions-cookies.md). Offline applications need a specific data/threat model; encrypted client data with a co-located key does not establish protection against same-origin script access.

### SD-WEB-001.C07 — Enforce the intended frame-embedding policy

- **Apply when:** sensitive interactive pages can be embedded by another document.
- **Required / prohibited:** allow embedding only by intended ancestors under the selected browser policy. Do not treat a report-only policy or HTML meta tag as enforced frame-ancestor protection.
- **Rationale:** an untrusted parent can mislead users into interacting with a protected page.
- **Implement:** deliver a justified CSP frame-ancestors policy in the HTTP response; select compatible fallback behavior only if the supported browsers need it. Preserve deliberately approved embedding. Verify all relevant ancestors and proxy/header handling.
- **Unsafe → corrected:** assume CSRF tokens prevent framing → enforce the intended ancestor policy before the browser renders the protected interaction.
- **Positive check:** direct navigation and explicitly allowed embedding work.
- **Negative check:** an unapproved top-level or nested ancestor cannot render the protected page in the supported browser; report-only mode cannot satisfy the denial claim.
- **Evidence:** final response headers and real multi-origin browser observations; header presence alone is static evidence.
- **Bounds / sources:** S4, framing defenses; S5 section 6.4.2. Not every public page needs a ban on embedding; derive policy from the interaction's threat model.

### SD-WEB-001.C08 — Verify the selected browser response protections

- **Apply when:** a browser-facing application relies on script/resource restrictions, content interpretation, referrer control, or persistent HTTPS policy.
- **Required / prohibited:** define each required property and verify its effective response/browser behavior. Do not apply an unexplained header bundle or report an observed header as proof of all browser protections.
- **Rationale:** deployment and browser semantics can differ from configuration intent.
- **Implement:** select CSP enforcement and allowed resources, accurate content types/nosniff where relevant, a referrer policy for sensitive navigation, and HSTS for an appropriate HTTPS deployment. Record compatibility, inheritance, and rollout effects; do not enable broad subdomain/preload commitments without a justified deployment scope. These mechanisms supplement safe sinks and authenticated TLS.
- **Unsafe → corrected:** add a CSP report-only header and claim scripts are blocked → choose enforcement deliberately and observe blocked and allowed resources in the intended browser.
- **Positive check:** legitimate scripts/resources/navigation still work under each selected policy.
- **Negative check:** test each claimed property independently: denied script/resource, forbidden MIME interpretation, excluded referrer data, or HTTP downgrade after HSTS establishment. Do not mark unused mechanisms applicable solely because the list mentions them.
- **Evidence:** production-equivalent headers/proxy chain and browser observations with selected origins. HSTS does not prove first-contact protection; HTTP unit tests alone do not prove browser policy enforcement.
- **Bounds / sources:** S5, policy delivery/enforcement; S6, HSTS model; S7, referrer policies; S8, nosniff. Normative outcome is the selected protection; individual mechanisms and durations follow actual deployment needs.

## Sources

- **S1:** [OWASP Cross Site Scripting Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) — Output Encoding, HTML Sanitization, Safe Sinks. Living documentation; checked 2026-09-24.
- **S2:** [OWASP Cross-Site Request Forgery Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) — framework protection, token defenses, SameSite. Living documentation; checked 2026-09-24.
- **S3:** [OWASP HTML5 Security](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) — Web Messaging, Cross Origin Resource Sharing, Local Storage. Living documentation; checked 2026-09-24.
- **S4:** [OWASP Clickjacking Defense](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html) — frame-ancestors and header limitations; checked 2026-09-28.
- **S5:** [W3C CSP Level 3](https://www.w3.org/TR/CSP3/) — policy delivery/enforcement and section 6.4.2 frame-ancestors; working specification checked 2026-09-28. Verify actual browser support; no blanket conformance claim.
- **S6:** [RFC 6797](https://www.rfc-editor.org/rfc/rfc6797.html) — November 2012, sections 6–8 and 12, HSTS processing/deployment; checked 2026-09-28.
- **S7:** [W3C Referrer Policy](https://www.w3.org/TR/referrer-policy/) — policy values and integration with Fetch; checked 2026-09-28.
- **S8:** [WHATWG Fetch](https://fetch.spec.whatwg.org/#x-content-type-options-header) — X-Content-Type-Options processing; living standard checked 2026-09-28.
