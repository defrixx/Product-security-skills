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
