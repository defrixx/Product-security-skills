# prompt-integrity

Static instruction verification at the final model-request dispatch boundary. Version 0.1.0. Static prompt MVP implemented with property, CLI and local HTTP integration tests, plus isolated installed-wheel verification. Requires Python 3.11+ and POSIX for filesystem operations. Runtime uses only the standard library.

## Install and use

Install this directory into an application-owned environment with `python -m pip install /path/to/prompt-integrity`. No skills or repository imports are required. Installation is a user/deployment action; the CLI never installs anything.

All example files are synthetic. From this package directory, use an absolute, symlink-free configuration root and file paths (replace `/path/to/examples` with its real path):

```sh
prompt-integrity baseline validate --baseline /path/to/examples/baseline.json --config-root /path/to/examples --expected-profile synthetic-support --expected-version 1
prompt-integrity request check --baseline /path/to/examples/baseline.json --request /path/to/examples/request.json --target primary --config-root /path/to/examples --expected-profile synthetic-support --expected-version 1
prompt-integrity baseline create --instructions /path/to/examples/instructions.json --policy /path/to/examples/policy.json --output /path/to/examples/new-candidate.json --config-root /path/to/examples --expected-profile synthetic-support --expected-version 1
```

Create emits a candidate, not approval. Existing destinations are refused. Exit 0 means the selected operation succeeded, 2 means a request failed integrity policy, 1 means configuration/I/O/resource/internal error. No CLI command calls a model. Original inputs remain unchanged. No payloads, raw paths, exception excerpts, or prompt hashes are logged.

## Library and trust boundary

```python
from prompt_integrity import load_policy, verify_and_send
from prompt_integrity.transport import HTTPTransport

policy = load_policy(
    "/protected/baseline.json", "synthetic-support", "1",
    config_root="/protected",
)
transport = HTTPTransport((("primary", "http://127.0.0.1:11434/api/chat"),))
# request is assembled by the application; this is the final outbound boundary.
# response = verify_and_send(policy, request, "primary", transport)
```

This example does not start a server. The included models are synthetic and not deployable model names. Supply approved real model mappings in your private baseline before actual use. `HTTPTransport` sends immutable bytes directly; it performs no redirects, proxies, SDK reconstruction, implicit retries, or fallback. HTTPS uses the platform certificate verification; cleartext endpoints are restricted to loopback. It returns bounded response bytes; interpret responses separately.

Route every application model call, job, retry, and fallback through `verify_and_send`. Each attempt checks the actual chosen alias/model and immutable snapshot. The application must not mutate inputs concurrently while the snapshot is being created. There is no global shared request state. A downstream custom transport is trusted and must send the supplied bytes to the approved target without modification. A caller bypassing the wrapper is outside its control.

`check_request` is diagnostic only; its result does not authorize later use of a mutable object. `IntegrityError` occurs before dispatch, while `TransportError` means a transport operation failed after a successful check. Neither permits falling back to an unchecked request. An earlier successful attempt cannot be recalled.

## Supported wire contract

Adapter `ollama-chat-text-v1`, version `1`, targets the documented Ollama `POST /api/chat` JSON shape. The supported subset requires exactly `model`, `messages`, and `stream: false`. Each message has exactly `role` and string `content`. The trusted prefix contains one or more exact `system` messages; only policy-selected `user`/`assistant` messages may follow. All other fields and content types are rejected, including tools, images, options, remote references, and extra instruction fields. This is a deliberately bounded adapter, not compatibility with every Ollama feature or other vendor's message format.

Source: [Ollama Generate a chat message](https://docs.ollama.com/api/chat), request body model/messages/stream and optional fields, checked 2026-09-30. The locally versioned adapter contract is not an upstream API version guarantee. Runtime baseline: [Python supported versions](https://devguide.python.org/versions/), checked 2026-09-30; Python 3.11+ selected independently of this repository's older helper runtime.

Exact matching preserves whitespace, newlines, case, and Unicode distinctions. Equivalent JSON escaping/key order may differ while decoded text remains equal. User text that says “ignore prior instructions” is still permitted data when in its allowed role; this tool does not classify prompt injection or prove model obedience.

## Policy and release lifecycle

The complete baseline schema is illustrated by `examples/baseline.json`. Unknown fields/versions and duplicate JSON keys are rejected. `allowed_targets` maps trusted aliases to exact model strings; endpoints are separately configured in the transport. `allowed_request_fields` must be the fixed stream-false constraint for this adapter. Limits can be tightened but cannot exceed the documented hard ceilings: 1 MiB baseline, 4 MiB request, 256 messages, depth 32, 100,000 nodes, 256 KiB per string. These are engineering resource bounds.

Keep baselines protected separately from mutable application input, with expected profile/version supplied by trusted deployment configuration. A directory being outside the source tree does not establish protection. The runtime principal must not be able to rewrite its approved baseline through untrusted paths. The library loads a frozen in-memory policy; no watcher, automatic refresh, learning, or approval occurs. Updating or rolling back requires an explicitly selected release and process restart/reload by trusted deployment code. Historical version existence is not authorization to use it.

Baseline contents are sensitive configuration. Review candidate content and promote it with normal release controls. Schema validation does not authenticate provenance; neither a digest nor a matching version proves approval. No signed-distribution or template feature is implemented. Filesystem access refuses symlink components, nonregular inputs and input hardlinks, and requires explicit roots. Use quiet inputs and trusted parent directories; hostile concurrent filesystem replacement is outside the guarantee. Failed candidate writes can leave a partial private file; validation must precede promotion and a retry needs a fresh destination.

## Limits and validation

This checks observable request integrity, not prompt safety, output safety, tool authorization, hidden provider instructions, or a compromised process. An attacker controlling both the baseline and checker can bypass it. Application/SDK logs outside the wrapper require their own review.

Run `python -m unittest discover -s tests -v` from this package directory. Fixtures use synthetic prompts and transport spies; no model credentials, server, or external checkout is required. Before deployment, inspect every request call site and any transport interceptor for bypass or post-check mutation.
