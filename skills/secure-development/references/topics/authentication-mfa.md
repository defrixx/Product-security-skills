# Authentication and MFA

## SD-AUTHN-001

Status: proposed baseline; applicable C01–C06 conditions are MUST requirements. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Determine the actual identity model before applying these conditions; a documented local-only application does not automatically need user accounts. Examples are synthetic design sketches, not authentication implementations.

### SD-AUTHN-001.C01 — Verify identity before creating authenticated state

- **Apply when:** login, federation, API authentication, or a callback turns credentials/assertions into an application identity.
- **Required / prohibited:** verify the credential using the intended identity mechanism before creating authenticated state. Do not trust decoded token claims, a client-supplied user ID, or a successful transport response alone.
- **Rationale:** Unverified identity claims permit account impersonation.
- **Implement:** use maintained identity components with explicit trusted issuers, audiences, keys, time checks, and protocol binding where applicable. Use the password verifier's supported comparison API for local passwords. Obtain exact settings from the deployed identity library's versioned documentation.
- **Unsafe → corrected:** decode a token and accept its `sub` → validate the assertion through the configured verifier, then map its verified identity to an account.
- **Positive check:** valid credentials/assertions for the intended application establish the expected identity.
- **Negative check:** invalid credentials and, where applicable, altered signatures, wrong issuer/audience, expired assertions, or callbacks from a different transaction establish no authenticated state. Test each verifier constraint independently.
- **Evidence:** verifier configuration and credential-to-session trace; actual provider/library tests and session observations. A mocked verifier returning success proves only application plumbing.
- **Bounds / sources:** S1, Authentication General Guidelines and Authentication Protocols. Federation protocol details require protocol-specific primary sources; this condition does not claim a complete OIDC/SAML implementation checklist. Password storage belongs to [cryptographic usage](cryptographic-primitives.md).

### SD-AUTHN-001.C02 — Require completion of the selected factors

- **Apply when:** a user flow requires MFA, including privileged account access under this proposed baseline.
- **Required / prohibited:** grant the protected authenticated state only after all required independent factors succeed. Do not issue a fully privileged session after only the first step or accept a client flag such as `mfaComplete=true`.
- **Rationale:** A partial authentication flow can bypass the selected assurance level.
- **Implement:** maintain server-controlled pending and completed states tied to the same account and transaction. Protect alternate login/API routes with the same factor policy. Prefer phishing-resistant factors where the identity system supports them; document factor and recovery choices.
- **Unsafe → corrected:** password success issues an unrestricted cookie before the OTP page → issue only a restricted pending transaction and promote it after verified completion.
- **Positive check:** complete required factors for the same transaction and access the intended protected operation.
- **Negative check:** skip the second factor, reuse another transaction's challenge, replay an already consumed single-use proof, or call an alternate route; the protected operation remains unavailable. Verify failed and expired pending transactions cannot be promoted.
- **Evidence:** state-machine and route inspection; executed intermediate-state and completed-state requests. Displaying an MFA page is not enforcement evidence.
- **Bounds / sources:** S2, MFA implementation and bypass considerations. Two knowledge questions are not independent factors. Privileged-user MFA is this baseline's acceptance condition; other users' scope follows the threat model and approved exceptions.

### SD-AUTHN-001.C03 — Bound authentication attempts

- **Apply when:** passwords, OTPs, recovery codes, or other limited-entropy proofs can be guessed repeatedly.
- **Required / prohibited:** enforce a documented attempt budget or equivalent abuse control on each applicable verification path. Do not protect the browser login while leaving an API or factor endpoint unlimited.
- **Rationale:** Unlimited guesses make online credential attacks practical.
- **Implement:** use shared enforcement appropriate to account, transaction, and source dimensions; define thresholds, reset behavior, and recovery from lockout. Choose values from risk and operational needs. Consider deliberate account-lockout abuse.
- **Unsafe → corrected:** limit only requests to `/login` → enforce the selected budget at each credential-verification boundary, including OTP and recovery verification.
- **Positive check:** legitimate attempts within the documented policy can authenticate; permitted recovery from throttling works.
- **Negative check:** exceed the budget in isolated tests, including parallel requests; verification is blocked or delayed as specified without granting a session. Check that switching an alternate route does not bypass enforcement.
- **Evidence:** enforcement/state-storage inspection and executed budget-boundary/concurrency observations. An in-process counter alone does not establish multi-instance limits.
- **Bounds / sources:** S1, Login Throttling; S2, OTP security. Do not brute-force real accounts. Record untested distributed behavior as a gap, not a pass.

