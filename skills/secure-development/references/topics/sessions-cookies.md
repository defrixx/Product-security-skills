# Sessions and cookies

## SD-SESSION-001

Status: proposed baseline; applicable C01–C04 are MUST conditions. Use the [requirement format](../requirement-format.md) for evidence and exceptions. Session checks do not establish account authentication or object authorization. Examples are synthetic design sketches.

### SD-SESSION-001.C01 — Accept only server-authorized session identifiers

- **Apply when:** a bearer value associates a request with authenticated server state.
- **Required / prohibited:** generate unpredictable identifiers through the maintained session mechanism and validate them against the intended session state. Do not derive IDs from user IDs/timestamps or adopt arbitrary client-provided IDs as authenticated sessions.
- **Rationale:** Predictable or attacker-selected identifiers enable session guessing or fixation.
- **Implement:** use framework-managed sessions with documented cryptographic randomness and strict lookup/validation. Keep identity and privilege authoritative on the server or in a correctly verified assertion with explicit lifecycle semantics.
- **Unsafe → corrected:** `session_id = user_id + timestamp` → obtain a new identifier from the configured session manager after successful authentication.
- **Positive check:** a newly issued session maps to exactly its authenticated account.
- **Negative check:** unknown, malformed, or altered identifiers do not create authenticated state or resolve to another account.
- **Evidence:** inspect generator and acceptance paths; execute issued/unknown/tampered cases. A small sample with no collisions is not proof of unpredictability; inspect the randomness source.
- **Bounds / sources:** S1, Session ID Properties and Strict Session Management. Signed self-contained tokens need signature/claim validation and explicit invalidation design; opaque-session tests do not cover them automatically.

### SD-SESSION-001.C02 — Limit exposure through the session transport

- **Apply when:** browsers receive session cookies or another bearer-session transport is configured.
- **Required / prohibited:** use the intended protected channel and prevent unnecessary script/domain exposure. Do not place session credentials in URLs or assume cookie defaults match the deployment.
- **Rationale:** Weak transport and cookie settings expose reusable session credentials.
- **Implement:** for HTTPS browser sessions set Secure, HttpOnly when script access is unnecessary, an explicit appropriate SameSite policy, and the narrowest practical host/path scope. Inspect trusted-proxy handling. Non-cookie clients need an explicit protected transport/storage design.
- **Unsafe → corrected:** issue a broadly scoped cookie readable by scripts → use a host-scoped protected session cookie with application-appropriate SameSite handling.
- **Positive check:** the browser sends the cookie on the intended authenticated flow, including any supported federation redirect.
- **Negative check:** inspect actual Set-Cookie headers and browser behavior: no unintended script access, insecure transport, or broader host delivery. Test each selected property independently.
- **Evidence:** middleware/proxy configuration and actual response/browser observations. A configuration flag alone does not prove the deployed header survives proxy rewriting.
- **Bounds / sources:** S1, Cookies and Exchange Mechanisms. Cookie Path is not an isolation boundary against same-origin scripts. SameSite is not a substitute for the [client-web CSRF design](client-web-security.md); local development exceptions need explicit scope.

### SD-SESSION-001.C03 — Replace sessions when trust increases

- **Apply when:** login, MFA completion, or a privilege transition promotes an existing session's authority.
- **Required / prohibited:** issue a session appropriate to the new trust level and prevent a pre-transition identifier from acquiring that authority. Do not simply mark an attacker-fixable anonymous session as privileged.
- **Rationale:** Retaining a pre-authentication identifier can preserve attacker control after login.
- **Implement:** use the framework's supported regeneration/invalidation mechanism; transfer only intended non-security state. Coordinate pending authentication with [MFA completion](authentication-mfa.md).
- **Unsafe → corrected:** retain the supplied anonymous session ID after login → regenerate at login and invalidate the prior ID according to the transition contract.
- **Positive check:** complete the transition and use the newly issued identifier successfully.
- **Negative check:** replay the pre-transition identifier from a separate client; it cannot access the newly granted authority. Verify all session-bearing cookies/tokens involved in the flow.
- **Evidence:** inspect transition and old-state disposal; execute two-client fixation/rotation tests. Observing a new cookie is insufficient if the previous one still works with elevated rights.
- **Bounds / sources:** S1, Renew the Session ID After Any Privilege Level Change. Distributed grace periods must not preserve unintended elevated access; document and test their exact scope.

### SD-SESSION-001.C04 — Enforce expiry and termination at the verifier

- **Apply when:** sessions have logout, inactivity, absolute lifetime, administrative invalidation, or recovery-related termination rules.
- **Required / prohibited:** enforce the documented lifetime and termination policy where sessions are accepted. Deleting a browser cookie or relying on its expiry alone is not server-side invalidation.
- **Rationale:** Client-side logout alone can leave a reusable server credential active.
- **Implement:** define actual idle/absolute lifetimes and revocation scope; use server state, session versions, or a documented bounded token strategy. Align sensitive account changes with the [authentication recovery policy](authentication-mfa.md).
- **Unsafe → corrected:** logout only clears the cookie → invalidate the server-side session and clear the client cookie with matching scope.
- **Positive check:** an active session within its permitted lifetime continues to work; a legitimate new login can establish a new session after logout.
- **Negative check:** replay a captured synthetic identifier after logout, expiry, or the selected invalidation event; the verifier rejects it according to the explicit policy. Test idle and absolute expiry separately with a controlled clock.
- **Evidence:** inspect lifetime/revocation enforcement and execute replay tests against the real acceptance path. Frontend redirects alone do not prove termination.
- **Bounds / sources:** S1, Session Expiration. No universal timeout is prescribed. If stateless tokens remain valid for a bounded interval, disclose that interval and do not claim immediate revocation.

## Sources

- **S1:** [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) — Session ID Properties; Exchange Mechanisms; Cookies; Session ID Life Cycle; Session Expiration. Living documentation, checked 2026-09-24. Verify actual framework and browser behavior for supported versions.
