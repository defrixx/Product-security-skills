# Security report triage

Template: replace prompts with actual evidence. Keep missing information explicit and omit empty optional sections.

## Result and next actions

[Unique confirmed findings, raw signals, hypotheses, unprocessed/out-of-scope counts, main limitation, prioritized next step. Zero confirmed findings is not a security guarantee.]

| Priority | Finding / origin | Assessment | Severity / rationale | Confidence | Next action |
| --- | --- | --- | --- | --- | --- |

## Scope and provenance

[Task/date; report fingerprint and safe ID; scanner/version; claimed scan revision; assessed revision/dirty state; skill fingerprint; tools; permitted operations; assumptions/exclusions; report-only or code-assisted; manual versus automated extraction.]

## Input accounting

| Run | Raw results | Confirmed | Hypothesis | Disproved | Out of scope | Unprocessed | Scan completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |

[Unknown counts remain unknown. Raw dispositions sum to known raw inputs; unique findings counted separately.]

## Findings and duplicate mapping

### [Canonical finding ID / title]

- Origin / aliases / raw result references: [identities and grouping rationale]
- Root cause and affected paths: [each path, guards, prerequisites, impact]
- Evidence: [static or executed observations, exact revision, safe references]
- Original scanner label / contextual severity / confidence: [independent fields]
- Remediation and acceptance cases: [original failure, alternate paths, allowed behavior]
- Implementation / verification: [unknown or actual state; no inferred fix]

## Hypotheses and counterevidence

| Raw result / finding | Disposition | Evidence or missing context | Next check | Confirm / disprove observation | Inconclusive stopping condition |
| --- | --- | --- | --- | --- | --- |

## Coverage and assessment checkpoints

[Unsupported formats/fields, external properties, invocation failures, source mismatch, substitutions/mocks, untested context, and safe errors. Record TRIAGE-01 through TRIAGE-06 evidence and passed/partial/not verified/not applicable with rationale.]

## Deliverables

[Selected redacted evidence and optional triage.json. Preserve raw reports privately; no source edits, scanner execution, publication, or ticket creation implied.]
