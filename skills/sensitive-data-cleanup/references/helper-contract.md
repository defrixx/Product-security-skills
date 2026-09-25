# Local cleanup helper contract

Use [scripts/cleanup.py](../scripts/cleanup.py) for deterministic, bounded local processing. It is part of this skill and needs only Python 3.9+ and POSIX descriptor-relative/no-follow filesystem support (tested on macOS; Windows is unsupported). It does not contact services or execute input files. The broader [detection workflow](detection-and-replacement.md) still requires contextual review.

## Invocation

Run from the copied skill directory, with an existing source and output parent. The output directory must not exist and must be disjoint from the source in both directions, including resolved aliases.

```sh
python3 scripts/cleanup.py --source /path/to/input --output /path/to/new-run --mode scan-only
python3 scripts/cleanup.py --source /path/to/input --output /path/to/new-clean-run --mode clean-copy --policy /path/to/policy.json
```

Default mode is `scan-only`. A fresh run contains `report.json` and, in clean-copy mode, `files/`. Exit codes: `0` completed within declared detector coverage; `2` partial due to skipped/failed/excluded coverage; `1` fatal/configuration error. A `RUNNING` marker means the run did not finish; never publish that output. Completed does not mean all sensitive information has been found.

Files are assigned opaque IDs in sorted, depth-first traversal order, including skipped file entries. Output filenames use those IDs and a validated format suffix. Reports never include original paths, keys, matched values, parser exception text, or suppression contents. Locations are source text line numbers, parsed JSON node ordinals, or CSV row/column ordinals. IDs refer to this input snapshot only. No original-path index or reversible replacement map is persisted; recovering original locations requires local inspection of the same scoped inventory. This favors path confidentiality over turnkey navigation.

## Formats and detectors

| Input | Handling and limits |
| --- | --- |
| `.json` | Parse before redaction; recognize sensitive field names and decoded/escaped values; preserve primitive types; reject duplicate keys, nonfinite numbers, excessive structure, or sensitive non-string values |
| `.jsonl` | Parse nonblank lines as JSON; preserve record order; JSON pointers use a zero-based physical line prefix for suppressions |
| `.csv` | Standard comma-delimited CSV with a unique header and rectangular records; field context from headers; preserve quoting/record values via the parser |
| `.txt`, `.md`, `.log`, `.env`, `.ini`, `.conf` | UTF-8 text detectors; no application/configuration semantic validation |
| Other extensions | Omitted unless explicitly added as text; never claim YAML/source-code syntax validation for that opt-in |

UTF-8 BOM is accepted; output uses UTF-8 with JSON escapes for non-ASCII characters. JSON whitespace and CSV serialization may change even without redactions. A changed-file count means redacted values, not byte-for-byte serialization changes. Binary/NUL content, invalid encodings, archives, PDFs, office documents, images, and unsupported formats are omitted. `.git`, `node_modules`, `.venv`, and `__pycache__` directory subtrees are excluded by default and counted separately.

Detectors cover named credential/personal fields, common provider-token shapes, credential assignments and URL userinfo, complete PEM private-key/certificate blocks, email addresses, IP literals, selected internal hostname suffixes, and exact user-specified sensitive values. They are deliberately finite. Arbitrary natural-language names, all identifier formats, encoded secrets, all IPv6 representations, and binary metadata are not covered. A match is a policy-selected candidate, not a live-credential finding. No credential validity check is performed.

The default network policy redacts matching addresses including loopback. For a copy that should preserve operational local bindings, set `redact_network` to false and supply exact sensitive infrastructure values as needed. This changes detector coverage and must be explained in the report narrative. Replacement markers are inert strings, not necessarily valid IPs, credentials, or executable configuration. The copy is for inspection/sharing review, not guaranteed execution.

## Policy

Start with [the policy template](../assets/cleanup-policy.json). Unknown properties and malformed policies fail closed. Treat a policy containing sensitive values as private; do not commit it or include it in reports.

