# Python / FastAPI profile

Scope: Python 3.12 semantics, FastAPI applications using Pydantic v2, and SQLAlchemy 2.0. Record the actual framework patch versions before implementation. FastAPI/Pydantic pages are living documentation; this profile does not certify every release combination.

Status: proposed baseline, source-reviewed on 2026-09-24. Every control below is a proposed MUST when applicable. Exceptions use [the requirement format](../requirement-format.md). These controls refine the linked condition IDs. Record evidence against those conditions; passing a profile example does not satisfy its entire parent topic. The short examples below are synthetic implementation sketches, not complete application code. Framework integration has not been run as part of the bundled standard-library regression suite.

## SD-PY-001 — Validate the mutation schema

- Required implementation behavior: enforce the declared mutation contract and constrain security-relevant types, ranges, and lengths. Reject extras for closed contracts; for intentionally extensible contracts, constrain extension names/values and prevent them from assigning protected model attributes.
- Rationale: unexpected fields or coercion can alter protected state.
- Implementation: use a dedicated Pydantic v2 input model; `model_config = ConfigDict(extra='forbid')` rejects extra fields. Choose strict validation for fields where coercion is unsafe.
- Limit: this validates data, not authorization. Existing extensible payload contracts may require a different explicit field policy.
- Source: [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/) — v2, Extra data and Data conversion; checked 2026-09-24.
- **Condition mapping:** [SD-INPUT-001.C01](../topics/input-validation-injection.md); protected field decisions also require [SD-AUTHZ-001.C04](../topics/authorization-access-control.md).
- **Apply when:** a FastAPI mutation route accepts a Pydantic model or an untyped dictionary that reaches persistence.
- **Unsafe → corrected:** pass an arbitrary request dictionary into an ORM update → validate a dedicated mutation model with forbidden extra fields, then explicitly select writable attributes.
- **Positive check:** submit documented fields at allowed boundaries, including a permitted extension when supported; expect only the intended mutation.
- **Negative check:** submit an unauthorized `is_admin` field, invalid strict type, and excessive length separately; expect no forbidden mutation. Closed contracts reject extra fields. An explicitly extensible contract accepts a valid extension while rejecting or safely discarding prohibited extensions according to its policy; inspect persistence separately.
- **Evidence:** inspect the actual route model and persistence mapping; execute requests through FastAPI and inspect committed state.

## SD-PY-002 — Keep secrets outside response models

- Required implementation behavior: response serialization must not expose stored or decrypted credentials.
- Rationale: a persistence model often contains more data than a client may see.
- Implementation: return a dedicated public DTO with an explicit FastAPI response model; expose a boolean indicating credential presence if needed.
- Limit: response filtering does not redact logs or prevent unrelated serialization paths.
- Source: [FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) — response filtering and returned Response; living documentation, checked 2026-09-24.
- **Condition mapping:** [SD-SECRET-001.C02](../topics/secrets.md); failure responses additionally require [SD-API-001.C05](../topics/api-web-services.md).
- **Apply when:** handlers serialize database entities or objects containing credentials into public responses.
- **Unsafe → corrected:** return a credential-bearing object's full dictionary → return an explicit public DTO through the declared response model.
- **Positive check:** a normal request returns every intended public field with the expected values.
- **Negative check:** a synthetic credential canary is absent from the actual HTTP response, including raw Response branches and error cases assessed separately.
- **Evidence:** inspect response models and serialization bypasses; execute route-level HTTP checks. Merely declaring a DTO does not prove all branches use it; logs remain a separate surface.

## SD-PY-003 — Bind SQL values

