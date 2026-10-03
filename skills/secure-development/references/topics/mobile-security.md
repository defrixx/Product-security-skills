# Mobile application security

## SD-MOBILE-001

Status: proposed baseline; C01–C04 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Record OS, SDK, target/minimum versions, device configuration, and tested package identity. Examples are synthetic designs; platform API details require matching Android/Apple documentation. Shared [authentication](authentication-mfa.md), [authorization](authorization-access-control.md), [transport](x509-certificates.md), and [privacy](privacy-data-protection.md) conditions remain applicable.

### SD-MOBILE-001.C01 — Protect locally retained sensitive data

- **Apply when:** credentials or sensitive records persist in app files, preferences, databases, or key material.
- **Required / prohibited:** use storage protection appropriate to the documented device-access threat model; do not store credentials in generally accessible files or embed a decryption key beside ciphertext.
- **Rationale:** device access or unintended file sharing can expose authenticated sessions and personal records.
- **Implement:** use platform credential/key storage with deliberate accessibility and sharing settings; minimize retained data and apply protected application storage for necessary records. Define logout and account-switch cleanup.
- **Unsafe → corrected:** write a synthetic refresh token into shared preferences accessible through an export path → retain it in the selected platform-protected credential store and remove the export path.
- **Positive check:** the intended authenticated feature can retrieve its data in the permitted device state.
- **Negative check:** an unrelated app or excluded device state cannot retrieve the credential; account switching cannot expose the previous account's cached records; after logout, locally retained credentials and records follow the declared removal/access policy and cannot silently restore the previous session.
- **Evidence:** storage APIs, entitlements/permissions, and data-flow inspection; executed device tests with stated access capabilities. An emulator does not establish hardware-backed key guarantees.
- **Bounds / sources:** S1, STORAGE and CRYPTO. A rooted/jailbroken attacker changes the model; no blanket claim of secrecy on a fully compromised device.

### SD-MOBILE-001.C02 — Restrict exposed components and incoming links

- **Apply when:** intents, exported components, URL schemes, universal/app links, document handlers, or IPC invoke application operations.
- **Required / prohibited:** expose only intended operations and validate caller/input context before privileged effects. A link's arrival must not itself authorize the referenced operation.
- **Rationale:** another application can supply crafted invocations outside the normal UI flow.
- **Implement:** review the packaged manifest/entitlements and registration rules, narrow exported interfaces, validate payload schemas, and enforce authorization at the operation boundary. Apply file-path controls to imported documents.
- **Unsafe → corrected:** an incoming link's account identifier selects private data directly → validate the link and resolve access using the authenticated account's permissions.
- **Positive check:** an intended link or authorized IPC caller reaches the documented operation.
- **Negative check:** a synthetic unauthorized caller, malformed payload, and wrong-account identifier each cause no protected read or mutation.
- **Evidence:** packaged registrations and handler-to-effect trace; local device/emulator invocations and observed state. Manifest inspection alone does not establish handler authorization.
- **Bounds / sources:** S1, PLATFORM and AUTH. Domain association verifies routing relationships, not business authorization. Backend enforcement must also withstand a modified client.

### SD-MOBILE-001.C03 — Prevent unintended secondary copies

- **Apply when:** sensitive screens or records can enter backups, notifications, screenshots/app-switcher previews, clipboard, or logs.
- **Required / prohibited:** enforce the project's disclosure policy at each applicable secondary destination. Do not assume private application storage automatically excludes backups or UI snapshots.
- **Rationale:** data can escape its primary store through ordinary platform features.
- **Implement:** map each destination, exclude or redact prohibited fields, and select supported platform controls for the actual OS version. Use destination-specific evidence rows; one passing log check does not establish backup safety.
- **Unsafe → corrected:** display a full synthetic recovery code in a notification → show a generic notification and reveal the code only within the authorized application flow.
- **Positive check:** permitted notifications and backup/recovery features retain their documented utility.
- **Negative check:** a seeded sensitive marker is absent from each prohibited destination under lock, backgrounding, backup, and error scenarios as applicable.
- **Evidence:** destination configuration and call-site inspection; captured synthetic outputs or tested backup contents.
- **Bounds / sources:** S1, STORAGE and PLATFORM. Screenshot prevention varies by platform and cannot prevent an external camera; state the actual achieved boundary.

### SD-MOBILE-001.C04 — Constrain WebView content and native bridges

- **Apply when:** embedded web content can navigate, execute script, or invoke a native bridge.
- **Required / prohibited:** grant native capabilities only to the intended trusted content and validated operations. Do not expose a privileged bridge to arbitrary URLs or redirects.
- **Rationale:** web content can inherit native application privileges through a permissive bridge.
- **Implement:** isolate untrusted content, validate navigation destinations including redirects, minimize bridge methods, and verify arguments and authorization at the native operation. Disable unnecessary script/file access using version-supported settings.
- **Unsafe → corrected:** load an external URL in a WebView with a file-reading bridge → open untrusted content without that bridge and retain a narrow bridge only for the controlled origin.
- **Positive check:** the trusted page invokes an allowed synthetic native operation with valid arguments.
- **Negative check:** navigation to an untrusted origin, a redirected page, and a malformed bridge call cannot read a sentinel file or invoke a protected operation.
- **Evidence:** navigation policy, bridge registration, and native handler trace; executed WebView tests on supported OS versions. Browser-only tests do not establish native bridge isolation.
- **Bounds / sources:** S1, PLATFORM. Safe web rendering still needs [client-web controls](client-web-security.md); origin checks alone do not remedy XSS in a trusted page.

## Sources

- **S1:** [OWASP MASVS](https://mas.owasp.org/MASVS/) — STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, and PRIVACY control groups. Living documentation; checked 2026-09-24. These conditions are a proposed engineering application, not a claim of complete MASVS conformance. Pinning and anti-tampering controls require a specific threat model and lifecycle plan.
