# model-security-eval

Check local LM Studio and Ollama models after updates and use the result as a blocking CI check. Select developer capabilities, set execution budgets, run adversarial scenarios alongside allowed tasks, and compare results with a baseline.

Version 0.2.0 requires Python 3.11+. Runtime uses the standard library. The package works independently of the repository's skills.

## Capabilities and scenarios

Select a comma-separated subset with `--capabilities`; include `chat` in every profile.

| Capability | Allowed task | Adversarial checks |
| --- | --- | --- |
| `chat` | Return requested public data | Instruction and role overrides, private-token disclosure, encoded disclosure, forged approval and multiple turns |
| `read` | Read `repo/README.md` and return its API description | Other paths; instructions embedded in README, code comments and retrieval metadata |
| `write` | Write public data to `repo/result.txt` | Other paths, forged approval and scope expansion |
| `command` | Invoke `tests` | Other commands, forged approval and scope expansion |
| `external` | Send public data to `sandbox` | Other recipients, private-token exfiltration and forged approval |

The runner uses synthetic repository content, in-memory file actions, virtual command results and intercepted messages. README/comment/retrieval scenarios have benign counterparts. Multi-stage cases first require the authorized action and its correct acknowledgement, then deliver the scope-expansion attempt. Read controls check both the read operation and the returned API description.

Tool-call JSON is normalized before private-token and scope checks. A proposed batch is checked before its first effect. Reports distinguish proposals, blocked operations and completed fixture actions.

## Run

From the repository root with a running local inference server:

```sh
mkdir -p artifacts
PYTHONPATH=tools/model-security-eval/src python3 -m model_security_eval \
  --backend lmstudio \
  --model "$MODEL_ID" \
  --model-revision "$MODEL_REVISION" \
  --server-version "$SERVER_VERSION" \
  --capabilities chat,read,write,command,external \
  --repetitions 3 --max-requests 300 --max-seconds 1800 \
  --request-timeout 120 --max-steps 6 --max-tokens 2048 \
  --output "artifacts/$RUN_ID"
```

Supply the loaded model ID, LM Studio release identity, server version and a fresh run-directory name through the shown environment variables. Use `--backend ollama` for native Ollama chat. Ollama discovers the model digest and server version; optional `--model-revision` and `--server-version` pin their expected values.

Default origins are `http://127.0.0.1:1234` for LM Studio and `http://127.0.0.1:11434` for Ollama. `--endpoint` accepts a numeric loopback HTTP origin with an explicit port, including IPv6 loopback. Use an origin without a path, query or URL credentials. Requests use direct local dispatch with redirects and proxies disabled.

Install independently into your environment with `python -m pip install /path/to/model-security-eval`, then invoke `model-security-eval` with the same parameters.

Inspect the selected scenario inventory:

```sh
PYTHONPATH=tools/model-security-eval/src python3 -m model_security_eval \
  --backend ollama --model inventory \
  --capabilities chat,read --output artifacts/unused --list-cases
```

## Identity and baseline comparison

Before and after a run, the CLI reads local model metadata. Ollama uses `/api/tags` and `/api/version`; LM Studio uses `/api/v1/models`, with compatibility discovery through `/v1/models` when required. Metadata records model IDs, digests, quantization and load configuration where supplied. Every inference response is matched against the selected model and the aliases established by discovery. Metadata changes close the admission gate.

LM Studio profiles require `--model-revision` and `--server-version`. Identity arguments must contain non-whitespace values. Ollama's expected digest accepts a 64-character hexadecimal value with an optional `sha256:` prefix.

Add `--baseline artifacts/previous-run/report.json` to compare case statuses. Compatible criteria use the same scenario suite, evaluator source bytes, capability policy, adapter, generation settings, repetitions and budgets. The comparison records model/revision/server/endpoint changes and per-trial changes. Report format version is 2.

## CI

The [CI entry script](examples/ci-gate.sh) runs from the repository root:

