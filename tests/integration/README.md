# Framework integration checks

These opt-in checks install dependencies in disposable containers. They use synthetic applications and data; no external application checkout is required. The standard-library test suite does not install or run them.

## Python

From the repository root:

```sh
docker run --rm --mount "type=bind,source=$PWD/tests/integration/python,target=/checks,readonly" python:3.12-slim sh -c 'pip install --disable-pip-version-check -r /checks/requirements.txt && python /checks/checks.py'
```

The requirements file pins the fixture dependencies. The base image tag is not digest-pinned; record its actual image ID for release evidence. Dependency installation requires network access; no project files are uploaded. Only this synthetic fixture directory is mounted, read-only, and no host ports or Docker socket are mounted.

The checks exercise actual FastAPI routing, Pydantic validation, response filtering, exception handling, and SQLAlchemy parameter binding to an in-memory SQLite database. They cover selected conditions of SD-PY-001, SD-PY-002, SD-PY-003, SD-PY-004, and SD-PY-005. No network server or PostgreSQL integration is implied. The import endpoint uses a real temporary filesystem: malicious filenames, existing symlinks, and overwrites are rejected, while valid writes succeed. It does not implement ZIP parsing or database/filesystem transactions. Framework logs, authentication, deployment, and all version combinations are not covered.

