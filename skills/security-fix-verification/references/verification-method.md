# Verification method

## Scope and comparison

Pin the finding's original evidence and the target being checked. Preserve original revision, patched revision, dirty state and included changes, skill fingerprint, tool versions, task, assumptions, and exclusions. Missing original code does not permit an invented before/after reproduction. Inspect the patch plus relevant callers, shared guards, and side effects. Select nearby bypasses based on root cause rather than an exhaustive payload list.

A grouped finding retains every affected path with its guards and acceptance case. Repairing one handler does not close another affected handler. Check authorization before disclosure/mutation, not only the returned status. Verify allowed operations still succeed. Feature removal counts only when it is the agreed desired behavior and all relevant entry points are accounted for.

## Evidence

Prefer the least invasive sufficient proof. When available, run the original and patched cases in disposable local environments. Verify the baseline reaches the defective operation and fails the security expectation for the intended reason. Record actual versions, environment differences, originals/extracted code/mocks, and expected versus observed effects. Preserve target content and use separate test storage.

A complete static trace can establish a code property with a stated rationale. Browser, deployment, concurrency, and network behavior need appropriate runtime evidence when decisive. A stub cannot establish a stronger integration claim. If a check is unavailable or unsafe, report the gap instead of silently substituting a mock. Unknown original revision alone need not prevent a current static verdict; unavailable runtime evidence can.

## Verdicts

| Verdict | Required basis |
| --- | --- |
| fixed | All selected affected paths and necessary acceptance cases establish the property; intended allowed behavior holds; no material gap for the bounded claim |
| partially_fixed | Some required paths/properties demonstrably repaired, while another remains vulnerable or required allowed behavior regresses |
| not_fixed | Original defect or equivalent in-scope bypass demonstrably remains, without an established complete repair of a distinct required portion |
| inconclusive | Missing or conflicting evidence prevents the required conclusion; retain observed successes and failures |

Unknown coverage alone is inconclusive, not proof of partial repair. A demonstrated vulnerable path supports not_fixed/partially_fixed despite other unknowns; list those separately. Universal denial cannot be fixed when allowed behavior is required. A missing scanner signal, suppression, renamed function, error-message change, swallowed exception, closed ticket, or test failing to start does not establish repair.

Keep a historically confirmed vulnerability confirmed at its original revision even after a fixed verdict at a later one. Explain severity reassessment separately. Retain original IDs; merges preserve aliases and splits link child IDs to their origin. Contradictory reports remain visible until resolved against revision-specific evidence.

## Checkpoints

FIX-01: provenance and scope pinned. FIX-02: original failure/property reconstructed. FIX-03: mechanism and surrounding flow inspected. FIX-04: failure/bypass/allowed cases assessed. FIX-05: authorized isolated checks with target preserved. FIX-06: bounded verdict, independent statuses, and IDs delivered.

For each checkpoint record evidence and passed/partial/not verified/not applicable with rationale. These describe assessment work, not whole-project security. Revalidate target state at completion and on resume; do not reuse drifted evidence without checking its continued applicability.
