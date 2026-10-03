# Synthetic regression corpus

Evaluation-harness tests live separately in [evals/tests/](../evals/tests/). Run `python3 scripts/run_regressions.py --output artifacts/new-regression-run` for both suites, or use the command below for product tests only.

These tests exercise actual helper behavior and small explicitly vulnerable/control fixtures. They do not import external applications or operate on a user repository. All writes and intentionally unsafe path probes use disposable temporary directories. The only Git commits/checkouts are inside repositories created by the tests.

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/run_regressions.py --output artifacts/new-regression-run
```

Requirements: Python 3.11+, Git, and a POSIX filesystem with no-follow/descriptor-relative operations. The full suite includes prompt-integrity, whose supported runtime starts at Python 3.11. The suite starts disposable HTTP servers bound only to 127.0.0.1; allow local socket binding when running under a sandbox. No external network services, third-party Python packages, Docker, or installed skills are needed. The reporting runner requires a new output path and records source fingerprints, tool/runtime versions, per-test outcomes, exact synthetic base/head/merge-base IDs, and a completed PR review exercise.

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

The cleanup scoring fixture has three labeled sensitive fields and three benign controls. The runner records true/false positives and negatives for those labeled fields. A passed archive reproduction test demonstrates the anti-example's vulnerability, not a secure control. Both vulnerable and fixed cases are labeled in the fixture source.

The PR exercise uses the review skill's required scope, threat model, provenance, evidence, counterevidence, and remediation fields. Expected results are intentionally known to the evaluator. Framework integration checks have a separate runner.

## Optional integration suite and personal-data coverage

[Framework integration checks](integration/README.md) run separately with Docker and pinned dependencies; they are not part of the dependency-free suite above. They exercise five Python integration cases, six Next.js/browser control groups, seven protocol/interpreter cases, and four Compose/BuildKit control groups on synthetic applications. The separate lifecycle integration injects three failures against actual Docker resources.

`test_personal_data.py` covers sixteen explicit personal-field aliases, ambiguous-field negative controls, numeric-identifier omission, CSV detection, and an explicit natural-language coverage limit. Field-context coverage is not a measurement of universal personal-data detection.

JPEG/PNG metadata-only regressions use synthetic container fixtures in `test_image_metadata.py`. `fixtures/synthetic-jpeg.json` stores tiny generated images as base64, without real photographs or personal metadata. Independent decoder checks run separately with `python3 tests/integration/images/checks.py` (Pillow 11.3.0 was used); runtime cleanup remains standard-library-only.

## Requirements expansion evidence

Eleven cases in `test_security_boundaries.py` contrast deliberately unsafe and safe synthetic controls for outbound connections/redirects/credentials, transitions/concurrent quotas/retries, event verification/deduplication, HMAC key versions/recovery, cache hits and HTTP MCP Origin rejection. Tests use actual loopback HTTP requests, SQLite transactions and HMAC operations with injected resolver answers and identities.

[The coverage manifest](requirement_coverage.json) maps exact cases to clauses and limits. The runner expands it to all 144 condition/profile/workflow IDs in `requirement-evidence.json`, records the run path, outcomes, repository revision/working tree and source fingerprints in `summary.json`, and leaves unmapped conditions explicitly unexercised. Failed or skipped mapped cases retain their outcome; a mapping never means a condition passed. Optional integrations from earlier runs are not imported. Evidence reporter tests verify this distinction and reject unknown condition IDs or unexecuted cases.

[Manual applicability and mapping review](requirements-manual-review.md) records contrasting design decisions and unexecuted branches. The review records the decisions made during the walkthrough.

Resource cleanup regression `test_resource_cleanup.py` injects exception, timeout and SIGTERM with real local processes/ports/temp files while a separately owned scope stays intact. See [integration details](integration/README.md#failure-cleanup-and-evidence) for Docker cleanup and optional framework evidence.


## New skill and prompt integrity evidence

`test_sarif_normalizer.py` exercises bounded extraction, private output, accounting, copied-skill execution, input preservation and failure handling. `test_handoff.py` checks structural identity/status/accounting; it does not judge evidence. `test_security_workflow.py` executes the deliberately vulnerable, partially repaired, repaired, deny-all and safe object-access fixture.

Run `python3 scripts/run_security_workflow_trial.py --output artifacts/new-workflow-trial` to record fixture observations and provenance for a manually guided skill assessment. The runner emits observations for assessment. Fill the new skills' report templates from its observations and preserve upstream IDs.

`test_prompt_integrity.py` includes the standalone package tests in the repository suite. They exercise static request integrity, safe CLI/filesystem behavior, real loopback HTTP byte delivery, retry/fallback, concurrency, and failure cases. Network sandbox permission may be needed for loopback binding. The package's supported runtime is Python 3.11+.
