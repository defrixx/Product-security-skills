# Fix verification report

Template: replace prompts with actual evidence; omit empty optional sections. Do not copy instructional examples into the final result.

## Result and next actions

| Finding / origin | Verdict | Candidate or applied | Target revision / snapshot | Confidence | Next action |
| --- | --- | --- | --- | --- | --- |

[Main limitation first. Verdicts: fixed / partially_fixed / not_fixed / inconclusive. Keep inconclusive findings visible.]

## Scope and provenance

[Task, date, selected findings, original and patched revisions, dirty state/included changes, source report references, skill fingerprint, tools/versions, permitted operations, assumptions, exclusions. State self-verification when applicable.]

## Finding evidence

### [Finding ID and title]

- Origin / aliases: [stable references]
- Historical assessment / severity: [status and rationale at original revision]
- Root cause and change: [entry, attacker control, guards, operation, impact, changed mechanism]
- Affected paths: [each path and distinct guard]

| Case / path | Expected | Original observation | Patched observation | Evidence kind / reference | Gaps |
| --- | --- | --- | --- | --- | --- |
| [original failure / bypass / allowed behavior] | [property] | [actual result or not run] | [actual result] | [static / execution / extracted / mock] | [limits] |

[Explain the verdict, any contradictory evidence, and the next decisive check. Distinguish deployment behavior from code evidence.]

## Assessment checkpoints

| Checkpoint | Evidence | Status / limitation |
| --- | --- | --- |
| [FIX-01 through FIX-06] | [reference] | [passed / partial / not verified / not applicable with reason] |

## Attachments and handoff

[Selected redacted evidence and optional verification.json; preserve prior assessments and originals. No raw logs/private indexes by default.]

## Short inline example

Illustrative synthetic result: F-007, partially_fixed, candidate patch at snapshot B. Direct unauthorized read is denied and owner read works; the previously affected export path still discloses the synthetic record. Confidence: high for these local cases; deployed middleware not assessed. Next: repair and recheck the export path. Historical vulnerability remains confirmed at snapshot A.
