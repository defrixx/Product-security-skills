# Repository-only behavioral evaluations

These runners and fixtures are development tools. Do not include `evals/`, repository tests, or local artifacts when copying a skill. Each skill works from its own directory. Run commands below from the repository root. Evaluation outputs belong in ignored `artifacts/`.

### Local-model pilot

`evals/run_model_pilot.py` runs one synthetic scenario for each of the five
skills, with and without skill instructions, through an already running LM Studio
server at `http://127.0.0.1:1234`. Select a loaded model explicitly:

```sh
python3 evals/run_model_pilot.py --model qwen/qwen3.8-27b --output artifacts/new-model-pilot
```

Use `--skill security-review --mode without` for a short initial probe. Each case
has a fresh conversation and virtual filesystem. By default the model can read
inventoried inputs and submit only explicitly allowed candidate outputs. It has
no arbitrary host filesystem, shell, or network access through tools.
By default, read-only tasks expose only the read tool and return reports in the final message.
Skill references and helper source are readable in the skill-enabled condition.
Optional checked dispatch and fixed executable tools are described below. An API connection failure or truncated response is
recorded as incomplete, never a passed skill assessment.

Use `--integrity --executable-checks` to test checked Chat Completions dispatch
and real synthetic cleanup operations. Integrity mode pins the trusted system
message, model, tool definitions and generation settings before the conversation;
every outbound model request passes through `prompt-integrity`. This in-memory
experiment baseline is not a deployment-approved release. It cannot detect a
compromised setup process or changes to trusted sources before initialization.
Responses mode is not covered and cannot be combined with `--integrity`.
The bounded transport requires a socket timeout of at most 900 seconds.

Executable mode adds `hash_file` for inventoried files and submitted outputs.
Cleanup also gets `run_cleanup` (the actual skill helper on a temporary synthetic
copy, with a fixed scenario-specific UI-label suppression) and `check_json`
(exact seeded-value and benign-control assertions). Tool results carry evidence
IDs and content hashes; hashes bind observations to a particular candidate, not
historical provenance. The `check_python` tool runs 15 function assertions in a disposable, network-disabled,
resource-limited Docker container. It accepts only a narrow AST-validated synthetic
Python subset with fixed records and three functions; unsupported candidates are
reported as not executed. Docker and a locally available `python:3.12-slim` image
are required; the tool never pulls images. No arbitrary shell is available. Tests exercise the real helper, preservation, invalid paths, and stale
output evidence. These capabilities are identical in with/without-skill modes. An evidence-reference
audit flags unknown IDs, citations of checks that did not execute, and hashes no
longer matching current content. Prose still needs semantic review; a valid ID
does not prove that a claim accurately describes its evidence.

```sh
python3 evals/run_model_pilot.py --integrity --executable-checks --skill sensitive-data-cleanup --mode both --max-tokens 16384 --max-steps 12 --timeout 900 --output artifacts/new-checked-cleanup
```

