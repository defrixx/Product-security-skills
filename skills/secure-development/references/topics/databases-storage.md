# Databases and data storage

## SD-DATASTORE-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Query construction belongs to [input validation](input-validation-injection.md); per-user and tenant decisions belong to [authorization](authorization-access-control.md). Examples describe synthetic deployments.

### SD-DATASTORE-001.C01 — Restrict the application's storage identity

- **Apply when:** a service authenticates to a database or storage service using a runtime identity.
- **Required / prohibited:** grant only the storage operations and resources needed by that service. Do not use an administrator or migration identity for ordinary runtime requests without a scoped exception.
- **Rationale:** An overprivileged storage account expands the impact of application compromise.
- **Implement:** separate runtime, migration, backup, and administrative identities; enumerate required grants and remove inherited broad permissions. Retrieve credentials through [secret controls](secrets.md). ORM configuration does not itself restrict server grants.
- **Unsafe → corrected:** the application connects as the database owner → it connects as a runtime role limited to required tables/operations, while migrations use a separate controlled identity.
- **Positive check:** the actual runtime identity performs the documented read/write workflow.
- **Negative check:** the same identity cannot create privileged roles, access an unrelated synthetic database, or perform other explicitly forbidden administration. Select probes appropriate to the engine and isolate them from production.
- **Evidence:** effective-grant inspection plus executed allowed/denied operations. An intended role declaration is insufficient if inherited grants still permit the forbidden action.
- **Bounds / sources:** S1, Creating Secure Permissions. Embedded databases may use OS-level access instead of roles; assess the actual security boundary rather than inventing a database account model.

### SD-DATASTORE-001.C02 — Restrict storage network reachability

- **Apply when:** a database, object store, cache, search index, or its administrative interface is network-accessible.
- **Required / prohibited:** expose it only to intended consumers under the documented deployment model. Do not publish a private backend to all host interfaces merely for convenience.
- **Rationale:** Unnecessary reachability exposes storage to additional attackers.
- **Implement:** select private endpoints, appropriate listener bindings, firewall/network policy, and authenticated administration. For local Compose services see [published-port checks](../stacks/docker-compose.md). Public objects require an explicit product policy, not an accidental default.
- **Unsafe → corrected:** publish the database port on every host interface → keep it on the internal service network or use a specifically justified restricted binding.
- **Positive check:** an intended application consumer reaches the required service.
- **Negative check:** a network context excluded by the reachability policy cannot establish the prohibited connection. For an intentionally public object-store endpoint, test private-object authorization separately; an HTTP access denial does not prove network isolation. Inspect actual listeners, published ports, and effective network policy.
- **Evidence:** deployed listener/policy inspection and authorized connectivity probes. A private-looking hostname or configuration file alone does not establish effective isolation.
- **Bounds / sources:** S1, Protecting the Backend Database. Object-store policy syntax and public-access semantics require the selected vendor's current documentation. Network isolation does not replace authentication or object authorization.

### SD-DATASTORE-001.C03 — Authenticate the storage transport peer

- **Apply when:** sensitive storage traffic crosses a network requiring transport confidentiality and peer authentication.
- **Required / prohibited:** use the intended authenticated encrypted connection and reject invalid peers. Do not disable certificate or hostname verification to make a connection succeed.
- **Rationale:** An encrypted connection to the wrong peer can still disclose credentials or data.
- **Implement:** configure the driver's supported verified-TLS mode and trusted roots for the actual server identity. Apply [X.509 validation](x509-certificates.md); inspect connection-pool and fallback paths as well as the primary configuration.
- **Unsafe → corrected:** a client encrypts traffic but accepts any certificate → configure trust and expected identity verification without plaintext fallback.
- **Positive check:** the client completes a normal query against a local test server with the expected certificate identity.
- **Negative check:** an untrusted issuer or wrong server name prevents connection before credentials or query data are sent. Verify plaintext fallback is unavailable where prohibited.
- **Evidence:** driver configuration and connection trace; executed TLS-failure tests with the actual driver version. A TLS-enabled server does not prove that clients verify it.
- **Bounds / sources:** S1, Transport Layer Protection. Local sockets and embedded stores have different boundaries. Record any alternative protected-channel design explicitly; do not infer it from network locality.

### SD-DATASTORE-001.C04 — Protect exported and backup copies

- **Apply when:** exports, snapshots, transaction logs, replicas, or backups contain protected data.
- **Required / prohibited:** maintain the declared confidentiality and access policy for each copy, including restored instances. Do not assume the primary store's ACL automatically protects an exported file or snapshot.
- **Rationale:** Exports and backups can bypass protections applied to the primary store.
- **Implement:** inventory copy destinations and readers; restrict backup/export identities and storage permissions. Apply the data's encryption/key policy, signed-link scope, and retention requirements using [privacy](privacy-data-protection.md), [cryptography](cryptography-policy.md), and [authorization](authorization-access-control.md) controls.
- **Unsafe → corrected:** place a database dump in a public download directory → store it in the restricted backup destination and serve any authorized export through a scoped retrieval mechanism.
- **Positive check:** an authorized test operator restores a synthetic backup and obtains the intended data under the restored access policy.
- **Negative check:** an unauthorized actor cannot list/read the copy or reuse a link outside its intended scope/lifetime; a restore does not silently expose it publicly.
- **Evidence:** effective copy permissions, lifecycle configuration, and authorized restore/access tests. A successful backup command does not establish confidentiality or recoverability.
- **Bounds / sources:** S1, Database Configuration and Hardening. Retention and encryption requirements depend on the data policy; do not invent universal periods. Remote backup access or destructive restore testing requires a separately authorized environment.

## Sources

- **S1:** [OWASP Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html) — Protecting the Backend Database; Transport Layer Protection; Creating Secure Permissions; Database Configuration and Hardening. Living documentation, checked 2026-09-24. Vendor-specific object-store, driver, and engine settings require matching primary documentation.