Sources consulted on 2026-09-24: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [response models](https://fastapi.tiangolo.com/tutorial/response-model/), and [SQLAlchemy SQLite threading/pooling](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).

The Python fixture contains five tests. Its pinned Starlette/HTTPX combination can emit a TestClient deprecation warning; retain warnings in the run log. Separate fixtures below cover Next.js and Compose.

## Run and capture evidence

Create the ignored `artifacts/` directory if absent. Use a new output directory for each run:

```sh
python3 tests/integration/run_framework.py python --output artifacts/python-run
python3 tests/integration/run_framework.py next --output artifacts/next-run
python3 tests/integration/compose/run.py --output artifacts/compose-run
```

The framework runner records image ID, fixture hashes, status, and tool output. The Compose runner creates a unique project and image, retains a summary/log, and removes its own project resources. Docker access is required. Only synthetic fixture directories enter containers/build context. Do not point these runners at production resources. Local firewall/browser sandbox and host compromise resistance are not tested.

## Next.js / React / Chromium

The fixture builds Next.js 16.3.6 and React 19.2.0 using the committed npm lockfile and runs Chromium from Playwright 1.55.1. Installation scripts are disabled. Dependencies install inside a disposable container; the fixture is mounted read-only and copied to its temporary filesystem. The server binds to container loopback without a host-published port. The test browser runs with its sandbox disabled inside this synthetic container; this is a test-environment limitation, not application hardening guidance.

- SD-TS-001: direct HTTP Route Handler calls reject missing identity, the wrong owner, a different object, and extra mutation fields before state changes; the authorized mutation succeeds. Fixed bearer tokens are synthetic identity fixtures, not a production authentication implementation. Server Actions and session-provider integration are not tested.
- SD-TS-002: an actual hydrated browser DOM contains the attack string as text, creates no injected script/image nodes, and records no payload execution. This does not test third-party HTML sanitizers or every rendering sink.
- SD-TS-003: an inert private environment canary is used at build/runtime; emitted client files, rendered HTML, and observed browser response bodies omit it. This does not cover unvisited routes or arbitrary encodings/exfiltration.

Sources consulted on 2026-09-24: [Next.js data security](https://nextjs.org/docs/app/guides/data-security) and [authentication / Route Handlers](https://nextjs.org/docs/app/guides/authentication).

## Docker Compose / BuildKit

Four checks cover the profile's selected conditions in real containers:

- SD-COMPOSE-001: inspect actual loopback port bindings, fetch HTTP successfully, and verify the second service has no published port. No outside-host network probe is claimed.
- SD-COMPOSE-002: the granted service reads the synthetic mounted secret; the ungranted service cannot see that mount. This is not proof of host-file encryption.
- SD-COMPOSE-003: a BuildKit step consumes a synthetic secret without persisting it; inspect image configuration, history, every readable file in saved layers, runtime absence, and captured logs for the canary. Exact-canary scans do not detect transformed/encoded leaks.
- SD-COMPOSE-004: verify actual non-root UID, zero effective capabilities, no-new-privileges, denied root-filesystem writes, and successful writes in the intended tmpfs.

Record actual Docker Engine and Compose CLI versions in each result; exercising Compose specification controls with one CLI version does not establish compatibility with other versions. Mutable base-image tags and platform-specific behavior limit portability. The runner inspects synthetic image layers without extracting them onto the host.

Sources consulted on 2026-09-24: [Compose service configuration](https://docs.docker.com/reference/compose-file/services/) and [service secret grants](https://docs.docker.com/compose/how-tos/use-secrets/).

## Protocols and interpreters

```sh
docker pull mongo:8.0.15
python3 tests/integration/run_framework.py protocols --output artifacts/protocols-new-run
```

Seven cases run Authlib 1.6.5, PyJWT 2.10.1, Jinja 3.1.6 and PyMongo 4.15.1 against MongoDB 8.0.15. All Python dependencies are pinned in [requirements.txt](protocols/requirements.txt); the log records installed versions. MongoDB has a unique run network, an anonymous data volume removed with its container, and no published host port. Image tags remain mutable; the report records actual image IDs. The Python and Playwright images used by the runner must already be available locally; pull them explicitly if needed.

- SD-PROTOCOL-001.C01: Authlib performs actual HTTP authorization-code and token requests to a minimal local synthetic issuer. The callback client restores saved state; state mismatch is rejected before exchange. Wrong PKCE verifier/redirect, code replay, issuer and nonce are rejected; valid login increments the synthetic session counter. A deliberately unbound-state client reproduces the failure. This was a demonstrated fixture integration defect during development, not a reported Authlib vulnerability.
- SD-PROTOCOL-001.C02: actual RSA signatures are verified by PyJWT. Wrong key/algorithm, issuer/audience, expiry/not-before, missing required expiry and wrong purpose are rejected. Fixture key-selection guards reject unknown key IDs and header-supplied URLs without requests to the sentinel. Nonce/purpose guards are application fixture code. No discovery/JWKS rollover or complete OIDC middleware is exercised.
- SD-PROTOCOL-001.C03: Authlib sends real refresh requests; the synthetic issuer permits one concurrent use, denies replay and issuer-side revoked refresh credentials. Audience/purpose checks reject unintended recipients. This does not establish a commercial provider's refresh-family policy or distributed durability.
- SD-INPUT-001.C06: real MongoDB executes the unsafe operator predicate; typed `$eq` lookup rejects operator objects while ordinary and dollar-prefixed literal values work.
- SD-INPUT-001.C07: actual Jinja evaluates the unsafe concatenated template, exposing a synthetic sentinel; a fixed template with data parameters preserves the expression as data. Untrusted template authoring, sandbox escape resistance and exhaustion are outside scope.

The issuer, accounts and session counter are synthetic substitutes; callback URLs are parsed directly rather than handled by a browser login/session stack. HTTP is permitted only for the isolated loopback issuer. The fixture is not production authentication code or a protocol conformance suite.

Primary references checked 2026-09-29: [Authlib 1.6.5 authorization code/state/PKCE](https://docs.authlib.org/en/v1.6.5/client/oauth2.html), [PyJWT 2.10.1 validation](https://pyjwt.readthedocs.io/en/2.10.1/usage.html), [MongoDB equality predicates](https://www.mongodb.com/docs/manual/reference/operator/query/eq/), and [Jinja 3.1 API](https://jinja.palletsprojects.com/en/stable/api/). These support fixture API choices, not blanket target compatibility.

## Cache and browser policy extensions

The existing `next` runner now executes six control groups: its original three plus:

- SD-API-001.C06 / AUTHZ C03/C05: actual Next.js Data Cache (`unstable_cache`) hits preserve a computation UUID. Actors and representation variants receive separate entries; current authorization rejects an actor after revocation despite a populated cache. The intentionally unsafe shared entry reproduces cross-actor disclosure. This does not test the `use cache` directive, CDN caches or a real identity provider.
- SD-WEB-001.C07: Chromium permits a same-origin iframe and blocks the protected document in a distinct loopback origin; a report-only policy permits the negative control. The same-origin parent is served using Playwright request routing; the protected document and its headers come from Next.js.
- SD-WEB-001.C08: enforced script CSP blocks the untrusted inline payload while permitting the nonce-bearing control. Unsafe and report-only variants execute the payload. The fixed fixture nonce is not production nonce-generation guidance. HSTS, MIME sniffing, referrer controls and other browser engines remain untested.

Primary references checked 2026-09-29: [Next.js unstable_cache](https://nextjs.org/docs/app/api-reference/functions/unstable_cache) (arguments/keys and dynamic request data), [CSP Level 3](https://www.w3.org/TR/CSP3/) (script enforcement, reporting and frame-ancestors). The browser test closes its separate-origin server and waits for the Next.js process to exit, escalating to termination if needed.

## Failure cleanup and evidence

```sh
python3 -m unittest discover -s tests -p test_resource_cleanup.py -v
python3 tests/integration/lifecycle_checks.py --output artifacts/lifecycle-new-run
```

The local regression uses actual subprocesses, loopback sockets and temporary directories. Exception, timeout and SIGTERM must remove the failing scope's resources while another scope's process, port and file stay available. A child intentionally ignores SIGTERM, exercising forced termination and reaping.

The opt-in Docker suite repeats the three faults with real running containers, published loopback HTTP ports, run-owned networks and anonymous volumes. It checks resource absence afterward and continued operation of the separate sentinel container/network/volume/port, then removes the sentinel too. It does not modify actual unrelated user resources. No prune or name-prefix deletion is used: the shared resource helper records immutable container/network IDs and verifies ownership labels before removal. It continues independent cleanup after an error and reports errors explicitly. SIGKILL, machine crashes or Docker becoming unavailable can prevent cleanup; those cases are not tested or claimed.

`run_framework.py` uses this helper, catches timeout/interruption, retains a failed summary and records cleanup success separately from test success. `--inject-failure after-start` exercises its failure-report path. The Docker lifecycle suite additionally invokes this runner with an injected failure and a timeout, requiring a failed summary, successful cleanup and sentinel survival. The separate Compose/BuildKit runner retains its existing project-scoped cleanup; these new fault cases do not establish Compose/BuildKit interruption behavior. Base images and downloaded image caches are retained; reports are deliberate evidence, not temporary files to erase.

[coverage.json](coverage.json) maps exact emitted test outcomes to clauses, substitutions and untested branches. Framework runs produce `summary.json`, `run.log` and `requirement-evidence.json`; a missing outcome is `not_observed`, never inferred passed from a process exit code. Each map remains partial evidence, including successful vulnerability reproductions. Reports include fixture/helper/skill fingerprints, Git revision/working tree and image identities. The default dependency-free runner does not silently import optional integration results from another snapshot.
