# Product Security Skills

Five standalone skill packages for AI coding assistants: secure development, sensitive data cleanup, security review, report triage, and fix verification. Independently installable tools provide [prompt integrity checks](tools/prompt-integrity/README.md), [prompt data guarding](tools/prompt-guard/README.md), and [model security regression evaluation](tools/model-security-eval/README.md).

Created for [Defrixx’s security resource](https://defrixx.github.io/en/). The repository provides reusable instructions, requirement references, report templates, and optional local helpers.

## Choose a skill

| Your task | Skill | What you receive |
| --- | --- | --- |
| Write or change code with security requirements in mind | [secure-development](skills/secure-development/SKILL.md) | Relevant requirements, implementation changes, and verification evidence |
| Find and remove sensitive information from a folder | [sensitive-data-cleanup](skills/sensitive-data-cleanup/SKILL.md) | A separate cleaned copy and a redacted replacement inventory and a cleaned-copy result |
| Assess a pull request or repository for vulnerabilities | [security-review](skills/security-review/SKILL.md) | Confirmed findings, separate hypotheses, and a prioritized remediation plan |
| Triage an existing scanner report | [security-report-triage](skills/security-report-triage/SKILL.md) | Accounted signals, justified grouping, and an action queue; bounded SARIF intake |
| Verify a specified repair | [security-fix-verification](skills/security-fix-verification/SKILL.md) | Per-finding verdicts, original/bypass/allowed cases, and evidence limits |

Use each skill independently or combine them in a task-driven sequence: triage or review → implementation → fix verification. Each skill directory can be copied on its own. A skill guides the assistant's decisions; its optional helper automates a bounded part of the work.

## How the skills work

### Secure development — while writing code

**Understand the change → select applicable requirements → implement controls → verify → report.**

The assistant identifies the stack, data, and trust boundaries, then reads only the relevant requirements. It explains what applies, implements within the requested scope, and checks both allowed and rejected behavior. Requirements form a source-backed engineering baseline selected for the target trust model.

> Use secure-development while implementing this upload endpoint. Apply relevant requirements, explain applicability, and report what was verified.

**Result:** changed code or an explicitly labeled candidate, applied requirement IDs, evidence, and next actions. See the [development report template](skills/secure-development/assets/development-report.md).

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

**Result:** a cleaned copy when requested, a redacted inventory, and processing outcomes. Supported image cleanup removes JPEG/PNG metadata while preserving encoded pixels. See the [cleanup report template](skills/sensitive-data-cleanup/assets/cleanup-report.md).

### Security review — assess existing code

**Fix the scope → model threats → find candidates → validate → analyze impact → report.**

The assistant follows untrusted data across security boundaries and checks reachability, prerequisites, existing defenses, and impact. Scanner signals remain hypotheses until supported by evidence.

| Mode | Scope |
| --- | --- |
| Pull request | Exact base/head revisions and surrounding code; distinguish introduced and pre-existing issues |
| Repository | Agreed components and revision, with working-tree state, exclusions, and coverage recorded |

> Use security-review on this PR from the supplied base/head revisions. Separate introduced and existing issues and produce a report without changing code.

> Use security-review on the current repository. Record the threat model, confirmed findings, hypotheses, and assessed data flows.

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

The application must protect its baseline separately and route every model call through the wrapper. Installation and CLI examples are in the package guide.

## Model security regression gate

The independent [model-security-eval CLI](tools/model-security-eval/README.md) tests local LM Studio/Ollama models against fixed synthetic instruction overrides, private-canary leaks, forged approvals, scope escapes and indirect/multiple-turn attacks. Select chat, read, write, command and external-service capabilities and set request/time budgets. Allowed controls prevent an always-refusing model from passing.

It emits JSON CI events, private JSON/Markdown evidence, baseline comparisons and exit codes: 0 pass, 1 fail, 2 inconclusive/error. Profiles select the synthetic developer workflow; identity discovery binds responses to the chosen local model. File, shell and external actions use in-memory fixtures. See the [CI entry script](tools/model-security-eval/examples/ci-gate.sh) for a blocking promotion step.

## Prompt data guard

The independent [prompt-guard library and CLI](tools/prompt-guard/README.md) checks untrusted UTF-8 text and JSON messages with source-scoped literal/regex rules. Default `strict` mode blocks matching requests; explicit `sanitize` mode applies policy-authorized replacements to a separate result and checks it again. Decisions are `allow`, `block`, `review` and `error`; only `allow` supplies dispatchable content. Regex execution has a subprocess deadline, and diagnostics omit input values.

Select packaged user, retrieval, tool, security or strict-topic profiles. Schema v2 adds mapped Unicode detection views, assembled-context checks, memory/overall deadlines and a four-worker cap. Policy releases can be pinned by independently selected identity/version/digest. The provider adapter dispatches accepted snapshots to configured local endpoints or an application-owned prompt-integrity boundary. `model-security-eval --guard-profile user-input --compare-guard` compares guarded and unguarded trials with separate detector/model/action observations.

Use it before model-request assembly, retain `prompt-integrity` at final dispatch, and authorize model-proposed actions before execution. Synthetic examples, policy fields and copy-output commands are in the package guide.

## What belongs in the result

Reports lead with **the outcome and next actions**, followed by selected evidence. Include only the attachments needed to act on the result: a detailed redacted inventory, the final cleaned copy, or a relevant patch/reproduction when useful.

`artifacts/` is local working storage. Intermediate trials, raw logs, superseded copies, private indexes, and replacement maps do not belong in the ordinary delivery bundle. An ignored file is not automatically safe to share. Do not delete supporting evidence or publish a bundle as a side effect of preparing a report.

## Requirement coverage

The [requirements catalog](skills/secure-development/references/requirements-index.md) contains 126 individually identified conditions across 29 topics, with 12 implementation controls across three stack profiles. It covers secrets, cryptography, certificates, APIs, identity and access, input handling, storage, files, client security, deployment, dependencies, and other security domains. Infrastructure as Code, CI/CD, and Kubernetes are separate topics.

Stack profiles add implementation and acceptance checks for:

- [Python / FastAPI / Pydantic / SQLAlchemy](skills/secure-development/references/stacks/python-fastapi.md)
- [TypeScript / React / Next.js](skills/secure-development/references/stacks/typescript-nextjs.md)
- [Docker Compose / BuildKit](skills/secure-development/references/stacks/docker-compose.md)

Requirements use [stable IDs, applicability, rules, implementation guidance, verification, sources, and exceptions](skills/secure-development/references/requirement-format.md). Assess each condition against its specific acceptance checks. Source dates and supported versions must be rechecked when applying version-sensitive guidance.

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
| prompt-guard | Python 3.11+, standard library runtime, POSIX file operations and subprocess execution |
| Full regression suite | Python 3.11+, Git, POSIX; standard library, local loopback sockets, no external services |
| Optional framework integration | Docker and fixture dependencies; see the integration instructions |
| Independent image decoding checks | Pillow; test-only, not required by the cleanup helper |

```sh
python3 scripts/validate_structure.py
python3 -m unittest discover -s tests -v
python3 scripts/run_regressions.py --output artifacts/new-regression-run
```

Create `artifacts/` if absent and use a new run directory. The [synthetic regression corpus](tests/README.md) exercises helper behavior, source preservation, path boundaries, classification, PR provenance, and copied-skill execution. Reports record source fingerprints, versions, and outcomes. Structural validation checks packaging and links.

The separate [integration suite](tests/integration/README.md) exercises synthetic FastAPI/SQLAlchemy, Next.js/Chromium, and Compose/BuildKit applications.

## Evaluation scope and project maintenance

### Behavioral evaluations

The optional model pilot and its fixed checks live in [evals/](evals/README.md), outside the standalone skill packages. Product regression tests live in `tests/`; evaluation-harness tests live in `evals/tests/`. The regression runner executes both suites without a model server. Local reports, copied targets and logs belong in ignored `artifacts/` and must not be committed.

### Combined workflow

Start with report triage for existing scanner signals or security review for code assessment. Continue to authorized implementation and fix verification while preserving finding IDs, provenance, and separate assessment/implementation/verification statuses. The two new skills carry local copies of the handoff contract; all five skills work independently. Cleanup is optional for selected delivery material; no stage implicitly authorizes installation or publication.

Checks cover helpers, workflow examples, and HTTP integration for prompt-integrity. Working evidence is stored in ignored `artifacts/`.

JPEG/PNG cleanup supports metadata-only processing.

Instructions required to use a copied skill remain inside that skill's directory. Local maintainer instructions and evaluation artifacts are not part of the distributed skills.

Per-condition evidence is generated as `requirement-evidence.json` by the regression runner: every topic condition, stack control and workflow condition is listed, with per-clause evidence records. See the [coverage manifest](tests/requirement_coverage.json) and [manual applicability review](tests/requirements-manual-review.md).

Optional [framework and lifecycle integrations](tests/integration/README.md) exercise OAuth/OIDC/JWT client/verifier boundaries with a synthetic issuer, real MongoDB/Jinja, Next.js Data Cache and Chromium policies. Failure injection verifies cleanup of owned resources while preserving a separate scope; per-clause observations are recorded in the integration evidence manifest.


## Workflow reports

The five skills use a common action ledger. Carry the same finding IDs through triage, review, implementation and verification; record changes and verification results at the selected revision. Cleanup identifies the final delivered copy and its preserved source. Prompt integrity uses its own [integration report template](tools/prompt-integrity/examples/integration-report.md).

## Deeper acceptance checks

Existing condition IDs are retained. Authorization checks now distinguish alternate output paths and the effective boundary of rights/publication changes. Business-operation checks identify independent commits and ambiguous outcomes. Data-lifecycle checks separate serving denial from disposition of retained copies.

| Improvement | Observable check | Scope of evidence |
| --- | --- | --- |
| Alternate access and lifecycle | Allowed/excluded reads across five paths; warm state, revocation, transfer, deletion and delayed publication | Synthetic SQLite authority/projection stores; sequential lifecycle transitions |
| Repeated effects and recovery | Synchronized duplicate attempts; actual process death at three commit boundaries; independent recipient counts | Two SQLite stores model caller and recipient; recipient deduplication is assumed and exercised |
| Cleanup usability | Replaced identifiers retain a two-file reference graph, distinct entities and benign labels | Actual helper; declared JSON value relationships |
| Report evidence validity | Policy drift, unknown revisions and contradictory current results reject unsupported claims | Structured evaluator inputs; explicit dependency set |

Review and verification guidance use these sequences to select decisive tests. Triage preserves findings across successive reports and reopens demonstrated recurrences under their original IDs. Evidence affected by code, configuration or relevant state changes is reassessed without rewriting earlier observations. See the [test contracts](tests/README.md#stateful-acceptance-cases) for fixture tasks and expected outcomes.

## License

Licensed under the [MIT License](LICENSE). Include the license notice when redistributing a standalone skill.
