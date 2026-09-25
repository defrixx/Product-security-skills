# Model Context Protocol security

## SD-MCP-001

Status: proposed baseline; C01–C05 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Record protocol revision, SDK version, transport, deployment, and identity model. HTTP OAuth requirements do not automatically apply to stdio. Examples are synthetic local scenarios.

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
- **Implement:** use the authorization server's supported validation mechanism and separate downstream credentials/authorization. For proxy authorization flows, bind consent to the actual client and requested permissions; validate registered redirect and callback state.
- **Unsafe → corrected:** forward any supplied bearer token to an API → reject a token for the wrong resource and obtain appropriately scoped downstream authorization through the intended flow.
- **Positive check:** a token for the intended MCP resource and allowed scope succeeds.
- **Negative check:** wrong-resource, expired, and insufficient-scope tokens each fail before downstream effects; a different client cannot reuse another client's consent decision. In proxy flows, an unregistered redirect or missing, mismatched, or replayed callback state must fail without issuing downstream authorization.
- **Evidence:** token verifier and proxy-flow inspection; executed per-case rejection with a synthetic issuer/downstream service. Decoding claims without validating them is insufficient.
- **Bounds / sources:** S1, Token Passthrough and Confused Deputy. Opaque-token validation differs from JWT verification; use the deployed authorization specification and issuer documentation.

### SD-MCP-001.C03 — Bind sessions to authenticated callers

- **Apply when:** MCP transport maintains session identifiers or resumable event delivery across requests.
- **Required / prohibited:** possession of a session ID alone must not authenticate a caller; prevent cross-user session use and event delivery.
- **Rationale:** session confusion can inject another principal's responses or expose their data.
- **Implement:** bind session state to the validated principal and recheck identity on subsequent requests. Partition queues/caches by authenticated ownership and define session invalidation behavior.
- **Unsafe → corrected:** route events using only a caller-supplied session ID → require that the current authenticated principal owns the referenced session before routing.
- **Positive check:** the owning synthetic principal resumes its session and receives only its events.
- **Negative check:** another principal reusing that session ID cannot invoke its state or receive queued events; invalidated sessions cannot resume.
- **Evidence:** session ownership and queue-key inspection; executed two-principal request/event tests. Random session identifiers alone do not establish ownership checks.
- **Bounds / sources:** S1, Session Hijacking. Record transport-specific session behavior rather than assuming every MCP deployment uses sessions.

### SD-MCP-001.C04 — Constrain network and local capabilities

- **Apply when:** discovery or tool arguments influence URLs, paths, process launches, or local server configuration.
- **Required / prohibited:** keep effects within the configured destination/resource boundary. Do not let metadata or tool input grant arbitrary network, filesystem, or process access.
- **Rationale:** indirect requests can expose internal services or execute local code with the client's authority.
- **Implement:** validate destinations through redirects and resolution, restrict egress where appropriate, and apply [file](files-uploads.md) and [command](input-validation-injection.md) controls. Inspect local server commands and minimize their inherited environment and permissions.
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

## Sources

- **S1:** [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices) — revision 2025-11-25; Confused Deputy, Token Passthrough, SSRF, Session Hijacking, Local MCP Server Compromise, Scope Minimization. Checked 2026-09-24. Match protocol/SDK versions before selecting implementation APIs.
