# Fix verification report

Template: replace prompts with actual evidence; omit empty optional sections. Do not copy instructional examples into the final result.

## Result and next actions

| Finding / origin | Verdict | Candidate or applied | Target revision / snapshot | Confidence | Next action |
| --- | --- | --- | --- | --- | --- |

[Verdicts: fixed / partially_fixed / not_fixed / inconclusive. Keep inconclusive findings visible.]


## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Scope and provenance

[Task, date, selected findings, original and patched revisions, dirty state/included changes, source report references, skill fingerprint, tools/versions, permitted operations, assumptions, exclusions. State self-verification when applicable.]

## Finding evidence

### [Finding ID and title]

- Origin / aliases: [stable references]
- Historical assessment / severity: [status and rationale at original revision]
- Root cause and change: [entry, attacker control, guards, operation, impact, changed mechanism]
- Affected paths: [each path and distinct guard]
- State and evidence dependencies: [relevant policy/configuration, versions and setup; effective transition boundary; changed dependencies and cases rerun, when applicable]

| Case / path | Expected | Original observation | Patched observation | Evidence kind / reference | Next action |
| --- | --- | --- | --- | --- | --- |
| [original failure / bypass / allowed behavior; state sequence or crash boundary when relevant] | [property] | [recorded result] | [actual result] | [static / execution / extracted / mock] | [specific action] |

[Explain the verdict, any contradictory evidence, and the next decisive check. Distinguish deployment behavior from code evidence.]


## Attachments and handoff

[Selected redacted evidence and optional verification.json; preserve prior assessments and originals. No raw logs/private indexes by default.]

## Short inline example

Illustrative synthetic result: F-007, partially_fixed, candidate patch at snapshot B. Direct unauthorized read is denied and owner read works; the previously affected export path still discloses the synthetic record. Confidence: high for the recorded cases. Next: repair and recheck the export path. Historical vulnerability remains confirmed at snapshot A.
