# Select and triage analysis tools

Detect manifests, lockfiles, runtime languages and deployment artifacts before choosing tools. Prefer complementary installed checks relevant to the assessed paths over running every available scanner. Check the executable's provenance, version and local help before using version-specific flags; do not auto-install tools or invoke a downloader such as npx merely to check availability.

## Execution contract

Inspect project configuration, plugins, hooks and build/test paths before execution. Static tools may load plugins; dependency resolution may execute build backends; tests execute target code. Use isolated disposable state with restricted credentials and authorized network effects. Preserve the target tree; exclude fix/update modes. Cache and build writes belong in disposable locations. A command labeled audit or test is not inherently read-only or isolated.

Separate downloading public advisory data from transmitting package inventories or source. For example, npm audit submits dependency information to a registry. Verify the configured endpoint and existing authorization before transmission; use offline/local evidence when transmission is outside scope. Do not print raw secret-scan matches or sensitive paths into ordinary logs.

## Selection table

Commands below are candidates after the execution contract is satisfied, not commands to run blindly.

| Input / purpose | Candidate | Selection detail |
| --- | --- | --- |
| Python source | `bandit -r <scoped-path> -f json` | Inspect configuration/plugins and exclude unrelated trees; a syntactic hit needs flow validation |
| Python requirements or prepared environment | `pip-audit -r requirements.txt -f json` or `pip-audit -f json` | Resolution can have installation-like effects; use a prepared isolated environment. Poetry lock is not a requirements file |
| npm project | `npm audit --json` | Sends dependency data; preserve lockfile and omit `fix`; confirm runtime/dev inclusion |
| Go packages | `govulncheck ./...` | Vulnerable-symbol evidence helps prioritize traces; review module resolution and build effects |
| Rust Cargo.lock | `cargo audit --json` | Check advisory database freshness and update/network behavior; assess features/platform applicability |
| Multiple source languages | Semgrep with selected reviewed local rules and JSON output | Check installed-version syntax, telemetry and configuration; remote rules require separate network assessment |
| Concurrent Go code | `go test -race <selected-packages>` | Executes tests; inspect their effects first; a clean run covers only exercised paths |
| Native concurrent code | Existing ThreadSanitizer-enabled build/tests | Use the actual supported toolchain and isolated build; detector evidence concerns executed interleavings |

For JVM/.NET/PHP/Ruby, choose the installed ecosystem advisory checker against the actual resolved graph. For secrets, containers and IaC, choose a scoped local detector when those artifacts are included. Verify exact commands against installed-version vendor documentation before execution. Do not expand current-state review into Git-history secret scanning without scope authorization.

A code index or local graph service can help find callers and alternate paths. Confirm that it indexes the recorded revision, inspect relevant source directly, and validate dynamic dispatch/generated-code edges separately. It does not authorize uploading source or establish exploitability.

## From signal to decision

1. Bind the result to the assessed input, tool version, rules/advisory database and command. Distinguish findings exit codes from execution/configuration errors.
2. Check the resolved component and delivered artifact. A lockfile is evidence of resolution, not proof of what was packaged; account for platform, features, vendoring and transitive dependencies.
3. Verify advisory version range and configuration, then trace vulnerable functionality and attacker influence. Preserve an applicable dependency advisory as an actionable signal even if exploit reachability remains unresolved.
4. Confirm impact and defenses using [analysis and validation](analysis-and-validation.md). Keep unverified signals as hypotheses, verified false premises as disproved, and sufficient static/runtime proof as confirmed.
5. Reconcile every relevant input signal with its disposition or concrete processing error. Group duplicates only at a demonstrated common repair boundary. Report useful executed outcomes and next actions; never turn tool failure or an empty result into a security pass.

## Sources

Living documentation verified 2026-10-18; match the installed version before use:

- [Bandit command manual](https://bandit.readthedocs.io/en/latest/man/bandit.html), recursive input and JSON format.
- [pip-audit usage and security model](https://github.com/pypa/pip-audit), requirements/environment inputs and installation-like behavior.
- [npm CLI v11 audit](https://docs.npmjs.com/cli/v11/commands/npm-audit/), registry submission, fix behavior and exit codes.
- [Go security tooling](https://go.dev/doc/security/), govulncheck and vulnerable-function analysis.
- [cargo-audit](https://github.com/rustsec/rustsec/tree/main/cargo-audit), Cargo.lock advisory analysis.
- [Semgrep rule execution](https://semgrep.dev/docs/running-rules), rule/configuration selection.
- [Go race detector](https://go.dev/doc/articles/race_detector), execution and coverage boundaries.
