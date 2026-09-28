# Requirement format and baseline semantics

Every requirement records:

- **ID:** stable `SD-<TOPIC>-NNN`; do not reuse retired IDs.
- **Title and status:** proposed baseline, source-checked, or policy-owner approved. Record owner and approval date for the last status.
- **Level:** MUST (proposed acceptance condition) or SHOULD (recommendation); identify the authority if an adopted policy imposes it.
- **Applicability:** language, versions, runtime, data, and exclusions.
- **Rule:** observable behavior that can be checked.
- **Rationale:** the threat the rule addresses.
- **Implementation:** an approach or supported API; options are not the only allowed implementation.
- **Verification:** procedure, expected result, and detection limitations.
- **Sources:** primary document, version/section, URL, and date checked.
- **Exceptions:** scope, justification, compensating controls, owner, and review/expiry date.

The topic status, level, and source date apply to its requirement unless overridden. Rules are an engineering synthesis of cited guidance; they do not inherit the legal or normative authority of an external standard. Requirements with multiple clauses need evidence for each applicable clause.

For an implementation report, use `ID / condition | applicability | change/evidence | verification result | exception or remaining gap`. A source review is not a behavioral test. An exception remains unresolved until the responsible owner accepts it; do not invent an approver. Use existing project exception processes when available.

For a source conflict, record both positions, their scope and versions, the selected interpretation, and the reason. Prefer protocol specifications for protocol semantics and vendor documentation for supported APIs; organizational constraints still need explicit mapping.

Use `partially verified` when evidence covers only some applicable conditions. Record whether a change is proposed, tested in an isolated copy, or applied to the target. A non-applicable control needs an applicability rationale, not a fabricated exception owner.

## Independently verifiable conditions

A topic ID identifies a group, not an indivisible pass/fail check. Conditions use stable suffixes, for example `SD-API-001.C01`. Keep each suffix attached to the same behavior; never reuse it for a different condition. A group is satisfied only when every applicable condition has sufficient evidence. Conditions without evidence remain `not verified`; mixed results remain `partially verified`. Do not average results into a passing score.

Each condition specifies:

1. **Apply when:** recognizable code, configuration, or architecture triggers and relevant exclusions.
2. **Required / prohibited:** one security property and the shortcuts that would violate it. Add **Rationale** identifying the concrete threat addressed.
3. **Implement:** concrete approaches; refer to a matching stack profile for API-specific details.
4. **Unsafe → corrected:** a short synthetic example, explicitly labeled as illustrative rather than production-ready code.
5. **Positive check:** allowed behavior and its expected observable result.
6. **Negative check:** rejected or adversarial behavior and its expected result, including absence of unauthorized side effects.
7. **Evidence:** static locations and data-flow argument; executed test setup and observations; unresolved assumptions. Static evidence can establish a visible implementation property but cannot substitute for claims about an unexecuted runtime.
8. **Bounds / sources:** versions, unsupported contexts, exceptions, and the primary-source section supporting the condition. Topic-level sources may be referenced by their local labels.

Report one row per condition: `condition ID | applicability rationale | implementation location | static evidence | executed check and observation | assumptions/gaps | status`. A described test is a verification plan until actually executed. A synthetic fixture proves only the exercised property in that fixture. Unknown applicability requires investigation, not an N/A result.

Common exception procedure: record the unmet condition ID, scope, rationale, compensating controls, owner, and review date. An exception does not turn a failing technical check into a pass. Stack profiles refine the condition's implementation; they do not create an alternative weaker acceptance criterion.

## Source-to-claim and mapping discipline

For each new or changed normative clause, identify the primary source section supporting its security property and label additional project synthesis. Record the document revision or vendor release, URL, actual verification date, and any unverified target compatibility. A source's page selector is not evidence of a tested runtime version. Recheck when the clause or target version changes; do not refresh dates without examining the relevant text.

Where source recommendations differ, record both scopes and the selected interpretation alongside the condition. Deployment preference, protocol implementation obligations, and regulated assurance profiles are not interchangeable. An implementation option is not the only compliant design. Required privileges permitted by the rule are normal applicability, while deliberately unmet restrictions need exceptions.

Stack **Condition mapping** fields are authoritative. Spell out every mapped condition ID; remove redundant parent metadata rather than maintaining competing classifications. Each mapped property needs its own evidence; a profile label cannot pass the entire parent topic. Keep historical condition IDs stable when clarifying scope; allocate a new ID for a distinct property and document migration rather than reusing a retired ID.
