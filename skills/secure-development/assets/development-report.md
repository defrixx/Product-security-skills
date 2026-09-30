# Secure development report

Template: replace prompts with evidence. Keep the summary short; omit empty optional sections. Do not turn a small code change into a full audit.

## Short inline example

Illustrative synthetic result, not evidence from an executed assessment:

> Change: applied an ownership check to the requested document-read handler.
> Conditions: SD-AUTHZ-001.C02, object authorization for the changed read handler; other entry points remain outside this check.
> Verification: an owner can read the document; another user is rejected before content is returned. Both focused checks passed in the synthetic test environment.
> Gaps: deployment middleware was not exercised; the condition remains partially verified.
> Separate observation: an unrelated export handler may need the same protection; recorded for follow-up, not changed or confirmed vulnerable here.

For a real inline result, replace the illustrative statements with actual IDs, observations, and evidence locations. Use the standalone sections below only when needed; omit this instructional example from a completed report.

## Result

[What changed, whether it was applied to the target or remains a candidate, and the main unresolved condition.]

| Context | Value |
| --- | --- |
| Target and revision | [safe identifier, commit, working-tree state] |
| Task and date | [requested change; assessment date] |
| Delivery state | [applied / candidate only / guidance only] |
| Verification | [verified conditions and important untested behavior] |

## Next actions

| Priority | Action | Acceptance check | Owner |
| --- | --- | --- | --- |
| [priority] | [specific action] | [observable expected outcome] | [assigned owner or unassigned] |

## Applied requirements

| Condition ID | Applicability | Implementation or candidate | Static evidence | Executed check and result | Assumptions / gaps | Status |
| --- | --- | --- | --- | --- | --- | --- |
| [stable condition ID] | [why relevant] | [safe location and change] | [inspected path and reasoning] | [actual setup and observation, or not run] | [unverified conditions] | [passed / failed / partially verified / not applicable / not verified] |

A passing subcondition does not pass the entire requirement. Record non-applicability with its reason; an unmet applicable condition requires an exception, not an N/A label.

## Verification and limits

[Checks actually run, tool versions, positive/negative cases, expected versus observed results, and evidence links. Distinguish original code, extracted functions, stubs, and real integrations. State what was not checked and why.]

## Exceptions and unresolved conditions

[If any: scope, rationale, compensating controls, owner, review date, and needed evidence. Do not invent owners or approval.]

## Attachments

[Only evidence needed to assess this change. Include a patch when it is a deliverable; identify candidate versus applied state. Keep trial scripts and raw logs in local working material unless needed for reproduction.]
