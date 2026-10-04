# prompt-guard

Inspect untrusted prompt data and model outputs against independent versioned, source-aware policies. Use strict mode to block matching requests or explicitly choose sanitize mode to remove or replace policy-selected fragments and check the result again.

Version 0.3.0 requires Python 3.11+ on Linux or macOS. Runtime uses the standard library. The package runs independently of the repository's skills and other tools. The inspection CLI is offline; the optional provider adapter sends only to its explicitly configured numeric loopback endpoint.

## Modes and outcomes

| Mode | Behavior |
| --- | --- |
| `strict` (default) | Preserve input bytes; a blocking match rejects the whole input. |
| `sanitize` | Apply authorized replacements to a separate result, then scan it again. Original input remains unchanged. |

| Decision | Exit | Application action |
| --- | --- | --- |
| `allow` | 0 | Use the returned payload for the selected policy. |
| `block` | 1 | Stop dispatch. |
| `review` | 2 | Stop automatic dispatch and resolve the signal through application policy. |
| `error` | 3 | Stop dispatch and address the diagnostic code. |

Both `review` and `error` close an admission gate. `allow` means the configured rules accepted this input; it is not a semantic verdict about every possible instruction or an authorization for tool actions. Schema v2 supports per-message and assembled-context rules. Set the assembly separator to the application's actual text composition and inspect every final data round.

## Install and run

Install this directory into an application-owned environment:

```sh
python -m pip install /path/to/prompt-guard
```

Use existing, symlink-free directories. From the installed CLI, replace the paths below with your actual absolute paths:

```sh
prompt-guard --policy /path/to/config/policy.json --config-root /path/to/config \
  --input /path/to/input/sample.txt --input-root /path/to/input --source user

prompt-guard --policy /path/to/config/policy.json --config-root /path/to/config \
  --input /path/to/input/sample.txt --input-root /path/to/input --source user \
  --mode sanitize --output /path/to/results/new-clean.txt --output-root /path/to/results

prompt-guard --policy /path/to/config/policy.json --config-root /path/to/config \
  --input /path/to/input/request.json --input-root /path/to/input --format json
```

The [example policy](examples/policy.json) is a synthetic demonstration, not an approved organizational policy. [unsafe.txt](examples/unsafe.txt) is an intentionally unsafe synthetic token fixture; [safe.txt](examples/safe.txt) is its allowed control. [request.json](examples/request.json) shows the JSON envelope.

Select a packaged profile without a separate configuration file:

```sh
prompt-guard --profile security-and-topics --input /path/to/input/sample.txt \
  --input-root /path/to/input --source user
```

## Attack and topic profiles

Profiles are explicit application policy choices. They contain representative English, Spanish, Russian and Japanese lexical expressions for role spoofing, instruction overrides, hidden-prompt/token disclosure, forged approvals, tool-scope escapes and jailbreak framing.

| Profile | Policy |
| --- | --- |
| [user-input](src/prompt_guard/policies/user-input.json) | User messages; selected command patterns require an initial imperative |
| [retrieval](src/prompt_guard/policies/retrieval.json) | Retrieved/file text; broad instruction markers |
| [tool-results](src/prompt_guard/policies/tool-results.json) | Tool text; broad instruction markers |
| [security](src/prompt_guard/policies/security.json) | Broad attack markers in all data sources and assembled context |
| [restricted-topics](src/prompt_guard/policies/restricted-topics.json) | Strict lexical restrictions on violence, weapons, fraud, credential theft and sexual content involving minors |
| [security-and-topics](src/prompt_guard/policies/security-and-topics.json) | Combined attack and topic rules |

Topic rules block any matching mention, including educational discussion, prevention, reporting, news and quotations. They have no contextual exemptions and authorize no sanitization; a topic match stops the entire request in either mode. A request about phishing prevention is intentionally blocked by `restricted-topics`; public account settings remain allowed. This is a lexical category policy: select and maintain terminology for the application's languages and scope. Security and topic rules have separate category IDs in diagnostics.

