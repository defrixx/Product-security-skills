# Synthetic regression corpus

These tests exercise actual helper behavior and small explicitly vulnerable/control fixtures. They do not import external applications or operate on a user repository. All writes and intentionally unsafe path probes use disposable temporary directories. The only Git commits/checkouts are inside repositories created by the tests.

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/run_regressions.py --output artifacts/new-regression-run
```

Requirements: Python 3.9+, Git, and a POSIX filesystem with no-follow/descriptor-relative operations. No third-party Python packages, network services, Docker, or installed skills are needed. The reporting runner requires a new output path and records source fingerprints, tool/runtime versions, per-test outcomes, exact synthetic base/head/merge-base IDs, and a completed PR review exercise.

## Scenarios and observable expectations

| Family | Task | Expected evidence |
| --- | --- | --- |
| Cleanup classification | Retain a reviewed UI label while redacting a credential in the same JSON file | Exact field suppression; changed suppression value is rejected; adjacent secret still redacted |
| Cleanup preservation | Process repeated/overlapping values, hidden files, and structured data | Consistent distinct replacements, unchanged input bytes, valid JSON/CSV, no originals in reports |
| Cleanup boundaries | Supply links, a FIFO, malformed input, oversized files, collisions, and failing writes | No out-of-root reads/writes through links; omitted unsafe files; explicit incomplete/partial status |
| PR provenance | Review a branch after the target advances independently | Merge-base-to-head changes exclude the target-only commit; exact revisions recorded |
| PR classification | Compare vulnerable legacy/new queries and a parameterized control | New flaw reproduced only on head; legacy flaw reproduced before and after; safe query remains effective |
| PR unavailable context | Remove a requested revision or provide dirty/untracked content | No silent fallback, no checkout, working tree unchanged |
| Archive metadata | Import a safe ZIP member with an unsafe manifest filename | Vulnerable fixture writes outside storage; fixed control rejects before write and preserves valid import |
| Packaging | Copy each executable skill outside the repository | CLI runs with no sibling skill or test dependency |

The cleanup scoring fixture has three labeled sensitive fields and three benign controls. The runner records true/false positives and negatives only for that fixture; it does not estimate real-world recall. A passed archive reproduction test demonstrates the anti-example's vulnerability, not a secure control. Both vulnerable and fixed cases are labeled in the fixture source.

The PR exercise uses the review skill's required scope, threat model, provenance, evidence, counterevidence, and remediation fields. Expected results are intentionally known to the evaluator. This is a reproducible workflow exercise, not independent agent behavior scoring. Full FastAPI/React/Next.js/Docker integration and arbitrary PII/binary detection remain outside this suite.

## Optional integration suite and personal-data coverage

[Framework integration checks](integration/README.md) run separately with Docker and pinned dependencies; they are not part of the dependency-free suite above. They exercise five Python integration cases, three Next.js/browser control groups, and four Compose/BuildKit control groups on synthetic applications.

`test_personal_data.py` covers sixteen explicit personal-field aliases, ambiguous-field negative controls, numeric-identifier omission, CSV detection, and an explicit natural-language coverage limit. Field-context coverage is not a measurement of universal personal-data detection.

JPEG/PNG metadata-only regressions use synthetic container fixtures in `test_image_metadata.py`. `fixtures/synthetic-jpeg.json` stores tiny generated images as base64, without real photographs or personal metadata. Independent decoder checks run separately with `python3 tests/integration/images/checks.py` (Pillow 11.3.0 was used); runtime cleanup remains standard-library-only.
