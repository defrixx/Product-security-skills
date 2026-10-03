# Security review report

Template: fill from evidence and retain explicit unknowns. Lead with the decision-relevant result; omit empty optional sections. Summary rows link to detailed findings and do not duplicate their full text.

## Result

[One short paragraph: main risk, confirmed finding count, hypothesis count, and recommended next action. No findings does not mean security is guaranteed.]

| Context | Value |
| --- | --- |
| Target / date | [safe identifier / assessment date] |
| Mode / revisions | [repo or PR; exact revisions and working-tree state] |
| Assessment state | [completed within scope / partial / blocked; reason] |
| Main limitation | [what most affects the conclusion] |


## Action ledger

Use one row per finding or unresolved action; preserve upstream IDs and aliases. For a combined workflow, carry these rows forward and link detailed evidence rather than silently replacing earlier assessments. Use safe paths/identifiers; never include original sensitive values. Omit the table only when there are no findings or outstanding actions, and say so explicitly.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [bounded observation; detail link] | [what changed or is proposed] | [proposed / candidate / applied / unchanged / unknown; target] | [check and actual observation; fixed / partial / not fixed / inconclusive where relevant] | [unresolved path, check or decision] |

Applied means observed in the named target or output copy; it does not mean verified or deployed. Record not run checks explicitly. Keep historical severity, evidence confidence and current fix verdict separate in the detailed finding.

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
- Exclusions and limitations: [including unavailable source or runtime evidence]
- Tools/checks: [versions, executed checks, checks not run and why]
- Evidence environment: [original code executed, extracted functions, mocks/stubs, real integrations]
- Probe outcomes: [vulnerability reproduced / control held / inconclusive; do not combine as security passes]

## Review acceptance evidence

| Condition ID | Applicability | Static evidence | Executed check and observation | Assumptions / gaps | Status |
| --- | --- | --- | --- | --- | --- |

[Assess REVIEW-001 through REVIEW-006. These statuses describe the review process, not target security. Missing evidence remains not verified.]

## Threat model

[Assets, actors, entry points, flows, trust boundaries, security invariants, assumptions. For PR: changes relative to the base.]

## Confirmed findings — repository or introduced/unknown PR issues

[If none: “No vulnerabilities were confirmed in the assessed scope.” This is not a guarantee of security.]

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

| ID | Signal and location | Missing evidence | Next validation step | Confirming / disproving observation | Inconclusive stopping condition |
| --- | --- | --- | --- | --- | --- |

## Disproved signals

[Signal and verified counterevidence, where useful.]

## Possible attack chains

[Finding IDs, dependencies, and evidence status of each link. Do not imply a fully confirmed chain when links are hypotheses.]

## Remediation plan

[Risk-based order, dependencies, and acceptance criteria. No external issues or comments are created by this report alone.]

## Coverage and residual uncertainty

### Flow coverage

Use one row per distinct in-scope entry-to-operation path; separate paths when their guards differ. Include identified but untraced paths with explicit gaps. Link to safe evidence locations at the recorded revision and finding/hypothesis IDs where relevant. Label static traces, executed checks, and mocks separately. A checked protection may have failed: record its observed outcome rather than implying that inspection means it held. Retain this table even when no findings are confirmed; it describes assessed coverage, not a security guarantee.

| Entry point | Sensitive operation | Protections checked and outcomes | Evidence | Gaps / untested conditions |
| --- | --- | --- | --- | --- |
| [route, event, import, or job; actor/input] | [read, write, execution, or outbound request; asset] | [specific guard and observed result, or not checked] | [static trace / executed check / mock; safe location or attachment; finding ID if any] | [untraced steps, unavailable runtime evidence, assumptions, or none identified within this path's stated scope] |

### Remaining limitations

[Examined areas, omissions, tool errors, runtime assumptions, and checks needing additional authorization or evidence.]

## Attachments

[List only selected redacted evidence needed for reproduction or remediation. Raw logs, whole source copies, private indexes, and exploratory scripts are working material by default. A candidate patch is optional and does not imply it was applied.]
