# Bifrost application boundary

Use Bifrost OSS's OpenAI-compatible `POST /v1/chat/completions` through an
application-owned Prompt Guard boundary. Existing skills and tools retain their
interfaces and can be used independently. No Bifrost fork or Enterprise
Guardrails subscription is required for this adapter.

## Run

Use Python 3.11+ and the existing Prompt Guard source or installed package:

```sh
export PYTHONPATH="$PWD/tools/prompt-guard/src:$PWD/integrations/bifrost"
python3 integrations/bifrost/example.py
```

The example uses a synthetic policy pinned by digest and sends to a locally
configured gateway at `http://127.0.0.1:8080`. Configure the real provider/model
in trusted application code; `ollama/local-model` is an example route, not model
discovery. Select an application policy and pin its independently approved ID,
version and SHA-256 using `load_policy`; the synthetic policy is a test fixture.
Construct `OutputGuard` in strict mode. The transport accepts an optional trusted
virtual-key token; never obtain endpoints, credentials, policies or routes from
model output or untrusted request data.

`GuardedClient.complete(records)` takes UTF-8 JSON bytes in Prompt Guard's closed
contract:

```json
{"messages": [{"source": "user", "text": "Hello"}]}
```

The application assigns source labels (`user`, `retrieval`, `file`, `tool`). They
select inspection rules; every accepted record becomes a user message, never a
system or tool privilege. The optional system instruction is trusted construction
configuration and is also inspected. Caller records cannot set roles, model,
headers, fallback routes, streaming, tools or arbitrary provider parameters.
The result is checked assistant text only. Catch `BoundaryError` and stop the
operation; do not catch it and retry outside the boundary. Errors contain fixed
codes rather than raw input, output or credentials.

The default transport supports literal loopback HTTP addresses only. Run it in
the same trusted host/network namespace as the gateway. It bypasses environment
proxies, rejects redirects and non-JSON responses, bounds response bytes and
transport time, and performs exactly one HTTP request. A connection failure can
have an uncertain server-side outcome, so it is never retried by this client.

## Enforcement scope

The original `GuardedClient` is an **opt-in application boundary** for text chat. Direct requests to
Bifrost bypass it; restrict gateway network access and credentials to the
application if all application traffic must cross this boundary. It does not
install a gateway-wide control. All non-allow input/output results
and inspection failures stop the application operation. Streaming, multimodal
content, tool execution and arbitrary response-envelope fields are outside this
contract. Only checked assistant content is released. Schema-invalid or
incomplete responses are rejected. Bifrost's serialized `refusal: null` is
removed before the strict decoder; non-null refusal is rejected. A custom transport is trusted application
code and must provide its own time/size limits.

Gateway caches, retries, key rotation and fallbacks remain gateway configuration.
They cannot skip this client's input check or final output check, but can change
which provider receives accepted input. Pin/disable routing alternatives and
caching where deployment policy requires it, and restrict direct gateway access.
This client neither enforces a gateway-wide policy nor attests to the selected
provider, model revision, internal calls or final provider payload bytes.

## Explicit reasoning-aware output

`GuardedClient(..., reasoning_mode="inspect-and-drop")` enables the supported
Bifrost reasoning-text response contract. The default remains `"reject"`.
The mode is trusted application configuration; request data cannot select it.

The visible content and all accepted reasoning strings are inspected together
with the exact effective strict OutputGuard policy, including protected-value
rules. Configured assembled rules can span those fields. Any block, review,
error or resource-limit decision rejects the entire response. The original
OutputGuard then checks the final message with its existing schema/tool contract.
Only checked `message.content` is released. Supported structured reasoning
fields are removed and neither returned nor logged, even when they pass
inspection. The adapter does not classify arbitrary prose or embedded tags
inside `content` as reasoning; that visible content still crosses OutputGuard.

Accepted fields are string/null `reasoning` and `reasoning_content`, plus at most
16 uniquely indexed `reasoning_details` entries of `reasoning.text` or
`reasoning.summary` with string text/summary and optional string ID. Conflicting
nonempty reasoning aliases, unknown fields, encrypted/signed/content-block
reasoning, malformed details, incomplete responses and tool calls are rejected.
This is a bounded text/summary contract, not a universal reasoning-provider API.
Existing policy limits also bound the combined inspection.

