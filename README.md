# Product Security Skills

Five standalone skill packages for AI coding assistants: secure development, sensitive data cleanup, security review, report triage, and fix verification. The repository also includes an independently installable [prompt-integrity library and CLI](tools/prompt-integrity/README.md).

Created for [Defrixx’s security resource](https://defrixx.github.io/en/). The repository provides reusable instructions, requirement references, report templates, and optional local helpers.

## Choose a skill

| Your task | Skill | What you receive |
| --- | --- | --- |
| Write or change code with security requirements in mind | [secure-development](skills/secure-development/SKILL.md) | Relevant requirements, implementation changes, and verification evidence |
| Find and remove sensitive information from a folder | [sensitive-data-cleanup](skills/sensitive-data-cleanup/SKILL.md) | A separate cleaned copy and a report of replacements, omissions, and limitations |
| Assess a pull request or repository for vulnerabilities | [security-review](skills/security-review/SKILL.md) | Confirmed findings, separate hypotheses, and a prioritized remediation plan |
| Triage an existing scanner report | [security-report-triage](skills/security-report-triage/SKILL.md) | Accounted signals, justified grouping, and an action queue; bounded SARIF intake |
| Verify a specified repair | [security-fix-verification](skills/security-fix-verification/SKILL.md) | Per-finding verdicts, original/bypass/allowed cases, and evidence limits |

Use each skill independently or combine them in a task-driven sequence: triage or review → implementation → fix verification. Each skill directory can be copied on its own. A skill guides the assistant's decisions; its optional helper automates a bounded part of the work.

## How the skills work

### Secure development — while writing code

**Understand the change → select applicable requirements → implement controls → verify → report.**

The assistant identifies the stack, data, and trust boundaries, then reads only the relevant requirements. It explains what applies, implements within the requested scope, and checks both allowed and rejected behavior. Requirements are a proposed engineering baseline, not approved corporate policy or compliance certification.

> Use secure-development while implementing this upload endpoint. Apply relevant requirements, explain applicability, and report what was verified.

**Result:** changed code or an explicitly labeled candidate, applied requirement IDs, evidence, and remaining gaps. See the [development report template](skills/secure-development/assets/development-report.md).

### Sensitive data cleanup — before sharing material

**Define scope → detect and classify → clean a separate copy → verify → report.**

The assistant distinguishes sensitive values from defaults, test data, and benign lookalikes. Originals are preserved. Reports use safe identifiers and replacement markers rather than original sensitive values.

Choose the mode that matches the task:

| Mode | Behavior |
| --- | --- |
| Scan-only | Report candidates and proposed actions; do not produce a cleaned copy |
| Text and structured-data cleanup | Replace selected values in supported UTF-8 text, JSON, JSONL, and CSV |
| JPEG/PNG metadata-only cleanup | Remove image metadata without rewriting encoded pixels; omit other formats |

> Use sensitive-data-cleanup to clean this folder into a new sibling directory. Report what was replaced and what could not be checked, without exposing original values.

> Remove only JPEG/PNG metadata into a separate copy. Leave source files unchanged and omit other formats.

**Result:** a cleaned copy when requested, a redacted inventory, and explicit coverage limits. Unsupported or failed files are omitted and reported. Image metadata removal can change orientation/color interpretation in viewers; visible image content is not redacted. No complete personal-data discovery or runnable-copy guarantee is claimed. See the [cleanup report template](skills/sensitive-data-cleanup/assets/cleanup-report.md).

### Security review — assess existing code

**Fix the scope → model threats → find candidates → validate → analyze impact → report.**

The assistant follows untrusted data across security boundaries and checks reachability, prerequisites, existing defenses, and impact. Scanner signals remain hypotheses until supported by evidence.

| Mode | Scope |
| --- | --- |
| Pull request | Exact base/head revisions and surrounding code; distinguish introduced and pre-existing issues |
| Repository | Agreed components and revision, with working-tree state, exclusions, and coverage recorded |

> Use security-review on this PR from the supplied base/head revisions. Separate introduced and existing issues and produce a report without changing code.

> Use security-review on the current repository. Record the threat model, confirmed findings, hypotheses, and untested areas.

**Result:** actionable findings with evidence, confidence, prerequisites, remediation, and fix-verification criteria. Review does not itself authorize code changes or publication. See the [review report template](skills/security-review/assets/review-report.md).

### Report triage — interpret scanner output

**Record provenance → account for signals → inspect context → group root causes → prioritize.**

> Use security-report-triage on this SARIF report against the current revision. Separate confirmed findings, hypotheses, disproved signals, and unprocessed results without changing code.

**Result:** an action queue with raw-result accounting, justified duplicate grouping, evidence, and coverage limits. The local SARIF normalizer prepares a bounded inventory; it does not determine whether a vulnerability exists. See the [triage report template](skills/security-report-triage/assets/triage-report.md).

### Fix verification — recheck a specified repair

**Pin the finding and revision → inspect the repair → check original and alternate paths → verify allowed behavior → report.**

> Use security-fix-verification to recheck finding F-007 at this patched revision. Preserve the original finding ID and distinguish candidate changes from applied fixes.

**Result:** fixed, partially fixed, not fixed, or inconclusive for each selected finding, with supporting evidence. Historical confirmation remains separate from the later repair verdict. See the [verification report template](skills/security-fix-verification/assets/verification-report.md).

## Prompt integrity tooling

The independent [prompt-integrity package](tools/prompt-integrity/README.md) checks application-controlled static instructions immediately before model-request dispatch. Its adapters support strict subsets of Ollama `/api/chat` and LM Studio `/v1/chat/completions` with pinned tool definitions. It blocks mismatches and sends the checked snapshot, including on explicitly managed retries and fallback attempts.

The application must protect its baseline separately and route every model call through the wrapper. This checks request integrity; it does not establish model obedience or resistance to prompt injection. Installation and CLI examples are in the package guide.

## What belongs in the result

Reports lead with **the outcome and next actions**, followed by evidence and limitations. Include only the attachments needed to act on the result: a detailed redacted inventory, the final cleaned copy, or a relevant patch/reproduction when useful.

`artifacts/` is local working storage. Intermediate trials, raw logs, superseded copies, private indexes, and replacement maps do not belong in the ordinary delivery bundle. An ignored file is not automatically safe to share. Do not delete supporting evidence or publish a bundle as a side effect of preparing a report.

## Requirement coverage

The [requirements catalog](skills/secure-development/references/requirements-index.md) contains 120 individually identified conditions across 28 topics, with 12 implementation controls across three stack profiles. It covers secrets, cryptography, certificates, APIs, identity and access, input handling, storage, files, client security, deployment, dependencies, and other security domains. Infrastructure as Code, CI/CD, and Kubernetes are separate topics.

Stack profiles add implementation and acceptance checks for:

- [Python / FastAPI / Pydantic / SQLAlchemy](skills/secure-development/references/stacks/python-fastapi.md)
- [TypeScript / React / Next.js](skills/secure-development/references/stacks/typescript-nextjs.md)
- [Docker Compose / BuildKit](skills/secure-development/references/stacks/docker-compose.md)

Requirements use [stable IDs, applicability, rules, implementation guidance, verification, sources, and exceptions](skills/secure-development/references/requirement-format.md). Passing one condition does not establish that an entire topic is satisfied. Source dates and supported versions must be rechecked when applying version-sensitive guidance.

---

## Running the optional helpers

Commands below run from the repository root. Read the [cleanup contract](skills/sensitive-data-cleanup/references/helper-contract.md), [image metadata contract](skills/sensitive-data-cleanup/references/image-metadata.md), or [PR context contract](skills/security-review/references/pr-context-helper.md) for the selected operation.

```sh
# Inventory without creating a cleaned copy.
python3 skills/sensitive-data-cleanup/scripts/cleanup.py --source /path/to/input --output /path/to/new-scan --mode scan-only

# Clean supported text formats into a separate copy.
python3 skills/sensitive-data-cleanup/scripts/cleanup.py --source /path/to/input --output /path/to/new-clean-run --mode clean-copy --policy /path/to/policy.json

# Remove only JPEG/PNG metadata.
python3 skills/sensitive-data-cleanup/scripts/cleanup.py --source /path/to/images --output /path/to/new-image-run --mode clean-copy --image-metadata-only

# Record local PR revisions and changed-file metadata; this is not a vulnerability scanner.
python3 skills/security-review/scripts/pr_context.py --repo /path/to/repo --base main --head feature --output /path/to/new-pr-context.json
```

Use a fresh output destination. Helpers do not install tools or publish results automatically.

For scanner report intake:

```sh
python3 skills/security-report-triage/scripts/normalize_sarif.py --input /path/to/report.sarif --output /path/to/new-normalized --target-root /path/to/target
```

Read the [SARIF subset and limits](skills/security-report-triage/references/sarif-subset.md) first. Normalization produces an inventory, not confirmed vulnerabilities. The [prompt-integrity package guide](tools/prompt-integrity/README.md) covers its independent CLI, baseline lifecycle and application integration.

## Dependencies and checks

| Component | Requirements |
| --- | --- |
| Skill instructions and templates | An assistant capable of reading the skill and the target project |
| Cleanup helper | Python 3.9+, standard library, POSIX filesystem operations |
| PR context helper | Python 3.9+ and Git |
| SARIF normalizer | Python 3.9+, standard library, POSIX filesystem operations |
| prompt-integrity | Python 3.11+, standard library runtime, POSIX file operations |
| Full regression suite | Python 3.11+, Git, POSIX; standard library, local loopback sockets, no external services |
| Optional framework integration | Docker and fixture dependencies; see the integration instructions |
| Independent image decoding checks | Pillow; test-only, not required by the cleanup helper |

```sh
python3 scripts/validate_structure.py
python3 -m unittest discover -s tests -v
python3 scripts/run_regressions.py --output artifacts/new-regression-run
```

Create `artifacts/` if absent and use a new run directory. The [synthetic regression corpus](tests/README.md) exercises helper behavior, source preservation, path boundaries, classification, PR provenance, and copied-skill execution. Reports record source fingerprints, versions, and outcomes. Structural validation checks packaging and links; it does not establish skill behavior.

The separate [integration suite](tests/integration/README.md) exercises synthetic FastAPI/SQLAlchemy, Next.js/Chromium, and Compose/BuildKit applications.

## Evaluation scope and project maintenance

### Behavioral evaluations

The optional model pilot and its fixed checks live in [evals/](evals/README.md), outside the standalone skill packages. Product regression tests live in `tests/`; evaluation-harness tests live in `evals/tests/`. The regression runner executes both suites without a model server. Local reports, copied targets and logs belong in ignored `artifacts/` and must not be committed.

### Combined workflow

Start with report triage for existing scanner signals or security review for code assessment. Continue to authorized implementation and fix verification while preserving finding IDs, provenance, and separate assessment/implementation/verification statuses. The two new skills carry local copies of the handoff contract; all five skills work independently. Cleanup is optional for selected delivery material; no stage implicitly authorizes installation or publication.

Checks cover helpers, workflow examples, and HTTP integration for prompt-integrity. Working evidence is stored in ignored `artifacts/`.

Complete personal-data discovery, document/archive cleanup and visible image-content redaction remain outside the current coverage. JPEG/PNG support is metadata-only.

Instructions required to use a copied skill remain inside that skill's directory. Local maintainer instructions and evaluation artifacts are not part of the distributed skills.

Per-condition evidence is generated as `requirement-evidence.json` by the regression runner: every topic condition, stack control and workflow condition is listed, with exact tested clauses or explicit untested status. See the [coverage manifest](tests/requirement_coverage.json) and [manual applicability review](tests/requirements-manual-review.md).

Optional [framework and lifecycle integrations](tests/integration/README.md) exercise OAuth/OIDC/JWT client/verifier boundaries with a synthetic issuer, real MongoDB/Jinja, Next.js Data Cache and Chromium policies. Failure injection verifies cleanup of owned resources while preserving a separate scope; exact tested clauses and limits are in the integration evidence manifest.


## Reporting and integration follow-up

The skills now require an evidence check before delivery and include a common
action ledger in their standalone report templates. Carry the same finding IDs
through triage/review, implementation and verification. Keep candidate/applied
state independent of the fix verdict; never close an issue solely because a patch
was produced. For cleanup, identify the delivered copy separately from the
preserved source. The tool has its own [integration report template](tools/prompt-integrity/examples/integration-report.md).

### Component results

| Component | Implemented change | Evidence / current limitation |
| --- | --- | --- |
| Security review | Unknown history remains unknown; repairs must preserve the stated invariant | Labeled history controls; improved model reporting still needs a new trial |
| Secure development | Exact-property coverage and observed application state required | Labeled coverage/state controls; no whole-control inference from one test |
| Sensitive data cleanup | Helper execution, syntax validation and rescans reported separately | Existing real-helper regressions; autonomous helper selection not established |
| Security report triage | Content identity separated from provenance; unresolved items retained | Existing triage regressions; revised reporting not yet model-evaluated |
| Security fix verification | Case counts, alternate paths, candidate state and actual authorship reconciled | Partial/fixed fixture controls; revised reporting not yet model-evaluated |
| prompt-integrity | Checked example attempts, optional release digest pin, safe failure codes | Package tests exercise wire rejection, release lifecycle and diagnostics |
| Combined workflow | Same ledger fields in all five report templates and tool report | Handoff guidance implemented with stable finding IDs and separate verification states |

### Shared action ledger

This is the repository follow-up register, not a report of repaired vulnerabilities
in EZII or another target. Changes are applied in the local working tree, not
published or deployed. Test sources below identify reproducible checks; dated run
outputs remain local in ignored `artifacts/`.

| ID | Observed issue | What changed | Implementation state | Verification | What remains |
| --- | --- | --- | --- | --- | --- |
| REPORT-01 | Historical provenance asserted from one snapshot | Require same-finding revision comparison; explicit unknown | Applied to review/triage guidance | [Labeled claim controls](evals/tests/test_report_grounding.py) | New model trial; original report errors remain historical evidence |
| REPORT-02 | Narrow tests presented as broader control coverage | Require evidence for the exact condition and revision | Applied to development guidance | Same fixture: unrelated property, stale revision and unexecuted check rejected | Measure model compliance on broader tasks |
| REPORT-03 | Candidate confused with applied or fully fixed | Explicit target/state evidence and per-path verdict | Applied to guidance and templates | Candidate/application and partial/fixed controls | Verify the resulting revision and preserve per-path evidence |
| REPORT-04 | Cleanup execution narration and verification authorship/counts overclaimed | Reconcile claims with actual tool records and known authorship | Applied to cleanup/verification guidance | Existing helper and fix-verification tests; new wording structurally validated only | Fresh semantic assessment of generated reports |
| TOOL-01 | Dispatch protection needs attempt-by-attempt evidence | Test tamper at primary, retry and fallback; document call inventory | Applied to package tests/docs | [Actual HTTP tests](tools/prompt-integrity/tests/test_integration.py), guarded pilot-loop tests | Keep the call inventory current; unguarded eval modes remain explicit |
| TOOL-02 | Version alone does not detect changed release bytes | Optional digest pin, pinned startup example, CLI pin | Applied to package | [Release lifecycle tests](tools/prompt-integrity/tests/test_release.py) | Protected release distribution and trusted pin storage belong to deployment |
| TOOL-03 | Generic transport errors obscure failure class | Bounded diagnostic codes propagated into guarded pilot output | Applied to tool and evaluation harness | Failure/redaction tests and guarded pilot diagnostic test | Timeout cannot prove the provider did not receive a request |
| FLOW-01 | Findings and unresolved work scattered across reports | Common action ledger in standalone templates; component summary and this register | Applied to documentation | Template structure/link validation | End-to-end user trial; no automated cross-report synchronization |
| EVAL-01 | Model pilot mixed with general repository scripts | Move runner, workers, rubric and harness tests into `evals/`; run both test suites | Applied to repository layout | Pilot regression tests and full suite; fingerprints include `evals/` | Evaluation harness stays outside copied skills; local results must not be committed |

These changes address implementation and reporting contracts. They do not establish
improved model accuracy, generalized prompt-injection resistance, or complete
application security. The next behavioral trial should assess the updated skill
fingerprints and the whole handoff, preserving unresolved findings in the final ledger.

## License

Licensed under the [MIT License](LICENSE). Include the license notice when redistributing a standalone skill.
