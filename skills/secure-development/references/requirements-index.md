# Requirements index

Status: proposed baseline; source review date **2026-09-24**. All 23 topics contain actionable requirements. This is a starting engineering baseline, not an exhaustive standard or approved corporate policy. Read only applicable topics and use the [requirement format](requirement-format.md) for extensions and exceptions.

Topic IDs below are stable groups, not single pass/fail checks. Each linked topic defines `.Cnn` conditions with applicability, examples, positive/negative checks, and evidence boundaries. A group passes only when every applicable condition is sufficiently verified; missing evidence remains not verified. Profiles refine implementation without replacing these acceptance criteria.

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
| `SD-MCP-001` | [Model Context Protocol security](topics/mcp-security.md) |
| `SD-MOBILE-001` | [Mobile application security](topics/mobile-security.md) |
| `SD-PRIVACY-001` | [Privacy and data protection](topics/privacy-data-protection.md) |
| `SD-SESSION-001` | [Sessions and cookies](topics/sessions-cookies.md) |
| `SD-SUPPLY-001` | [Dependencies and supply chain](topics/dependencies-supply-chain.md) |
| `SD-SERIAL-001` | [XML and serialization hardening](topics/xml-serialization.md) |

## Stack-specific controls

Load a profile only when its stack and trust model match. Each profile maps its implementation checks to individual topic conditions. Assess the mapped conditions separately and report partial coverage explicitly. Profiles are source-reviewed, not blanket runtime compatibility certifications.

| IDs | Profile | Refines |
| --- | --- | --- |
| `SD-PY-001`–`SD-PY-005` | [Python / FastAPI / Pydantic v2 / SQLAlchemy 2.0](stacks/python-fastapi.md) | Input validation, API responses, files, secrets, logging |
| `SD-TS-001`–`SD-TS-003` | [TypeScript / React 19 / Next.js 16](stacks/typescript-nextjs.md) | Access control, browser rendering, client-visible configuration |
| `SD-COMPOSE-001`–`SD-COMPOSE-004` | [Docker Compose v2 / BuildKit](stacks/docker-compose.md) | Exposure, secrets, build artifacts, runtime privilege |