For the facade example, set the trusted environment variable
`BIFROST_REASONING_MODE=inspect-and-drop` before starting the process. A deployment
can use `dataclasses.replace(client, reasoning_mode="inspect-and-drop")` directly.
The mode changes response handling only; it does not disable model reasoning or
change user model/server settings.

## Scoped HTTP ingress facade

`ingress.py` exposes a token-authenticated HTTP facade around the composed
Prompt Guard + Prompt Integrity client. Start the local synthetic example with
an application-owned `BIFROST_INGRESS_TOKEN` of 32–256 printable non-space ASCII
characters:

```sh
export PYTHONPATH="$PWD/tools/prompt-guard/src:$PWD/tools/prompt-integrity/src:$PWD/integrations/bifrost"
python3 integrations/bifrost/example_ingress.py
```

The listener is `127.0.0.1:18080`. Supply `Authorization: Bearer <token>` and a
JSON request matching the pinned integrity baseline: model, pinned system
instruction followed by user messages, and exactly the approved `stream`,
`temperature`, `max_tokens` and empty `tools` fields. The synthetic example
baseline supplies these values. Existing clients need to adopt this closed
contract; arbitrary OpenAI options are not forwarded.

Only `POST /v1/chat/completions` is accepted. Other routes/methods, routing headers,
duplicate headers, chunked request bodies, oversized bodies and unapproved
parameters are rejected before any upstream request. Read deadlines include
headers and body; concurrent request workers are bounded. Incoming credentials
and headers are never forwarded. An allowed response contains checked assistant
text and a fresh facade envelope; its `model` identifies the configured route,
not an attested provider revision. Input rejection returns 403; rejected upstream
output returns 502. Both use fixed diagnostic codes without original content.

This facade protects requests **through its listener**. Mandatory deployment
requires publishing only that listener and preventing application clients from
reaching Bifrost directly. The facade and gateway may share a private network
namespace with Bifrost bound to loopback and only the facade port exposed by
trusted deployment configuration. A non-loopback facade listener requires the
explicit `allow_network_listener=True` option; that deployment owns TLS and
access control. Administrators/processes inside the trusted namespace can still
reach Bifrost. No network topology is created by the library.

The facade is an external HTTP boundary, not a native Go plugin or a control over
all Bifrost APIs. Its ingress-byte guarantee ends before Bifrost transformations;
provider egress integrity, cache/fallback admission and model revision attestation
retain their separate contracts. Do not expose unsupported gateway endpoints
alongside this facade and call the deployment protected by it.

## Mandatory reference path and final-provider integrity

`egress.ProviderBoundary` implements the final provider send for the selected
`openai-provider-text-v1` contract. It pins one model, system instruction and
exact `temperature` / `max_completion_tokens` options. Input also crosses Prompt
Guard. `verify_and_send` owns the snapshot, validation, final serialization and
single fixed-endpoint send. No JSON reassembly occurs after that check. The
optional trusted observer receives only the SHA-256 of the verified bytes.

The service checks response model binding, complete text output and supported
reasoning with the configured OutputGuard. Only checked final content is relayed;
reasoning, raw provider envelopes and unverified usage metadata are removed.
Failures stop the operation without retrying an uncertain model-side outcome.
The model string is an endpoint response binding, not weights/revision attestation.

The local synthetic example is:

```sh
export PYTHONPATH="$PWD/tools/prompt-guard/src:$PWD/tools/prompt-integrity/src:$PWD/integrations/bifrost"
python3 integrations/bifrost/example_egress.py
```

It requires an application-owned `BIFROST_PROVIDER_TOKEN` (32–256 printable
non-space ASCII characters), listens on loopback port 18081 and sends to a
synthetic backend on loopback port 18082. The provider baseline is digest-pinned.
For Bifrost v2.4.0's OpenAI-base provider, use origin
`http://<egress-address>:18081` as `network_config.base_url`; this gateway adds
`/v1/chat/completions`. Adding `/v1` to that base URL doubles the path and is
rejected by the strict egress listener. Configure the provider key to the egress
token. The service does not forward incoming credentials to the final model.

A checked reference topology separates these roles:

| Role | Networks | Published host ports |
| --- | --- | --- |
| Ingress facade | client-facing + private gateway | facade only, on host loopback |
| Bifrost | private gateway only | none |
| Final egress service | private gateway + private model | none |
| Model | private model only | none |

Both private networks are internal. Only the facade accepts application traffic.
The final model is unreachable from Bifrost's namespace; the provider URL points
to the egress service. Gateway and model credentials remain separate. Trusted
Docker/host administrators and service processes are outside the untrusted-client
boundary. Production remote ingress requires deployment-owned TLS and access
control; the reference test publishes only on host loopback.

