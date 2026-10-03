# Fix verification report

Template: replace prompts with actual evidence; omit empty optional sections. Do not copy instructional examples into the final result.

## Result and next actions

| Finding / origin | Verdict | Candidate or applied | Target revision / snapshot | Confidence | Next action |
| --- | --- | --- | --- | --- | --- |

[Main limitation first. Verdicts: fixed / partially_fixed / not_fixed / inconclusive. Keep inconclusive findings visible.]


## Action ledger

Use one row per finding or unresolved action; preserve upstream IDs and aliases. For a combined workflow, carry these rows forward and link detailed evidence rather than silently replacing earlier assessments. Use safe paths/identifiers; never include original sensitive values. Omit the table only when there are no findings or outstanding actions, and say so explicitly.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [bounded observation; detail link] | [what changed or is proposed] | [proposed / candidate / applied / unchanged / unknown; target] | [check and actual observation; fixed / partial / not fixed / inconclusive where relevant] | [unresolved path, check or decision] |

Applied means observed in the named target or output copy; it does not mean verified or deployed. Record not run checks explicitly. Keep historical severity, evidence confidence and current fix verdict separate in the detailed finding.

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
