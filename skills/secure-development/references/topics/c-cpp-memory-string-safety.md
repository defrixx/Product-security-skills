# C/C++ memory and string safety

## SD-MEMORY-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Applies to native code, including extensions behind managed-language interfaces. Examples illustrate isolated properties and are not complete implementations. Record language standard, compiler, architecture, and analysis configuration; the Python and TypeScript profiles do not establish native-code safety.

### SD-MEMORY-001.C01 — Keep accesses within valid storage

- **Apply when:** code copies, indexes, parses, or exposes a buffer or string across an API boundary.
- **Required / prohibited:** every accessed byte must belong to the valid source/destination range; string consumers must receive the representation they expect. Do not assume a bounded copy supplies termination or makes silent truncation acceptable.
- **Rationale:** incorrect bounds can corrupt memory or disclose adjacent data.
- **Implement:** carry explicit lengths and capacities in C; prefer owning containers and checked access where appropriate in C++. Reserve terminator space for C strings and reject embedded NUL or truncation when the protocol forbids them. A view still needs valid backing storage.
- **Unsafe → corrected:** copy an arbitrary label into `char label[16]` → validate that its length is at most 15, copy that many bytes, and append the terminator; reject longer labels before writing.
- **Positive check:** empty and maximum permitted labels produce exactly the expected terminated value without changing adjacent canaries.
- **Negative check:** a 16-byte label and a forbidden embedded-NUL label fail without partial publication or out-of-range access. Exercise source read bounds as well as destination writes.
- **Evidence:** capacity/length argument for each access; executed boundary tests with supported address-sanitizer instrumentation. A clean run covers only executed paths and does not establish every parser branch.
- **Bounds / sources:** S1 and S5, Description and Potential Mitigations, for writes and reads respectively. Container choice alone does not prove bounds; unchecked indexing, pointer extraction, and foreign APIs still require review.

### SD-MEMORY-001.C02 — Check size arithmetic before allocation or access

- **Apply when:** external counts or dimensions influence multiplication, addition, offsets, allocation, or conversion to a smaller/unsigned type.
- **Required / prohibited:** reject unrepresentable or policy-exceeding sizes before the arithmetic result is used. Do not detect signed overflow by performing the overflowing expression first.
- **Rationale:** wraparound can allocate a small buffer for a large logical operation.
- **Implement:** validate signed inputs before conversion; use checked arithmetic or preconditions appropriate to the actual types. Separately impose the application's resource budget after representability checks.
- **Unsafe → corrected:** allocate `count * sizeof(Item)` without checking → reject `count > SIZE_MAX / sizeof(Item)` before multiplication, then apply the configured count limit and handle allocation failure.
- **Positive check:** representative valid counts allocate the expected size and process exactly that many items.
- **Negative check:** overflow-sized counts, negative inputs before unsigned conversion, and over-budget counts fail before allocation or writes; inject allocation failure to verify safe propagation.
- **Evidence:** type widths and conversion/arithmetic trace; executed boundary cases on the supported architecture. Undefined-behavior instrumentation does not generally prove absence of unsigned wraparound.
- **Bounds / sources:** S2, Potential Mitigations. The sketch addresses one multiplication; headers, alignment, additions, and later offsets require their own checked expressions.

### SD-MEMORY-001.C03 — Preserve ownership and lifetime through every use

- **Apply when:** pointers, references, views, callbacks, or foreign interfaces retain access to allocated or stack-backed data.
- **Required / prohibited:** each use must occur while its backing object is alive and valid; release resources through the designated owner exactly once. Do not return or queue a view into expired storage.
- **Rationale:** dangling references and duplicate release can enable memory corruption.
- **Implement:** express ownership with RAII and owning values in C++; document ownership transfer and cleanup paths in C. Copy data or extend ownership across asynchronous work; account for container reallocation and cancellation.
- **Unsafe → corrected:** return a `string_view` into a local string → return an owning string, or accept caller-owned storage with an explicit lifetime contract.
- **Positive check:** normal and delayed consumers receive valid data for the documented lifetime.
- **Negative check:** exercise cancellation, error cleanup, repeated teardown, and container reallocation; no subsequent consumer may access released storage or release it again.
- **Evidence:** ownership graph and normal/error-path inspection; executed lifetime tests with address instrumentation. Lack of a crash without instrumentation is weak evidence; concurrent ownership also needs synchronization analysis.
- **Bounds / sources:** S3, Description and Potential Mitigations. Setting one pointer to null does not invalidate aliases; reference counting alone does not establish race freedom.

### SD-MEMORY-001.C04 — Keep external strings out of formatting syntax

- **Apply when:** printf-family or equivalent formatting APIs receive user-controlled strings, including logging wrappers.
- **Required / prohibited:** external values occupy data arguments, never the format program. Do not forward a validated-looking user message as the format string.
- **Rationale:** format directives can read or write memory through unintended argument interpretation.
- **Implement:** use a fixed format and correctly typed arguments, or a non-formatting output API. Preserve format-checking annotations on wrappers where supported by the toolchain.
- **Unsafe → corrected:** `printf(message)` → `printf("%s", message)` for a valid terminated string; use a length-aware data output API for arbitrary bytes.
- **Positive check:** an ordinary synthetic message is emitted with the expected formatting.
- **Negative check:** synthetic percent directives are emitted literally without interpreting missing arguments or altering a canary. Run intentionally unsafe comparisons only in a disposable local process.
- **Evidence:** format-argument provenance and wrapper inspection; compiler diagnostics plus executed literal-output checks. A warning-free build does not prove dynamically selected format strings are trusted.
- **Bounds / sources:** S4, Potential Mitigations. Correct formatting does not independently establish valid pointer lifetime, termination, or log-injection protection; apply C01, C03, and [logging](logging-monitoring.md).

## Sources

- **S5:** [MITRE CWE-125](https://cwe.mitre.org/data/definitions/125.html) — Out-of-bounds Read, CWE 4.20, Description and Potential Mitigations; checked 2026-09-28. Compiler and library API details still require their primary documentation.

- **S1:** [MITRE CWE-787](https://cwe.mitre.org/data/definitions/787.html) — Description and Potential Mitigations, CWE 4.20; checked 2026-09-24. Mitigations are contextual: a bounded string-copy API alone is not accepted as proof of safety.
- **S2:** [MITRE CWE-190](https://cwe.mitre.org/data/definitions/190.html) — Description and Potential Mitigations, CWE 4.20; checked 2026-09-24.
- **S3:** [MITRE CWE-416](https://cwe.mitre.org/data/definitions/416.html) — Description and Potential Mitigations, CWE 4.20; checked 2026-09-24.
- **S4:** [MITRE CWE-134](https://cwe.mitre.org/data/definitions/134.html) — Description and Potential Mitigations, CWE 4.20; checked 2026-09-24.
