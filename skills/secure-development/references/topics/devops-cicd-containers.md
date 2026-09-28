# DevOps, CI/CD, and containers

## SD-CICD-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Synthetic examples describe boundaries rather than vendor-specific workflow syntax. Use the [Compose profile](../stacks/docker-compose.md) for matching container implementations; select CI vendor documentation for the actual trigger and runner version.

### SD-CICD-001.C01 — Isolate untrusted execution from release authority

- **Apply when:** pull requests, forks, dependency hooks, or contributor-controlled scripts run in automation.
- **Required / prohibited:** untrusted execution must not obtain release credentials or modify the trusted release environment. Do not assume a workflow's trusted location makes checked-out contributor code trusted.
- **Rationale:** build/test scripts execute with the job's available privileges.
- **Implement:** separate runner and credential boundaries; use disposable environments for untrusted work. Prevent writable workspaces, caches, and artifacts from becoming executable trusted inputs without validation.
- **Unsafe → corrected:** execute a PR's install hook in a signing job → run it in an unprivileged isolated job and promote only inputs accepted by the release trust policy.
- **Positive check:** a trusted release fixture reaches the intended authorized signing stage.
- **Negative check:** an untrusted fixture cannot read a synthetic release-secret canary or persist a script consumed by the trusted job. Check cache/workspace paths separately.
- **Evidence:** trigger-to-checkout-to-runner trace and credential availability; executed isolated workflow observations. A local simulation does not prove hosted platform trigger semantics.
- **Bounds / sources:** S1, Pipeline and Execution Environment. Inspect scripts before tests; do not use real release credentials in adversarial fixtures.

### SD-CICD-001.C02 — Limit each job identity to required operations

- **Apply when:** jobs receive repository tokens, cloud identities, registry credentials, or deployment rights.
- **Required / prohibited:** grant only the operations/resources needed by that job and constrain identity issuance to its intended context. Do not reuse a deployment administrator credential for ordinary tests.
- **Rationale:** job compromise should not automatically grant unrelated repository or environment control.
- **Implement:** declare explicit token permissions, separate identities by role/environment, and prefer bounded credentials where supported. Review federation issuer/audience/subject constraints as well as downstream permissions.
- **Unsafe → corrected:** give a test job repository write and production deployment rights → give it the read access needed for the test and no deployment grant.
- **Positive check:** the job completes its documented authorized operation with the scoped test identity.
- **Negative check:** that identity cannot publish, modify another environment, or obtain a stronger identity through an unintended federation context; select tests for each actual grant.
- **Evidence:** effective identity policies and issuance conditions; executed allowed/denied operations in an authorized sandbox. Workflow YAML alone does not show external cloud trust policy.
- **Bounds / sources:** S1, IAM and Least Privilege. Hidden organization-level grants remain a gap until inspected; do not infer their absence.

### SD-CICD-001.C03 — Keep build credentials out of image artifacts

- **Apply when:** image builds consume private registry/package credentials or other secrets.
- **Required / prohibited:** credentials must not persist in image layers, configuration, build history, caches intended for sharing, or logs. Deleting a file in a later layer does not remove an earlier copy.
- **Rationale:** anyone able to obtain the artifact may recover embedded credentials.
- **Implement:** use supported temporary build-secret mechanisms and prevent commands from copying or printing their contents; minimize build context. Apply [secret conditions](secrets.md) to other distributed outputs.
- **Unsafe → corrected:** copy a synthetic credential into one layer and delete it later → mount it only for the necessary build step and keep it out of generated files.
- **Positive check:** the isolated build can access its synthetic private dependency using the temporary credential.
- **Negative check:** the credential canary is absent from exported layers, history, image configuration, logs, the runtime filesystem, and any cache exported for sharing; inspect each applicable surface. Verify the inspection detects an intentionally planted canary in a disposable control artifact.
- **Evidence:** build data-flow inspection plus executed artifact extraction and canary search. A secret-mount declaration alone cannot prove the build command did not copy it.
- **Bounds / sources:** S2, secrets guidance; implementation details in the Compose profile. An exact canary test proves that fixture's non-disclosure, not exhaustive detection of arbitrary encodings.

### SD-CICD-001.C04 — Restrict the effective container execution privileges

- **Apply when:** a service or build workload runs in a container.
- **Required / prohibited:** use only justified process capabilities and host access. Unnecessary privileged mode, host control sockets, writable host mounts, or privilege escalation must be absent.
- **Rationale:** a compromised process can otherwise cross the intended container boundary.
- **Implement:** choose a non-root identity where feasible, drop unnecessary capabilities, restrict filesystem writes, and apply supported no-new-privileges and syscall controls. Record justified required privileges as part of the normal policy; record a scoped exception only for a deliberately unmet applicable restriction and verify effective settings after orchestration overrides.
- **Unsafe → corrected:** launch a web service privileged with the host engine socket mounted → remove host control access and run under the limited identity/capabilities its operation requires.
- **Positive check:** normal service operations succeed with writes limited to the declared writable locations.
- **Negative check:** writes outside those locations and selected operations requiring removed privileges fail; inspect absence of host-control mounts separately.
- **Evidence:** resolved runtime configuration and process identity/capabilities; executed denial checks in a disposable container. Image scanning does not establish runtime confinement.
- **Bounds / sources:** S2, daemon socket, user, capabilities, and privilege escalation rules. Each runtime restriction needs its own observation; containers do not eliminate kernel/runtime vulnerabilities.

## Sources

- **S1:** [OWASP CI CD Security](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html) — Pipeline and Execution Environment; IAM. Living documentation; checked 2026-09-24.
- **S2:** [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) — daemon socket, user, capabilities, privilege escalation, and secrets guidance. Living documentation; checked 2026-09-24. Runtime options require version-matched vendor verification.
