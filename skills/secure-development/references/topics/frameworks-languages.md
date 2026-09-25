# Framework and language guidance

## SD-STACK-001

Status: proposed baseline; C01–C03 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. These are rules for selecting and verifying implementations, not a declaration that a framework makes an application secure.

### SD-STACK-001.C01 — Match advice to the actual runtime

- **Apply when:** a security-sensitive setting, API, default, or mitigation depends on the language, framework, parser, or deployment version.
- **Required / prohibited:** establish the relevant installed/runtime version and supported behavior before prescribing a setting. Do not copy an option from another release or stack and report it as effective without verification.
- **Rationale:** A setting from the wrong release may be ignored or have different semantics.
- **Implement:** inspect manifests, lockfiles, container/build inputs, and runtime version output where available. Locate the matching vendor documentation and record the API/setting's scope. Use the available profile only when its assumptions match.
- **Unsafe → corrected:** enable a security flag copied from unrelated middleware → identify the actual middleware and version, select its documented mechanism, then test that mechanism.
- **Positive check:** the selected supported setting is accepted and protects the intended operation in the actual runtime.
- **Negative check:** an unsupported or misspelled setting is detected by validation or an explicit behavior test; it must not silently justify a pass.
- **Evidence:** version provenance and vendor section, plus executed configuration/behavior checks. A dependency constraint alone does not prove the deployed version.
- **Bounds / sources:** S1 demonstrates version-scoped framework guidance; the matching vendor source is required for each target implementation. If runtime access is unavailable, report that assumption rather than inventing a version.

### SD-STACK-001.C02 — Account for bypass APIs and disabled protections

- **Apply when:** code uses raw SQL, unsafe template/HTML APIs, custom serialization, middleware exclusions, or another framework escape hatch.
- **Required / prohibited:** preserve the required security property when bypassing a framework mechanism. Do not infer protection from framework usage when the actual call bypasses it.
- **Rationale:** Escape hatches bypass protections otherwise supplied by a framework.
- **Implement:** enumerate security-relevant escape hatches in the requested change and trace their producers/consumers. Prefer supported safe APIs; justify unavoidable bypasses with the corresponding topic condition and compensating implementation.
- **Unsafe → corrected:** assume an ORM protects an interpolated raw SQL call → bind values through the driver's supported API and test the executed query.
- **Positive check:** the safe replacement preserves the intended valid operation.
- **Negative check:** the topic's adversarial input remains inert or rejected through the bypass/replacement path, not merely through an unrelated safe endpoint.
- **Evidence:** concrete bypass call sites and data-flow inspection; executed positive/negative tests through those sites. A scanner keyword hit is a lead, not proof of an exploitable bypass.
- **Bounds / sources:** S1, XSS and SQL Injection Protection. Apply [input](input-validation-injection.md), [client-web](client-web-security.md), and [serialization](xml-serialization.md) conditions as relevant; do not duplicate weaker versions of them here.

### SD-STACK-001.C03 — Verify effective production configuration

- **Apply when:** environment overrides, reverse proxies, middleware order, debug flags, or deployment adapters can change a security mechanism.
- **Required / prohibited:** verify the intended protection in the effective request/processing pipeline. Do not treat development defaults or isolated helper tests as proof of production behavior.
- **Rationale:** Deployment overrides can invalidate a protection tested only in isolation.
- **Implement:** inspect environment-specific configuration and middleware ordering, constrain proxy trust to intended proxies, and disable inappropriate debug exposure. Test the complete representative pipeline in a disposable environment using production-equivalent settings.
- **Unsafe → corrected:** test host validation directly while deployment trusts arbitrary forwarded headers → verify the request through the configured proxy/middleware chain and restrict the trusted forwarding boundary.
- **Positive check:** legitimate requests from the intended deployment path retain the documented behavior.
- **Negative check:** a spoofed host/forwarded value or controlled error cannot bypass the selected protection or expose debug details. Select tests for the actual override being assessed.
- **Evidence:** effective configuration and pipeline trace, actual response/state observations, and explicit differences from production. A mock proxy does not prove the real proxy's rewriting behavior.
- **Bounds / sources:** S1, Host Header Validation and deployment security considerations. Each override needs its own evidence row; testing one flag does not establish all framework protections. External deployment access requires authorization.

## Sources

- **S1:** [Django security](https://docs.djangoproject.com/en/5.2/topics/security/) — Django 5.2; XSS, CSRF, SQL Injection, Host Header Validation. Checked 2026-09-24. This is an illustrative versioned primary source, not a universal configuration guide. Target-specific settings require that target vendor's documentation.

## Available profiles

Use the [stack-specific controls in the index](../requirements-index.md#stack-specific-controls) for Python/FastAPI, TypeScript/Next.js, and Docker Compose. Profiles supply implementation details and stack-specific checks for general conditions. Load only matching profiles and report each applicable condition; one passing check does not establish that a whole stack is secure.
