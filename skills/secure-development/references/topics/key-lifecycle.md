# Cryptographic key lifecycle

## SD-KEY-001

Status: proposed baseline; C01–C03 are MUST when applicable. Use the [requirement format](../requirement-format.md). Choose [cryptographic profiles](cryptography-policy.md) and [primitive constraints](cryptographic-primitives.md) separately. Examples are synthetic lifecycle designs, not crypto implementations. Managed providers are valid options; HSMs, certifications, universal rotation periods, and backups for every key are not imposed.

### SD-KEY-001.C01 — Restrict key use by identity and purpose

- **Apply when:** the application uses encryption, signing, MAC, or wrapping keys.
- **Required / prohibited:** bind key identity and allowed operations to their intended actors and purposes. Untrusted key IDs must not select arbitrary key material or confer key-use permission.
- **Rationale:** a correct primitive with the wrong key authority can cross an application boundary.
- **Implement:** inventory owners, identifiers, storage/provider locations and permissions; separate purposes through the chosen protocol's key separation mechanism. Protect distribution and access with the selected platform. Link diagnostics and packaging to [secret controls](secrets.md).
- **Unsafe → corrected:** accept a key path from a request → select an authorized key identity from trusted policy and enforce the allowed operation.
- **Positive check:** an authorized identity uses its intended key for the permitted purpose.
- **Negative check:** another actor, unknown key ID, and wrong-purpose request cannot perform the operation or disclose key bytes.
- **Evidence:** key-to-policy mapping and actual provider/local boundary checks; a mocked KMS result proves only caller behavior.
- **Bounds / sources:** S1, Key Usage and storage/distribution; S2, lifecycle. Project synthesis applies these principles without importing certification requirements outside their regulated scope.

### SD-KEY-001.C02 — Enforce key-version transitions

- **Apply when:** keys rotate, usage budgets expire, or old material remains for verification/decryption.
- **Required / prohibited:** distinguish permitted new operations from legacy reads/verification. Retired or revoked keys cannot silently resume prohibited use; do not fall back to an embedded key when the provider fails.
- **Rationale:** version ambiguity can revive compromised authority or write more data with exhausted material.
- **Implement:** record active/read-only/revoked states, key-version metadata, permitted transitions, and migration boundaries. Coordinate nonce spaces and invocation budgets across writers. Authenticate version/context according to the selected construction.
- **Unsafe → corrected:** always select the first available historical key → choose the active version for new writes and allow old versions only for explicitly permitted consumption.
- **Positive check:** a new operation uses the active version; an authorized historical read follows the documented policy.
- **Negative check:** retired-for-write, revoked, unknown, or unavailable key states cannot trigger a prohibited operation. A stale worker cannot bypass the transition; tampered version metadata is not trusted.
- **Evidence:** real key-selection and provider observations across transition/restart; distinguish signature verification from AEAD decryption tests.
- **Bounds / sources:** S2, key states and cryptoperiods; S1, compromise/recovery. Exact lifetime and migration rules are policy choices, not universal time values.

### SD-KEY-001.C03 — Test compromise and recovery disposition

- **Apply when:** retained protected data requires recovery, or key compromise/destruction can affect its access policy.
- **Required / prohibited:** define and verify the disposition of affected data and keys, including retained backups. Do not claim revocation alone recovers exposed plaintext or that deleting a key preserves recoverability.
- **Rationale:** a transition can either retain compromised access or make required data irrecoverable.
- **Implement:** select re-encryption, re-signing, bounded verification retirement, or destruction according to purpose. Protect required recovery material and rehearse access restoration; exclude ephemeral keys from backup where their purpose requires erasure. Identify responsible owners without inventing approval.
- **Unsafe → corrected:** delete the only decryption key while promising backup recovery → verify the protected recovery/migration path before the authorized destruction transition.
- **Positive check:** required recovery restores access for its intended actor without broadening permissions.
- **Negative check:** an unauthorized recovery actor fails; a synthetic compromise transition stops prohibited use, and missing required recovery material produces an explicit failure rather than a success claim.
- **Evidence:** isolated recovery/compromise exercise and resulting access state. No real provider revocation or destructive action is authorized by this condition alone.
- **Bounds / sources:** S1, escrow/backup and compromise; S2, recovery and compromised keys. No universal secure-erasure or post-compromise confidentiality guarantee.

## Sources

- **S1:** [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html) — Key Usage, Lifecycle, storage, recovery; checked 2026-09-28. Its FIPS/HSM-specific statements are not adopted as universal requirements here.
- **S2:** [NIST SP 800-57 Part 1 Rev. 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final) — May 2020, key states, cryptoperiods, compromise and recovery; checked 2026-09-28. Lifecycle concepts inform this engineering synthesis; deployment profiles and required assurance remain separately scoped.
