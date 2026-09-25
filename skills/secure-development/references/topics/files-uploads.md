# Files and uploads

## SD-FILES-001

Status: proposed baseline; C01–C05 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for exceptions and evidence. Select controls against actual filesystem, parser, and serving behavior. Examples use synthetic paths and content.

### SD-FILES-001.C01 — Constrain every path-bearing input

- **Apply when:** a supplied name, archive entry, manifest field, or identifier influences a filesystem read, write, or deletion.
- **Required / prohibited:** restrict operations to the intended storage boundary. Do not assume that validating archive members also validates an independent manifest filename, or that joining a root with a supplied path proves containment.
- **Rationale:** Independent filename sources can escape an otherwise validated storage boundary.
- **Implement:** prefer generated storage names with display names kept separately. If names must be retained, validate the final decoded name and enforce the root boundary with platform-appropriate filesystem operations. See [Python import paths](../stacks/python-fastapi.md).
- **Unsafe → corrected:** `open(root / manifest.file_name, 'wb')` after only ZIP member validation → validate the manifest name independently and write using a constrained storage operation.
- **Positive check:** a valid supported filename is stored/read at the intended location.
- **Negative check:** absolute paths, traversal, platform separators, invalid types, and symlink escape cannot touch outside sentinels. Include parent-directory links or races if an attacker can mutate the tree.
- **Evidence:** trace every path origin to use; execute filesystem tests with outside sentinels in disposable directories. String checks alone do not prove race resistance.
- **Bounds / sources:** S1, Filename Safety and Storage Location. POSIX no-follow behavior does not establish Windows reparse-point safety. The threat model must state who can modify parent directories.

### SD-FILES-001.C02 — Prevent unintended overwrite and unsafe publication

- **Apply when:** uploads, temporary files, or imports create files or replace existing content.
- **Required / prohibited:** create or replace only the intended target under the operation's authorization policy; do not expose partially validated content or silently overwrite an unrelated file.
- **Rationale:** Unsafe publication can replace existing files or expose incomplete results.
- **Implement:** use private staging, exclusive creation where replacement is not intended, and a documented publication/cleanup strategy. Treat database rollback and filesystem cleanup as separate mechanisms.
- **Unsafe → corrected:** write to final storage, then validate and rely on database rollback → validate in bounded private staging and publish only after acceptance, with explicit failure cleanup.
- **Positive check:** a valid upload publishes exactly the intended content; authorized replacement follows its documented semantics.
- **Negative check:** a colliding name, validation failure, or injected post-write failure preserves unrelated files and leaves no publicly accessible partial object. Verify cleanup rather than merely observing an error response.
- **Evidence:** inspect create/replace flags and publication order; run collision/failure tests with before/after file and database state.
- **Bounds / sources:** S1, Malicious Files, Storage Location, and Filesystem Permissions. No universal atomicity across database and filesystem is assumed; document compensating cleanup and residual states.

### SD-FILES-001.C03 — Accept only the intended file formats

- **Apply when:** uploaded bytes are parsed, transformed, indexed, or rendered as a particular format.
- **Required / prohibited:** establish an allowed format using bounded content validation appropriate to the consumer. Do not trust only the filename extension, declared MIME type, or a magic prefix.
- **Rationale:** A misleading filename or MIME declaration can select unsafe processing.
- **Implement:** define accepted formats and parser versions, reject mismatches and malformed structures, and quarantine unsupported content rather than sending it to an arbitrary fallback parser. Additional malware scanning or reconstruction depends on the product's risk and available capability.
- **Unsafe → corrected:** a `.png` suffix selects a parser without inspecting bytes → validate the supported PNG structure under limits before the intended processing step.
- **Positive check:** valid representative files for each supported format are accepted and remain usable by the intended consumer.
- **Negative check:** mismatched MIME/suffix, double extensions, truncated content, and unsupported active formats are rejected or quarantined without publication or fallback execution.
- **Evidence:** parser-selection and validation trace; actual consumer tests for accepted/rejected fixtures. Header checks establish only a header property, not full decodability or malware absence.
- **Bounds / sources:** S1, Extension, Content-Type, Signature, and Content Validation. Record scanner/parser failures as incomplete checks; do not claim complete malicious-file detection.

### SD-FILES-001.C04 — Bound upload and expansion work

- **Apply when:** a stream, archive, image, document, or batch can consume storage, memory, CPU, or parser work.
- **Required / prohibited:** enforce explicit budgets on actual consumption at the relevant stage. Do not trust advertised content length or compressed size as the only bound.
- **Rationale:** Small compressed or multipart inputs can consume disproportionate resources.
- **Implement:** limit streamed bytes, expanded bytes, entries, nesting, dimensions, and processing duration as applicable. Enforce while consuming, before allocation where possible; clean partial staging after limit failure.
- **Unsafe → corrected:** permit a small ZIP based on its compressed size, then extract without limits → count actual expanded bytes and entries during constrained extraction and stop at the configured budget.
- **Positive check:** a supported input at the documented boundary completes within the budget.
- **Negative check:** exceed each selected budget independently using small synthetic fixtures; observe bounded termination and cleanup, not disk exhaustion or an unbounded parser operation.
- **Evidence:** inspect enforcement location and accounting; execute boundary tests with measured output/work. A limit configured only at the reverse proxy leaves background imports unverified.
- **Bounds / sources:** S1, Malicious Files and Upload/Download Limits. Values are workload-specific. Report each selected budget separately; one oversized-file test does not verify expansion depth or CPU limits.

### SD-FILES-001.C05 — Serve uploaded content without granting execution or access

- **Apply when:** stored content can be downloaded, previewed, or served to a browser or another interpreter.
- **Required / prohibited:** enforce the intended retrieval permission and prevent untrusted content from executing with application authority. Storage outside a web root alone does not protect a later inline preview.
- **Rationale:** Uploaded content can acquire execution privileges or expose another user’s data.
- **Implement:** use authorized object handlers, controlled content types/disposition, and an isolated serving origin or reviewed rendering path where needed. Apply [object authorization](authorization-access-control.md) and [client-web controls](client-web-security.md).
- **Unsafe → corrected:** return user HTML inline from the authenticated application's origin → deliver it as a controlled download or through the product's appropriately isolated preview mechanism.
- **Positive check:** an authorized user obtains the intended file or safe preview.
- **Negative check:** another user's identifier does not disclose content; a harmless active-content canary does not execute with application authority. Test retrieval authorization and rendering as separate observations.
- **Evidence:** inspect storage/serving configuration and handler policy; execute direct download requests and browser preview checks. Filesystem permissions alone do not prove browser isolation.
- **Bounds / sources:** S1, Public File Retrieval, Storage Location, and User Permissions. Download headers are not a universal sanitizer. Public files may intentionally allow anonymous retrieval but still require a safe execution boundary.

## Sources

- **S1:** [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — File Upload Threats; Extension/Content-Type/Signature/Content Validation; Filename Safety; Storage Location; User and Filesystem Permissions; Upload and Download Limits. Living documentation, checked 2026-09-24. Platform-specific filesystem and parser APIs require matching vendor documentation.
