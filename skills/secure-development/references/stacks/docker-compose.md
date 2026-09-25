# Docker Compose profile

Scope: Linux containers managed by Docker Compose v2 and BuildKit-capable builds. Inspect the actual engine, Compose version, rendered configuration, and host networking behavior. This is a proposed baseline, source-reviewed on 2026-09-24; applicability and enforcement require evidence from the target environment.

Every applicable control below is a proposed MUST. Examples are synthetic sketches. Record evidence per mapped condition and per independently tested runtime restriction; one passing container check does not satisfy the whole profile. Exceptions follow [the requirement format](../requirement-format.md). Local Compose secrets and network isolation are not a managed secret service or proof of production compliance.

## SD-COMPOSE-001 — Publish only intended listeners

- Parent: `SD-CICD-001`, `SD-API-001`; applies to published service ports.
- Required implementation behavior: bind a local-only application to the intended loopback interface; leave internal stores unpublished unless explicitly required.
- Rationale: accidental host-wide exposure invalidates a local-only trust model.
- Implementation: specify `host_ip` or the host-IP portion of a port mapping instead of relying on an omitted binding.
- Limit: reverse proxies, tunnels, overrides, and host networking can change exposure.
- Source: [Compose services](https://docs.docker.com/reference/compose-file/services/) — `ports` and `network_mode`; checked 2026-09-24.
- **Condition mapping:** [SD-API-001.C01](../topics/api-web-services.md) for the intended endpoint boundary and [SD-DATASTORE-001.C02](../topics/databases-storage.md) for internal storage reachability.
- **Apply when:** `ports`, overrides, host networking, or a proxy can expose a local service beyond its intended interface.
- **Unsafe → corrected:** publish a local-only service with an unspecified host binding → bind its declared port to the intended loopback address and omit the database's host publication.
- **Positive check:** the intended local client can reach the application through the declared listener.
- **Negative check:** inspect that no unintended wildcard/IPv6 listener exists; where an authorized separate network vantage is available, verify the service is unreachable there. Internal stores have no unintended published port.
- **Evidence:** rendered configuration, actual port/listener inspection, and executed reachability observations. A loopback request succeeding does not prove remote requests fail; unavailable network vantage remains a gap.

## SD-COMPOSE-002 — Restrict runtime secret access

- Parent: `SD-SECRET-001`; applies to secret-consuming containers.
- Required implementation behavior: provide secret material only to services that require it, without embedding it in committed configuration or images.
- Rationale: unnecessarily shared credentials expand compromise scope.
- Implementation option: declare Compose secrets and grant them to selected services; read the mounted file from the application. Protect the original host file too.
- Limit: local file-backed Compose secrets do not imply encryption of the host source or automatic rotation.
- Source: [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) — service grants and mounted files; checked 2026-09-24.
- **Condition mapping:** [SD-SECRET-001.C01 and C02](../topics/secrets.md); service-specific access is a profile refinement requiring its own denial observation.
- **Apply when:** a service consumes a file-backed Compose secret or equivalent runtime credential injection.
- **Unsafe → corrected:** mount the same credential directory into every service → grant only the required secret to its designated consumer and protect the host source.
- **Positive check:** the intended service can read the synthetic secret at its configured mount and perform its test operation.
- **Negative check:** a service without a grant cannot read the canary through a secret mount or another shared volume; rendered configuration and images contain no credential value.
- **Evidence:** service grants, host-file protections, and other mount paths; executed reads as actual runtime identities. A missing standard mount is insufficient if another volume exposes the same source.

## SD-COMPOSE-003 — Keep build credentials out of layers

- Parent: `SD-SECRET-001`, `SD-SUPPLY-001`; applies to authenticated build steps.
- Required implementation behavior: build credentials must not persist in image layers, history, or exported artifacts.
- Rationale: later deletion does not remove a value from an earlier layer.
- Implementation: use BuildKit secret mounts for the needed step rather than credential-bearing `ARG`, `ENV`, or copied files.
- Limit: a command can still copy or print a mounted secret. A mount alone is not a complete guarantee.
- Source: [Docker build secrets](https://docs.docker.com/build/building/secrets/) — secret mounts versus build arguments/environment; checked 2026-09-24.
- **Condition mapping:** [SD-CICD-001.C03](../topics/devops-cicd-containers.md) and [SD-SECRET-001.C02](../topics/secrets.md).
- **Apply when:** a Dockerfile RUN step needs credentials for private downloads or other authenticated build operations.
- **Unsafe → corrected:** copy a credential and delete it in a later layer → use a BuildKit secret mount for the required step without copying its contents into output.
- **Positive check:** an isolated synthetic build consumes the mounted canary for its intended operation.
- **Negative check:** inspect exported image layers, configuration, history, runtime files, and captured build logs; none contains the canary. Include shared caches if exported by the build.
- **Evidence:** Dockerfile and invoked-script data flow; executed build and per-surface inspection results. A failed extraction or unreadable log is an unverified surface, not a passing absence check.

## SD-COMPOSE-004 — Minimize runtime privilege

- Parent: `SD-CICD-001`; applies to ordinary application containers.
- Required implementation behavior: use a non-root identity where supported and grant only required capabilities, mounts, and writable paths.
- Rationale: unnecessary host or container privileges amplify application compromise.
- Implementation options: configure `user`, `cap_drop`, `read_only`, and dedicated writable volumes as appropriate; avoid privileged mode and host daemon sockets without a scoped requirement.
- Limit: settings vary with entrypoint needs and platform; non-root execution alone does not establish isolation.
- Source: [Compose services](https://docs.docker.com/reference/compose-file/services/) — `user`, `cap_drop`, `read_only`, `privileged`, `volumes`; checked 2026-09-24.
- **Condition mapping:** [SD-CICD-001.C04](../topics/devops-cicd-containers.md). Assess identity, capabilities, host access, and writable paths independently.
- **Apply when:** Compose launches an application process with configurable user, capabilities, mounts, or privilege flags.
- **Unsafe → corrected:** run an ordinary service as privileged root with a writable root filesystem → select its supported unprivileged identity, drop unnecessary capabilities, and provide only required writable locations.
- **Positive check:** the service starts and completes required writes in the declared writable volume or temporary filesystem.
- **Negative check:** a write outside permitted locations and an operation needing a removed capability fail; inspect actual runtime absence of privileged mode and host control sockets separately.
- **Evidence:** effective container inspection and process identity/capability observations; executed allowed/denied operations. Source YAML can be overridden and does not establish effective runtime restrictions.