The broad `security` profile also blocks quoted attack expressions. `user-input` permits selected explanatory quotes because its imperative patterns are anchored. Paired evaluation counts blocked benign controls explicitly; broad-profile selection does not redefine them as malicious. Packaged profiles are example policies, not approved organizational rules.

Stdout is one JSON diagnostic record with decisions, bounded codes, policy identity, rule IDs, message indexes and match counts. It excludes input text, matched fragments, offsets, raw paths and prompt hashes. Choose nonsensitive policy/rule identifiers; these trusted identifiers appear in diagnostics. Parsing errors also exclude argument excerpts. A sanitize run without `--output` checks the transformation but does not emit the content. A CLI copy is written only on `allow`, using mode 0600 and exclusive creation. Existing destinations are refused. Output must be outside both input and configuration roots. A write error returns `error`; a failed write may leave a partial private file that must not be dispatched.

## Input contract

Text input is a single bounded UTF-8 file, including empty text. `--source` defaults to `user`. JSON input has exactly this shape:

```json
{"messages": [{"source": "user", "text": "Public request"}, {"source": "retrieval", "text": "Public document"}]}
```

Sources are `user`, `retrieval`, `file`, `tool`, and `assistant`. Sources describe provenance, not provider message roles. The application assigns them from trusted routing context; untrusted content must not select its own source. This envelope is distinct from Ollama or Chat Completions wire requests. All keys, sources and types are validated; unknown fields, duplicate JSON keys, nonfinite numbers, invalid Unicode and empty message lists are rejected. CLI JSON input does not accept `--source`.

The CLI checks one file, not a directory. It rejects symbolic link components, hardlinked inputs and nonregular files. Keep input/configuration parent directories under trusted control and use quiet inputs. File reads detect observed metadata changes during reading. JSON sanitization preserves message ordering, sources and text meaning outside selected spans; it reserializes the envelope and can change whitespace/escaping.

## Policy contract

Schema version `1` retains its original fields and raw per-message behavior. Schema `2` adds required `assembly_separator` (a string of at most 16 characters), the `overall_ms` and `memory_mb` limits, and rule fields `view`, `scope` and `category`. Policy IDs, versions, categories and rule IDs use 1–64 ASCII letters, digits, dots, underscores or hyphens, beginning with a letter or digit. Rule IDs must be unique. Each rule has:

| Field | Contract |
| --- | --- |
| `id` | Stable nonsensitive identifier, such as `PG-001` |
| `kind` | `literal` or Python `regex` |
| `pattern` | Nonempty expression, at most 512 characters |
| `ignore_case` | Boolean; Python Unicode case-insensitive matching when true |
| `sources` | Nonempty unique subset of the supported sources |
| `action` | `block` or `review` |
| `replacement` | `null` for no authorized transformation; a literal string for replacement; `""` for removal |
| `view` (v2) | `raw` or `normalized` |
| `scope` (v2) | `message` or `assembled`; assembled rules require `replacement: null` |
| `category` (v2) | Nonsensitive stable category identifier |

Only blocking rules can specify a replacement. In strict mode replacements are ignored. Sanitize mode blocks any blocking match without an authorized replacement. Distinct overlapping transformations block with `overlapping_transformations`; identical span/replacement pairs are deduplicated. Adjacent edits are allowed. Replacement strings never expand regex backreferences. After one transformation pass the whole result is checked again; residual blocking matches stop dispatch and residual review matches require review. There is no iterative removal or automatic approval.

`raw` rules match original text. `normalized` rules use a mapped detection view: format characters (`Cf`, including zero-width and bidi controls) are removed, base/combining clusters undergo NFKC normalization, and case-insensitive rules also casefold. Matches map back to original cluster spans. Sanitization edits those spans and preserves surrounding original text; it does not rewrite the whole input into normalized text. Expansions causing conflicting edits block. Regex authors write patterns for the selected view; literal patterns are normalized automatically. The view does not transliterate arbitrary confusable alphabets or decode base64. Assembled rules concatenate source-selected data messages in order with the configured separator and report `message_index: null`; they can block/review but cannot remove across message boundaries.

