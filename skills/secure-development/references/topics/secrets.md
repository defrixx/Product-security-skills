# Secrets and hardcoding

## SD-SECRET-001

Status: proposed engineering baseline; not corporate approval. Each applicable condition C01–C05 is a MUST. Use the [requirement format](../requirement-format.md) for exceptions and evidence. No condition establishes complete secret discovery. Examples below are synthetic pseudocode, not usable credentials.

### SD-SECRET-001.C01 — Obtain credentials without source literals

- **Apply when:** code or configuration authenticates to a database, provider, signing service, or other protected resource.
- **Required / prohibited:** obtain usable credentials through the intended deployment mechanism. Do not embed them in source, fixtures, URLs committed to source, or packaged default configuration.
- **Rationale:** Source literals distribute credentials beyond their intended runtime boundary.
- **Implement:** use workload identity or a runtime secret provider with a restricted application identity. Treat environment variables as one delivery option, not protection against logs or process inspection. See [Compose secret grants](../stacks/docker-compose.md).
- **Unsafe → corrected:** `client(token="SYNTHETIC_EXAMPLE")` represents a prohibited production literal → `client(token=provider.require("service-token"))`, where the provider is configured outside source.
- **Positive check:** supply an inert test credential through the selected mechanism; the isolated consumer receives it.
- **Negative check:** omit it; the protected operation remains unavailable rather than using a committed fallback. No credential appears in the failure response.
- **Evidence:** inspect credential origin through the client constructor; execute present/missing-provider cases. Merely replacing a literal with an environment lookup leaves deployment configuration unverified.
- **Bounds / sources:** S1 sections 2.2, 2.3, 5.1. Clearly inert examples are allowed; production usability and privilege need contextual assessment, not entropy alone.

### SD-SECRET-001.C02 — Keep credentials out of distributed output

- **Apply when:** builds, browser bundles, source maps, images, installers, or generated configuration can capture secret-bearing inputs.
- **Required / prohibited:** distributed output must not contain the credential. Deleting a secret from a later image layer or hiding it behind minification does not satisfy this condition.
- **Rationale:** Public artifacts can retain credentials even when source code appears clean.
- **Implement:** isolate server-only data and restrict build-secret lifetime. Follow [Next.js client-boundary checks](../stacks/typescript-nextjs.md) and [BuildKit secret checks](../stacks/docker-compose.md) when applicable.
- **Unsafe → corrected:** a build copies a credential file then deletes it → the needed build step reads an ephemeral secret mount and emits only its non-sensitive result.
- **Positive check:** the build completes with an inert canary and the intended output remains usable.
- **Negative check:** search actual output, layer contents, source maps, and client responses for the canary; any occurrence fails. Verify a planted disposable leak is detected before trusting the search setup.
- **Evidence:** build-input-to-output trace and executed artifact inspection, including exact image/build identity. Source inspection alone cannot prove generated-output absence.
- **Bounds / sources:** S1 section 3. Exact canary searches miss transformed values; inspect explicit encoding/inlining paths. Application logs are checked separately.

### SD-SECRET-001.C03 — Prevent diagnostic disclosure

- **Apply when:** authentication headers, provider settings, connection strings, or request bodies reach logging, tracing, exceptions, or debug endpoints.
- **Required / prohibited:** diagnostic outputs must exclude usable secret values. Do not serialize an entire credential-bearing object and rely on downstream consumers to redact it.
- **Rationale:** Failure and debugging paths can disclose values excluded from normal outputs.
- **Implement:** allowlist diagnostic fields at the producer and filter unavoidable structured error inputs before export. Link to [logging controls](logging-monitoring.md) and [API failure responses](api-web-services.md).
- **Unsafe → corrected:** `log(config)` → `log({provider: config.provider, configured: true})` with no secret-bearing fields.
- **Positive check:** a normal operation still emits the necessary non-sensitive event and correlation identifier.
- **Negative check:** induce authentication and serialization failures with a synthetic canary; inspect captured logs, traces, and error responses for absence.
- **Evidence:** inspected logging/exception call sites and actual sink output. A redacting logger's existence is insufficient if some handlers bypass it.
- **Bounds / sources:** S1 sections 2.6, 3.4, 8.3. Record uncaptured sinks as not verified. Masking only part of a value needs a justified disclosure policy.

### SD-SECRET-001.C04 — Verify detection and narrow exclusions

- **Apply when:** a change introduces credential-handling code, fixtures, generated artifacts, or a secret-detection gate.
- **Required / prohibited:** run the selected redacting detection checks over the declared scope and review their findings. Do not report scanner failure as a clean result or exempt an entire directory because one fixture is benign.
- **Rationale:** Untested detectors and broad exclusions can create false confidence in secret checks.
- **Implement:** record detector/configuration, scanned surfaces, skips, and exact contextual suppressions with rationale, owner, and review date. Use inert seeded values appropriate to the detector; never test real credentials against external services.
- **Unsafe → corrected:** suppress all matches under `tests/` → suppress the reviewed fixture location/value while detecting an adjacent planted match.
- **Positive check:** the benign reviewed fixture is accepted under its exact exclusion and ordinary files remain scanned.
- **Negative check:** an adjacent or changed planted credential-like value triggers the gate; a tool error produces incomplete/failed coverage rather than success.
- **Evidence:** executed seeded and benign controls, exit behavior, scope and exclusions. A zero-match report without a functioning seeded control is weak evidence.
- **Bounds / sources:** S1 section 8. Detection is bounded; custom/encoded credentials need source-flow inspection. Suppression is not authorization to retain a usable secret.

### SD-SECRET-001.C05 — Separate source removal from credential invalidation

- **Apply when:** evidence indicates that a usable credential was exposed through source, artifacts, logs, or other unintended recipients.
- **Required / prohibited:** track containment and credential invalidation separately from deleting the exposed text. Do not label exposure remediated solely because the current file no longer contains it.
- **Rationale:** Deleting a source value does not invalidate a credential already obtained by others.
- **Implement:** identify the responsible owner and affected consumer, then use the authorized provider-specific rotation/revocation process. Record pending actions without printing the credential. Source-history rewriting and service changes require their own task authorization.
- **Unsafe → corrected:** close the incident after removing a token from a file → retain an unresolved invalidation action until authorized provider evidence establishes the old credential is unusable.
- **Positive check:** in an authorized test environment, the replacement credential supports the intended operation.
- **Negative check:** the revoked synthetic credential is rejected by the test provider; caches and long-lived sessions are assessed where relevant.
- **Evidence:** provider audit/status evidence and authorized observations, or an explicit unverified owner action. Never contact a production provider just to validate a discovered token.
- **Bounds / sources:** S1 sections 2.7 and 9. No universal rotation period is implied. Do not revoke production credentials under an ordinary code-review task.

## Sources

- **S1:** [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) — sections 2 General Secrets Management; 3 CI/CD; 5 Containers; 8 Detection; 9 Incident Response. Living documentation, checked 2026-09-24. These conditions are project acceptance criteria informed by the source, not compliance certification.
