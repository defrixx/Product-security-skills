# Review modes and scope

## Mode selection

Choose the smallest scope supported by the request. Preserve the report's `PR` (change comparison) and `repo` (snapshot assessment) modes; record the subtype below. Do not default an ambiguous request to an entire repository.

| Requested input | Mode / subtype | Bind the assessment to |
| --- | --- | --- |
| PR or branch comparison | PR / branch | Exact target, head and merge base; merge-base-to-head unless another comparison was requested |
| Specific commit | PR / commit | Commit and selected parent; root commits use the empty tree; ask about an ambiguous merge parent |
| Uncommitted changes | PR / working-tree | HEAD, staged and unstaged changes, and in-scope untracked files; preserve index versus working-tree content |
| File or directory | repo / path | Exact revision or working-tree snapshot and path boundary; inspect callers outside it as context |
| Whole repository | repo / repository | Exact revision or identified working-tree snapshot |

An explicit request to review current changes includes staged, unstaged and relevant untracked content. Record file identities/content fingerprints for mutable inputs without copying sensitive values into reports. Do not combine staged and unstaged versions silently or claim snapshot atomicity if files changed during collection. Reconcile changed inputs before concluding. The optional PR helper supports committed comparisons only; collect working-tree evidence separately. A path audit includes existing code in that path; reading callers outside it does not authorize an unrelated repository audit. If the intended scope remains unclear, ask and continue only a safe inventory.

## Pull request

For the PR/branch subtype, input is local base/head revisions or a PR whose metadata and source are accessible. Record target branch, exact base/head commit IDs, and merge base. Compare merge base to head for branch-introduced changes; document any different comparison semantics. For commit and working-tree subtypes, use the comparison defined in the mode table instead. Separate committed PR content from uncommitted working-tree changes.

Inspect modified code and the callers, routes, models, configurations, tests, and data flows necessary to assess it. Do not limit reasoning to added lines. Classify each finding as introduced, pre-existing, or provenance unknown. Check the base version where possible; do not attribute a pre-existing issue to the PR merely because nearby lines changed. Put existing issues in a separate report section.

Use read-only revision inspection or an isolated checkout without overwriting the user's working tree. Do not fetch from a remote or publish a comment merely because a PR URL is present if access/action is not authorized. If the base is unavailable, request it and continue only a clearly labeled partial analysis of accessible code. Do not silently substitute a repository assessment for the requested PR comparison.

The optional [local PR context helper](pr-context-helper.md) records these revisions without switching the working tree. Its success means metadata collection, not a completed review.

## Whole repository

Input: repository path and commit ID, or an explicitly identified working-tree snapshot. Record uncommitted changes and relevant untracked files. Map components, external interfaces, dependency manifests, build and deployment boundaries, and security-sensitive data stores.

Prioritize attacker-reachable paths, high-value data, and privileged components. Record reviewed and skipped components and why. Time/tool limits do not justify claiming exhaustive coverage. Git history is outside a current-state assessment unless requested.

## Evidence states

- **Confirmed:** a sufficient static trace or local reproduction establishes the vulnerability under documented prerequisites. State when confirmation is static only.
- **Hypothesis:** a signal lacks proof of reachability, prerequisite, or impact. Specify the next check needed.
- **Disproved:** a verified defense or false premise invalidates the signal; preserve a short reason when useful.
- **Not assessed:** a coverage status, not evidence that an area is safe.
