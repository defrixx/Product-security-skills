# Cryptographic primitive usage

## SD-PRIMITIVE-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Select the [cryptographic profile](cryptography-policy.md) first. Examples are synthetic sketches; library/API versions and algorithm-specific limits must be recorded. Key access and distribution also follow [secrets](secrets.md).

### SD-PRIMITIVE-001.C01 — Generate unpredictable security values

- **Apply when:** keys, recovery tokens, challenges, or other values depend on unpredictability.
- **Required / prohibited:** use the platform/library cryptographic random generator with a purpose-appropriate output length. Do not substitute timestamps, counters, ordinary PRNGs, or a fixed fallback after entropy failure.
- **Rationale:** predictable values can enable credential guessing or key recovery.
- **Implement:** select the runtime's documented CSPRNG API and propagate generation failures without issuing a credential. Keep deterministic test generators outside production configuration.
- **Unsafe → corrected:** derive a reset token from current time → obtain the selected number of bytes from the runtime CSPRNG and encode them without reducing entropy.
- **Positive check:** normal generation produces the required type and length and the intended consumer accepts the value.
- **Negative check:** an injected generator failure prevents issuance; a test-only deterministic generator cannot be enabled in the production configuration.
- **Evidence:** API provenance and entropy/encoding argument; executed failure-path tests. A sample with no duplicates does not prove unpredictability.
- **Bounds / sources:** S1, Secure Random Number Generation. Nonces may require uniqueness rather than unpredictability; apply C02 according to the selected primitive instead of prescribing randomness universally.

### SD-PRIMITIVE-001.C02 — Preserve per-key nonce requirements

- **Apply when:** encryption or another primitive consumes a nonce/IV with uniqueness or randomness constraints.
- **Required / prohibited:** satisfy the selected primitive's nonce constraints for the full key lifetime, including concurrent processes and restarts. For GCM, do not reuse a nonce with the same key.
- **Rationale:** nonce reuse can destroy confidentiality and authentication guarantees.
- **Implement:** use a documented library-managed allocation scheme or a reviewed allocator with persistent/concurrency-safe state. For random nonces, enforce the profile's invocation/collision budget and key rotation boundary; do not assume random means impossible to repeat.
- **Unsafe → corrected:** restart a per-process GCM counter at zero while retaining the key → allocate a non-overlapping nonce space across instances and restarts, or use the profile's reviewed alternative.
- **Positive check:** concurrent writers and a restart preserve the allocator's documented invariant in the synthetic fixture.
- **Negative check:** simulated state rollback, counter exhaustion, or allocation failure prevents encryption or triggers the specified safe key transition before reuse.
- **Evidence:** key/nonce lifecycle argument and allocator implementation; executed concurrency/restart/failure observations. A finite uniqueness test cannot prove the invariant by itself.
- **Bounds / sources:** S1, Cipher Modes and Key Management; S3 section 8 for GCM uniqueness and invocation constraints. The selected algorithm/library specification supplies exact nonce length and limits. Do not transfer GCM rules blindly to another construction.

### SD-PRIMITIVE-001.C03 — Authenticate before consuming protected data

- **Apply when:** code decrypts authenticated ciphertext or verifies a MAC/signature before a protected action.
- **Required / prohibited:** accept data only after successful verification with the intended key, algorithm, and context. Do not expose unauthenticated plaintext or continue after a verification exception.
- **Rationale:** ignoring verification can turn modified data into trusted instructions or records.
- **Implement:** use high-level verified-decryption/verification APIs; bind required contextual fields through the protocol's authenticated representation. Keep tentative streamed plaintext inaccessible until the construction's authentication boundary succeeds.
- **Unsafe → corrected:** process decrypted bytes before checking the tag → obtain authenticated plaintext from the verified API and only then parse or publish it.
- **Positive check:** valid synthetic data with the expected key and context reaches the intended consumer.
- **Negative check:** altered ciphertext, tag/signature, and context each fail independently without plaintext publication or protected side effects; a wrong-key case also fails.
- **Evidence:** verification-to-effect control flow; executed tamper cases with consumer/state observations. Catching an exception is insufficient if an earlier callback already consumed plaintext.
- **Bounds / sources:** S1, Cipher Modes. Authenticity does not independently provide freshness, replay prevention, or business authorization; add those at the protocol boundary where required.

### SD-PRIMITIVE-001.C04 — Use a dedicated password verifier

- **Apply when:** the application stores password-derived verifiers rather than delegating password handling to an identity provider.
- **Required / prohibited:** use a supported password-hashing scheme with salts and reviewed cost parameters. Do not use reversible encryption or an ordinary fast hash as the password verifier.
- **Rationale:** stolen verifier databases enable offline guessing; password-specific work factors slow that attack.
- **Implement:** prefer a maintained Argon2id implementation where compatible with the selected policy, with library-managed salts and encoded parameters. Benchmark costs under realistic concurrency, record the chosen primary-source guidance, and support rehashing when the profile changes.
- **Unsafe → corrected:** store an unsalted SHA-256 password digest → use the library's password-hash and verify functions under the documented deployment profile.
- **Positive check:** the correct synthetic password verifies, and a verifier using an accepted older cost is upgraded according to policy after successful authentication.
- **Negative check:** an incorrect password and malformed verifier fail without authenticating; excessive/untrusted encoded cost values cannot force unbounded work.
- **Evidence:** hash/verify call sites and effective parameters; executed correct/wrong/malformed cases and measured resource cost. Different salts in two samples do not establish secure salt generation.
- **Bounds / sources:** S2, Password Hashing Algorithms and Salting. Algorithm choice and minimum costs depend on current guidance and constraints; no universal deployment cost is inferred here. Online rate limiting remains separate.

## Sources

- **S1:** [OWASP Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html) — Cipher Modes, Secure Random Number Generation, Key Management. Living documentation; checked 2026-09-24. Exact primitive limits require the selected library/algorithm's primary specification.
- **S2:** [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — Password Hashing Algorithms and Salting. Living documentation; checked 2026-09-24.

- **S3:** [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) — November 2007, sections 7.2, 8, and 9; checked 2026-09-25. The publication page notes revision work; recheck the applicable final guidance before adopting a deployment profile. This reference does not imply module certification.
