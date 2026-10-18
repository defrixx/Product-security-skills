# Model Context Protocol security

## SD-MCP-001

Status: proposed baseline; C01–C06 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Record protocol revision, SDK version, transport, deployment, and identity model. HTTP OAuth requirements do not automatically apply to stdio. Select the 2026-07-28 checks or an explicitly versioned legacy profile; session/resumable checks remain applicable to older revisions such as 2025-11-25. Examples are synthetic local scenarios.

### SD-MCP-001.C01 — Authorize each tool operation and resource

- **Apply when:** an MCP server exposes tools or resources with restricted effects or data.
- **Required / prohibited:** enforce the caller's permitted operation and resource scope at the server boundary. Tool visibility, a client approval dialog, or valid JSON schema does not replace authorization.
- **Rationale:** a modified client can invoke tools directly with another user's resource identifier.
- **Implement:** resolve authenticated identity independently of tool arguments, validate schema, and check operation/object permissions before effects. Apply [authorization](authorization-access-control.md) and [input](input-validation-injection.md) conditions to the handler.
- **Unsafe → corrected:** trust a `user_id` argument to select private documents → resolve the principal from the authenticated context and authorize the requested document.
- **Positive check:** an authorized synthetic principal can invoke the tool on its permitted resource.
- **Negative check:** a direct call with an unauthorized resource or operation produces no protected read or mutation, even when the tool name and schema are valid.
- **Evidence:** identity-to-handler-to-effect trace; executed direct tool requests and state observations. A hidden client menu is not server evidence.
- **Bounds / sources:** S1, Scope Minimization and confused-deputy guidance. Local single-user servers still need explicit file/process capability boundaries.

### SD-MCP-001.C02 — Keep authorization tokens bound to their resource

- **Apply when:** HTTP MCP authentication uses bearer tokens or a proxy calls downstream APIs.
- **Required / prohibited:** validate that incoming tokens are issued for the MCP resource and satisfy its authorization policy; do not pass arbitrary client tokens through to downstream services.
- **Rationale:** token reuse across trust boundaries can turn a proxy into an unauthorized deputy.
- **Implement:** use the authorization server's supported validation mechanism and separate downstream credentials/authorization. For proxy authorization flows, bind consent to the actual client and requested permissions; validate registered redirect and callback state. For 2026-07-28, persist pre-registered and DCR client credentials under the issuing authorization server's `issuer`, not merely the MCP endpoint. When protected resource metadata selects a different issuer, never send the previous issuer's credentials: obtain registration for the new server; surface a mismatch for pre-registered credentials rather than silently reusing them. CIMD HTTPS client IDs are portable and need no re-registration on issuer change; this does not make issuer-issued tokens or credentials portable.
- **Unsafe → corrected:** forward any supplied bearer token to an API → reject a token for the wrong resource and obtain appropriately scoped downstream authorization through the intended flow.
- **Positive check:** a token for the intended MCP resource and allowed scope succeeds. Credentials selected for the recorded issuer work; a supported CIMD HTTPS client ID works across two synthetic authorization servers without re-registration.
- **Negative check:** wrong-resource, expired, and insufficient-scope tokens each fail before downstream effects; a different client cannot reuse another client's consent decision. In proxy flows, an unregistered redirect or missing, mismatched, or replayed callback state must fail without issuing downstream authorization. Change the issuer in synthetic protected resource metadata and confirm the client does not send the old pre-registered/DCR credentials to the new server; require issuer-specific registration before that credential flow proceeds.
- **Evidence:** token verifier and proxy-flow inspection; executed per-case rejection with a synthetic issuer/downstream service. Decoding claims without validating them is insufficient.
- **Bounds / sources:** S1, Token Passthrough and Confused Deputy; S6, Authorization Server Binding (2026-07-28). Opaque-token validation differs from JWT verification; use the deployed authorization specification and issuer documentation.

### SD-MCP-001.C03 — Bind request state, caches and retries to authorized callers

