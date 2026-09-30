# Triage method

## Validation and priority

Locate the reported entry and sensitive operation at the recorded revision. Follow actual input control, transformations, guards, prerequisites, deployment assumptions, and effects. Seek counterevidence; a scanner hit starts as a hypothesis. Static evidence may establish a defect without execution. A failing reproduction is not disproof when setup failed or the relevant path was not reached.

For dependency findings establish exact component/version and environment applicability using current primary advisory sources; record source/version/date or unavailable verification. Lack of a demonstrated exploit or a dev-only declaration alone does not prove irrelevance. Unknown deployment configuration is missing evidence, not an observed insecure setting.

Keep original scanner labels separate from contextual severity and remediation priority. Explain exposure, impact, and prerequisites. Do not invent CVSS/CWE mappings. Record confidence independently. Supplied suppressions and accepted-risk notes require context; neither establishes a false positive or a fix.

## Accounting and grouping

Every raw result has exactly one primary disposition: confirmed, hypothesis, disproved, out_of_scope, or unprocessed. Reasons are mandatory for exclusions/errors. A fatal parse may make counts unknown; never report unknown as zero. Duplicate relationships are additional mappings, not dispositions. Sum disposition counts to the known raw input count and separately count unique confirmed canonical findings.

Group only when evidence establishes a shared defective control and common repair boundary. Rule ID, fingerprint, message similarity, shared sink, or location alone is insufficient. Preserve independent guards and affected paths, impact, and acceptance cases. Uncertain paths do not become confirmed by merging. Keep aliases to prior finding IDs; split mistaken groups with linked child IDs and rationale.

Disproved means specific counterevidence for the claimed path. Each hypothesis states missing evidence, next check, confirming/disproving observations, and an inconclusive stopping condition. Unprocessed/out-of-scope coverage is not clean. Missing signals after a rerun do not establish remediation.

## Checkpoints and delivery

TRIAGE-01: report/target provenance and scope. TRIAGE-02: all results accounted for. TRIAGE-03: path/guard analysis and counterevidence. TRIAGE-04: justified grouping and aliases. TRIAGE-05: independent statuses and priority. TRIAGE-06: redacted queue with source preserved.

Record evidence and passed/partial/not verified/not applicable with rationale per checkpoint. Include tool versions, skill fingerprint, target dirty state, actual execution versus mocks, errors, and untested context. Check selected attachments for sensitive text and links. Opaque location IDs require authorized local source inspection before implementation; do not pretend they alone describe the repair.
