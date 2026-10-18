# Decisive checks by defect mechanism

Select cases by the actual suspected root cause. Before each check, name the forbidden effect, allowed control, evidence needed, and observation that would leave the result inconclusive. Use synthetic data and authorized isolated execution; this guide does not authorize external probes. Static proof can suffice for code properties; runtime-dependent claims require appropriate observations.

| Mechanism | Separate paths/conditions | Decisive observation and control |
| --- | --- | --- |
| SSRF | Parser output, normalized host, resolution, redirects, actual connection target and credential forwarding | Observe denied destination staying off transport and allowed destination completing. An injected resolver proves only modeled resolution; a real rebinding claim needs appropriate local network evidence |
| Authorization | Actor/object/operation, property/bulk/export routes, delegated identity | Denied actor receives no protected data/effect; intended actor succeeds through the same operation. A 403 after a write does not hold the control |
| Traversal | Archive member, manifest path, decoded name and symlink are distinct channels | Outside sentinel stays unchanged and no out-of-root file is read; valid nested content succeeds. Inspect destination identity at use, not only string normalization |
| Race | Contested check/write, alternate writer, transaction isolation | Synchronize contenders at the boundary; count successes and all effects. Allowed capacity is preserved; rejection cannot leave an effect. Startup errors or arbitrary sleeps are inconclusive |
| Agent approval | Direct proposal, effective tool/target/arguments, dispatch retries and mutations after consent | Unapproved or changed protected action never reaches the sink; matching authorized action works. A refusal or claimed approval in text is insufficient |
| Injection/output | Every transformation from input to SQL/shell/HTML/template/tool sink | Input remains data or is rejected before interpretation; benign special characters retain intended behavior. A mocked sink does not establish browser or database integration |
| Lifecycle/replay | Rights changes, stale copies, captured work, independent effect commits | Use the [lifecycle scenarios](lifecycle-and-recovery.md); observe outputs and durable effects after transition/restart |

For every selected path, record guard, prerequisites, expected result, observed result, evidence kind and revision. A test that never reaches the disputed operation cannot disprove the signal. Keep confirmed, disproved and unresolved paths distinct when grouped.

## Sources

- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), application/network controls, redirects and DNS considerations; verified 2026-10-18.
- [OWASP Authorization Testing Automation](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Testing_Automation_Cheat_Sheet.html), feature/role/data matrix; verified 2026-10-18.
- [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), filename, storage and archive-size considerations; verified 2026-10-18.

Remaining case-selection and evidence rules are workflow synthesis, not universal platform guarantees.
