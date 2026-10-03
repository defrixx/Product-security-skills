# Cleanup acceptance conditions

These stable IDs define required workflow outcomes for this skill, not a corporate policy or a promise of complete detection. Assess each applicable condition separately. Record static inspection, executed observations, and assumptions in separate report columns. A described test is a plan until executed; a successful synthetic fixture proves only that fixture. Unknown coverage is not N/A. Exceptions or requested deviations require scope, rationale, compensating measures, owner, and review date; they do not convert a failed check into a pass.

Examples below use synthetic data. Implementation details and supported versions are defined by the local [helper contract](helper-contract.md), [detection policy](detection-and-replacement.md), and [image contract](image-metadata.md); these are the authoritative sources for the bundled helper, not external certification claims.

## CLEAN-001 — Preserve the agreed source and output boundary

- **Apply when:** any scan or replacement run is prepared.
- **Required / prohibited:** preserve source data by default and create output outside the source tree in a fresh destination. Do not overwrite an existing output or treat an ambiguous root as authorization to scan adjacent data.
- **Rationale:** cleanup must not destroy originals or recursively process its own output.
- **Implement:** resolve source/output paths before processing; use scan-only or clean-copy per the helper contract. In-place requests require a verified recovery mechanism and separate implementation because the bundled helper does not supply that mode.
- **Unsafe → corrected:** write replacements over the input folder → create a disjoint clean copy and record preservation checks.
- **Positive check:** clean-copy emits sanitized supported files while original bytes and layout remain unchanged.
- **Negative check:** an existing or overlapping destination is rejected before writes; scan-only produces no source changes.
- **Evidence:** path/mode inspection; executed before/after source comparison and destination tests. A configured copy mode alone is not preservation evidence.
- **Bounds / sources:** helper contract, modes and path constraints. State which metadata was compared; content hashes alone do not establish all filesystem metadata preservation.

## CLEAN-002 — Confine reads and writes to ordinary authorized files

- **Apply when:** inventory or processing encounters filesystem entries and path-bearing metadata.
- **Required / prohibited:** do not follow links into other data or emit links that expose originals. Reject unsupported special entries and unsafe path changes instead of silently reading or copying them.
- **Rationale:** a benign-looking tree can redirect operations outside the approved scope.
- **Implement:** use the helper's no-follow traversal and file-type checks; keep temporary/output files outside input. Inspect any alternative tool for equivalent behavior before execution.
- **Unsafe → corrected:** recursively follow a source symlink → omit the link with an opaque ID and reason.
- **Positive check:** an ordinary nested supported file is processed within the declared root.
- **Negative check:** symlink, hardlink, and special-file fixtures do not expose outside sentinel content or alter outside files; report omissions safely.
- **Evidence:** traversal/open implementation inspection; executed sentinel and race/error tests where supported. A path-prefix string check is insufficient.
- **Bounds / sources:** helper contract, filesystem restrictions. Platform support and mutable parent-directory assumptions must be recorded.

## CLEAN-003 — Apply the declared classification and replacement policy

- **Apply when:** detectors identify candidate sensitive values or policy-defined fields.
- **Required / prohibited:** distinguish matches from confirmed leaks, apply the selected sensitivity policy consistently, and scope exclusions narrowly. Do not validate credentials by contacting their services.
- **Rationale:** broad replacements corrupt benign data, while broad suppressions conceal sensitive values.
- **Implement:** use contextual field/value rules and opaque value identities per the detection policy. Include benign lookalikes and seeded sensitive fields in verification. Keep reversible mappings private if required at all.
- **Unsafe → corrected:** suppress every value in a field because one fixture was harmless → suppress only the reviewed field/value pair supported by the format and policy.
- **Positive check:** repeated synthetic values receive consistent replacements while approved benign examples retain their intended meaning.
- **Negative check:** a different sensitive value in the same field is still replaced; generated markers are not recursively transformed or confused with pre-existing marker text.
- **Evidence:** detector/policy and suppression inspection; executed labeled-fixture results, including misses and false positives. Same-detector rescanning cannot establish complete personal-data discovery.
- **Bounds / sources:** detection policy and helper contract. Contextual names, free text, encodings, and unsupported formats remain explicitly bounded; do not claim universal PII recall.

