# Logging and monitoring

## SD-LOG-001

Status: proposed baseline; applicable C01–C04 are MUST conditions. Follow the [requirement format](../requirement-format.md) for evidence and exceptions. Secret exclusion is governed by [SD-SECRET-001.C03](secrets.md); personal-data minimization by [privacy controls](privacy-data-protection.md). These conditions do not authorize sending project data to a monitoring service.

### SD-LOG-001.C01 — Emit useful security events

- **Apply when:** authentication, denied access, administrative changes, exports, or other threat-model events require detection or investigation.
- **Required / prohibited:** record the selected event with sufficient trusted context to distinguish action and outcome. Do not substitute generic HTTP access logs for application decisions they cannot represent.
- **Rationale:** Missing context prevents useful investigation and correlation of security events.
- **Implement:** define event names and allowlisted fields: event time, action, outcome, correlation identifier, and suitably scoped actor/resource references. Derive authoritative fields from server state, not user-supplied labels.
- **Unsafe → corrected:** emit only `request failed` → emit a structured access-denied event identifying the operation and a safe actor reference without its credentials or request body.
- **Positive check:** a synthetic administrative change produces the expected successful event with correct correlation.
- **Negative check:** a rejected operation produces a denied event rather than a success event; client-supplied actor/outcome values cannot overwrite authoritative fields.
- **Evidence:** event-to-decision call-site inspection and captured events from executed flows. An event schema without producer coverage does not prove useful logging.
- **Bounds / sources:** S1, Which Events to Log and Event Attributes. Select events from actual risk; avoid unnecessary personal data and invented universal retention periods.

### SD-LOG-001.C02 — Keep untrusted values inside one log record

- **Apply when:** filenames, usernames, headers, error strings, or other untrusted values reach logs or log viewers.
- **Required / prohibited:** untrusted content must not forge records, fields, or executable viewer markup. Do not concatenate raw values into a line-oriented or HTML log format.
- **Rationale:** Untrusted delimiters can forge records or conceal the actual event.
- **Implement:** use structured serializers, field-length limits, and sink-specific encoding. Treat control characters and viewer rendering separately; JSON serialization alone does not make an HTML viewer safe.
- **Unsafe → corrected:** concatenate `user + '\nstatus=success'` into a text log → serialize the user value as a bounded data field using the logger's supported API.
- **Positive check:** ordinary Unicode values remain readable and attributed to the correct event.
- **Negative check:** CR/LF, delimiter, and harmless markup canaries remain data within one event and cannot create a false success record or execute in the viewer.
- **Evidence:** producer/serializer/viewer trace and executed parser/viewer tests. Capturing raw stdout alone cannot establish behavior in a downstream log UI.
- **Bounds / sources:** S1, Event Collection and Verification. Record each sink's encoding contract; do not assume an escape function for one sink covers another.

### SD-LOG-001.C03 — Restrict access to collected evidence

- **Apply when:** logs, traces, audit exports, or monitoring indexes retain security or personal information.
- **Required / prohibited:** enforce the intended reader/writer/deletion roles and lifecycle policy. Do not expose logs through a public file path or grant an ordinary application identity unnecessary alteration rights.
- **Rationale:** Diagnostic stores can expose sensitive evidence or permit evidence tampering.
- **Implement:** separate collection and review permissions, protect transport/storage as appropriate, and apply a documented retention/deletion policy. Preserve integrity for the declared audit use case without claiming non-repudiation merely because logs exist.
- **Unsafe → corrected:** serve `/logs/debug.txt` without authorization → place logs in restricted storage and expose only an authorized review interface.
- **Positive check:** the collector writes events and an authorized reviewer can retrieve the intended evidence.
- **Negative check:** an unauthorized reader or writer cannot read, replace, or delete protected records. Verify the effective storage policy rather than only application UI permissions. With a controlled clock or synthetic aged records, verify configured expiry/disposal and any explicit retention hold separately; neither unauthorized deletion nor indefinite retention may be hidden by a passing read-access test.
- **Evidence:** effective ACL/identity inspection and isolated allowed/denied access tests. Encryption at rest does not establish reader authorization.
- **Bounds / sources:** S1, Where to Record Event Data, Protection, and Disposal. Retention follows actual policy; external archival systems outside the test scope remain unverified.

### SD-LOG-001.C04 — Verify alert delivery and logging-failure behavior

- **Apply when:** a security control relies on alerting, or log collection can fail, block, or exhaust resources.
- **Required / prohibited:** demonstrate the configured signal reaches its intended test destination and define bounded behavior when collection fails. Do not claim operational detection merely because an application printed an event.
- **Rationale:** Undelivered alerts and silent collection failures hide security events.
- **Implement:** map selected event patterns to thresholds, destinations, and responsible roles; bound queues/retries and define fail-open/fail-closed behavior per operation. Keep logging failure from silently changing an authorization denial into an allow.
- **Unsafe → corrected:** assume a logged denial proves alerting → trigger a synthetic pattern and observe receipt through the configured test pipeline; test collector outage separately.
- **Positive check:** the intended pattern reaches the designated test sink with usable context and correct classification.
- **Negative check:** collector unavailability or a bounded synthetic burst does not cause unbounded memory/disk growth or bypass the protected decision; the documented failure signal is observable.
- **Evidence:** rule/configuration inspection, received test alert, and outage observations. Separate event generation, transport, alert evaluation, and human response evidence.
- **Bounds / sources:** S1, Verification and Monitoring of Events. A test-sink receipt does not prove production delivery or human response. Sending real notifications requires authorization; do not invent an assigned owner.

## Sources

- **S1:** [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — Which Events to Log; Event Attributes; Data to Exclude; Event Collection; Verification; Protection; Monitoring; Disposal. Living documentation, checked 2026-09-24. Actual sink configuration requires the deployed logger/collector's versioned documentation.