`PrivateNetworkTransport` supports a trusted fixed numeric RFC1918 endpoint on an
explicit `/24`–`/30` network for this topology. It requires an explicit port,
rejects DNS/public/link-local addresses and retains the bounded no-proxy,
no-redirect, no-retry HTTP behavior. This is cleartext on a dedicated trusted
virtual network, not a general remote HTTP transport. Endpoints/CIDRs and
credentials must never come from model output or request data.

With an approved Docker installation and the exact Bifrost image and
`python:3.11-slim` already provisioned locally, run:

```sh
python3 scripts/run_bifrost_isolated_trial.py --output artifacts/bifrost-isolated-NEW
```

Run with non-optimized Python: `-O`, `-OO` and optimization-enabled
`PYTHONOPTIMIZE` are rejected before any output directory or Docker action. Required trial properties use
explicit failure checks, independent of Python assertion optimization.

The runner uses `--pull=never`, resolves the cached Python image to an immutable
local ID, creates uniquely labeled temporary resources and journals their names
before creation. It exercises real Bifrost with a synthetic model oracle, compares
verified and received byte hashes, probes client/gateway bypasses and tests
instruction/options/tools/output failures. It removes only its labeled containers
and networks and preserves private evidence. It neither installs software nor
starts/stops Docker or removes pre-provisioned images.

The tested configuration disables gateway retries, cache plugins and alternate
routes/keys and uses file-only configuration. The default trial proves the selected non-streaming text path. The explicit
agent profiles below test buffered streaming and tool proposals. Other providers,
deployed cache-hit or fallback/key-rotation combinations require their own
contracts and verification. A different deployment is not protected merely by importing these
classes. Model Security Eval still does not issue weights/revision admission.

## Buffered streaming and authorized tools

`agent_boundary.AgentBoundary` is an additional closed chat contract. The original
text client and existing direct Ollama/LM Studio adapters retain their behavior.
Select `bifrost-chat-agent-v1` at ingress and `openai-provider-agent-v1` at final
egress in separately approved Prompt Integrity policies. Pin the exact system,
model, tool descriptions/JSON schemas, temperature and token limit. Set
`data_message_policy.roles` to `user`, `assistant`, `tool`. Gateway options are
exactly `stream`, `temperature`, `max_tokens`, `tools`; provider options use
`max_completion_tokens` and omit `stream` for JSON. Streaming provider options
include `stream: true`; `stream_options: {"include_usage": true}` is supported
only when explicitly pinned. Offered names must match strict OutputGuard tool
contracts. Use the same authenticated `IngressServer` at both boundaries.

`example_agent.py gateway` and `example_agent.py provider` start separate
loopback listeners using digest-pinned synthetic streaming policies and the same
`BIFROST_INGRESS_TOKEN` / `BIFROST_PROVIDER_TOKEN` variables as the text examples.
Use the `PYTHONPATH` shown above. They offer only the synthetic `read_record`
schema and execute nothing. Approve application policies and deployment endpoints
before adapting these examples; the example tokens are supplied by the operator.
The provider endpoint is the loopback model on port 18082, the gateway on 8080.

The transport buffers the **entire** upstream SSE response within the existing
byte/deadline limits. No downstream headers, chunks or tool calls are released
before complete framing, finish status, assembled arguments, reasoning and
visible output pass checks. The boundary emits a fresh bounded SSE envelope with
checked content/tool proposals and `[DONE]`; original reasoning, usage and routing
metadata are discarded. This supports SSE consumers but adds full-response
latency and provides no incremental token delivery. Incomplete streams, unknown
reasoning formats, ambiguous indices, length truncation and malformed arguments
fail closed. `reasoning_details` must be an array even when empty. Any stream
event containing an `error` field rejects the complete operation, including a
terminal usage event. Split secrets are inspected after assembly. The JSON contract also
validates Bifrost's positional tool-call indices before removing them.

A tool proposal is **not permission to execute**. `tool_gate.ToolGate` accepts a
canonical checked message, validates tool arguments against the owned schemas,
and issues a one-shot `ToolBatch`. `execute(batch, authorize=..., executors=...,
context=...)` requires an application-owned authorizer returning exactly `True`
for every call before any effect, and again immediately before each call. The
callback receives the authenticated principal/context and a copy of the call;
never derive authorization from model prose, tool arguments or a bearer token
supplied by the model. The executor mapping is application-owned. No shell,
imports, network destinations or executable code are selected dynamically here.

