# Product Security Skills

Three standalone skills for AI coding assistants: secure development, sensitive data cleanup, and evidence-based security reviews.

Created for [Defrixx’s security resource](https://defrixx.github.io/en/). The repository provides reusable instructions, requirement references, report templates, and optional local helpers.

## Choose a skill

| Your task | Skill | What you receive |
| --- | --- | --- |
| Write or change code with security requirements in mind | [secure-development](skills/secure-development/SKILL.md) | Relevant requirements, implementation changes, and verification evidence |
| Find and remove sensitive information from a folder | [sensitive-data-cleanup](skills/sensitive-data-cleanup/SKILL.md) | A separate cleaned copy and a report of replacements, omissions, and limitations |
| Assess a pull request or repository for vulnerabilities | [security-review](skills/security-review/SKILL.md) | Confirmed findings, separate hypotheses, and a prioritized remediation plan |

The skills work independently. Each skill directory can be copied on its own. A skill guides the assistant's decisions; its optional helper automates a bounded part of the work.

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

## Dependencies and checks

| Component | Requirements |
| --- | --- |
| Skill instructions and templates | An assistant capable of reading the skill and the target project |
| Cleanup helper | Python 3.9+, standard library, POSIX filesystem operations |
| PR context helper | Python 3.9+ and Git |
| Core regression suite | Python 3.9+, Git, POSIX; no third-party Python packages or network services |
| Optional framework integration | Docker and fixture dependencies; see the integration instructions |
| Independent image decoding checks | Pillow; test-only, not required by the cleanup helper |

```sh
python3 scripts/validate_structure.py
python3 -m unittest discover -s tests -v
python3 scripts/run_regressions.py --output artifacts/new-regression-run
```

Create `artifacts/` if absent and use a new run directory. The [synthetic regression corpus](tests/README.md) exercises helper behavior, source preservation, path boundaries, classification, PR provenance, and copied-skill execution. Reports record source fingerprints, versions, and outcomes. Structural validation checks packaging and links; it does not establish skill behavior.

The separate [integration suite](tests/integration/README.md) exercises synthetic FastAPI/SQLAlchemy, Next.js/Chromium, and Compose/BuildKit applications. These checks do not certify a target deployment or every framework version. A successful vulnerability reproduction demonstrates the vulnerable behavior, not a passed security control.

## Evaluation scope and project maintenance

Complete personal-data discovery, document/archive cleanup, visible image-content redaction, and target-application integration remain outside the current coverage. JPEG/PNG support is metadata-only.

Instructions required to use a copied skill remain inside that skill's directory. Local maintainer instructions and evaluation artifacts are not part of the distributed skills.

## License

Licensed under the [MIT License](LICENSE). Include the license notice when redistributing a standalone skill.

Per-condition evidence is generated as `requirement-evidence.json` by the regression runner: every topic condition, stack control and workflow condition is listed, with exact tested clauses or explicit untested status. See the [coverage manifest](tests/requirement_coverage.json) and [manual applicability review](tests/requirements-manual-review.md). Partial synthetic evidence is not a full-condition pass or independent skill evaluation.

Optional [framework and lifecycle integrations](tests/integration/README.md) exercise OAuth/OIDC/JWT client/verifier boundaries with a synthetic issuer, real MongoDB/Jinja, Next.js Data Cache and Chromium policies. Failure injection verifies cleanup of owned resources while preserving a separate scope; exact tested clauses and limits are in the integration evidence manifest.