- Required implementation behavior: keep untrusted values out of SQL syntax construction.
- Rationale: interpolation lets a value change query meaning.
- Implementation option: `db.execute(text("SELECT name FROM records WHERE name = :name"), {"name": value})`. Use explicit allowlists for identifiers that cannot be parameters.
- Limit: binding does not enforce object ownership, tenant scope, or safe dynamic identifiers.
- Source: [SQLAlchemy SQL expressions](https://docs.sqlalchemy.org/en/20/core/sqlelement.html) — 2.0, `text()` and `bindparam()`; checked 2026-09-24.
- **Condition mapping:** [SD-INPUT-001.C02 and SD-INPUT-001.C03](../topics/input-validation-injection.md); assess value binding and dynamic identifiers separately.
- **Apply when:** request-derived values enter SQLAlchemy expressions, `text()`, or driver calls.
- **Unsafe → corrected:** interpolate `value` into a SQL string → pass it as the `:name` bind value shown above; select sort columns from fixed application mappings.
- **Positive check:** a synthetic ordinary name returns its expected row through the actual database driver.
- **Negative check:** a quote/tautology value cannot broaden the result set or mutate unrelated rows; a disallowed sort identifier is rejected independently.
- **Evidence:** inspect query construction and bindings; execute database-backed positive/negative cases. A mocked execute call proves argument shape only, not SQL interpretation or authorization.

## SD-PY-004 — Validate every filesystem-name source

- Required implementation behavior: an untrusted archive manifest filename must not escape its storage boundary, even when ZIP member names are valid.
- Rationale: metadata and member paths are independent inputs.
- Implementation: validate bare filenames before writes or generate storage names independently; constrain resolved parents and use exclusive/no-follow operations appropriate to the platform. Account for symlink races and existing-file replacement requirements.
- Limit: `resolve()` is not an atomic filesystem sandbox. Trust in writable parent directories matters.
- Sources: [Python pathlib](https://docs.python.org/3.12/library/pathlib.html) — 3.12, path joining and `resolve()`; [Python os](https://docs.python.org/3.12/library/os.html) — 3.12, `open()`, `dir_fd`, `O_NOFOLLOW`; checked 2026-09-24.
- **Condition mapping:** [SD-FILES-001.C01 and SD-FILES-001.C02](../topics/files-uploads.md); confinement and overwrite/publication require separate results.
- **Apply when:** archive members, manifest fields, upload names, or database metadata determine filesystem destinations.
- **Unsafe → corrected:** validate ZIP member names but join an unchecked manifest filename → validate every destination source or use generated storage names with confined, race-aware operations.
- **Positive check:** a valid synthetic import creates only its expected files and records.
- **Negative check:** traversal and symlink fixtures leave outside sentinels unchanged; a collision preserves the existing file under exclusive-create policy; if replacement is intentional, only the authorized target is replaced and unrelated files remain intact; a later failure leaves no falsely published result.
- **Evidence:** inspect each path producer and open/write/publication boundary; execute filesystem and persistence observations. Passing one archive-path case does not establish manifest handling or rollback behavior.

## SD-PY-005 — Redact validation failures

- Required implementation behavior: invalid credential-bearing input must not be returned or logged verbatim.
- Rationale: failure paths can bypass normal DTO filtering.
- Implementation: use a controlled validation handler and an allowlist of safe diagnostic fields; do not serialize the full body or arbitrary exception values.
- Limit: third-party middleware and server access logs need separate checks.
- Source: [FastAPI Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) — override validation handlers and request body in errors; living documentation, checked 2026-09-24.
- **Condition mapping:** [SD-SECRET-001.C03](../topics/secrets.md) and [SD-API-001.C05](../topics/api-web-services.md); assess response and diagnostic disclosure separately.
- **Apply when:** FastAPI validation errors or custom exception handlers can include request input or exception objects.
- **Unsafe → corrected:** serialize the full validation exception/body → emit only approved error codes and safe field locations, omitting input values.
- **Positive check:** a benign invalid field produces the documented useful error response and permitted diagnostic event.
- **Negative check:** malformed input containing a synthetic credential appears in neither the response nor captured application logs, including nested validation errors.
- **Evidence:** inspect handler registration and diagnostic serializers; execute malformed requests and capture both surfaces.