Executors receive `(arguments, idempotency_key)` and must return bounded JSON
**bytes**. Results cross Prompt Guard as tool input before `ToolOutcome.messages()`
can be added to trusted conversation history. The application explicitly sends
the next model round; the library never loops or retries automatically. History
must belong to the authenticated workflow and its stored checked proposals and
results; the stateless facade does not authenticate caller-supplied history or
turn its tool-role records into trusted execution evidence. All history remains
untrusted input. Do not expose a tool executor by treating arbitrary facade history
as proof that a previous action was approved.

The trusted executor must implement its own I/O bounds, effect-side atomic
authorization and durable idempotency. The in-memory gate prevents local batch
replay and policy drift within one workflow, but cannot roll back external
side effects or guarantee exactly-once effects across process restarts. On error,
`ToolGateError.attempted`, `.completed` and `.effects_may_have_occurred` distinguish
possible partial effects; no automatic retry is safe. Keep a gate per workflow
and restrict mutating tools to executors with an appropriate transaction/approval
contract. The synthetic reference trial executes only an in-memory read fixture.

Run the additional provisioned-image trials separately:

```sh
python3 scripts/run_bifrost_isolated_trial.py --agent-profile json --output artifacts/bifrost-agent-json-NEW
python3 scripts/run_bifrost_isolated_trial.py --agent-profile stream --output artifacts/bifrost-agent-stream-NEW
```

These profiles exercise the actual pinned Bifrost image, fixed tools, explicit
authorization, checked results and a second completion, alongside the original
network, final-wire and output rejection probes. The backend is synthetic; this
does not certify every provider's streaming or tool schema dialect.

## Completion receipt verification

`model_receipt.ReceiptVerifier` checks a bounded first-party HMAC claim against
an independently provisioned issuer key. A fresh request nonce, exact request
and response hashes, provider ID, model/runtime revisions and route-policy digest
must match an owned `ReceiptExpectation`. Unknown issuers/revisions, expired or
future-dated claims, fallback identity, changed configuration/body and replay
are rejected. Ordinary Bifrost/LM Studio responses do not supply these receipts.

A verified claim establishes the issuer's bound statement, not which weights
actually served the completion. The result always has **`weights_attested=false`
and `eligible=false`**. Model names, server metadata and file hashes are not
accepted as proof of actual loaded weights. This integration provides no
weights-attestation guarantee or automatic model-admission permit.

Requiring Model Security Eval admission continues to reject **before any model
send**, including for matching offline evidence. Receipts and metadata cannot
override that decision. The separately documented Guard/Integrity path retains
its own request/output protection contract without claiming model admission.

## Stage the five skills

```sh
python3 integrations/bifrost/stage_skills.py /tmp/product-security-skills-import
```

Choose a new destination with an existing parent. This creates five independent
skill folders and a SHA-256 manifest from the local checkout without changing the
skills. Use a trusted, quiescent checkout; inspect the staged files before import.
The script rejects links/special files and existing destinations and excludes
Python cache files. It performs no network action or publication.

In Bifrost's Skills Repository dashboard, create each skill with its existing
frontmatter name/description, paste the Markdown **body** into the editor, and
upload its supporting `references`, `assets`, and `scripts` folders with their
relative structure. Bifrost generates frontmatter from the editor's metadata;
transfer any additional frontmatter fields too. Review then explicitly publish
a version only when authorized. Do not upload `manifest.json` as a sixth skill.
Hosting a skill supplies instructions to the harness; it does not execute the
security tools or establish mandatory gateway enforcement.

## Opt-in Prompt Integrity at gateway ingress

```sh
export PYTHONPATH="$PWD/tools/prompt-guard/src:$PWD/tools/prompt-integrity/src:$PWD/integrations/bifrost"
python3 integrations/bifrost/example_integrity.py
```

`GatewayIntegrity` composes the existing `verify_and_send` operation with the
client's single transport call. Its closed contract pins the route model, system
instructions, non-streaming options, token limit and empty tools list. The alias
is the only allowed target; additional fallbacks, role elevation and request
fields are rejected. The example loads a synthetic baseline using an independently
written SHA-256 pin. Replace this with an application-owned approved baseline
and trusted endpoint/credentials; do not derive an approval pin from a candidate
request or regenerate the policy to match untrusted instructions.

