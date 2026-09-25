# Input validation and injection prevention

## SD-INPUT-001

Status: proposed engineering baseline; each applicable C01–C05 condition is a MUST. Follow the [requirement format](../requirement-format.md) for reporting and exceptions. Input validation and sink protection require separate evidence. Examples are deliberately small synthetic pseudocode; adapt APIs to the actual stack.

### SD-INPUT-001.C01 — Validate decoded input before effects

- **Apply when:** external requests, messages, files, or provider responses enter trusted business logic.
- **Required / prohibited:** enforce the accepted type, shape, and semantic constraints before side effects. Do not rely on TypeScript declarations, a browser form, or an upstream consumer's validation.
- **Rationale:** Unvalidated values can reach sensitive effects before their meaning is constrained.
- **Implement:** define a boundary schema, explicit coercion rules, and cross-field invariants. Reject unexpected mutation fields unless extensibility is an intentional contract. See [Python schema validation](../stacks/python-fastapi.md) and [Next.js server operations](../stacks/typescript-nextjs.md).
- **Unsafe → corrected:** copy a decoded dictionary directly into an account model → validate a dedicated mutation DTO and assign only permitted fields.
- **Positive check:** documented values at the accepted boundaries reach the intended operation.
- **Negative check:** wrong types, unknown privilege fields, excessive lengths, and invalid cross-field combinations fail before writes or jobs are scheduled. Observe each selected constraint independently.
- **Evidence:** trace the decoded object to validation and every use; execute schema-boundary cases with state observations. An unused schema is not enforcement evidence.
- **Bounds / sources:** S1, Syntactic and Semantic Validity and Allowlist vs Denylist. Validation does not establish authorization or protect dynamically constructed interpreter syntax.

### SD-INPUT-001.C02 — Bind database values as data

- **Apply when:** untrusted values reach SQL, including ORM raw-query escape hatches and stored-procedure internals.
- **Required / prohibited:** keep values separate from executable query syntax through the driver's binding API. Do not interpolate or concatenate values into SQL or rely on ad hoc quote replacement.
- **Rationale:** Query syntax built from values can change the intended database operation.
- **Implement:** use prepared/bound queries; inspect the final raw-query call rather than assuming use of an ORM guarantees safety. See [SQLAlchemy binding](../stacks/python-fastapi.md). Dynamic identifiers belong to C03.
- **Unsafe → corrected:** `execute("SELECT id FROM records WHERE label='" + value + "'")` → `execute("SELECT id FROM records WHERE label=:label", {label: value})` with the driver's actual parameter convention.
- **Positive check:** a known label returns its intended record; a legitimate label containing an apostrophe remains usable.
- **Negative check:** an input such as `' OR 1=1 --` does not select unrelated records or change state; an unmatched exact value returns no records.
- **Evidence:** inspected query construction plus executed database tests. A mocked driver's received arguments establish call shape, not actual database interpretation.
- **Bounds / sources:** S2, Prepared Statements and Stored Procedures. Binding does not authorize returned rows; SQL evidence does not establish safety for NoSQL operators or other query languages.

### SD-INPUT-001.C03 — Select executable identifiers from fixed mappings

- **Apply when:** users select table/column names, sort direction, template names, or another syntactic element that a value-binding API cannot parameterize.
- **Required / prohibited:** map public choices to trusted predefined syntax or objects. Do not accept arbitrary syntax merely because adjacent values are bound.
- **Rationale:** SQL binding does not constrain identifiers that become executable syntax.
- **Implement:** use a finite map from public options to known query objects, approved templates, or literal directions. Unknown choices reject or use a documented safe default without retaining any untrusted fragment.
- **Unsafe → corrected:** append `request.sort` after `ORDER BY` → select the column object from `{created: records.created_at, title: records.title}`.
- **Positive check:** every supported public option selects the intended operation/order.
- **Negative check:** unknown names and syntax-bearing input are rejected before query/template execution; no fallback interpolates the original value.
- **Evidence:** inspect all map construction and consumers; run valid and invalid selections against the real interpreter where practical. A regex alone needs a complete argument for the allowed grammar.
- **Bounds / sources:** S2, Allow-list Input Validation. This applies to finite application choices; products intentionally accepting query languages need a separately designed capability boundary.

### SD-INPUT-001.C04 — Prevent shell and argument injection

- **Apply when:** external values influence process creation, executable selection, or command arguments.
- **Required / prohibited:** prevent untrusted input from selecting shell syntax or privileged command options. An argument array alone is insufficient if attacker-controlled flags change the tool's behavior.
- **Rationale:** Shell syntax and program options can turn data into unintended commands.
- **Implement:** prefer an in-process library. Otherwise fix the executable, use a non-shell argument API, validate the argument's meaning, and use an option terminator only when the invoked tool supports it. Constrain environment and working directory to the operation's needs.
- **Unsafe → corrected:** `shell("convert " + name)` → call the selected library, or a fixed executable with separately supplied validated operand arguments and tool-specific option handling.
- **Positive check:** a valid operand, including supported spaces, is processed correctly.
- **Negative check:** shell metacharacters do not create another process/action; an operand starting with an option prefix cannot enable unintended tool features. Use harmless local sentinels, never real destructive commands.
- **Evidence:** process-launch/data-flow inspection and isolated execution observing arguments and side effects. Mocked argument capture cannot prove the executable's option semantics.
- **Bounds / sources:** S3, Primary Defenses and Argument Injection. Windows and POSIX invocation rules differ; test the actual operating system and executable version.

### SD-INPUT-001.C05 — Preserve meaning across decoding boundaries

- **Apply when:** input undergoes URL decoding, Unicode normalization, parsing, or another transformation before a security decision or interpreter sink.
- **Required / prohibited:** validate the representation consumed by the protected operation and prevent a later decoding stage from changing the security-relevant meaning. Do not validate one representation and use another without checking the relationship.
- **Rationale:** Different decoding interpretations can bypass validation boundaries.
- **Implement:** document the transformation order, apply the intended canonicalization once at the boundary, and use destination-specific encoding or safe APIs at the sink. For output contexts follow [client-web controls](client-web-security.md); for filesystem names follow [file controls](files-uploads.md).
- **Unsafe → corrected:** reject `../` before URL decoding, then decode and open the result → validate the actual decoded filename and enforce the filesystem boundary at use.
- **Positive check:** supported non-ASCII and encoded inputs retain their documented meaning.
- **Negative check:** malformed, multiply encoded, or ambiguous input cannot bypass the same policy applied to its final representation; inspect the sink's actual operand, not only the validator result.
- **Evidence:** complete transformation trace and executed end-to-end cases through the relevant parser stack. An isolated validator test leaves downstream reinterpretation unverified.
- **Bounds / sources:** S1, Unicode and Free-form Unicode Text. Do not normalize passwords or arbitrary binary data without a protocol-specific contract; encoding for one output context is not reusable everywhere.

## Sources

- **S1:** [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html) — Input Validation Strategies; Syntactic and Semantic Validity; Unicode. Living documentation, checked 2026-09-24.
- **S2:** [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) — Prepared Statements; Stored Procedures; Allow-list Input Validation. Living documentation, checked 2026-09-24.
- **S3:** [OWASP OS Command Injection Defense](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html) — Argument Injection; Primary Defenses. Living documentation, checked 2026-09-24.
