# Sensitive data cleanup report

Template: replace bracketed prompts with actual evidence; keep unknowns explicit. Start with the outcome and sharing limitations. For a large inventory, include a category summary here and link one complete redacted inventory instead of duplicating every row.

## Result

[What was scanned or replaced, where the final output is, and what remains unresolved. Do not describe scan-only proposals as completed replacements or claim universal safety for sharing.]

| Measure | Result |
| --- | --- |
| Mode / completion | [scan-only or clean-copy / completed within declared coverage, partial, or not performed] |
| Files | [inventoried; checked; emitted; changed; omitted] |
| Replacements | [actual occurrences; proposed occurrences separately for scan-only] |
| Remaining work | [omissions, unknowns, and next action] |


## Action ledger

Use one row per finding or unresolved action; preserve upstream IDs and aliases. For a combined workflow, carry these rows forward and link detailed evidence rather than silently replacing earlier assessments. Use safe paths/identifiers; never include original sensitive values. Omit the table only when there are no findings or outstanding actions, and say so explicitly.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [bounded observation; detail link] | [what changed or is proposed] | [proposed / candidate / applied / unchanged / unknown; target] | [check and actual observation; fixed / partial / not fixed / inconclusive where relevant] | [unresolved path, check or decision] |

Applied means observed in the named target or output copy; it does not mean verified or deployed. Record not run checks explicitly. Keep historical severity, evidence confidence and current fix verdict separate in the detailed finding.

## Scope and accounting

- Status: [scan-only / completed within declared coverage / partial / not performed]
- Source: [safe alias, not a sensitive original path]
- Output: [final sanitized path, or no replacements performed; identify superseded trials]
- Replacement policy: [which sensitivity classes are replaced; whether runnable formats are required]
- Mode and time: [values]
- Tools and versions: [actual tools; detector configuration]
- Coverage: [formats, hidden files, metadata, archives, binary files, Git history]
- Limits and exclusions: [file size, expansion, depth, excluded areas]
- Source preservation: [method and result]
- File counts: [inventoried / checked / skipped / failed; changed / emitted / omitted]
- Classification counts: [sensitive / synthetic or default / benign / unresolved occurrences; unique values separately]
- Action counts: [candidates / rejected candidates / replaced / residual occurrences; replacements are not a leak count]
- Excluded subtrees: [safe identifiers and reasons; not included as individually checked files]
- Location convention: [source coordinates under opaque file IDs / output coordinates]

## Acceptance evidence

| Condition ID | Applicability | Static evidence | Executed check and observation | Assumptions / gaps | Status |
| --- | --- | --- | --- | --- | --- |

[Use CLEAN-001 through CLEAN-006 as applicable. Missing evidence remains not verified; mixed results remain partial. Do not infer complete detection from a clean rescan.]

## Replacement inventory

| Finding ID | File ID and sanitized location | Category and classification | Basis without original value | Replacement or action | Verification |
| --- | --- | --- | --- | --- | --- |

## Rescan and format validation

[Checks actually performed, results, remaining candidates, and reasons for unavailable checks. Distinguish same-detector rescan, independent checks, syntax validation, and semantic compatibility; do not infer completeness.]

## Rejected candidates and exclusions

[Safe location, reviewed field/context, reason, and narrowly scoped exclusion. No original values.]

## Omissions and errors

[Safe file IDs, reasons, disposition, and impact. Identify any unprocessed material explicitly retained in a restricted partial copy.]

## Follow-up

[Unresolved decisions, credential rotation/revocation needs, broken references, and separately scoped history/backup cleanup.]

Original sensitive values and reversible maps must not appear here. No matches is not proof of complete removal; this report covers only the declared formats and checks.

## Deliverables

[Link this report, the final redacted inventory if separate, and the final cleaned copy when cleanup was requested. State whether the copy is partial and identify omitted files by safe IDs. Do not attach superseded copies, raw matches, reversible maps, or private source-path indexes. Keep machine-generated output intact; write this narrative alongside it, not over it.]

Name the exact final content directory, not just the run directory. In scan-only mode state that no cleaned copy exists. For helper output, adapt this illustrative tree using sanitized names and only files actually present:

```text
selected-run/
  files/             Final cleaned content; coverage limitations still apply
  report.json        Machine-generated redacted inventory
  cleanup-report.md  Narrative report, if saved here
```

The helper creates `report.json` and, for clean-copy mode, `files/`; the narrative is written separately. Select attachments explicitly rather than handing over the whole working directory. A `RUNNING` marker indicates incomplete output that must not be delivered as a completed result.
