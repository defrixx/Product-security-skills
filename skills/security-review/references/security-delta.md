# Security delta for change reviews

Load for branch, commit or working-tree comparisons. Pin inputs using [review modes](review-modes.md). Compare security properties, not just changed dangerous APIs.

1. Identify the changed entry, caller, parser, identity source, guard, default, dependency or output consumer.
2. Trace the old and new path to the same protected operation. Record the actor/input, normalization, policy/configuration, guards, effect and relevant environment on each side.
3. Explain which capability or guarantee changed. Search call sites and route/job registrations: unchanged code can become newly reachable or consume more trusted data.
4. Check an allowed case and a forbidden case on both sides when execution is useful and authorized. Keep static comparisons separate from executed observations.

| Delta | Decisive question |
| --- | --- |
| New caller or endpoint | Is an old privileged helper now reachable with weaker authority? |
| Removed/moved guard | Does parsing, disclosure, filesystem or network activity now occur before authorization? |
| Parser/default change | Do duplicate fields, encodings, omitted options or proxy trust alter effective input/identity? |
| Cache/job/schema change | Does deferred use preserve actor, scope, freshness and revocation semantics? |
| Dependency/configuration update | Does effective behavior change even with identical application source? Compare delivered version and configuration |
| New output consumer | Does previously inert stored text now become HTML, a command, a path or a tool argument? |

Synthetic case: a helper formerly called only after an administrator check is registered directly as a public route. The helper body is unchanged, but the new unguarded caller introduces exposure. Cite the old guard, new registration and reachable effect; do not classify by the age of the sink lines. Conversely, a nearby comment change does not introduce an already reachable flaw.

Use a finding-linked delta record: old path/property, new path/property, exact comparison evidence, changed prerequisite and resulting impact. If only one side is accessible, retain unknown provenance. Disabling the feature is a repair only when it matches the authorized product behavior and closes every relevant path.
