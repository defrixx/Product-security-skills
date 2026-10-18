# Repair bypass matrix

Start from the reported defective control and repair boundary. Enumerate actual alternate callers and input channels, then select cases; do not generate arbitrary payload permutations unrelated to that cause.

Use one row per path with a distinct guard: finding ID, entry/input representation, actor/prerequisite, guard and repair location, allowed control, forbidden effect, original observation, patched observation, evidence and next action. This is a case-selection schema, not a requirement for a new file or exhaustive Cartesian product.

Consider alternate routes/methods, create/update/bulk/import/export, encoded/structured inputs, shared-helper callers, cache hits, delayed jobs, redirects, retries and fallback only where present. Reuse an observation across paths only with evidence that the same guard runs on the same effective input before the effect. A shared sink alone does not prove shared protection.

Synthetic partial repair: direct download checks ownership, while export uses a different query and exposes the same object. Test both plus legitimate owner downloads/exports. Another synthetic bypass: ZIP member validation is repaired but manifest-controlled output paths remain unchecked. Member-name cases cannot close the manifest path.

Use [decisive checks](decisive-checks.md) and [lifecycle and recovery](lifecycle-and-recovery.md) for observations. An untested necessary path makes the bounded claim inconclusive; a demonstrated remaining bypass supports not_fixed or partially_fixed under the [verdict rules](verification-method.md). Avoid labeling unknown coverage as a demonstrated failure. Preserve original finding IDs and aliases.
