# Allowed and prohibited cryptography

## SD-CRYPTO-001

Status: proposed baseline; C01–C03 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. These are scoped engineering choices, not a universal allowlist or FIPS/GOST approval. Examples are synthetic configurations. Protocol-specific requirements and supplied organizational policy take precedence within their documented scope; record conflicts explicitly.

### SD-CRYPTO-001.C01 — Select a purpose-specific profile

- **Apply when:** code introduces or changes encryption, hashing, signatures, key derivation, or a cryptographic protocol.
- **Required / prohibited:** identify the required property and a supported profile specifying algorithm, parameters, library, and usage constraints. Do not invent a cryptographic algorithm or use an algorithm name alone as evidence of security.
- **Rationale:** a primitive suitable for one purpose can fail another purpose despite sounding secure.
- **Implement:** inventory call sites and map each to its purpose; choose maintained high-level library APIs and matching primary documentation. Keep password verification, encryption, integrity, and signatures distinct. Apply [primitive conditions](cryptographic-primitives.md) to actual usage.
- **Unsafe → corrected:** label a reversible encoding function as encryption → select an authenticated-encryption profile with explicit key and nonce handling for the storage use case.
- **Positive check:** each synthetic operation selects the documented supported profile and produces an interoperable result for that purpose.
- **Negative check:** an unknown profile identifier or unsupported parameter combination is rejected before cryptographic processing; no fallback to a custom algorithm occurs.
- **Evidence:** purpose/profile inventory and library/version inspection; executed profile-selection tests. A round trip alone proves neither algorithm suitability nor authenticity.
- **Bounds / sources:** S1, Algorithms and Custom Algorithms. Regulated and long-lived confidentiality use cases require additional authoritative policy; do not infer certification from an algorithm name.

### SD-CRYPTO-001.C02 — Require authenticated protection for new confidential storage

- **Apply when:** new general-purpose application code encrypts stored confidential data.
- **Required / prohibited:** use a reviewed authenticated-encryption construction; reject ECB and unauthenticated encryption for this baseline's use case. Legacy read compatibility must not silently enable new writes using a retired profile.
- **Rationale:** confidentiality without integrity can allow malicious alteration of encrypted records.
- **Implement:** prefer a maintained library's AEAD API, such as AES-GCM with at least a 128-bit key and its documented nonce/tag constraints. Other profiles need equivalent purpose-specific justification. Separate migration readers from the writer's permitted profiles.
- **Unsafe → corrected:** encrypt a synthetic record with AES-ECB → use the selected AEAD profile and bind any required record context as authenticated data.
- **Positive check:** a record written under the selected profile decrypts with its correct key and context.
- **Negative check:** a disallowed write profile fails configuration validation; modified ciphertext or authentication data is rejected without returning usable plaintext.
- **Evidence:** selected mode/parameters and write/read-path inspection; executed configuration rejection and tamper tests. A library dependency without call-site evidence does not establish authenticated encryption.
- **Bounds / sources:** S1, Algorithms and Cipher Modes. Nonce uniqueness, key lifecycle, and authentication-before-use are separately assessed in primitive conditions. Legacy exceptions require migration scope and review date.

### SD-CRYPTO-001.C03 — Restrict negotiated transport profiles

- **Apply when:** an application or its terminating proxy configures TLS clients or servers.
- **Required / prohibited:** disable SSL and TLS 1.0/1.1; prefer TLS 1.3 and permit TLS 1.2 only with a reviewed compatibility need and cipher configuration. Do not weaken the transport silently when negotiation fails.
- **Rationale:** a nominal HTTPS endpoint can still negotiate obsolete protection.
- **Implement:** select a version-matched TLS configuration at every termination point, including outbound clients. Inventory enabled cipher suites separately for applicable protocol versions; use vendor-supported configurations and [certificate validation](x509-certificates.md).
- **Unsafe → corrected:** retry a failed TLS handshake using an obsolete protocol → fail the connection and resolve compatibility through the reviewed profile.
- **Positive check:** an intended client/server pair negotiates an allowed protocol and cipher through the actual termination path.
- **Negative check:** a client offering only a prohibited protocol cannot connect; a disallowed cipher offer also fails where independently configurable. Verify no plaintext fallback.
- **Evidence:** effective endpoint configuration and negotiated parameters; executed local handshakes with known offer sets. Failure caused by an unrelated certificate error is not proof of protocol rejection.
- **Bounds / sources:** S2, Only Support Strong Protocols and Only Support Strong Ciphers. Proxy and client configurations need distinct observations. No universal cipher string applies across TLS libraries and versions.

## Sources

- **S1:** [OWASP Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html) — Algorithms, Custom Algorithms, Cipher Modes. Living documentation; checked 2026-09-24.
- **S2:** [OWASP Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html) — Only Support Strong Protocols; Only Support Strong Ciphers. Living documentation; checked 2026-09-24. Record the target TLS implementation/version before selecting concrete settings.
