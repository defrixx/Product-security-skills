# Compound content and linked replacements

Load when a selected tree includes archives, office documents, PDFs, embedded objects or multiple representations of one entity. Establish a component inventory before claiming a format covered. The bundled helper processes only its [declared formats](helper-contract.md); this guide adds review procedure, not archive/Office/PDF/OCR parser support.

## Format decision

| Input | Components to account for with a suitable inspected local tool |
| --- | --- |
| Archive | Every entry, nested containers, names, comments, links, encryption and expanded-size/depth limits |
| Office container | Main content, comments, revisions/tracked deletions, properties, custom XML, embedded objects, media and previews |
| PDF | Text, annotations, metadata, attachments, form fields, layers and image content; incremental revisions can retain older bytes |
| Image | Metadata versus encoded pixels, previews and sidecars; JPEG/PNG helper mode covers only its explicit metadata contract |
| Linked text/JSON/CSV | Repeated entities, identifiers/references, filenames and supported decoded representations |

Do not extract an untrusted container until entry count, per-entry/total expanded bytes, depth and resource/time limits are selected. Inspect parser/extractor behavior: no external relationships, network fetches, macros, active content execution, absolute paths, traversal or links outside the sandbox. Use fresh private scratch outside the source; rejected/unsupported content remains omitted with an actionable reason. A parser's ability to open a file does not prove that all components were inspected.

If no appropriate safe local tool is available, account for the container as unsupported and identify the required processing step; do not rename it to text or copy it into the shareable result. Encrypted content needs explicitly authorized local decryption with keys kept out of logs. Preserving such a file on explicit request leaves a restricted partial deliverable.

## Semantic replacement plan

Maintain a private entity graph: opaque entity identity, recognized representations, emitted targets/references and selected replacement type. Equal original values retain the run's consistent mapping; distinct entities must not accidentally merge. Do not canonicalize case, Unicode, punctuation or leading zeros unless the target format's semantics justify equivalence. Decide intentionally when two representations refer to one entity.

Use non-sensitive synthetic fixtures to check: one entity repeated across JSON/CSV/text, two distinct entities, ambiguous lookalikes, reserved-marker collision, overlapping matches, renamed targets, omitted targets and supported encoded representations. Transform parsed original values/spans once; do not cascade replacements. The helper does not automatically rewrite encoded references or cross-file paths. If those relationships require preservation, select a separately inspected transformation and verify it before delivery, or report the broken relationship concretely.

## Verification

Reinventory the emitted/repacked container, parse supported components and rescan both content and metadata. Check comments, thumbnails, attachments, temporary extraction names and logs. A visible black box or changed current PDF text does not prove older bytes or hidden objects were removed; verify actual emitted content with suitable format tools. Rendering can reveal visible leaks but does not cover hidden components. Do not run the cleaned project.

Compare emitted references against emitted targets and entity distinctness using private opaque identities. Count outer files separately from contained components; reconcile checked/skipped/failed components and omitted outputs without exposing original names/values. Preserve source bytes, keep replacement maps private and deliver only selected cleaned files. Cleanup does not revoke credentials or sanitize prior copies.

These are workflow selection and evidence rules, not claims of automatic format support. Confirm version-specific parser settings against the chosen tool's primary documentation before use.

## Sources

- [Microsoft Document Inspector guidance](https://support.microsoft.com/en-us/office/remove-hidden-data-and-personal-information-by-inspecting-documents-presentations-or-workbooks-356b7b5d-77af-44fe-a07f-9aa4d085966f), hidden data, revisions, properties and embedded content; living documentation verified 2026-10-18. Inspect the selected Office format and version; the inspector does not cover every hidden representation.
- [PyMuPDF Document documentation](https://pymupdf.readthedocs.io/en/latest/document.html), saving, incremental updates and garbage collection; living documentation verified 2026-10-18. Match the selected tool/version; saving options alone do not establish complete redaction.
