# Sensitive data cleanup report

Template: replace bracketed prompts with actual evidence; use observed results. Start with the outcome and next actions. For a large inventory, include a category summary here and link one complete redacted inventory instead of duplicating every row.

## Result

[What was scanned or replaced, where the final output is, and the next action. Do not describe scan-only proposals as completed replacements or claim universal safety for sharing.]

| Measure | Result |
| --- | --- |
| Mode / completion | [scan-only or clean-copy / completed within declared coverage, partial, or not performed] |
| Files | [inventoried; checked; emitted; changed; omitted] |
| Replacements | [actual occurrences; proposed occurrences separately for scan-only] |
| Next action | [specific action and owner] |


## Action ledger

Carry stable finding IDs through the workflow and record the observed change, verification result and next action.

| ID | Observed issue | Change / next action | Implementation state | Verification and exact revision / copy | Next check |
| --- | --- | --- | --- | --- | --- |
| [stable ID] | [observation and detail reference] | [change or action] | [actual target state] | [check, result and revision/copy] | [specific action] |


## Scope and accounting

- Status: [scan-only / completed within declared coverage / partial / not performed]
- Source: [safe alias, not a sensitive original path]
- Output: [final sanitized path, or no replacements performed; identify superseded trials]
- Replacement policy: [which sensitivity classes are replaced; whether runnable formats are required]
- Mode and time: [values]
- Tools and versions: [actual tools; detector configuration]
- Coverage: [formats, hidden files, metadata, archives, binary files, Git history]
- Source preservation: [method and result]
- File counts: [inventoried / checked / skipped / failed; changed / emitted / omitted]
- Classification counts: [sensitive / synthetic or default / benign / unresolved occurrences; unique values separately]
- Action counts: [candidates / rejected candidates / replaced / residual occurrences; replacements are not a leak count]
- Location convention: [source coordinates under opaque file IDs / output coordinates]


## Replacement inventory

| Finding ID | File ID and sanitized location | Category and classification | Basis without original value | Replacement or action | Verification |
| --- | --- | --- | --- | --- | --- |

## Rescan and format validation

[Checks performed, results and selected follow-up actions. Distinguish same-detector rescan, independent checks, syntax validation, and semantic compatibility. For linked deliverables, record checked entity/reference relationships, missing referents and unsupported encodings separately; do not infer completeness.]

## Rejected candidates and exclusions

[Safe location, reviewed field/context, reason, and narrowly scoped exclusion. No original values.]

## Actions requiring attention

[Safe file IDs, reasons, disposition, and impact. Identify any unprocessed material explicitly retained in a restricted partial copy.]

## Follow-up

[Unresolved decisions, credential rotation/revocation needs, broken references, and separately scoped history/backup cleanup.]

Original sensitive values and reversible maps must not appear here.

## Deliverables

[Link this report, the final redacted inventory if separate, and the final cleaned copy when cleanup was requested. State whether the copy is partial and identify omitted files by safe IDs. Do not attach superseded copies, raw matches, reversible maps, or private source-path indexes. Keep machine-generated output intact; write this narrative alongside it, not over it.]

Name the exact final content directory, not just the run directory. In scan-only mode state that no cleaned copy exists. For helper output, adapt this illustrative tree using sanitized names and only files actually present:

```text
selected-run/
  files/             Final cleaned content
  report.json        Machine-generated redacted inventory
  cleanup-report.md  Narrative report, if saved here
```

The helper creates `report.json` and, for clean-copy mode, `files/`; the narrative is written separately. Select attachments explicitly rather than handing over the whole working directory. A `RUNNING` marker indicates incomplete output that must not be delivered as a completed result.
