# Architecture profiles

Select by observed exposure and effects, combining profiles where needed. These are investigation/implementation selection aids, not approved corporate policy. Record actors, reachable interfaces, protected assets and deployment evidence before choosing controls. An absent component is non-applicable, not an exception.

| Observed architecture | Boundaries to inspect | Controls/checks to select |
| --- | --- | --- |
| Local CLI or desktop | Imported files, plugins, IPC, loopback listeners, browser-to-local requests, filesystem permissions | Input-to-file/command paths, caller/origin binding where exposed, path containment, secret storage; do not add multi-user login merely for checklist coverage |
| Public API | Anonymous/authenticated requests, object ownership, proxy headers, outbound calls | Authentication plus per-operation authorization, request/cost bounds, parsing and network boundaries; distinguish application settings from proxy/deployment evidence |
| Hosted multi-user service | Actor, tenant, shared caches, bulk/export/admin and support operations | Scope propagation through reads/writes/jobs, least privilege and verified lifecycle behavior; derive actual tenancy from the product |
| Webhook or background worker | Producer identity, payload, delivery duplication/order, delegated authority | Verify event authenticity and audience where required; bind operation identity, enforce state transitions, bound retries and inspect recipient effects |
| Agent/tool workflow | Untrusted context, model proposals, execution identity, approval, persistent memory | Deterministic action authorization, scoped delegation, approval binding, output-sink checks and bounded autonomy; prompt refusal is separate evidence |

For each selected profile, name one allowed operation and one forbidden effect. Verify that the selected control separates them without preventing intended behavior. A hybrid desktop app using cloud tools needs both local and remote boundaries assessed. Profiles do not authorize scans, code changes, production access or data transmission.