The existing `lmstudio-chat-tools-v1` adapter ID denotes the supported wire
request grammar reused here. It does not identify Bifrost as LM Studio. The
verifier-generated bytes go directly to the gateway transport without a second
send or downstream JSON reassembly in this client. An integrity failure results
in zero gateway requests. The optional integrity configuration does not alter
standalone Prompt Integrity interfaces.

This attests only to the checked request bytes sent **to Bifrost ingress**.
Gateway transformations, plugins, cache, keys, retry and fallback behavior remain
outside this boundary. Final-provider-byte integrity still requires verification
where the final payload is serialized and sent. Keep the existing direct Ollama
and LM Studio transports for their original contracts. Never verify-and-send
there and then send the same operation through Bifrost again.

## Model Security Eval on a gateway text route

```sh
export PYTHONPATH="$PWD/tools/model-security-eval/src:$PWD/tools/prompt-guard/src:$PWD/integrations/bifrost"
python3 integrations/bifrost/evaluate_route.py \
  --endpoint http://127.0.0.1:8080 --model ollama/local-model \
  --reported-model local-model --output artifacts/gateway-route-evaluation-NEW
```

This explicit command sends bounded synthetic chat trials through the actual
configured gateway HTTP endpoint. Only `chat` capability is selected, with no real
tool execution. The existing evaluator's OpenAI-style `lmstudio` wire codec is
reused; native model discovery is not attempted against the gateway. The required
`--reported-model` is caller configuration and is checked against every response,
including tool rounds and refusals. It is not provider revision attestation.
Endpoint, requested route, reported model, budgets and integration fingerprint
are bound into evaluation criteria. `RouteConfig.token` supports trusted
programmatic virtual-key configuration and is omitted from reports.

Reports preserve actual case results and failures. Their identity source clearly
states caller-configured gateway-route binding. They always set `eligible=false`:
observed failures produce `fail`/exit 1; otherwise the aggregate is
`inconclusive`/exit 2 because internal provider identity/routing are not attested.
Use case results for behavioral investigation; do not reuse this as a deployment
admission token or silently turn exit 2 into success. Direct-backend evaluation
and this gateway-route evaluation retain separate identities and contracts.

## Evaluation evidence and route-release binding

`admission.RouteSnapshot.capture` binds owned route/configuration data to the
actual frozen egress objects: provider endpoint/model, transport limits,
integrity baseline, effective input/output policies and output contracts. It
also fingerprints the relevant implementation source. The snapshot requires an
explicit route version and gateway image digest, a file-only configuration,
one OpenAI-base provider/key, no retry/cache plugins and no fallback configuration.
Credential values in the gateway file must be `env.NAME` references. A private
egress origin also requires its explicit `egress_network` CIDR; URLs are origin-only,
so an extra `/v1` is rejected. A nonempty
final-provider credential requires an independent 32–64 byte private
`credential_hmac_key`; only its HMAC is included, never the credential or key.

`EvaluationBinding.create(report_bytes, snapshot, report_sha256=...,
model_revision=..., criteria_sha256=...)` validates an independently approved
report pin, criterion pin, complete case inventory and all-pass native evaluation.
The supported revision evidence is the same exact direct Ollama endpoint/model,
a known SHA-256 model digest observed consistently before/after evaluation and
matching server-version metadata. LM Studio caller assertions, reported model
alone, unknown revision, changed metadata, incomplete results and unproven
namespace/endpoint remapping are rejected. Do not calculate an approval pin from
a candidate report and treat that calculation as approval.

`binding.assess(current_snapshot)` reports offline evidence compatibility and
always sets **`eligible=false`**. A matching report/snapshot does not establish
Bifrost's loaded runtime configuration or which weights served a completion.
Model-server metadata is also an assertion by that selected server. No boolean,
report field or configured model name upgrades these facts into runtime admission.

`evaluate_route(..., binding=binding, snapshot_reader=trusted_reader)` checks the
release snapshot before evaluation and before each synthetic request. A changed
snapshot prevents further sends; the final report includes the binding fingerprint
and drift result. The reader must capture owned configuration and current frozen
boundary objects, never accept request/model-supplied snapshots. A configuration
file fingerprint does not attest that the running gateway loaded that file.