The default socket I/O timeout is 300 seconds; it is not a whole-run deadline.
The local paired experiment uses `--max-tokens 16384 --max-steps 12 --timeout 900`;
earlier lower-budget attempts timed out or exhausted their response budget.
These limits do not guarantee completion and can permit long runs. Keep
timeout/truncation attempts and changed-budget runs separate. Identical budgets
and tool contracts are required for a paired comparison; the runner does not
automatically retry or mix configurations. Use `--repetitions 2` for repeated
trials; mode order alternates between repetitions. Two trials remain descriptive,
not a statistically reliable skill-effect estimate. The request format follows LM Studio's
[tool-use API](https://lmstudio.ai/docs/developer/openai-compat/tools) and
[Chat Completions parameters](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
(checked 2026-10-02).

For a separately labeled run with an explicit reasoning request, use LM Studio's
[Responses API](https://lmstudio.ai/docs/developer/openai-compat/responses)
(checked 2026-10-02):

```sh
python3 evals/run_model_pilot.py --api responses --reasoning low --max-tokens 8192 --timeout 300 --output artifacts/new-responses-pilot
```

The adapter replays the bounded conversation statelessly, requests `store: false`,
and exposes only local virtual function tools. It does not configure remote MCP
or replay provider reasoning. Server-side logging/retention and whether a model
honors the requested reasoning level are not independently established. Compare
runs using the same API and reasoning settings; changing protocols is a separate
experiment, not a transparent retry.

Results include tasks, source fingerprints, model metadata when available, token
usage, tool-call metadata, candidate outputs, and final reports. Provider-internal
reasoning is not persisted. The known synthetic credential is redacted before
saving evidence; this is not a general-purpose scrubber for real target data.
Keep real projects and sensitive inputs out of this runner. Outputs use fresh
private directories; no skills are installed and no reports are published.

The pilot checks tool operation and selected observable properties. Semantic
assessment requires a separate evidence review; completed generation is not a
passed security control. One small scenario per skill, even when repeated, does
not measure general skill quality. In the default virtual-only mode, development
produces an unexecuted candidate and review/verification are static-only. With
fixed checks enabled, record exactly which checks executed and which output hash
they cover; unsupported or superseded candidates are not verified final outputs.
Historical and nonexecution citations can be honest reporting, so audit flags
are review signals rather than automatic semantic failures. Full shell agents,
framework execution, prompt-injection resilience, application integration, and
randomized comparisons remain separate evaluations. Reasoning uses server defaults unless
explicitly requested with the Responses adapter; the manifest records requested
settings and reported model configuration without claiming independent
verification of effective inference settings.

Offline runner tests are included in the regression suite:

```sh
python3 -m unittest discover -s evals/tests -p test_model_pilot.py -v
```

The local 2026-10-02–03 validation stage passed 155 regression tests and completed
20 paired model cases (five skills, two modes, two repetitions). Completion was
not treated as semantic success: review provenance/remediation claims, development
control claims, and several reporting details still needed correction. All four
development candidates passed the 15 fixed behavior assertions; all four cleanup
outputs passed the labeled JSON checks. A separate guided probe verified actual
cleanup-helper dispatch through prompt-integrity and matching final output hashes.
The paired series used a frozen prompt before a capability-wording clarification;
the guided probe is not included in its comparison. Live dispatch used host Python
3.9, outside the package's declared deployment runtime; supported-runtime package
and HTTP tests passed on Python 3.11/3.12.

A target-specific EZII snapshot experiment also passed 13 selected boundary checks
with synthetic data, SQLite substitute models and in-memory Qdrant. Detailed local
evidence and semantic assessments are in ignored `artifacts/stage2-report-20261002.md`;
they are not distributed with a fresh clone. Skills themselves were unchanged.

### Reporting-grounding regressions

[Report-grounding fixtures](fixtures/report-grounding.json) pair intentionally
unsupported claims with valid controls: unknown history versus an actual revision
comparison, tested scope filtering versus untested input validation, candidate
versus observed application, and a partial versus fully checked fixture repair.
`report_grounding.py` evaluates structured claims against these labeled observations;
it does not extract prose, authenticate evidence, or act as a general security gate.
Run `python3 -m unittest discover -s evals/tests -p test_report_grounding.py -v`.
A future model trial must extract claims independently, retain raw reports and
record current skill fingerprints. Passing these evaluator tests alone does not
establish that the revised skill produces more accurate model reports.

The historical stage-2 outcomes above predate the reporting instruction changes.
They must not be presented as evaluation of the updated skills. New guarded pilot
failures include safe `TransportError.code` diagnostics without private exceptions.

### Harness test suite

All harness tests live in `evals/tests/`. Run them independently from the repository root:

```sh
python3 -m unittest discover -s evals/tests -v
```

The root `scripts/run_regressions.py` runner discovers both `tests/` and `evals/tests/` and includes both in its results and source fingerprints. These tests require neither a model server nor Docker.

The local-model pilot has a separate [evaluator-only rubric](fixtures/model-pilot-ground-truth.json).
The model's virtual file inventory excludes this rubric and the test code.
It records expected vulnerable/safe paths, signal accounting, candidate state,
and evidence limitations. In particular, a single snapshot cannot establish
introduced versus pre-existing provenance. These semantic criteria require
review of actual outputs; they are not scored with instruction-text or substring
assertions. `test_model_pilot.py` independently checks the fixture's original,
partially repaired and safe behavior, virtual-tool boundaries and transport-loop
failure handling without contacting a model.

The rubric distinguishes virtual-only runs from fixed-check runs. Execution
claims in fixed-check mode require actual tool evidence for the relevant content
hash. `test_model_pilot.py` includes a simulated-model loop through the real
prompt-integrity checker and cleanup helper; it checks the returned output and
evidence chain without contacting LM Studio. `test_pilot_checks.py` validates the
restricted Python candidate boundary and container command/cleanup contract with
a subprocess stub. It does not itself prove container execution; live isolated
checks are recorded separately in ignored artifacts. Reference-audit flags can
identify honest citations of earlier rejected candidates and require semantic
review before being called report errors.