## Execution bounds

| Limit | Hard maximum |
| --- | --- |
| Policy bytes | 65,536 |
| Input and transformed payload bytes | 1,048,576 |
| JSON messages | 128 |
| Rules | 64 |
| Matches per scan | 1,024 |
| Worker timeout per scan | 2,000 ms |
| Replacement UTF-8 bytes | 1,024 |
| Overall inspection deadline | 6,000 ms |
| Worker memory budget | 256 MiB (v2 permits 64–256 MiB) |
| Concurrent workers per interpreter | 4; excess requests return `worker_capacity_exhausted` |

Policies may tighten their limits; booleans, zero and larger limits are rejected. Regex compilation, empty-input validation and matching all execute in a worker. Policy construction has a bounded validation pass; inspection uses one scan in strict mode and up to two in sanitize mode under a shared overall deadline. The parent kills and waits for timed-out workers and releases admission slots. Linux uses an address-space resource limit; macOS samples peak resident memory through recurring 10 ms signal checks, so its termination threshold is not an instantaneous allocation ceiling. Worker startup/platform failures close the gate. The worker is an execution boundary, not an OS sandbox for arbitrary policy code. Policies contain expressions, never callbacks. Context-dependent zero-length matches also return errors. Schema v1 uses the same four-worker cap and default 6 s/256 MiB budgets. Inspection budgets are separate from provider execution.

## Pinned policy releases

Use `load_policy(path, config_root=..., expected_id=..., expected_version=..., expected_sha256=...)` for a pinned release. Obtain expected values from separately protected deployment configuration. The digest binds exact file bytes, including whitespace. Wrong identity/version/digest stops loading, with no automatic refresh, repair or unpinned fallback. A loaded policy remains frozen until trusted code selects another release. Rotation and rollback require selecting the approved identity/version/digest together.

The CLI exposes the same selection through `--expected-policy`, `--expected-version` and `--expected-sha256`; supply all three with `--policy`. Packaged `--profile` policies are selected from the installed package; customized pinned releases use an explicit file.

## Library and application integration

```python
import json
from prompt_guard import inspect, policy_from_dict

# Load this object from separately protected application configuration.
policy = policy_from_dict(trusted_policy_object)
result = inspect(policy, b"Public request", source="user")
diagnostics = result.diagnostics()  # Safe metadata only.
if result.decision == "allow":
    checked_input = result.payload  # Use these bytes, including sanitize changes.
```

For the JSON envelope, pass `format="json", source=None`. `policy_from_dict` returns an immutable serialized snapshot; changing the caller's object does not change it. Policy construction raises `GuardError` for invalid configuration. `inspect` returns `error` for execution/input failures. `payload` is available only on `allow`, is excluded from result repr and diagnostics, and must be handled as private content. Unselected sensitive data may still be present in an allowed payload.

Use [application.py](examples/application.py) to dispatch only the accepted bytes. Integrate in this order:

1. Assign trusted provenance and inspect incoming data, including retrieved/tool content at each round.
2. Assemble the model request from accepted payloads and validate the final request with `prompt-integrity` when that package is configured.
3. Authorize every proposed tool operation against actual application permissions before effects.

Keep static instructions and tool definitions in the protected `prompt-integrity` policy. Protect guard policies separately too. Every retry/fallback and new tool round must use the same boundaries; never fall back to an unchecked original after a block/error. Inspection never executes tools.

`prompt_guard.adapters.GuardedDispatch` implements the final data boundary for Ollama `/api/chat` and Chat Completions `/v1/chat/completions`. Create it from a trusted static request template, policy and exact numeric loopback HTTP endpoint. All non-message fields and the static instruction prefix must match. Data roles derive provenance (`user`, `assistant`, `tool`); application-owned `sources={message_index: "retrieval"}` can mark routed documents. Payload fields and embedded text cannot override provenance. Every data message is checked together, replacements enter a separate request snapshot, and block/review/error requests never dispatch. Original request/template objects remain unchanged. `GuardRejected.result` carries the safe decision record.

