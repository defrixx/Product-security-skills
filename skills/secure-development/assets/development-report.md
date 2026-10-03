# Secure development report

Template: replace prompts with evidence. Keep the summary short; omit empty optional sections. Do not turn a small code change into a full audit.

## Short inline example

Template example using synthetic data:

> Change: applied an ownership check to the requested document-read handler.
> Conditions: SD-AUTHZ-001.C02, object authorization for the changed read handler.
> Verification: an owner can read the document; another user is rejected before content is returned. Both focused checks passed in the synthetic test environment.
> Separate observation: an unrelated export handler may need the same protection; recorded for follow-up, not changed or confirmed vulnerable here.

For a real inline result, replace the illustrative statements with actual IDs, observations, and evidence locations. Use the standalone sections below only when needed; omit this instructional example from a completed report.


## Result

[What changed, whether it was applied to the target or remains a candidate, and the next action.]

| Context | Value |
| --- | --- |
| Target and revision | [safe identifier, commit, working-tree state] |
| Task and date | [requested change; assessment date] |
| Delivery state | [applied / candidate only / guidance only] |
| Verification | [checks and recorded results] |

## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Next actions

| Priority | Action | Acceptance check | Owner |
| --- | --- | --- | --- |
| [priority] | [specific action] | [observable expected outcome] | [assigned owner or unassigned] |


## Verification

[Checks actually run, tool versions, positive/negative cases, expected versus observed results, and evidence links. Distinguish original code, extracted functions, stubs, and real integrations.]


## Attachments

[Only evidence needed to assess this change. Include a patch when it is a deliverable; identify candidate versus applied state. Keep trial scripts and raw logs in local working material unless needed for reproduction.]
