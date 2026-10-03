# Requirements index

Status: proposed baseline; source verification is recorded per document. All 29 topics contain actionable requirements. This is a starting engineering baseline, not an exhaustive standard or approved corporate policy. Read only applicable topics and use the [requirement format](requirement-format.md) for extensions and exceptions.

Topic IDs below are stable groups, not single pass/fail checks. Each linked topic defines `.Cnn` conditions with applicability, examples, positive/negative checks, and evidence boundaries. Profiles refine implementation without replacing these acceptance criteria.

## Selection decisions

Use observed behavior and trust boundaries, not filenames or keywords alone. Record the trigger and selected individual IDs in the development report. Combine applicable rows; when context is unknown, inspect it or record an unresolved applicability question rather than silently marking the control not applicable.

| Observed circumstance | Selection decision | Boundary / exclusion |
| --- | --- | --- |
| A value reaches a network client, interpreter, file operation, or protected state change | Follow its flow and select the corresponding rows below, including downstream operations. | A URL rendered as browser text does not by itself trigger server-side outbound-request conditions. |
| Identity, object ownership, or tenant isolation affects the operation | Select the relevant authentication, authorization and session conditions separately. | A local single-user tool does not acquire a requirement for accounts or tenants merely from using this catalog. |
| The target uses a listed framework and compatible APIs | Load its stack profile after the general conditions; use its individual condition mappings. | A matching language alone does not establish framework/version applicability. No listed profile does not make the general condition inapplicable. |
| A control has several independent clauses | Select and verify the applicable clauses, recording each observed result. | One passing check does not verify the entire condition or topic. |
| An applicable requirement is intentionally unmet | Record an exception with scope, rationale, compensating controls, owner and review date. | Non-applicability needs a reason grounded in the actual design; use evidence for the selected status. |
| A change is documentation-only or has no affected security boundary | Record that scope briefly and select only conditions actually affected. | Do not expand the task into an unrelated repository audit. |

## Select by change

Use these starting points to select individual conditions, then read their applicability and follow the actual data flow for additional topics. Combine rows when a change spans several operations. Ranges below refer to each condition individually; they are neither mandatory bundles nor exhaustive coverage. Select matching stack profiles afterward.

| Change | Conditions to inspect first | Add when relevant / coverage limits |
| --- | --- | --- |
| Add an export, cache, search projection or deferred reader | [SD-AUTHZ-001.C02 and C05](topics/authorization-access-control.md): alternate object paths and access lifetime | Warm derived data before rights/publication changes; record the effective boundary and stale-event behavior. Select C03 only for an actual tenant boundary. |
| Change deletion, unpublication or reindexing | [SD-PRIVACY-001.C04](topics/privacy-data-protection.md) for personal-data disposition; [SD-AUTHZ-001.C05](topics/authorization-access-control.md) for access changes | Test delayed events and retained copies separately; withholding a result does not prove deletion of stored bytes. |
| Add retry, worker recovery or an external effect | [SD-BUSINESS-001.C02–C03](topics/business-logic.md): competing updates and ambiguous outcomes | State the shared invariant, commit boundaries and recovery observation; a timeout does not prove that no effect happened. |
| Add or change file uploads | [SD-FILES-001.C01–C04](topics/files-uploads.md): paths, publication, accepted formats, and resource limits | `SD-FILES-001.C05` when serving uploaded content; [SD-AUTHZ-001.C01–C02](topics/authorization-access-control.md) for operation/object access, and `.C03` for tenant boundaries. |
| Add an API endpoint | [SD-API-001.C01–C05](topics/api-web-services.md): access, methods, representation, resource limits, and failures; [SD-INPUT-001.C01](topics/input-validation-injection.md): decoded input | [SD-AUTHZ-001.C02–C04](topics/authorization-access-control.md) for objects, tenants, or privilege-bearing fields; `SD-INPUT-001.C02–C04` for database, dynamic syntax, or process sinks; [SD-WEB-001.C03–C04](topics/client-web-security.md) for browser request and cross-origin boundaries. |
| Change authorization or roles | [SD-AUTHZ-001.C01–C05](topics/authorization-access-control.md): grants, objects, tenants, privilege fields, and deferred/cached access | [SD-SESSION-001.C03–C04](topics/sessions-cookies.md) if session trust or termination changes. Load [authentication conditions](topics/authentication-mfa.md) only if identity verification, factors, or recovery also changes; authorization alone does not imply a new login system. |
| Process an external URL | [SD-INPUT-001.C01 and .C05](topics/input-validation-injection.md): input contract and decoding | For server-side fetching, [SD-OUTBOUND-001.C01–C04](topics/outbound-requests.md): destinations, actual connections, redirects, and recipient-bound credentials; for HTTPS, [SD-X509-001.C01–C02](topics/x509-certificates.md). For browser rendering, [SD-WEB-001.C02](topics/client-web-security.md). Input/TLS checks alone do not establish destination confinement. |
| Add a reservation, quota, approval, or repeatable external effect | [SD-BUSINESS-001.C01–C03](topics/business-logic.md): authoritative transitions, concurrency, retries | Select actual invariants; do not add transactions or accounts to unrelated changes. |
| Consume a webhook or queued event | [SD-EVENT-001.C01–C03](topics/webhooks-events.md): authenticity, scope/freshness, delivery semantics | Reuse business invariants for duplicate effects and [SD-API-001.C04](topics/api-web-services.md) for bounded intake/work. |
| Rotate or recover a cryptographic key | [SD-KEY-001.C01–C03](topics/key-lifecycle.md): allowed use, versions, recovery | Apply primitive constraints independently; no universal rotation schedule or required HSM. |
| Add OAuth/OIDC/JWT or local password enrollment | [SD-PROTOCOL-001.C01–C03](topics/authentication-protocols.md) for the actual protocol; [SD-AUTHN-001.C07](topics/authentication-mfa.md) for local passwords | Delegated identities do not require local password handling; SAML/passkeys need their own selected primary references. |
| Cache a protected response | [SD-API-001.C06](topics/api-web-services.md) and [SD-AUTHZ-001.C03/C05](topics/authorization-access-control.md) | Test real cache hits across actors and policy changes; load the Next.js profile only for that stack. |
| Change browser document delivery | [SD-WEB-001.C07–C08](topics/client-web-security.md) | Select framing and response protections from the threat model, not an unconditional header bundle. |
| Add a non-SQL query or server template | [SD-INPUT-001.C06–C07](topics/input-validation-injection.md) | LDAP/XPath/prototype mutation and other engines require separately sourced, sink-specific assessment when used. |
| Assemble model requests, expose agent tools or use generated changes | [SD-AI-001.C01–C06](topics/ai-assisted-development.md) | Select actual runtime boundaries; ordinary AI-written code needs C06 and its affected conventional controls, not a model gateway. |
| Add an HTTP MCP endpoint | [SD-MCP-001.C01–C06](topics/mcp-security.md) | Select applicable token/session conditions; HTTP Origin tests do not apply to stdio. |

