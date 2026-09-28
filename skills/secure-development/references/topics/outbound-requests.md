# Server-side outbound requests

## SD-OUTBOUND-001

Status: proposed baseline; C01–C04 are MUST when applicable. Use the [requirement format](../requirement-format.md). Applies to URL fetches, previews, callbacks, discovery, and background imports influenced by untrusted data. Internal destinations may be intentional. The examples are synthetic design sketches; select the actual HTTP client, proxy, resolver, and deployment versions before implementation.

### SD-OUTBOUND-001.C01 — Define the destination capability

- **Apply when:** external input selects a server-side network destination.
- **Required / prohibited:** permit only destinations within the operation's documented network capability. A valid URL or valid TLS certificate alone does not grant that capability.
- **Rationale:** a caller can otherwise reach services through the server's network authority.
- **Implement:** distinguish fixed partner destinations from general public fetching. Constrain schemes, ports, authority syntax, address families, and excluded services according to that model; reject ambiguous parsing and userinfo. Prefer accepting an application-owned destination ID where suitable.
- **Unsafe → corrected:** fetch any syntactically valid URL → select a permitted destination and apply the declared network boundary.
- **Positive check:** an intended synthetic partner or allowed public destination works.
- **Negative check:** a prohibited service, alternate numeric address spelling, unwanted scheme, and disallowed port cannot cause a connection. Include allowed internal destinations when the policy permits them.
- **Evidence:** input-to-policy trace and observed connections to local sentinel services; string rejection alone does not establish connection confinement.
- **Bounds / sources:** S1, Cases 1/2. The project supplies the destination policy; no universal ban on private networks or DNS lookups is prescribed.

### SD-OUTBOUND-001.C02 — Enforce policy on the actual connection

- **Apply when:** a hostname, proxy, resolver, or client pool can change the endpoint after validation.
- **Required / prohibited:** the endpoint actually used must satisfy the selected destination policy. Do not validate one resolution and silently reconnect through another unrestricted resolution.
- **Rationale:** validation-to-use differences can bypass an otherwise correct address decision.
- **Implement:** use a client/egress mechanism that binds the checked address to connection establishment, or an equivalent enforced gateway policy. Preserve original hostname-based TLS verification and intended authority; inspect IPv4/IPv6, proxies, retries, and pool reuse.
- **Unsafe → corrected:** check a hostname once, then let the client resolve it again → constrain the actual connection to the validated destination while retaining independent TLS identity checks.
- **Positive check:** the approved address is contacted and, for HTTPS, the intended service identity is verified.
- **Negative check:** change the resolver result between check and connection; the excluded sentinel is never reached. Independently test prohibited proxy/retry paths.
- **Evidence:** actual client connection path and controlled resolver/transport observations. A mocked resolver establishes selection logic only; it is not a full DNS-rebinding or HTTPS integration proof.
- **Bounds / sources:** S1, DNS pinning protections; S2, connection and tunnel APIs. Exact mechanisms require target-client documentation. Apply [X.509](x509-certificates.md) independently.

### SD-OUTBOUND-001.C03 — Constrain every redirect

- **Apply when:** the outbound client can follow redirects.
- **Required / prohibited:** either disable redirects or reapply the destination and connection policy to every permitted hop. Do not treat an approved initial URL as approval for the redirect chain.
- **Rationale:** a trusted first hop can redirect to an excluded destination.
- **Implement:** use explicit bounded redirect handling; resolve relative locations with the client's actual parser, check scheme changes, and apply C01/C02 before each new connection. Apply [resource budgets](api-web-services.md) to the entire operation.
- **Unsafe → corrected:** validate a partner URL then auto-follow all redirects → disable following or validate each bounded hop before connecting.
- **Positive check:** an allowed redirect completes if the product permits it; otherwise a direct request succeeds and redirects return the documented outcome.
- **Negative check:** a redirect to a prohibited sentinel causes no request there; a loop terminates at the configured budget.
- **Evidence:** redirect configuration and per-hop connection log using synthetic destinations. A final denial after the excluded request is too late.
- **Bounds / sources:** S1, redirect guidance; per-hop validation is this baseline's conditional design alternative when redirects are a feature, not a claim that every library implements it automatically.

### SD-OUTBOUND-001.C04 — Bind outbound credentials and data to the recipient

- **Apply when:** requests carry credentials, cookies, headers, or confidential payloads.
- **Required / prohibited:** send each value only to its intended recipient and purpose, including redirects and retries. Do not forward inbound authentication wholesale or inherit unrelated ambient client credentials.
- **Rationale:** a permitted network destination is not necessarily authorized to receive the original request's secrets.
- **Implement:** construct an allowlisted outbound request; bind credentials to the approved authority, scope, and scheme. Re-evaluate body/header forwarding after redirects. Inspect proxy/environment and cookie-jar behavior. Never bypass certificate verification to retain functionality.
- **Unsafe → corrected:** reuse the incoming Authorization header on every fetch → acquire the intended downstream credential only for its bound destination.
- **Positive check:** the intended synthetic recipient receives exactly its allowed fields.
- **Negative check:** a different allowed host or port receives no original authorization/cookie/body canary; disallowed forwarding terminates before transmission.
- **Evidence:** recipient captures and actual client behavior per redirect status/method; redact captured values from reports.
- **Bounds / sources:** S3 section 15.4; recipient policy is project synthesis. Combine [secrets](secrets.md) and [privacy](privacy-data-protection.md); a header-only test does not prove body confidentiality.

## Sources

- **S1:** [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) — Cases 1/2, redirect handling, DNS pinning, application/network boundaries; living guidance checked 2026-09-28. Supports destination and resolution risks, not a universal client implementation.
- **S2:** [Python http.client](https://docs.python.org/3.12/library/http.client.html) — Python 3.12, HTTPConnection, HTTPSConnection, set_tunnel; checked 2026-09-28. API illustration only; a low-level client is not itself an SSRF defense.
- **S3:** [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4) — June 2022, redirection and request/header handling; checked 2026-09-28. Supplies protocol semantics, not the application's recipient authorization policy.
