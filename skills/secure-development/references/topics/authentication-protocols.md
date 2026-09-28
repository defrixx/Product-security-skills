# Conditional authentication protocol guidance

## SD-PROTOCOL-001

Status: proposed baseline; C01–C03 are MUST within their stated applicability. Use the [requirement format](../requirement-format.md). Load only for OAuth/OIDC/JWT integrations; general identity decisions still follow [authentication](authentication-mfa.md). Record library, issuer, client type, grant, token type, and versions. These conditions do not implement SAML, passkeys, or every federation profile. Examples are synthetic protocol sketches, not a custom authentication library.

### SD-PROTOCOL-001.C01 — Bind redirect login to its initiating transaction

- **Apply when:** OAuth/OIDC authorization-code flows cross a browser redirect boundary.
- **Required / prohibited:** bind the returned code/assertion to the intended issuer, client, redirect URI, and initiating user-agent transaction using the selected protocol's defenses. Do not accept an arbitrary return URL or an unsolicited callback as authenticated state.
- **Rationale:** code injection and issuer/transaction confusion can authenticate the wrong identity.
- **Implement:** use a maintained code-flow implementation with PKCE and its required state/nonce/issuer validation. Match the provider's registered redirect policy, including native loopback exceptions where specified. Avoid implicit and resource-owner-password grants under this baseline. Do not invent mandatory redundant tokens when the protocol supplies an equivalent verified binding.
- **Unsafe → corrected:** exchange any callback code then log in its subject → validate the expected transaction and issuer, complete the bound exchange, and verify the ID token before creating a session.
- **Positive check:** the intended code flow for the same browser transaction creates the expected identity.
- **Negative check:** wrong issuer, redirect, PKCE verifier, required state/nonce, and replayed callback independently fail before session creation; test only predicates applicable to the chosen flow.
- **Evidence:** provider/library configuration and actual callback-to-session observations. A fake issuer cannot establish a real provider's behavior.
- **Bounds / sources:** S1 sections 2.1, 2.4, 4.1, 4.4–4.8; S2 sections 3.1.3.7 and 15.5.2. Protocol requirements differ across client types; do not require OAuth for a local utility.

### SD-PROTOCOL-001.C02 — Validate tokens for their specific purpose

- **Apply when:** JWTs or OIDC ID tokens establish identity or authorize a resource.
- **Required / prohibited:** verify the allowed algorithm/key, issuer, audience, time, and token-purpose constraints before use. Do not let attacker-selected headers choose an arbitrary key URL, file, or algorithm, or treat an ID token as an access token by default.
- **Rationale:** a valid token in one context can be invalid authority in another.
- **Implement:** use the verifier's configured trust source and bounded key selection/refresh. Keep token-type validation rules distinct; check required claims and clock behavior for the selected profile. Apply [outbound controls](outbound-requests.md) to permitted metadata/JWKS fetching and [key lifecycle](key-lifecycle.md) to rotation.
- **Unsafe → corrected:** decode claims and fetch any header-supplied key URL → verify through the intended issuer's configured key source and token-type policy.
- **Positive check:** the intended token with the correct purpose reaches its allowed operation.
- **Negative check:** wrong algorithm/key, issuer, audience, expiry, purpose, and untrusted key-source selectors each fail without protected effects or arbitrary network/file access.
- **Evidence:** verifier settings, trust-source provenance, and actual library tests. Decoding or a mocked verify result does not establish signature validation.
- **Bounds / sources:** S3 section 3; S2 ID token validation. Opaque tokens require issuer-supported validation rather than applying JWT parsing rules to them.

### SD-PROTOCOL-001.C03 — Enforce token lifecycle and recipient scope

- **Apply when:** OAuth access or refresh tokens are issued, persisted, refreshed, or forwarded.
- **Required / prohibited:** constrain tokens to their intended resources and grants, and enforce the chosen expiry, refresh/replay, and revocation policy. Do not silently reuse tokens across integrations or claim immediate revocation for a bounded-validity design.
- **Rationale:** stolen or misdirected tokens can retain authority beyond the intended session or recipient.
- **Implement:** use provider-supported scope/audience restrictions and appropriate refresh-token rotation or sender constraints for the client type. Handle concurrency, retries, key rollover, and invalidation explicitly. Coordinate with [session C04](sessions-cookies.md) and [outbound C04](outbound-requests.md).
- **Unsafe → corrected:** retain a refresh token indefinitely and forward its access token to any service → use the intended grant/resource and verified lifecycle mechanism.
- **Positive check:** an allowed refresh produces the intended bounded access and normal use succeeds.
- **Negative check:** a token for another recipient cannot authorize the operation; an expired/revoked token or disallowed refresh replay fails according to the documented policy. Exercise concurrent refresh and permitted retry behavior separately.
- **Evidence:** actual issuer/client/resource-server observations with synthetic accounts; local state removal alone does not prove issuer revocation.
- **Bounds / sources:** S1 sections 2.2–2.3 and 4.14. Exact lifetimes, sender constraints, and reuse detection follow the actual issuer/client profile, not universal constants.

## Sources

- **S1:** [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) — BCP 240, January 2025, sections 2 and 4; checked 2026-09-28. Supplies OAuth threat/flow requirements; library APIs need matching vendor documentation.
- **S2:** [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation) — ID Token Validation section 3.1.3.7 and nonce notes 15.5.2, incorporating errata set 2; checked 2026-09-28.
- **S3:** [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html) — February 2020, section 3, JWT Best Current Practices; checked 2026-09-28. These conditions are a scoped engineering application, not a complete protocol conformance claim.
