# XML and serialization hardening

## SD-SERIAL-001

Status: proposed baseline; applicable C01–C03 are MUST conditions. Follow the [requirement format](../requirement-format.md) for evidence and exceptions. Inspect the parser actually invoked, including framework wrappers and secondary transformation steps. Examples are synthetic design sketches.

### SD-SERIAL-001.C01 — Prevent untrusted external resource resolution

- **Apply when:** XML, schemas, stylesheets, or document processing can resolve external entities, includes, or resource references.
- **Required / prohibited:** prevent attacker-selected file/network resolution. Do not assume a parser's default or a network-only restriction also prevents local-file reads.
- **Rationale:** Parser-initiated external resolution can expose files or make unintended requests.
- **Implement:** disable unnecessary DTD/entity/include features and external resolution at every processing stage. If the product needs local schemas, use a controlled resolver mapping approved identifiers to fixed local resources, with no arbitrary fallback. Check the exact parser/version documentation before setting features.
- **Unsafe → corrected:** parse imported XML with an unrestricted resolver → use the intended restricted parser/resolver for parsing and subsequent validation/transformation.
- **Positive check:** a supported document, and an approved local schema if required, produce the intended data without unexpected I/O.
- **Negative check:** synthetic external references to a disposable file sentinel and a controlled local endpoint cause no unauthorized read/request. Exercise parser, validator, and transformer separately when they have independent resolvers.
- **Evidence:** configuration-to-call-site trace and observed file/network behavior in an isolated test. An error after a network request is not proof that resolution was prevented.
- **Bounds / sources:** S1, General Guidance and parser-specific defenses. Test the installed library/version; wrappers can override configuration. Do not use production files or external services as probes.

### SD-SERIAL-001.C02 — Keep deserialization data-only

- **Apply when:** untrusted serialized values can select runtime types, constructors, callbacks, or native object reconstruction.
- **Required / prohibited:** prevent attacker-selected executable object construction. Do not treat JSON, YAML, or a signed container as inherently safe if configured hooks instantiate arbitrary classes.
- **Rationale:** Object reconstruction can invoke behavior controlled by serialized input.
- **Implement:** prefer data-only decoding followed by explicit schema validation and application-owned construction. Where polymorphism is necessary, map a finite public discriminator to reviewed data models without dynamic imports or arbitrary type names.
- **Unsafe → corrected:** load user-supplied native objects or resolve a payload's class name dynamically → decode a plain mapping, validate it, and instantiate an explicitly selected application DTO.
- **Positive check:** a supported data message constructs only the expected inert model and preserves legitimate fields.
- **Negative check:** an unknown type tag or synthetic constructor-hook request is rejected without invoking the hook or creating an external side effect. A harmless local hook counter can establish invocation without executing a real exploit.
- **Evidence:** decoder options/type-resolution trace and executed hook/unknown-type tests. Schema validation performed after arbitrary construction is too late.
- **Bounds / sources:** S2, General Precautions and language-specific guidance. Existing native-object protocols need a scoped migration or tightly justified trust boundary; signatures do not make a compromised producer's object graph safe.

### SD-SERIAL-001.C03 — Bound parser and expansion work

- **Apply when:** XML entities, nesting, aliases, object graphs, or decoded collections can amplify processing beyond input byte size.
- **Required / prohibited:** enforce the selected size/depth/expansion/work budgets during processing. Do not rely on compressed or raw input size alone to bound expanded memory and CPU.
- **Rationale:** Unbounded parser work can exhaust memory or CPU before business validation.
- **Implement:** use supported parser limits and disable unnecessary amplification features; bound input and decoded records. If a library cannot enforce the necessary budget, use an isolated worker with enforced resource limits or choose a suitable parser. Record each budget and its enforcement stage.
- **Unsafe → corrected:** accept a small input and allow unrestricted entity expansion → reject unsupported entities and enforce parser/work limits before expansion exhausts resources.
- **Positive check:** a representative supported document at the declared boundary parses successfully.
- **Negative check:** bounded synthetic deep nesting, repeated aliases/entities, or excessive records terminate with the expected controlled failure; verify no partial trusted object is published. Use small configured limits rather than creating a real resource-exhaustion incident.
- **Evidence:** parser limit configuration and executed boundary observations with time/memory/output measurements as relevant. A recursion exception alone does not establish a deliberate resource budget.
- **Bounds / sources:** S1, Secure Processing and Entity Expansion; S2, defensive deserialization guidance. Limits and safe defaults vary by implementation/version.

## Sources

- **S1:** [OWASP XML External Entity Prevention](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) — General Guidance; XML Parser Security Features; parser-specific defenses. Living documentation, checked 2026-09-24.
- **S2:** [OWASP Deserialization](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html) — General Precautions; language-specific safe decoding and type-restriction guidance. Living documentation, checked 2026-09-24. Exact settings require the selected library's primary documentation.
