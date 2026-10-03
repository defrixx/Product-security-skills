# Behavioral evaluation tools

Run evaluation commands from the repository root. Results use a fresh directory under ignored `artifacts/`. Standalone skills are copied from their own directories.

## Local-model skill pilot

`run_model_pilot.py` runs a synthetic scenario for each of the five skills through a running LM Studio server at `http://127.0.0.1:1234`. It compares runs with and without the skill instructions.

```sh
python3 evals/run_model_pilot.py --model "$MODEL_ID" --output artifacts/new-model-pilot
```

Select a task with `--skill security-review`; select `--mode with`, `without` or `both`. Every case starts a new conversation with a virtual filesystem and a fixed tool contract. Read-only tasks offer a read tool; implementation tasks accept candidate outputs in selected paths.

### Guarded dispatch and executable checks

`--integrity` pins system instructions, model, tool definitions and generation settings for each Chat Completions request. `--executable-checks` adds hashes, actual cleanup operations, JSON checks and a constrained Python check in a disposable network-disabled Docker container. Python checks use a locally available `python:3.12-slim` image.

```sh
python3 evals/run_model_pilot.py --model "$MODEL_ID" \
  --integrity --executable-checks --skill sensitive-data-cleanup --mode both \
  --max-tokens 16384 --max-steps 12 --timeout 900 \
  --output artifacts/new-checked-cleanup
```

Tool evidence contains IDs and candidate hashes. The evidence audit checks cited IDs and their content identity. Tool-call batches validate names, shapes, unique IDs and arguments before their first effect. Duplicate JSON keys, nonfinite constants and invalid encodings are rejected; path checks enforce each operation's virtual boundary.

### Configuration and repetitions

`--max-tokens` controls response generation, `--max-steps` controls inference rounds and `--timeout` sets socket I/O timeout (default 300 seconds, maximum 900 for guarded transport). `--repetitions` repeats cases and alternates mode order. Use matching budgets and tool contracts for paired comparisons.

Responses API runs use a separate adapter and an explicit reasoning setting:

```sh
python3 evals/run_model_pilot.py --model "$MODEL_ID" --api responses --reasoning low \
  --max-tokens 8192 --timeout 300 --output artifacts/new-responses-pilot
```

`--integrity` selects Chat Completions. Responses conversations are replayed statelessly with `store: false`. Requested settings and reported model configuration are recorded in the manifest.

Results contain tasks, fingerprints, model metadata, token usage, tool-call records, outputs and final reports. Synthetic credentials are redacted before persistence. Use synthetic projects and fixture data for these evaluations.

## Report grounding

[Report-grounding fixtures](fixtures/report-grounding.json) pair supported and unsupported claims with labeled observations. `report_grounding.py` checks structured claim/evidence consistency, including revision provenance, tested properties, implementation state and repair verdicts. Relevant configuration/dependency fingerprints bind observations to their assessment context.

[The pilot rubric](fixtures/model-pilot-ground-truth.json) defines vulnerable and allowed paths, signal accounting and expected candidate state. The model's virtual inventory excludes evaluator files.

## Local model security gate

[model-security-eval](../tools/model-security-eval/README.md) is an independent installable CLI for local-model security checks and CI admission. It provides capability profiles, adversarial and benign task pairs, identity discovery, execution budgets, progress checkpoints and baseline comparison.

## Tests

```sh
python3 -m unittest discover -s evals/tests -v
python3 scripts/run_regressions.py --output artifacts/new-evaluation-regressions
```

The root runner includes product tests and evaluation-harness tests. Package tests for model-security-eval are included through `tests/test_model_security_eval.py`.

Protocol references, checked 2026-10-04: [LM Studio tool use](https://lmstudio.ai/docs/developer/openai-compat/tools), [Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions), and [Responses](https://lmstudio.ai/docs/developer/openai-compat/responses).
