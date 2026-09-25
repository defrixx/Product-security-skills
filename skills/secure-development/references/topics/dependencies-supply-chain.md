# Dependencies and supply chain

## SD-SUPPLY-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Examples are synthetic scenarios. Apply these conditions to direct/transitive packages, build tools, and release artifacts; [CI/container](devops-cicd-containers.md) controls govern the execution environment.

### SD-SUPPLY-001.C01 — Resolve packages from the intended source

- **Apply when:** a resolver downloads packages, modules, tools, or images, especially with mixed public/private namespaces.
- **Required / prohibited:** bind each dependency to its intended source and identity. Do not permit an unrelated public package to satisfy an internal dependency through resolver precedence.
- **Rationale:** a familiar package name can resolve to attacker-controlled code.
- **Implement:** configure registry/namespace mappings, inspect resolved URLs and publisher/source changes, and restrict credential scope. Use the selected package manager's version-specific documentation rather than assuming registries have identical precedence.
- **Unsafe → corrected:** let an internal package fall back to any public index → configure its namespace to the approved private source and fail when that source cannot supply it.
- **Positive check:** the synthetic internal package resolves from the intended test registry.
- **Negative check:** an identically named package in a separate local test registry cannot replace it, including when the intended package is unavailable.
- **Evidence:** resolver configuration and dependency-source review; isolated resolution logs with credentials redacted. A manifest name alone does not establish provenance.
- **Bounds / sources:** S1, Assess Suppliers and private artifact repositories. Test with local synthetic registries; do not publish package names or attack real registries.

### SD-SUPPLY-001.C02 — Enforce reviewed dependency content

- **Apply when:** installation or build steps consume dependency versions or artifact references.
- **Required / prohibited:** consume the reviewed resolved graph and verify available content integrity. Unexpected graph/content changes must fail or return to review; do not silently regenerate a lock during a release build.
- **Rationale:** mutable resolution can introduce code that was never assessed.
- **Implement:** use the ecosystem's frozen/locked installation mode and integrity metadata, including transitive dependencies and build tools. Pin immutable image content where supported. Maintain deliberate update changes rather than treating pins as permanent protection.
- **Unsafe → corrected:** resolve a floating dependency afresh in release CI → install the reviewed locked graph and reject manifest/lock inconsistency.
- **Positive check:** a clean isolated install produces the recorded dependency versions and identities.
- **Negative check:** a changed package byte stream or inconsistent manifest/lock causes failure before the altered dependency is executed.
- **Evidence:** lock and integrity metadata inspection; executed clean-install and tamper-rejection observations. Matching hashes prove matching bytes, not that those bytes are benign.
- **Bounds / sources:** S1, Lockfile/Version Pinning. Record platform-specific graph differences and package-manager versions; dependency reproducibility does not imply bit-for-bit build reproducibility.

### SD-SUPPLY-001.C03 — Assess advisories against the delivered inventory

- **Apply when:** dependencies enter a release or deployed inventory is monitored for new advisories.
- **Required / prohibited:** determine version applicability and relevant exposure, then record a remediation or accepted-exception decision under the project's policy. Do not equate an advisory hit with confirmed exploitability or a clean scan with absence of vulnerabilities.
- **Rationale:** scanning the wrong inventory misses shipped components; untriaged signals do not reduce risk.
- **Implement:** inventory actual packaged components, including transitive/runtime and base-image packages; record scanner/advisory freshness and assess reachable functionality. Assign a concrete update or mitigation with verification; do not invent universal remediation deadlines.
- **Unsafe → corrected:** scan only top-level declarations and ignore a bundled vulnerable transitive package → assess the delivered graph and document the affected component's disposition.
- **Positive check:** a synthetic applicable advisory produces a traceable assessment and the configured release decision.
- **Negative check:** an affected component cannot disappear merely because it is transitive; scanner failure or stale/unavailable advisory data is reported as incomplete, not clean.
- **Evidence:** artifact-bound inventory, tool/database version, advisory applicability reasoning, and executed gate result. Reachability assumptions remain explicit unless traced or tested.
- **Bounds / sources:** S1, Understand and Monitor Software Dependencies and Scan Final Build Binary. Synthetic advisory fixtures test workflow only; live applicability requires current primary vendor advisories.

### SD-SUPPLY-001.C04 — Verify release provenance at promotion

- **Apply when:** an artifact is promoted or deployed under a policy requiring source/build identity or signing.
- **Required / prohibited:** verify the artifact digest and the required trusted producer/source claims before promotion. A valid signature from an arbitrary identity must not satisfy an expected-signer policy.
- **Rationale:** substituted artifacts can bypass review even when the source repository is intact.
- **Implement:** bind release metadata to immutable source revision, build identity, and artifact digest; configure the verifier's trust policy independently of untrusted artifact metadata. Select supported signing/attestation tooling and keep signing authority outside untrusted builds.
- **Unsafe → corrected:** deploy anything with a mathematically valid signature → verify the required producer identity and source/build claims for that exact digest.
- **Positive check:** an artifact from the approved synthetic producer with matching claims passes the promotion policy.
- **Negative check:** altered content, wrong signer, and wrong source revision each fail promotion; test each policy predicate separately.
- **Evidence:** trust policy and promotion-path inspection; executed accepted/rejected verification records bound to artifact digests. A generated attestation without a consuming verification gate is insufficient.
- **Bounds / sources:** S1, Verify Provenance and Enforce Code Signing. Provenance establishes asserted origin under a trust model, not absence of malicious source or a compromised trusted builder.

## Sources

- **S1:** [OWASP Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html) — Mitigating Dependency Threats; Build Threats; Deployment and Runtime Threats. Living documentation; checked 2026-09-24. Package-manager, registry, and attestation implementation settings require matching vendor/version documentation.
