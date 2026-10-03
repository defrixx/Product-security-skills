# Security report triage

Template: replace prompts with actual evidence. Omit empty optional sections.

## Result and next actions

[Unique confirmed findings, raw signals, hypotheses, unprocessed/out-of-scope counts, prioritized next step.]

| Priority | Finding / origin | Assessment | Severity / rationale | Confidence | Next action |
| --- | --- | --- | --- | --- | --- |


## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Scope and provenance

[Task/date; report fingerprint and safe ID; scanner/version; claimed scan revision; assessed revision/dirty state; skill fingerprint; tools; permitted operations; assumptions/exclusions; report-only or code-assisted; manual versus automated extraction.]


## Findings and duplicate mapping

### [Canonical finding ID / title]

- Origin / aliases / raw result references: [identities and grouping rationale]
- Root cause and affected paths: [each path, guards, prerequisites, impact]
- Evidence: [static or executed observations, exact revision, safe references]
- Original scanner label / contextual severity / confidence: [independent fields]
- Remediation and acceptance cases: [original failure, alternate paths, allowed behavior]
- Implementation / verification: [unknown or actual state; no inferred fix]
- Prior assessment, when supplied: [same origin ID; still/newly observed, absent or unassessed; comparison scope changes; evidence for any reopened work]

## Hypotheses and counterevidence

| Raw result / finding | Disposition | Evidence or missing context | Next check | Confirm / disprove observation | Inconclusive stopping condition |
| --- | --- | --- | --- | --- | --- |


## Deliverables

[Selected redacted evidence and optional triage.json. Preserve raw reports privately; no source edits, scanner execution, publication, or ticket creation implied.]