- **Apply when:** MCP carries protected requests, caches, application state or elicitation; select the deployed revision. Legacy session/resumable checks apply only when that transport/profile supports them. Stdio process-local state does not imply an HTTP identity system.
- **Required / prohibited:** for 2026-07-28, authorize every self-contained request without treating an old initialization/session decision as authority. Prevent cross-principal state/cache use and duplicate committed effects on retry. Elicitation consent must not substitute for verified identity or completed external authorization. For legacy sessions, possession of a session ID alone must not authenticate a caller.
- **Rationale:** state, cached responses, retries and interactive continuations can cross authorization boundaries even without protocol sessions.
- **Implement:** for 2026-07-28, implement `server/discover` on servers; clients may use it for version/capability selection. Carry per-request version/capability metadata; bind application handles and cached data to the effective caller/access context. Honor `ttlMs` and `cacheScope`; a `private` result must not enter a shared intermediary cache. Recheck authorization after access changes. Retry a broken stream with a new request ID and use business-level idempotency for mutations; a new JSON-RPC ID does not deduplicate effects. For elicitation, use `InputRequiredResult` and retry `inputResponses`; bind `requestState` and external completion to the initiating user/client, show the complete URL and obtain consent before navigation or prefetch, and reject credential requests in form mode. Decline, cancel or unfinished authorization must not perform the dependent action. In legacy 2025-11-25 profiles, bind sessions and resumable event queues to the validated principal and invalidate them explicitly; retain their supported resumption behavior. For process-local stdio, document the trusted process/channel boundary rather than inventing accounts.
- **Unsafe → corrected:** reuse a cached result or continuation by handle alone, then retry a timed-out mutation blindly → authorize the current caller, isolate private data and deduplicate the committed business operation.
- **Positive check:** an authorized request and same-principal cache hit succeed; a retry after a lost response produces one intended effect. A consented, identity-bound elicitation completes; for the selected legacy profile, the owner resumes and receives only its events.
- **Negative check:** warm user A's private cache, then request as B and after A's access revocation; no protected cached result escapes. Retry after commit/disconnect without duplicating the effect. Substituted user/client or `requestState`, URL prefetch before consent, form credential requests, decline/cancel and unfinished external authorization produce no dependent effect. For legacy sessions, another principal's session ID and invalidated resumptions fail separately.
- **Evidence:** selected revision and identity model, authorization/state/cache-key inspection, two-principal cache/continuation observations, and retry effect counts. Capture elicitation navigation/consent and completion observations without raw credentials. Random handles alone do not establish ownership.
- **Bounds / sources:** S1 for legacy Session Hijacking; S3 for stateless metadata, caching and retry changes; S4 for stream retry; S5 for elicitation. Cache partitioning, business idempotency and the complete-URL display are this baseline's implementation checks; stdio retains its process/channel scope.

### SD-MCP-001.C04 — Constrain network and local capabilities

- **Apply when:** discovery or tool arguments influence URLs, paths, process launches, or local server configuration.
- **Required / prohibited:** keep effects within the configured destination/resource boundary. Do not let metadata or tool input grant arbitrary network, filesystem, or process access.
- **Rationale:** indirect requests can expose internal services or execute local code with the client's authority.
- **Implement:** apply the independently assessed [outbound request conditions](outbound-requests.md) to destinations, resolution, redirects, and credential forwarding, restrict egress where appropriate, and apply [file](files-uploads.md) and [command](input-validation-injection.md) controls. Inspect local server commands and minimize their inherited environment and permissions.
- **Unsafe → corrected:** fetch every discovery URL including a redirect to an excluded service → enforce the deployment's destination policy on every hop and the actual connection target.
- **Positive check:** an approved synthetic destination or file operation completes within scope.
- **Negative check:** an excluded destination, redirect escape, path escape, and unapproved process argument are denied in separate fixtures with no out-of-scope effect.
- **Evidence:** capability inventory and validation/enforcement trace; executed local sentinel tests. A URL string check alone does not establish connection-time destination enforcement.
- **Bounds / sources:** S1, SSRF and Local MCP Server Compromise. Private destinations may be intentional in local deployments; define allowed scope instead of blindly blocking all internal use.

### SD-MCP-001.C05 — Prevent tool content from granting new authority

