# Prompt integrity integration report

Template: fill from the application's actual call sites and observed attempts.

## Result

[Protected routes, known bypasses, decision and next action. State that request integrity does not establish semantic prompt-injection resistance or model obedience.]

## Release and scope

[Application revision and working-tree state; package/runtime versions; baseline profile/version and privately recorded digest reference; trusted configuration owner; endpoint mapping; deployment or synthetic environment; excluded routes. Do not embed prompt contents or private configuration.]

## Call coverage

| Entry / job | Primary / retry / fallback | Checked boundary | Wire observation / rejection evidence | Gaps |
| --- | --- | --- | --- | --- |
| [call site] | [attempt] | [actual wrapper and adapter] | [check ID; result at revision] | [unverified route or none within stated scope] |

## Action ledger

| ID | Observed issue | Change / next action | Implementation state | Verification and revision | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [bounded finding] | [change or proposal] | [proposed / candidate / applied / unchanged / unknown; target] | [check, outcome, revision] | [residual risk / next decisive check] |

## Failure and release checks

[Initial send, retry and fallback tamper rejection; legitimate data accepted; unavailable endpoint; timeout; redirect; oversized response; same-version baseline tampering; rotation; rollback selection; frozen running policy; missing/invalid release configuration. Record not run checks and bounded diagnostic codes without raw payloads.]

## Limits and handoff

[Keep historical findings and IDs. Applied wiring is not proof that every dynamic caller uses it. Record separate application authorization, model-output and semantic-injection controls as untested unless actually assessed. Link only selected redacted evidence.]
