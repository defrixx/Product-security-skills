# Infrastructure as Code

## SD-IAC-001

Status: proposed baseline; C01–C03 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Examples are synthetic workflow sketches. Terraform illustrates implementation; other tools require their own version-matched documentation. Module/provider provenance follows [supply-chain conditions](dependencies-supply-chain.md).

### SD-IAC-001.C01 — Protect state and plan contents

- **Apply when:** infrastructure tooling writes state, saved plans, exports, or CI artifacts that can contain credentials or infrastructure details.
- **Required / prohibited:** restrict access to the intended operators/jobs and protect stored/transmitted content according to its classification. Do not treat a sensitive display flag as encryption or exclusion from persistence.
- **Rationale:** state and plan downloads can disclose values hidden in normal console output.
- **Implement:** use a protected backend and restricted artifact permissions; exclude local state/plans from source control and public build attachments. Where supported, use ephemeral/write-only mechanisms to avoid unnecessary persistence, after checking tool and provider support.
- **Unsafe → corrected:** mark a synthetic password sensitive and upload the saved plan publicly → retain the plan only in access-controlled storage and verify its actual contents and access policy.
- **Positive check:** the authorized deployment identity can retrieve the required plan/state through the intended protected channel.
- **Negative check:** an unrelated identity cannot retrieve it; seeded sensitive values do not appear in ordinary logs or delivery attachments. Inspect JSON/raw exports separately.
- **Evidence:** backend/artifact ACL and output-path inspection; executed access-denial and synthetic leak checks. Masked console output alone does not establish storage confidentiality.
- **Bounds / sources:** S1, Background and Hide sensitive variables and outputs. Terraform ephemeral and write-only features are version/provider dependent; their availability does not imply all resource attributes are omitted.

### SD-IAC-001.C02 — Gate the effective change before applying it

- **Apply when:** definitions, variables, modules, or environment selection change deployed permissions, network exposure, or resources.
- **Required / prohibited:** assess the effective proposed changes against explicit project constraints before application. Do not approve solely from a source fragment when resolved inputs can change its behavior.
- **Rationale:** module defaults and substitutions can create permissions or exposure absent from the reviewed fragment.
- **Implement:** inspect the resolved plan, account/workspace and inputs; evaluate each relevant policy separately, such as allowed ingress or identity scope. Bind the apply workflow to the reviewed plan and reject unreviewed substitutions. Scope the deployment identity independently.
- **Unsafe → corrected:** approve a module call while ignoring its public-storage default → inspect the resulting storage access change and reject it unless the explicit policy permits it.
- **Positive check:** a synthetic plan implementing the intended private resource passes its applicable policy checks; an isolated workflow rehearsal accepts that exact reviewed plan for the intended account/workspace without deploying infrastructure.
- **Negative check:** synthetic broad-IAM and unintended-public-ingress changes each fail their own gate; unknown security-relevant values remain unresolved instead of passing by omission. In an isolated workflow rehearsal, substitute the plan, change the target account/workspace, or bypass the policy stage; each attempt must stop before any apply operation.
- **Evidence:** source/input/plan identity and policy review; executed policy checks on synthetic plans. Record workflow binding checks separately: a policy test alone does not prove the apply job uses that gate or the reviewed plan.
- **Bounds / sources:** S2, planning behavior and saved plans. Planning can execute provider code and contact APIs; inspect those operations before running them. This skill does not authorize infrastructure deployment.

### SD-IAC-001.C03 — Distinguish declared configuration from observed infrastructure

- **Apply when:** an assessment claims properties of an existing deployment or the project requires drift detection.
- **Required / prohibited:** base runtime claims on appropriately scoped observations and report drift or missing visibility. Do not infer current resource policy solely from checked-in definitions or stale state.
- **Rationale:** out-of-band changes can invalidate the security properties of the declared configuration.
- **Implement:** collect authorized read-only observations for the relevant resources; compare intended and observed access/exposure and route differences to the project's remediation process. Record observation time, environment, and coverage.
- **Unsafe → corrected:** declare a resource private because its source says so → compare the current access policy with the intended policy and report a mismatch without silently applying a fix.
- **Positive check:** a matching synthetic observed configuration produces a no-difference result for the assessed fields.
- **Negative check:** an out-of-band public-access change in the fixture is detected; missing or denied reads produce an incomplete assessment, not a clean result.
- **Evidence:** declared and observed values with timestamps plus executed comparison results. A mocked provider establishes comparison logic only; actual deployment state needs authorized environment evidence.
- **Bounds / sources:** S2, refresh and planning options. A refresh-only plan is an observation aid, not authorization to update state or remediate resources; provider coverage and permissions constrain completeness.

## Sources

- **S1:** [Terraform sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data) — Background, Requirements, Hide sensitive variables and outputs; living documentation; Requirements section rechecked 2026-09-28: ephemeral features require Terraform 1.10+, resource write-only arguments 1.11+ plus provider support. These are feature prerequisites, not a tested target version. The earlier 1.16.x selector observation is not retained as verified provenance; select the actual target version.
- **S2:** [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) — planning behavior, planning modes/options, saved plans; living CLI documentation checked 2026-09-24. General acceptance conditions are this baseline's engineering synthesis, not universal Terraform defaults.
