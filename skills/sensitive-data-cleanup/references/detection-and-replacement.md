# Detection and replacement

## Coverage and classification

| Category | Inspect locally | Replacement in the output copy |
| --- | --- | --- |
| IPv4/IPv6, DNS, URLs, infrastructure | Address fields, connection strings, hostnames, account/tenant IDs, environment labels, paths | Consistent inert labels or format-compatible documentation values |
| Credentials and tokens | Password fields, authorization headers, cookies, configuration, environment files, encoded credential containers | Explicit nonfunctional marker; preserve surrounding structure |
| Keys and certificates | PEM blocks, private keys, bundles, keystores, X.509 subject/SAN metadata | Remove the material or substitute an explicitly synthetic fixture if valid structure is essential |
| Personal data | Names, contacts, identifiers, free text, and combinations of attributes | Consistent fictitious values or field removal |
| Other internal information | Organization names, comments, filenames, document properties, embedded content | Generic description appropriate to the requested sharing purpose |

An IP address is not automatically confidential. A public certificate is not a private key, but its fields may identify internal infrastructure or people. Do not treat every high-entropy string as a credential or restrict detection to private IPv4 ranges. Use format-aware parsers where available; inspect context for unstructured personal and organizational information. Do not promise exhaustive PII recognition.

Choose supported formats explicitly. Text, JSON, YAML, XML, CSV, notebooks, PDFs, office files, images/OCR, archives, and encrypted/binary formats have different requirements. A text scan does not cover embedded objects, comments/properties in binary containers, or image pixels. Declare limits on file bytes, records, archive depth, expanded bytes, and compression ratio before processing. Unsupported, oversized, encrypted, and malformed files are skipped with a reason, never marked clean.

## Context decisions and false positives

Before replacement, distinguish a sensitive value from a UI label, variable name, synthetic fixture, documented default, or operational constant. A field named `apiKey` in a locale dictionary can be a display label. A private address in a test can be synthetic. Defaults can still be usable credentials; do not dismiss them solely because they appear in documentation.

Record the classification, confidence, and chosen action without the value. Treat sensitivity classification and replacement as separate decisions: a sharing policy may require replacing synthetic infrastructure examples too, but those replacements are not evidence of live leaks. Preserve local exposure controls such as loopback binding unless the requested policy requires changing them; document any resulting loss of functionality.

Scope false-positive exclusions to the reviewed field/context and record their reason. Do not exempt an entire file or all credentials merely because one UI label was benign. A future real secret in the same file must remain detectable. Use both benign lookalikes and seeded sensitive values when checking a detector change.

An inert marker inside a string can parse successfully while breaking an IP validator, connection URI, cross-file reference, or test. Use format-compatible synthetic values when required, or specify a reading-only output contract.

## Safe local processing

- Assign opaque file IDs before exposing paths; sanitize filenames and error messages in inventory and reports.
- Use fresh restrictive-permission output and scratch directories outside the resolved source tree. Ensure they are not ancestors of the source either. Do not hardlink originals into the destination.
- Do not traverse directory symlinks, symlink files, special device files, or links introduced during traversal. Avoid following archive links; reject absolute and escaping archive entries. Work from a stable source snapshot when concurrent changes are possible.
- Inventory `.git` explicitly and exclude it from shareable copies by default. Ignore rules are not sensitivity rules: `.env` and other hidden files need coverage. Do not silently skip files solely because Git ignores them.
- Keep raw matches, replacement maps, parser errors, and tool logs local and protected. Configure scanner redaction before execution; never first print raw matches and then redact the conversation.
- Do not execute macros, source code, deserialization hooks, or unknown project scripts. Network lookups, DNS resolution, external scanning, and credential testing are outside this local workflow.

## Replacement invariants

Use a single mapping per run and semantic category: repeated values get consistent replacements; distinct values must not accidentally collapse. Opaque counters are sufficient for reports; bare hashes of original values can disclose low-entropy data. Cross-category representations need explicit coordination when they refer to one entity. For a linked deliverable, compare the declared entity/reference relationships before and after cleanup, using private synthetic or opaque identities. Verify each emitted reference against emitted targets and retain distinctness; do not execute the cleaned project to infer compatibility. Plain repeated-value consistency does not cover encoded references, signatures, renamed paths or omitted files.

Plan replacements against the original parsed values or spans, resolving overlaps before writing. Do not repeatedly run global substitutions over already replaced text. Preserve field types and escaping. A redacted credential can intentionally be nonfunctional; do not claim the application will still run.

When format permits, use inert labels such as `REDACTED_TOKEN_001` or `HOST_001`. If actual address/email syntax is required, verify appropriate documentation-reserved values against an authoritative source for that format before use. Do not substitute an arbitrary real address or generate credentials for a live service.

Sanitize file and directory names with collision-safe deterministic names, then update in-scope references where supported. Track changes with file IDs rather than original sensitive paths. If references or signatures cannot be preserved, disclose the impact. Remove or sanitize metadata instead of copying it blindly.

Use an in-memory map by default. Persisting a reversible map requires a concrete recovery need and protected storage separate from the shareable copy and report; do not commit it. Generated synthetic private keys, if necessary for test fixtures, must be labeled test-only and never trusted by real systems.

For ambiguous candidates, use context and the user's sharing purpose. If their safe treatment cannot be determined, record them as unresolved and omit the affected file from the shareable output rather than claiming success. Scan-only reports may retain the unresolved classification.

## Verification and completion

Verify that source bytes and paths remain unchanged using local pre/post evidence without publishing sensitive inventories. Rescan the output with the original detectors and context checks; parse supported formats without executing their content. Check report paths, replacement labels, embedded metadata, and exception messages for leakage. Do not put matched values in the report even as “before” examples.

Reconcile file counts: inventoried files = checked + skipped + failed, using mutually exclusive final statuses. Track changed/emitted/omitted files separately. Track candidate, confirmed, replaced, residual, and unresolved occurrences; distinguish occurrences from unique values. State whether locations refer to source or output coordinates after structural edits. Count excluded subtrees separately from inventoried files; do not imply their descendants were scanned. Record rejected candidates and reasons separately from replacements. Mark earlier outputs superseded when rerunning into a fresh destination, and identify the final output unambiguously.

Record interruptions as partial, including which files were emitted. Do not reuse partial destinations blindly. Remove temporary raw data created by this run when no longer needed, within the agreed workspace; do not claim secure erasure of filesystem snapshots or backups.
