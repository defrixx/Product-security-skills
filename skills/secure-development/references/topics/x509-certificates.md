# X.509 inspection and validation

## SD-X509-001

Status: proposed baseline; C01–C03 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Applies to PKIX-based TLS verification. Examples use a synthetic local CA and reserved service names. Record verifier/library version, trust-store inputs, verification time, and purpose. Parsing or displaying certificate fields is inspection, not peer authentication.

### SD-X509-001.C01 — Validate the certification path for the intended purpose

- **Apply when:** a connection or identity decision relies on an X.509 certificate chain.
- **Required / prohibited:** validate the path to configured trust anchors, signatures, validity, constraints, and applicable key usage/purpose before trusting the peer. Do not accept a presented root as trusted merely because it is self-signed or supplied by the peer.
- **Rationale:** well-formed certificates can carry untrusted identities or invalid delegation.
- **Implement:** invoke the maintained platform verifier with explicit trust and purpose settings; keep verification failures fatal. Remove trust-all callbacks and inspect debug/environment overrides. Use [crypto policy](cryptography-policy.md) for algorithm constraints.
- **Unsafe → corrected:** parse a PEM certificate and accept its subject → verify the chain using the intended CA store and server-authentication purpose before accepting it.
- **Positive check:** the synthetic valid chain with appropriate purpose passes using the test CA as an explicitly configured anchor.
- **Negative check:** independently test an untrusted issuer, invalid signature, expired/not-yet-valid certificate, invalid CA constraint, and incompatible purpose. Each must fail without authenticated application traffic.
- **Evidence:** verifier call/configuration and failure-path trace; executed per-case verification results with fixture identities and clock. One failed certificate does not establish all path predicates.
- **Bounds / sources:** S1, sections 4.1.2.5, 4.2, and 6. Platform policy and applicable RFC updates affect details; use the target verifier's documented behavior. A successful path does not establish the service name.

### SD-X509-001.C02 — Match an independently chosen service identity

- **Apply when:** a TLS client connects to a named service or IP address.
- **Required / prohibited:** match the expected service identity against the appropriate certificate SAN identity under the selected protocol rules. Do not derive the expected name from the untrusted certificate or use arbitrary substring matching.
- **Rationale:** a valid certificate for another service does not authenticate the requested peer.
- **Implement:** pass the independently selected hostname/IP to the supported verifier, with hostname checking enabled. Distinguish DNS and IP SAN types; apply the library's standards-compliant wildcard handling. Do not introduce Common Name fallback under this profile.
- **Unsafe → corrected:** accept any trusted certificate for `api.example.test` → require its SAN to match that reference identity as well as passing C01.
- **Positive check:** a certificate for the exact synthetic DNS name, or matching IP SAN in an IP-based case, passes.
- **Negative check:** a trusted certificate for another name, a suffix lookalike, and a DNS SAN containing textual IP where an IP SAN is required each fail. Test wildcard boundaries when supported.
- **Evidence:** reference-identity provenance and verifier settings; executed wrong-name and valid-name connection tests. SNI alone does not prove identity checking.
- **Bounds / sources:** S2, sections 4 and 6. Application protocols may define additional identity types; document their profile. mTLS client identities need their own mapping and authorization rules rather than server-hostname assumptions.

### SD-X509-001.C03 — Make revocation handling explicit and testable

- **Apply when:** a deployment's certificate trust policy relies on revocation information or needs a documented decision about it.
- **Required / prohibited:** define the revocation mechanism, freshness expectations, and unavailable-status behavior and verify the implementation follows that policy. Do not describe an offline certificate parse as a current revocation check.
- **Rationale:** a certificate may remain within its validity dates after its authority has been withdrawn.
- **Implement:** configure supported CRL/OCSP or platform-managed mechanisms according to the deployment profile. Document soft-fail versus hard-fail decisions and their consequences; bound retrieval and avoid uncontrolled network fetches during inspection.
- **Unsafe → corrected:** report a certificate as not revoked because its dates are valid → report only date validity until the configured revocation mechanism supplies acceptable evidence.
- **Positive check:** a synthetic non-revoked certificate with fresh valid status follows the policy's acceptance path.
- **Negative check:** a known-revoked certificate is rejected; stale status and unavailable responders follow the separately documented policy, without being mislabeled as verified non-revoked.
- **Evidence:** effective revocation configuration and status provenance/freshness; executed local responder or CRL fixtures. Unknown status remains an explicit limitation even when availability policy allows connection.
- **Bounds / sources:** S1, sections 3.3 and 6.3 for CRLs; OCSP implementations require the matching protocol/vendor sources. No universal network-failure policy is assumed. Private-PKI and platform behavior vary.

## Sources

- **S1:** [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html) — sections 3.3, 4.1.2.5, 4.2, and 6; May 2008, checked 2026-09-24. Apply relevant updates and verifier policy for the target deployment.
- **S2:** [RFC 9525](https://www.rfc-editor.org/rfc/rfc9525.html) — sections 4 and 6, service reference identities and matching; November 2023, checked 2026-09-24.
