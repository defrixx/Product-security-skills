# Prompt integrity integration report

Template: fill from the application's actual call sites and observed attempts.

## Result

[Protected routes, known bypasses, decision and next action.]

## Release and scope

[Application revision and working-tree state; package/runtime versions; baseline profile/version and digest reference; trusted configuration owner; endpoint mapping; deployment or synthetic environment; excluded routes. Do not embed prompt contents or private configuration.]

## Call coverage

| Entry / job | Primary / retry / fallback | Checked boundary | Wire observation / rejection evidence | Next action |
| --- | --- | --- | --- | --- |
| [call site] | [attempt] | [actual wrapper and adapter] | [check ID; result at revision] | [selected follow-up action] |

## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Failure and release checks

[Initial send, retry and fallback tamper rejection; legitimate data accepted; unavailable endpoint; timeout; redirect; oversized response; same-version baseline tampering; rotation; rollback selection; frozen running policy; missing/invalid release configuration.]

## Handoff

[Keep historical findings and IDs. Carry selected application authorization, model-output and injection-control observations with their evidence references. Link only selected redacted evidence.]