The default sender uses local HTTP with bounded bodies, no redirects/proxies/retries and a socket timeout. It neither executes tools nor cancels accepted inference. To use `prompt-integrity`, configure `integrity_sender(request, timeout)` to call that package's `verify_and_send` with a protected baseline/transport. This callback owns final-byte dispatch; there is no mandatory sibling dependency. Assistant tool-call metadata is also inspected as serialized data; attempted sanitization of this structured metadata stops dispatch with `metadata_transformation_not_supported`. Protocol/history validation and authorization of proposed arguments/effects remain in the application or integrity layer.

For direct input, call `send_user_text(text, documents=(...))`: this method constructs user roles and retrieval provenance from application routes and never accepts role/source fields from the text. Low-level `prepare`/`send` accept application-assembled wire history, not a client-supplied serialized request. The application owns history and any explicit provenance assignments.

`model-security-eval` supports `--guard-profile`, `--guard-mode` and `--compare-guard` when this package is available. A pair uses the same synthetic canary, scenarios, generation parameters and per-arm budgets; it checks identity across both arms. Reports retain guard decisions separately from model violations and fixture actions, full unguarded evidence, policy/runtime fingerprints and blocked benign controls. A blocked input is `not_assessed_for_blocked_input`, not evidence that the model resisted it. Incomplete/interrupted comparisons close the gate. See the evaluator's guide for CLI commands.

## Checks

```sh
python -m unittest discover -s tests -v
```

Run from this package directory. [corpus.json](tests/corpus.json) contains labeled synthetic multilingual attacks, benign controls and intentional strict-topic blocks. `prompt_guard.evaluation.evaluate_corpus` reports per-category positives/misses/false blocks, separate review/errors, policy fingerprints, descriptive latency and throughput without recording input text. The corpus defines lexical ground truth, not recall on arbitrary real requests.

Repository maintainers can run `python scripts/verify_prompt_guard_package.py --output artifacts/new-package-run` with setuptools 68+ and wheel available. It builds a standalone sdist and wheel, installs offline into a disposable venv, exercises the installed CLI/tests, and records sequential/four-worker measurements. Run these checks in the deployment CI environment on its selected supported Python version.

## Output boundaries

Select a separate output policy and keep it in trusted application configuration.
`output-topics` blocks matched topic mentions in both modes. `output-secrets` detects
private-key blocks (including an unfinished block), selected token shapes and credential
assignments. `output-security-and-topics` combines these. `output-personal-data` is an
explicit email/international-phone profile; selecting it also blocks public contact
examples in strict mode. These are lexical profiles. Exact protected values are supplied
through `protected=(...)`; they are always blocked, including in sanitize mode. Select
encoded variants explicitly when your application's protected-value contract needs them.

```python
from prompt_guard import OutputGuard, load_profile

boundary = OutputGuard.create(
    load_profile("output-security-and-topics"),
    mode="sanitize",
    protected=("SYNTHETIC_APPLICATION_CANARY",),
)
result = boundary.check_text("Public greeting API")
if result.decision == "allow":
    deliver(result.payload.decode("utf-8"))
else:
    deliver("The response was withheld by application policy.")
```

Use an application-owned fallback, never fragments from a rejected result. Output
results expose bytes only on `allow`; diagnostics and repr exclude their content.
A custom output policy must select the `assistant` source. `check_message` accepts
`{"content": text_or_json, "tool_calls": [{"id": ..., "name": ..., "arguments": ...}]}`.
It scans string values in content/arguments, then field names and routing metadata,
with assembled rules also inspecting the combined values. Sanitization changes values
only; modifying names, keys or IDs is refused. The original object is preserved.
Transformed content and arguments must satisfy their contracts again.

### Structured content and tools

