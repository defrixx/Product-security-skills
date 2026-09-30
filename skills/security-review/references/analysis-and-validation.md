# Analysis and validation

## Threat model and discovery

Start with assets and security invariants: who may read, change, invoke, or administer each asset? Identify anonymous users, authenticated users, other tenants, compromised dependencies, administrators, and external services only where relevant. Map each entry point through parsing, authentication, authorization, business operations, storage, and output. Record assumptions such as proxy trust and deployment isolation.

Use this matrix to guide investigation, not as a claim that every row was tested:

| Area | Candidate paths to trace | Useful negative checks |
| --- | --- | --- |
| Identity and sessions | Login, recovery, factor changes, token verification, session invalidation | Alternate login bypass, wrong token audience, reused session |
| Authorization and business logic | Object ownership, tenant scope, bulk/export/admin routes, state transitions | Another user's object, repeated or concurrent operation, skipped state |
| Injection and parsing | Query/command/template sinks, XML and native deserialization | Data becoming syntax, external resolution, attacker-chosen types |
| Files and outbound requests | Upload/download, archive paths, callbacks, URL fetches | Traversal, symlink escape, redirect bypass, internal destination |
| Data and cryptography | Credential use, certificate validation, key/nonce lifecycle, logs/backups | Invalid peer accepted, modified ciphertext consumed, secret disclosure |
| Native/browser/mobile | Lifetime and bounds, DOM sinks, message origins, IPC/deep links | Boundary input, untrusted markup, unauthorized component invocation |
| Deployment and supply chain | CI triggers, dependency hooks, IaC, images, RBAC and runtime | Untrusted build with secrets, overprivileged workload, public data |
| MCP and agent integrations | Tool authorization, session binding, data/tool trust boundaries | Cross-user invocation, injected instructions, excessive data transmission |

Dependency advisories require exact version and environment applicability. Explain whether vulnerable code is reachable; lack of a demonstrated exploit does not automatically make an applicable advisory irrelevant. A configuration omission in source may be supplied at deployment: distinguish missing evidence from a confirmed insecure deployed setting.

The declared product model is context to verify, not a blanket exemption: for a local single-user application, examine loopback exposure, browser request boundaries, and imported content rather than automatically prescribing multi-user authentication. Distinguish observed configuration from runtime evidence.

## Candidate validation

For each candidate, locate the entry point and sensitive operation at the recorded revision. Follow transformations and all guards, including middleware and shared helpers. Identify what the attacker actually controls and the minimum privilege required. Seek counterevidence before confirmation.

Trace each independent input channel to its sink. Validating ZIP member names does not establish that manifest filenames are safe; a defense in an upload route does not automatically protect an import route. Check whether validation occurs before the side effect and whether rollback covers filesystem/network effects as well as database changes.

Use the least invasive sufficient proof. A complete code trace may be sufficient; a local reproduction can resolve uncertain runtime behavior. Inspect helper scripts and dependencies first, disable external connectivity where practical, use disposable storage and synthetic fixtures, and avoid actual credentials. Record expected secure behavior and observed behavior separately. Do not include operational attack details beyond what remediation and reproduction require.

For extracted-function or mocked tests, record which original code ran unchanged, which dependencies were replaced, and what the test can establish. A simulated transport may prove the order of checks without proving DNS rebinding; a fabricated browser header does not prove a browser can generate an exploitable request. State the demonstrated primitive separately from conditional downstream impact. Count “vulnerability reproduced” separately from “control held.”

If a check cannot run, preserve the candidate as a hypothesis unless static evidence independently establishes it. Tool failure means unverified coverage, not a clean result. For each hypothesis, state the observation that would confirm it, the counterevidence that would disprove it, and when the check must stop as inconclusive (for example, missing runtime evidence). A failed probe alone does not disprove a candidate if it did not reach the relevant operation.

Group findings only when evidence establishes the same defective control and a common repair boundary. List each affected path, its guards, prerequisites, impact, and verification case under the canonical finding. Similar titles, the same CWE, or a shared sink are insufficient: independent guards or independently required repairs can warrant separate findings. Preserve alternate bypass paths even when grouping. Retain existing IDs as aliases if previously reported findings are merged; count the canonical finding once and do not combine uncertain paths into confirmed evidence.

## Impact and remediation

Explain confidentiality, integrity, availability, or privilege impact in the actual deployment context. Record severity and rationale separately from confidence. Do not claim administrative compromise from an unverified chain of assumptions.

Each confirmed finding needs a concrete repair direction and an acceptance test that would fail before the fix and pass afterward, including relevant unauthorized and authorized cases. Prioritize credible exposure and impact, then prerequisites and remediation dependencies. Do not fix code during a review-only task.

For attack chains, reference finding IDs, prerequisites for each link, and whether each link is confirmed. Keep speculative consequences labeled. Report only what the examined evidence supports.
