# Kubernetes hardening

## SD-K8S-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Record cluster version, node OS, runtime, admission configuration, and network plugin. Examples are synthetic local-cluster scenarios. Render charts/overlays before inspection; declarations alone do not prove enforcement.

### SD-K8S-001.C01 — Restrict workload API authority

- **Apply when:** workloads use service accounts or identities with Kubernetes API permissions.
- **Required / prohibited:** grant only required verbs, resources, and namespace scope. Do not provide cluster-admin or secret-listing rights to a workload that does not need them.
- **Rationale:** a compromised workload can use its API identity for lateral movement.
- **Implement:** assign dedicated service accounts, narrow Role/RoleBinding grants, and disable automatic token mounting when API access is unnecessary. Inspect indirect escalation through workload creation, impersonation, or role binding as well as direct secret reads.
- **Unsafe → corrected:** bind a reporting service to cluster-admin → grant only its documented read operations in the intended namespace.
- **Positive check:** the workload identity completes its required API request.
- **Negative check:** the same identity cannot read a synthetic unrelated Secret or create a privileged workload; verify relevant escalation paths individually.
- **Evidence:** rendered bindings and effective authorization inspection; executed requests as the workload identity in an authorized cluster. A role definition without its bindings is incomplete evidence.
- **Bounds / sources:** S1, RBAC and service accounts. Cloud identity federation adds another authorization boundary requiring separate inspection.

### SD-K8S-001.C02 — Enforce the selected Pod security boundary

- **Apply when:** workloads can be created or updated in a namespace.
- **Required / prohibited:** enforce the chosen version-compatible Pod security policy at admission. Warning or audit mode alone must not be reported as rejection enforcement.
- **Rationale:** permissive workload creation can grant host-level capabilities.
- **Implement:** select the appropriate Pod Security Standards profile, prefer Restricted where feasible, and configure enforcement with explicit exceptions. Review init, sidecar, and ephemeral containers; apply [container runtime conditions](devops-cicd-containers.md) to effective process settings.
- **Unsafe → corrected:** label a namespace for warnings only and claim privileged Pods are blocked → configure enforce mode for the intended profile and verify rejection.
- **Positive check:** a compliant synthetic Pod is admitted and can perform its intended work.
- **Negative check:** a Pod violating a selected profile rule is rejected; test each relevant exception path and confirm it cannot broaden access unintentionally.
- **Evidence:** effective admission configuration, profile version, exemptions, and rendered Pod specs; executed admission results. Accepted controller objects do not prove their eventual Pods pass admission.
- **Bounds / sources:** S1, Pod security. Linux and Windows controls differ; match the actual OS/version and avoid asserting unsupported settings are effective.

### SD-K8S-001.C03 — Enforce declared network flows

- **Apply when:** workloads require ingress/egress isolation from other workloads or external destinations.
- **Required / prohibited:** allow documented flows and deny prohibited flows through an enforcement-capable network implementation. A NetworkPolicy object without supported enforcement is insufficient.
- **Rationale:** unrestricted connectivity exposes neighboring services and enables unintended data transfer.
- **Implement:** define the required flow matrix, apply ingress/egress policies, and inspect selectors and all additive policies. Account for DNS, control-plane dependencies, service routing, and plugin-specific behavior.
- **Unsafe → corrected:** create a default-deny manifest on a plugin that ignores it → use supported enforcement and verify the expected allowed and denied paths.
- **Positive check:** a synthetic client reaches the approved service/port and required DNS path.
- **Negative check:** prohibited namespace-to-service and egress paths fail; record each direction and source/destination identity separately.
- **Evidence:** selected Pods/namespaces, effective policies, plugin/version configuration; executed connectivity observations. A timeout alone needs a healthy allowed control to distinguish policy denial from service failure.
- **Bounds / sources:** S1, Network security. Standard policy semantics do not cover every host-network or application-layer boundary; document unsupported paths.

### SD-K8S-001.C04 — Bound workload resource consumption

- **Apply when:** workloads share node or namespace resources and can consume CPU, memory, storage, or object counts.
- **Required / prohibited:** enforce project-selected resource budgets at the relevant boundary. Do not present scheduling requests alone as runtime consumption limits.
- **Rationale:** one workload can exhaust shared capacity and disrupt others.
- **Implement:** configure appropriate requests/limits and namespace quotas/limit ranges; account for init/sidecar containers and ephemeral storage where supported. Choose values from workload measurements and availability requirements rather than universal constants.
- **Unsafe → corrected:** deploy an unbounded synthetic worker in a shared namespace → define its measured runtime budget and enforce the namespace's allocation ceiling.
- **Positive check:** expected workload traffic completes within the selected budget.
- **Negative check:** a controlled over-budget fixture is rejected, throttled, or terminated according to the specific resource mechanism without exhausting the test environment.
- **Evidence:** effective Pod resource settings and namespace policies; bounded execution observations for each claimed resource. Do not infer memory behavior from a CPU-only test.
- **Bounds / sources:** S1, resource protection guidance. Runtime/OS semantics and storage accounting differ; use target-version documentation. Run stress fixtures only in a disposable, explicitly bounded environment.

## Sources

- **S1:** [Kubernetes Security Checklist](https://kubernetes.io/docs/concepts/security/security-checklist/) — RBAC, Pod security, Network security, resource and secret protection. Living documentation; checked 2026-09-24. Consult the matching cluster release and plugin documentation before selecting concrete settings. Secret storage/distribution also follows [secrets](secrets.md); these four conditions do not claim complete cluster hardening.