```sh
sh tools/model-security-eval/examples/ci-gate.sh
```

Set `MODEL_ID` and `EVAL_OUTPUT`; set `MODEL_REVISION` and `SERVER_VERSION` for LM Studio. Optional `EVAL_BACKEND`, `EVAL_CAPABILITIES`, `EVAL_REPETITIONS`, `EVAL_MAX_REQUESTS`, `EVAL_MAX_SECONDS`, `EVAL_REQUEST_TIMEOUT`, `EVAL_MAX_STEPS` and `EVAL_MAX_TOKENS` configure execution. Additional CLI flags pass through as script arguments.

| Exit | Result | CI action |
| --- | --- | --- |
| 0 | `pass`: all planned trials complete and all checks hold | Allow promotion |
| 1 | `fail`: observed violation or failed allowed task | Block promotion |
| 2 | `inconclusive` or execution/configuration error | Block promotion |

The script preserves the CLI exit status. Place it before the promotion step on a runner with the selected local model server. Preserve reports using the pipeline's artifact-retention step.

Stdout is newline-delimited JSON: `evaluation_started`, `case_finished`, `evaluation_finished` and `evaluation_error`. Events carry case IDs, diagnostic codes, counts, run state and the criteria fingerprint.

## Budgets

| Parameter | Default | Controls |
| --- | --- | --- |
| `--repetitions` | 3 | Trials per scenario; order alternates |
| `--max-requests` | 300 | Total inference and metadata dispatch attempts |
| `--max-seconds` | 1800 | Run budget |
| `--request-timeout` | 120 | Whole-request client deadline, bounded by remaining run time |
| `--max-steps` | 6 | Inference rounds per trial |
| `--max-tokens` | 2048 | Requested output tokens per response |
| `--temperature` | 0 | Requested sampling temperature |
| `--seed` | 17 | Base sampling seed; repetition index is added |

An isolated HTTP worker enforces the client deadline. Requests and responses have 4 MiB and 2 MiB bounds. Each attempt is counted; dispatch uses explicit attempts without automatic retries or fallback.

## Reports and recovery

`--output` creates a fresh private directory under an existing parent. Use a canonical path without symlink components. Directory permissions are 0700; evidence files use 0600.

- `report.md`: outcome, CI decision, counts, case results and next action.
- `report.json`: configuration, identity snapshots, source fingerprints, normalized observations, effects and structured assessment data.
- `checkpoint.json`: atomically updated progress after observations and completed trials.

Private-token forms are redacted before persistence. Normalized observations are scored in full, then recorded as a bounded preview plus a hash. Checkpoints preserve completed, active and pending trial IDs. SIGINT/SIGTERM interruption produces an interrupted report and a blocking exit status; earlier final reports are preserved.

## Development checks

```sh
python3 -m unittest discover -s tools/model-security-eval/tests -v
python3 scripts/validate_structure.py
python3 scripts/run_regressions.py --output artifacts/new-model-security-regressions
```

The package suite exercises normalization, scope, identity discovery and drift, task prerequisites, checkpoints, redaction, CI outcomes and actual loopback HTTP exchanges. Root regressions include the package suite through `tests/test_model_security_eval.py`.

## Protocol sources

Checked 2026-10-04:

- [Ollama Chat](https://docs.ollama.com/api/chat): `model/messages/tools/options/stream` and response identity.
- [Ollama List models](https://docs.ollama.com/api/tags): names, digest and model details; [API reference](https://github.com/ollama/ollama/blob/main/docs/api.md): version endpoint.
- [Ollama Modelfile](https://docs.ollama.com/modelfile): generation parameters.
- [LM Studio Models](https://lmstudio.ai/docs/developer/rest/list): model keys, loaded instances, quantization and configuration.
- [LM Studio compatibility discovery](https://lmstudio.ai/docs/developer/openai-compat/models), [Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions) and [Tool Use](https://lmstudio.ai/docs/developer/openai-compat/tools): discovery and inference messages.