## Topic catalog

| Group ID | Topic |
| --- | --- |
| `SD-SECRET-001` | [Secrets and hardcoding](topics/secrets.md) |
| `SD-CRYPTO-001` | [Allowed and prohibited cryptography](topics/cryptography-policy.md) |
| `SD-X509-001` | [X.509 inspection and validation](topics/x509-certificates.md) |
| `SD-PRIMITIVE-001` | [Cryptographic primitive usage](topics/cryptographic-primitives.md) |
| `SD-API-001` | [API and web services](topics/api-web-services.md) |
| `SD-AUTHN-001` | [Authentication and MFA](topics/authentication-mfa.md) |
| `SD-AUTHZ-001` | [Authorization and access control](topics/authorization-access-control.md) |
| `SD-MEMORY-001` | [C/C++ memory and string safety](topics/c-cpp-memory-string-safety.md) |
| `SD-CICD-001` | [DevOps, CI/CD, and containers](topics/devops-cicd-containers.md) |
| `SD-WEB-001` | [Client-side web security](topics/client-web-security.md) |
| `SD-DATASTORE-001` | [Databases and data storage](topics/databases-storage.md) |
| `SD-FILES-001` | [Files and uploads](topics/files-uploads.md) |
| `SD-STACK-001` | [Framework and language guidance](topics/frameworks-languages.md) |
| `SD-IAC-001` | [Infrastructure as Code](topics/infrastructure-as-code.md) |
| `SD-INPUT-001` | [Input validation and injection prevention](topics/input-validation-injection.md) |
| `SD-K8S-001` | [Kubernetes hardening](topics/kubernetes-hardening.md) |
| `SD-LOG-001` | [Logging and monitoring](topics/logging-monitoring.md) |
| `SD-AI-001` | [AI-assisted development and model integrations](topics/ai-assisted-development.md) |
| `SD-MCP-001` | [Model Context Protocol security](topics/mcp-security.md) |
| `SD-MOBILE-001` | [Mobile application security](topics/mobile-security.md) |
| `SD-PRIVACY-001` | [Privacy and data protection](topics/privacy-data-protection.md) |
| `SD-SESSION-001` | [Sessions and cookies](topics/sessions-cookies.md) |
| `SD-SUPPLY-001` | [Dependencies and supply chain](topics/dependencies-supply-chain.md) |
| `SD-SERIAL-001` | [XML and serialization hardening](topics/xml-serialization.md) |
| `SD-OUTBOUND-001` | [Server-side outbound requests](topics/outbound-requests.md) |
| `SD-BUSINESS-001` | [Business invariants and concurrent operations](topics/business-logic.md) |
| `SD-KEY-001` | [Cryptographic key lifecycle](topics/key-lifecycle.md) |
| `SD-EVENT-001` | [Webhooks and asynchronous events](topics/webhooks-events.md) |
| `SD-PROTOCOL-001` | [Conditional authentication protocol guidance](topics/authentication-protocols.md) |

## Stack-specific controls

Load a profile only when its stack and trust model match. Each profile maps its implementation checks to individual topic conditions. Assess the mapped conditions separately and report partial coverage explicitly. Profiles are source-reviewed, not blanket runtime compatibility certifications.

| IDs | Profile | Refines |
| --- | --- | --- |
| `SD-PY-001`–`SD-PY-005` | [Python / FastAPI / Pydantic v2 / SQLAlchemy 2.0](stacks/python-fastapi.md) | Input validation, API responses, files, secrets, logging |
| `SD-TS-001`–`SD-TS-003` | [TypeScript / React 19 / Next.js 16](stacks/typescript-nextjs.md) | Access control, browser rendering, client-visible configuration |
| `SD-COMPOSE-001`–`SD-COMPOSE-004` | [Docker Compose v2 / BuildKit](stacks/docker-compose.md) | Exposure, secrets, build artifacts, runtime privilege |
