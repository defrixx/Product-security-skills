# TypeScript / React / Next.js profile

Scope: TypeScript applications with React 19 and Next.js 16 App Router. Sources are living vendor documentation (Next.js selector showed 16.3.6 when checked on 2026-09-24). Verify the installed patch release and relevant advisories before prescribing production settings. TypeScript typing is not runtime input validation.

Status: proposed baseline, source-reviewed; every applicable rule below is a proposed MUST. Use [the requirement format](../requirement-format.md) for exceptions. These controls refine specific general conditions; record each applicable condition separately. Examples are synthetic sketches. No React/Next.js build or browser integration is claimed by the bundled Python regression suite.

## SD-TS-001 — Enforce access at server operations

- Parent: `SD-AUTHZ-001`, `SD-API-001`; applies to protected Server Actions and Route Handlers.
- Required implementation behavior: validate input and enforce the intended access policy inside each callable server operation.
- Rationale: hiding controls in a page does not protect the callable operation.
- Implementation: perform checks in the server-side data-access boundary and return only the necessary DTO fields. Treat action arguments as untrusted.
- Limit: `use server` does not itself authenticate callers. Local-only applications need a documented local request boundary rather than an invented user model.
- Source: [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security) — Server Actions, authorization, and data-access layer; checked 2026-09-24.
- **Condition mapping:** [SD-AUTHZ-001.C01, C02, and C04](../topics/authorization-access-control.md), [SD-INPUT-001.C01](../topics/input-validation-injection.md), and [SD-API-001.C01](../topics/api-web-services.md). Operation, object, protected-field, and schema checks need separate observations.
- **Apply when:** an exported Server Action or Route Handler reaches protected reads or writes, including actions invoked outside the page that normally displays them.
- **Unsafe → corrected:** hide an edit button but let the handler update any supplied record ID → resolve the server-side principal, validate the request, and authorize the operation and record before writing.
- **Positive check:** a synthetic authorized caller updates its permitted record and receives only the intended public result.
- **Negative check:** invoke each operation directly as an unauthenticated caller, an unauthorized role, and a caller supplying another object's ID; expect no unauthorized state change. Test forbidden privilege fields independently.
- **Evidence:** trace every callable entry point to its data-access checks; execute requests through the relevant Next.js mechanism and inspect persisted state. A Route Handler test does not establish Server Action protection; mocked identities leave actual authentication unverified.

## SD-TS-002 — Keep rendering data inert

- Parent: `SD-WEB-001`; applies to untrusted text/HTML rendering.
- Required implementation behavior: untrusted markup must not execute in the application origin.
- Rationale: rendering escape hatches can bypass normal text treatment.
- Implementation: render text as JSX children. If HTML is a product requirement, use a reviewed sanitizer before `dangerouslySetInnerHTML` and inspect the actual producer of that value.
- Limit: finding an escape hatch is not proof of exploitable XSS; URL and third-party component behavior require separate checks.
- Source: [React common DOM components](https://react.dev/reference/react-dom/components/common) — React 19, `dangerouslySetInnerHTML`; checked 2026-09-24.
- **Condition mapping:** [SD-WEB-001.C01 and C02](../topics/client-web-security.md). Plain-text rendering and deliberately supported HTML have distinct acceptance paths.
- **Apply when:** URL/API/storage values reach JSX, third-party components, or direct DOM/HTML escape hatches.
- **Unsafe → corrected:** render a plain user label with `dangerouslySetInnerHTML` → render it as `{label}`; if rich text is required, apply the selected sanitizer policy at the HTML boundary.
- **Positive check:** plain labels retain their literal content; allowed rich-text formatting remains usable where supported.
- **Negative check:** synthetic element/event payloads do not set a browser execution marker; forbidden attributes and URL schemes are absent or inert through the actual rich-text path.
- **Evidence:** inspect the value producer, context, sanitizer configuration/version, and sink; execute browser checks of DOM and side effects. A string snapshot cannot establish browser execution behavior; a text-only test leaves rich HTML unverified.

## SD-TS-003 — Keep credentials out of browser bundles

- Parent: `SD-SECRET-001`; applies to secrets supplied during build or server execution.
- Required implementation behavior: private credentials must not become client-visible configuration or component props.
- Rationale: browser bundles are distributable artifacts.
- Implementation: keep credentials in server-only code; do not put them in `NEXT_PUBLIC_` variables. Send only public values across the server/client boundary.
- Limit: build-time filtering is not a substitute for runtime access controls, and already distributed artifacts need separate handling after a leak.
- Source: [Next.js Environment Variables](https://nextjs.org/docs/app/guides/environment-variables) — browser inlining with `NEXT_PUBLIC_`; checked 2026-09-24.
- **Condition mapping:** [SD-SECRET-001.C02](../topics/secrets.md), with response/diagnostic paths additionally assessed under C03 where applicable.
- **Apply when:** build environment values, server modules, configuration, or server-produced props can cross into client assets or responses.
- **Unsafe → corrected:** put a private API credential in `NEXT_PUBLIC_SERVICE_KEY` → retain it in the server-side integration and expose only the public result fields required by the client.
- **Positive check:** the intended server operation can use an inert synthetic credential while the page receives its documented public data.
- **Negative check:** the canary is absent from generated client assets, initial HTML, server-component payloads, and captured responses; exercise success and error branches separately.
- **Evidence:** inspect module imports, configuration inlining, and server/client serialization; build and exercise the actual app, then inspect each output surface. A response-body read failure must be reported as uninspected, not treated as an empty safe response.