## CLEAN-004 — Account for every unsupported or failed item

- **Apply when:** files exceed limits, fail parsing, use unsupported formats, or retain unresolved sensitivity.
- **Required / prohibited:** omit them from a purported cleaned copy and identify the required next action. Explicitly requested retention makes the copy partial/restricted; absence of detector matches cannot override a processing failure.
- **Rationale:** unnoticed pass-through can publish exactly the data cleanup was meant to remove.
- **Implement:** track inventoried, processed, emitted, omitted, and failed items with safe IDs; validate structured output using the supported parser without executing project code.
- **Unsafe → corrected:** copy a malformed JSON file unchanged → omit it and report the parse failure without its contents.
- **Positive check:** valid supported input produces parseable output with the documented replacement behavior.
- **Negative check:** malformed, oversized, or unsupported fixtures are omitted and counted; interrupted work is not reported as a completed clean copy.
- **Evidence:** format dispatch/error paths and accounting inspection; executed failures with output-tree and report checks. Syntax validity does not prove application compatibility. Where the intended deliverable needs linked identifiers or files, check that in-scope references still resolve, distinct entities remain distinct, and repeated identities agree. Preserve reference relationships using supported encodings.
- **Bounds / sources:** helper contract, format/size limits and completion state. Excluded subtrees need explicit scope accounting, not invented per-file scan counts.

## CLEAN-005 — Limit binary cleanup to selected JPEG/PNG metadata

- **Apply when:** the user selects the bundled image-metadata-only mode.
- **Required / prohibited:** remove only metadata covered by the image contract while preserving encoded image data; omit unsupported variants and all other formats. Do not claim visible personal data was removed.
- **Rationale:** metadata removal and image-content redaction are different operations.
- **Implement:** use the dedicated mode and its structural checks; inspect accepted markers/chunks and declared limits. Keep source images intact and report presentation implications of removed orientation/color metadata.
- **Unsafe → corrected:** label an image fully anonymized after removing EXIF → report metadata removal only and explicitly leave visible content outside coverage.
- **Positive check:** supported synthetic JPEG/PNG files lose targeted metadata while the contract's retained encoded data remains unchanged.
- **Negative check:** malformed or unsupported image variants and a non-image binary are omitted; no general binary rewrite occurs.
- **Evidence:** parser/retention rules and source/output comparison; executed metadata checks and, when used, independent decoder observations. Structural acceptance alone does not prove every decoder accepts the output.
- **Bounds / sources:** image contract. No OCR, pixel redaction, PDF/document/archive cleanup, or broad binary sanitization is included.

## CLEAN-006 — Deliver evidence without redisclosing sensitive data

- **Apply when:** console output, inventories, reports, or attachments are produced.
- **Required / prohibited:** report safe location, category, action, and verification without original values or sensitive paths. Separate proposed scan-only replacements from executed replacements and residual uncertainty.
- **Rationale:** a cleanup report can become another disclosure channel or falsely certify incomplete work.
- **Implement:** use opaque file/finding IDs and the report template; inspect all selected attachments. Keep raw matches and private indexes out of ordinary delivery, and preserve the helper's machine output alongside the narrative.
- **Unsafe → corrected:** include before/after secrets in the report → include category, opaque location, replacement type, and observed verification result only.
- **Positive check:** a reader can locate the sanitized output and understand actions, omissions, and remaining work from the redacted report.
- **Negative check:** synthetic canaries in values, filenames, and error messages are absent from emitted reports/logs; unresolved and failed checks prevent an unqualified completion claim.
- **Evidence:** report/exception formatting inspection; executed canary search across every emitted surface and accounting reconciliation. Unreadable attachments remain uninspected.
- **Bounds / sources:** helper contract and detection policy, reporting rules. Cleaning a copy does not revoke credentials or sanitize history, backups, or already shared material.