`OutputGuard.create(..., schema=..., tools={name: argument_schema})` pins contracts.
Unconfigured tools are denied. A batch is validated completely before any handler runs.
Use `execute_tools(message, executors)` for trusted application handlers, or dispatch
only the calls decoded from an allowed result. The method returns `(diagnostics, results)`;
a rejected proposal returns `results=None`. Tool results must pass the input boundary
before the next model round. Handlers own current authorization, effect deadlines and
transactions; handler failure stops later calls and raises `tool_execution_failed`,
without rolling back earlier effects. Do not accept a handler registry from model data.

The JSON contract subset supports `type`, `enum`, closed object `properties`/`required`/
`additionalProperties: false`, array `items`/`minItems`/required `maxItems`, string
`minLength`/required `maxLength`, and numeric `minimum`/`maximum`. Unknown keywords,
references, regex validators and coercion are rejected. Nesting is limited to 16;
booleans do not satisfy numeric contracts. Bind sensitive paths, recipients and commands
to exact application-authorized enums rather than accepting unrestricted strings.
Contracts validate JSON values; filesystem access still belongs to the trusted handler.

### Provider responses and streaming

Set `output_guard=boundary` on `GuardedDispatch.create(...)`. For `stream: false`,
`send` and `send_user_text` return safe diagnostics and an approved canonical message,
not the original provider envelope. `check_provider(response, "openai" | "ollama")`
provides the same boundary separately. Structured contracts parse the provider's content
as strict JSON. One complete assistant choice is supported; length-limited/truncated
responses, unsupported message fields and malformed argument JSON close the gate.
Multimodal content and additional provider channels require a separately defined contract.

For a trusted template with `stream: true`, call `send_stream(request, emit, timeout=30)`.
It consumes OpenAI-compatible SSE or Ollama NDJSON, collects fragmented tool arguments,
requires the terminal protocol marker, validates the completed message and invokes `emit`
once only on `allow`. No raw protocol event reaches the caller. The local sender uses
numeric loopback HTTP, bounded input, explicit content types, socket read timeouts, a whole-transport shutdown deadline and
no redirects/retries. The iterator closes on completion or rejection. An integrity-backed
stream requires an explicit `stream_sender` that owns final-byte integrity verification.
The wire contracts follow [Chat Completions streaming](https://developers.openai.com/api/reference/resources/chat)
and [Ollama streaming](https://docs.ollama.com/api/streaming).

For application-decoded text chunks, `boundary.stream(chunks, emit, delivery="buffered")`
accepts UTF-8 bytes or strings, including split Unicode sequences. Buffered delivery
holds the entire answer until acceptance and supports both modes, regex, normalization
and assembled policies. Default limits are 4,096 chunks, 1 MiB and 60 seconds between
iterator reads; custom iterators must enforce their own blocking-read timeout.

`delivery="delayed"` is an explicitly selected text-only option for raw case-sensitive
literal rules. It checks accumulated text and retains the longest possible partial-match
tail. Arbitrary regex, normalization, assembled rules and sanitize replacements require
buffered delivery and return `stream_policy_requires_buffering` before reading data.
Delayed delivery can stop later output but cannot retract an earlier approved prefix;
use buffering for whole-answer rejection on any topic mention. Diagnostics include
`emitted_characters`, never emitted text. Emitter/iterator failures stop delivery without
fallback. A callback should commit the approved fragment atomically.

The offline CLI accepts `--direction output`. Text is assigned to `assistant`; JSON is
a canonical output message. `--output-contract /path/to/config/contract.json` requires
`--config-root` and exactly `{"schema": ..., "tools": ...}`. A separate approved copy can
be written with `--output`/`--output-root` in either output mode. Input files are preserved.

```sh
prompt-guard --direction output --profile output-security-and-topics \
  --input /path/to/input/answer.txt --input-root /path/to/input
```

Use `model-security-eval --output-guard-profile output-security-and-topics --compare-guard`
for paired output evaluation, optionally together with an input profile. Reports retain
raw-generation violations as redacted evidence separately from released outputs, output
guard decisions and virtual effects. Blocking a model violation can pass the application
control while the generated model violation remains recorded. Blocked benign controls
fail; output execution errors are inconclusive. The evaluator protects the fixture canary
and selected encoded variants and binds tool arguments to its synthetic authorized scope.