An egress may explicitly require `ProviderBoundary(..., admission=binding,
admission_snapshot=trusted_reader)`. With the currently supported evidence this
fails closed **before any model send**, including when offline evidence matches.
The verifier issues no automatic allow permits. Omit this requirement only when
operating the separately documented Guard/Integrity path without claiming Model
Security Eval admission. This integration does not verify actual serving weights
or issue automatic model-admission permits.

## Verification commands

Run these commands from the repository root with Python 3.11+.

### Focused application-boundary suite

```sh
python3 -m unittest discover -s tests -p test_bifrost_integration.py -v
```

This command runs only `test_bifrost_integration.py`: text-client input/output
checks, transport behavior, local HTTP handling and skill staging. It uses real
Prompt Guard workers, synthetic records and a local HTTP server fixture; it does
not run a Bifrost binary or prove gateway routing behavior.

### All local Bifrost suites

```sh
python3 -m unittest discover -s tests -p 'test_bifrost_*.py' -v
```

This discovers every local Bifrost test module: the focused suite, ingress and
egress, Prompt Integrity composition, route evaluation, reasoning, buffered SSE,
tool authorization, receipt verification, admission binding and runner failure
checks. Tests use synthetic fixtures and local HTTP services. Runner failure
checks use a child-process Docker double; real-gateway trials run separately.

### Standalone Prompt Guard and Prompt Integrity suites

```sh
python3 -m unittest discover -s tools/prompt-guard/tests -v
python3 -m unittest discover -s tools/prompt-integrity/tests -v
```

These run each tool's own suite directly, including provider-output/SSE checks
for Prompt Guard and pinned request-byte/adapter checks for Prompt Integrity.

### Repository structure

```sh
python3 scripts/validate_structure.py
```

This checks skill/tool structure, frontmatter, relative resources and requirement
identifiers. Behavioral checks are supplied by the test suites above.

### Full repository regressions and evidence

```sh
python3 scripts/run_regressions.py --output artifacts/bifrost-regressions-NEW
```

This discovers `tests/` and `evals/tests/`, including the Bifrost and standalone
tool suites, and records synthetic Git/SQLite exercises and structured evidence.
Choose a new output directory for each run.

### Real Bifrost reference trials

With Docker and the pinned Bifrost image plus `python:3.11-slim` already
provisioned as described in the reference-path section, run:

```sh
python3 scripts/run_bifrost_isolated_trial.py --output artifacts/bifrost-text-NEW
python3 scripts/run_bifrost_isolated_trial.py --agent-profile json --output artifacts/bifrost-tools-NEW
python3 scripts/run_bifrost_isolated_trial.py --agent-profile stream --output artifacts/bifrost-stream-NEW
```

The default profile checks the text path; `json` adds tool proposals, explicit
authorization and checked results; `stream` checks the buffered SSE/tool path.
Each trial runs the real pinned gateway with a synthetic model oracle and probes
final-provider bytes, isolation and rejection behavior. Each writes its own new
evidence directory and cleans up its labeled containers and networks.

## Contract references

The reproducible runtime trials pin Bifrost **v2.4.0**, Linux ARM64 manifest
`sha256:5197ad08ddd34b3a60ac2c548cb84945f106e9ec49d549b644e4491debf75f53`
and [release source](https://github.com/maximhq/bifrost/tree/e869c3f9adc96ea53c38694a21bb04a8e1085487).
The runner contains the complete immutable image reference. It uses only
pre-provisioned images; image acquisition is an operator action.

Reviewed 2026-11-04 against upstream revision
`170e5086e0b6abdf4121653d10f40b52af7e36d7`:

- [Bifrost OSS quick start](https://github.com/maximhq/bifrost/tree/170e5086e0b6abdf4121653d10f40b52af7e36d7): OpenAI-compatible chat endpoint.
- [Plugin contracts](https://github.com/maximhq/bifrost/blob/170e5086e0b6abdf4121653d10f40b52af7e36d7/core/schemas/plugin.go): per-attempt PreLLM hooks, explicit short circuit and non-blocking Go errors.
- [Chat response serialization](https://github.com/maximhq/bifrost/blob/170e5086e0b6abdf4121653d10f40b52af7e36d7/core/schemas/chatcompletions.go): `ChatAssistantMessage.Refusal` has no `omitempty`, including for text-only responses.
- [Skills Repository](https://github.com/maximhq/bifrost/blob/170e5086e0b6abdf4121653d10f40b52af7e36d7/docs/features/skills-repository.mdx): metadata/body separation and supporting-file imports.

The HTTP adapter uses the documented wire contract rather than Go plugin ABI.