- **Apply when:** a client/model reads server descriptions, tool results, resources, or retrieved documents.
- **Required / prohibited:** treat that content as untrusted data; it must not change the user's authorized task or grant additional capabilities/transmission rights.
- **Rationale:** injected instructions can redirect an agent's otherwise legitimate privileges.
- **Implement:** preserve source/trust labels, enforce action permissions outside model-generated text, and validate each proposed action against the user's scope. Do not rely exclusively on a prompt asking the model to ignore injection.
- **Unsafe → corrected:** a tool result says to upload a local credential file and the client complies → reject the out-of-scope action at the capability boundary while retaining the legitimate result as data.
- **Positive check:** ordinary synthetic tool content supports the requested task and its authorized next action.
- **Negative check:** injected instructions in descriptions and results cannot trigger a sentinel file read or outbound transfer outside scope; record the attempted action and denial without sensitive contents.
- **Evidence:** action-gate design and trust-flow inspection; executed adversarial tool-content scenarios with observable effects. A few resisted prompts do not prove general prompt-injection immunity.
- **Bounds / sources:** S1, session hijack prompt injection and local-server trust boundaries; external action enforcement is this baseline's engineering application. Human consent complements rather than replaces server authorization.

### SD-MCP-001.C06 — Enforce version-selected HTTP origin and metadata boundaries

- **Apply when:** an MCP endpoint uses Streamable HTTP; record its selected protocol revision. Not applicable to stdio header handling.
- **Required / prohibited:** enforce the transport's Origin policy before processing messages. Under revisions 2025-11-25 and 2026-07-28, a present invalid Origin must be rejected with HTTP 403. For 2026-07-28, require applicable request headers and reject disagreement with their body fields before dispatch. Loopback binding, CORS, or a session identifier alone is not this check.
- **Rationale:** a website can otherwise cross a local server's intended request boundary.
- **Implement:** configure allowed origins explicitly, including scheme/host/port and trusted proxy handling. Document missing-Origin behavior for non-browser clients without accepting a present invalid origin. For local deployment prefer loopback-only binding and verify effective listeners; separately enforce the intended authentication policy. For 2026-07-28 requests, compare `MCP-Protocol-Version` with the body protocol-version metadata, `Mcp-Method` with `method`, and `Mcp-Name` with `params.name` or `params.uri` for `tools/call`, `resources/read` and `prompts/get`. A name is not required for `server/discover` or list methods. Compare decoded Base64 sentinel values where required and validate any `x-mcp-header`/`Mcp-Param-*` mirroring. Keep legacy header/session behavior in the explicitly selected compatibility profile; do not silently downgrade a 2026 request.
- **Unsafe → corrected:** accept every request because the listener is local → validate the transport Origin and the separately selected caller policy before tool effects.
- **Positive check:** a permitted origin and a legitimate non-browser client under the declared absent-Origin policy can perform the allowed operation. In 2026-07-28, matching headers/body and a nameless `server/discover` request pass the applicable transport checks.
- **Negative check:** unapproved, suffix-lookalike, and null origins receive the specified denial without tool side effects. For 2026-07-28, missing applicable required headers, version/method/name mismatches, invalid mirrored parameters and header injection fail before tool dispatch; an unsupported version follows the specified version error path. Inspect wildcard/IPv6 exposure independently.
- **Evidence:** actual HTTP requests, handler effects, effective listener configuration, and protocol/SDK version. Forged-header tests prove server behavior, not complete browser DNS-rebinding resistance.
- **Bounds / sources:** S2 for the legacy Security Warning; S4 for 2026-07-28 Security & Endpoint, Request Metadata and Server Validation. Neither profile requires rejecting every request without Origin; preserve legitimate native clients through an explicit identity policy. Stdio needs its process/channel boundary, not new HTTP accounts.

## Sources

- **S1:** [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices) — revision 2025-11-25; Confused Deputy, Token Passthrough, SSRF, Session Hijacking, Local MCP Server Compromise, Scope Minimization. Checked 2026-09-24. Match protocol/SDK versions before selecting implementation APIs.
- **S2:** [MCP 2025-11-25 Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) — Streamable HTTP Security Warning, Origin validation and local binding; checked 2026-09-28.
- **S3:** [MCP 2026-07-28 Key Changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog) — stateless requests, discovery, private cache semantics and removal of stream resumability; checked 2026-10-16. S1/S2 retain their historical verification dates and legacy scope.
- **S4:** [MCP 2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) — Security & Endpoint, Request Metadata, Server Validation and retry behavior; checked 2026-10-16.
- **S5:** [MCP 2026-07-28 Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) — User Interaction Model, Statefulness, Safe URL Handling and Identifying the User; checked 2026-10-16.
- **S6:** [MCP 2026-07-28 Client Registration](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration#authorization-server-binding) — issuer-keyed pre-registration/DCR credentials and portable CIMD client IDs; checked 2026-10-16.