- `exclude_dirs`: exact directory basenames, not file glob exclusions. Subtree omissions remain visible in coverage.
- `text_extensions`: explicit additional lowercase suffixes to process only as text.
- `redact_network`: enables/disables generic IP/internal-hostname detection.
- `sensitive_values`: exact strings, minimum four characters, for locally known internal/PII data the generic detectors cannot recognize.
- `suppressions`: JSON/JSONL string-field exclusions, each with exact relative `file`, JSON `pointer`, `expected_value`, and a nonempty `reason`. Globs and whole-file exemptions are rejected. Reasons/values never enter the report.

Example synthetic label exclusion:

```json
{
  "suppressions": [
    {
      "file": "settings.json",
      "pointer": "/labels/apiKey",
      "expected_value": "API key",
      "reason": "Reviewed interface label, not a credential"
    }
  ]
}
```

Only that exact string field is exempted; another secret in the same file remains detectable. A changed value causes file omission with `suppression_value_changed`. An unused rule makes the run partial. Suppressions are intentional retention decisions; review them before use. CSV/text suppressions are not supported.

## Safety and repeatability

Sources are opened read-only. Descriptor-relative traversal refuses symlinks, special files, and hardlinks; no archives are unpacked. Source bytes and metadata are compared immediately before/after each processed file. This is not a global snapshot: use a quiet source tree and a trusted output parent. Hostile concurrent renaming/mount changes and other processes modifying already checked files remain outside the guarantee.

Outputs use a new private directory and exclusive, no-follow writes with restrictive permissions. Original permissions, names, timestamps, and extended metadata are not copied. Same complete values receive consistent markers within a run, including across files/categories. Different values get different IDs; overlapping detections are merged before replacement. Existing reserved marker syntax causes omission to avoid collisions. The helper does not support in-place cleanup or recursively recleaning its output as though it were fresh input.

Default bounds: 2 MiB per file, 64 MiB total input read for processing, 128 MiB emitted content, 10,000 traversed entries, 10,000 findings, 10,000 structural nodes/records per file, and depth 32. Preservation rereads add I/O beyond the processing-input budget. Override a bound explicitly with the matching CLI option, such as `--max-file-bytes 1048576`, `--max-total-bytes 16777216`, `--max-output-bytes 33554432`, `--max-entries 2000`, `--max-findings 2000`, `--max-records 2000`, or `--max-depth 16`. All must be positive integers. Limit hits mean partial coverage, not clean skipped data. When a directory enumeration reaches the entry budget, that directory is not processed from an arbitrary filesystem-order prefix. Source-byte limits and structural limits also bound CSV/JSON parsing; text opt-ins do not make an unbounded parser safe.

Every emitted file is rescanned with the same detector and policy. This checks replacement mechanics, not independent detection recall. Report counts reconcile checked/skipped/failed files; excluded subtrees do not imply enumerated descendants. Scan-only findings use `proposed`; clean-copy findings use `replace`; reviewed exclusions use `suppressed`. Failed files are never emitted. Fatal interruption can leave a restricted incomplete run with `RUNNING`; use a fresh destination for retry.

## Personal-data field coverage

The detector recognizes explicit structured field names for middle names, birth dates, home/residential addresses, passport/national/social-security/taxpayer/driver-license identifiers, bank accounts/IBANs, credit-card numbers, and medical-record numbers. These are contextual string-field detections in JSON/JSONL and CSV, using case/separator normalization (for example, `dateOfBirth` and `date_of_birth`). They do not validate an identifier or establish that it belongs to a real person. Non-string sensitive fields cause omission rather than silent retention or type conversion.

Generic keys such as `name`, `address`, `id`, and `account` remain ambiguous and are not automatically classified as personal. Free-text names, postal addresses, medical narratives, unlabeled document numbers, and regional identifier variations remain outside this field-based coverage. Use reviewed exact sensitive values for known omissions. The synthetic field corpus measures only these explicit names, including benign lookalikes; it cannot establish universal PII recall.

## Optional image-only mode

`--image-metadata-only` selects the separate [JPEG/PNG metadata contract](image-metadata.md). Text and document cleanup are disabled in this mode; unsupported files are omitted, not altered or copied. Image container removal counts are separate from text replacement counts.
