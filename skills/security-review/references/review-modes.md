# Review modes and scope

## Mode selection

An explicit PR, target/base/head comparison, or selected pull request means `PR` mode. An explicit whole-repository assessment means `repo` mode. Infer a mode from unambiguous task context; otherwise ask which mode is intended and perform only a safe inventory while waiting.

## Pull request

Input: local base/head revisions, or a PR whose metadata and source are accessible. Record target branch, exact base/head commit IDs, and merge base. Compare merge base to head for branch-introduced changes; document any different comparison semantics. Separate committed PR content from uncommitted working-tree changes.

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
