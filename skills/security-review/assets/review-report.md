# Security review report

Template: fill from observed evidence. Lead with the decision-relevant result; omit empty optional sections. Summary rows link to detailed findings and do not duplicate their full text.

## Result

[One short paragraph: main risk, confirmed finding count, hypothesis count, and recommended next action.]

| Context | Value |
| --- | --- |
| Target / date | [safe identifier / assessment date] |
| Mode / revisions | [repo or PR; exact revisions and working-tree state] |
| Assessment state | [completed within scope / partial / blocked; reason] |


## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Findings at a glance

| ID | Finding | Severity | Confidence | Provenance | Next action |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [short title; link to detail] | [contextual rating] | [evidence confidence] | [introduced / pre-existing / unknown / repo: not assessed] | [specific action] |

Count confirmed findings once, including pre-existing findings. Keep hypotheses out of severity totals. In PR mode, place introduced or unknown-provenance findings in the first detailed section and existing findings in the pre-existing section.

## Scope and method

- Mode: [PR / repo]
- Repository: [safe identifier]
- Revisions: [base/head/merge base or commit and working-tree state]
- Comparison semantics: [what the diff represents, if applicable]
- Assessed components: [boundaries and entry points]
- Tools/checks: [versions, executed checks and observations]
- Evidence environment: [original code executed, extracted functions, mocks/stubs, real integrations]
- Probe outcomes: [vulnerability reproduced / control held / inconclusive; do not combine as security passes]


## Threat model

[Assets, actors, entry points, flows, trust boundaries, security invariants, assumptions. For PR: changes relative to the base.]

## Confirmed findings — repository or introduced/unknown PR issues

[If none: “No vulnerabilities were confirmed in the assessed scope.” ]

### [ID] [Title]

- Severity / remediation priority: [rating and contextual rationale]
- Confidence: [level and evidence basis]
- Location: [safe path, lines/symbol, revision]
- PR provenance: [introduced / pre-existing / unknown; base comparison evidence]
- Prerequisites and reachability: [attacker capabilities and guards]
- Evidence: [redacted static trace or local reproduction; expected and observed behavior]
- Attack and impact: [demonstrated primitive; conditional consequences and missing prerequisites separately]
- Remediation: [specific direction]
- Fix verification: [negative and positive cases, expected outcome]
- Related paths / aliases: [when grouped: affected paths, distinct guards and bypasses, per-path evidence and checks; preserve earlier finding IDs]

## Pre-existing findings in PR mode

[Use the same finding fields; separate these from introduced issues.]

## Hypotheses

| ID | Signal and location | Evidence basis | Next validation step | Confirming / disproving observation | Inconclusive stopping condition |
| --- | --- | --- | --- | --- | --- |

## Disproved signals

[Signal and verified counterevidence, where useful.]

## Possible attack chains

[Finding IDs, dependencies, and evidence status of each link. Do not imply a fully confirmed chain when links are hypotheses.]

## Remediation plan

[Risk-based order, dependencies, and acceptance criteria. No external issues or comments are created by this report alone.]

## Assessed flows

### Flow coverage

Use one row per distinct in-scope entry-to-operation path; separate paths when their guards differ. Link to safe evidence locations at the recorded revision and finding/hypothesis IDs where relevant. Label static traces, executed checks, and mocks separately. A checked protection may have failed: record its observed outcome rather than implying that inspection means it held. Retain this table even when no findings are confirmed; it describes assessed coverage at the recorded revision.

| Entry point | Sensitive operation | Protections checked and outcomes | Evidence | Next action |
| --- | --- | --- | --- | --- |
| [route, event, import, or job; actor/input] | [read, write, execution, or outbound request; asset] | [specific guard and observed result] | [static trace / executed check / mock; safe location or attachment; finding ID if any] | [specific investigation or remediation action] |


## Attachments

[List only selected redacted evidence needed for reproduction or remediation. Raw logs, whole source copies, private indexes, and exploratory scripts are working material by default. A candidate patch is optional and does not imply it was applied.]