### SD-AUTHN-001.C04 — Avoid account disclosure through authentication failures

- **Apply when:** login, registration, or recovery returns information about account existence or state to an untrusted caller.
- **Required / prohibited:** use the approved public response policy without unnecessarily distinguishing nonexistent, disabled, or wrong-credential accounts. Do not expose the reason merely through a different status, redirect, or response body.
- **Rationale:** Observable account differences can enable targeted enumeration.
- **Implement:** normalize public failure behavior and retain necessary internal diagnostics without credentials. Assess materially different execution paths where timing could disclose state.
- **Unsafe → corrected:** return `Unknown user` for one input and `Wrong password` for another → use the same public failure contract for both.
- **Positive check:** the legitimate authentication or recovery flow remains usable and gives its intended confirmation.
- **Negative check:** compare synthetic nonexistent and existing-account failures; bodies, statuses, and redirects do not disclose the distinction outside the documented policy. Evaluate timing over repeated local measurements when relevant.
- **Evidence:** failure-path inspection and recorded response comparisons. A single timing sample cannot establish timing resistance.
- **Bounds / sources:** S1, Authentication Responses; S3, Forgot Password Request. Some enrollment products intentionally reveal availability; record the justified policy and compensating abuse controls rather than inventing a universal concealment guarantee.

### SD-AUTHN-001.C05 — Bind recovery proof to one account and purpose

- **Apply when:** password reset or account recovery accepts a token, link, or recovery code.
- **Required / prohibited:** accept valid, unexpired proof only for its intended account and recovery action; consume single-use proof atomically. Do not allow replay or substitution of a different target account.
- **Rationale:** Reusable or unbound recovery credentials can transfer account control.
- **Implement:** use the identity provider's recovery mechanism or protected server-side recovery state with purpose, account, expiry, and consumption checks. Deliver proof through the intended verified channel. Do not derive reset-link authority from an untrusted Host header.
- **Unsafe → corrected:** verify a reset token then apply it to `request.userId` → derive the target from verified recovery state and consume it in the same protected transition.
- **Positive check:** valid proof completes the intended reset once and the new credential works.
- **Negative check:** expired, replayed, wrong-account, wrong-purpose, or concurrently reused proof cannot reset another account or perform a second transition. Confirm unchanged credentials on rejection.
- **Evidence:** token binding/consumption trace and stateful recovery tests, including concurrent redemption where supported. A signed token alone does not establish single use.
- **Bounds / sources:** S3, Reset Tokens and User Resets Password. Session invalidation follows the documented recovery policy and [session controls](sessions-cookies.md). Never trigger real users' recovery flows during a code review.

### SD-AUTHN-001.C06 — Reauthenticate factor and recovery-channel changes

- **Apply when:** an authenticated session can add/remove MFA, replace an authenticator, or change a recovery destination.
- **Required / prohibited:** require the intended fresh proof before changing the account's authentication boundary. Possession of a session alone must not silently replace the required factor.
- **Rationale:** An unattended session must not silently transfer future authentication control.
- **Implement:** use provider-supported sensitive-change workflows, verify the new factor/channel before activation, and apply the product's notification and recovery policies. Lost-factor recovery must have its own documented verification process.
- **Unsafe → corrected:** a session cookie can replace the MFA seed directly → require fresh authorized proof, enroll and verify the new factor, then activate it.
- **Positive check:** the legitimate user completes the required proof and successfully activates the verified replacement.
- **Negative check:** a session without fresh proof, an unverified new factor, or another account's enrollment transaction cannot change the active factor or recovery channel.
- **Evidence:** enrollment-to-activation state trace and executed change-flow tests. Notification delivery alone is not prevention of unauthorized replacement.
- **Bounds / sources:** S1, Reauthentication; S2, Changing MFA Factors and Resetting MFA. Freshness and lost-factor rules depend on the chosen provider and assurance policy; do not prescribe arbitrary universal durations.

## Sources

- **S1:** [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) — General Guidelines; Authentication Responses; Login Throttling; Reauthentication; Authentication Protocols. Living documentation, checked 2026-09-24.
- **S2:** [OWASP Multifactor Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html) — MFA implementation; OTP security; Resetting MFA; Changing MFA Factors. Living documentation, checked 2026-09-24.
- **S3:** [OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) — Forgot Password Request; Reset Tokens; User Resets Password. Living documentation, checked 2026-09-24.
