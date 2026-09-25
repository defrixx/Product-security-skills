# Local PR context helper

Use [scripts/pr_context.py](../scripts/pr_context.py) to record available local base/head commits and the merge base. It collects metadata; it does not discover or classify vulnerabilities. Requires Python 3.9+, Git, and POSIX no-follow output support. It does not fetch, checkout, modify tracked files, run project hooks, use external diff/textconv, or honor a configured filesystem-monitor command.

```sh
python3 scripts/pr_context.py --repo /path/to/repo --base main --head feature --output /private/new-pr-context.json
```

The output must be new. It records exact commit IDs, merge-base-to-head semantics, shallow-repository status, working-tree dirtiness, and change kinds under opaque IDs. Rename detection is disabled; renames appear as deletion/addition and require analyst interpretation. Uncommitted/untracked content is recorded as a dirty-state flag and is not included in the PR diff.

If local source paths are appropriate for the report audience, explicitly add `--include-paths`. That report can contain sensitive filenames; keep it private. Diff contents and original code are never printed by the helper. stdout contains only a summary, stderr only fixed error codes.

Missing base/head, unrelated histories, or multiple merge bases result in an incomplete error, not a current-directory fallback. The helper does not fetch missing history. A command has a 30-second timeout; returned metadata above 8 MiB is rejected after collection. This is not a sandbox for an arbitrarily large repository; scope inputs accordingly.

After collection, inspect surrounding source at the recorded head and comparison revisions. Confirm suspected issues on head and base/merge base when available. A changed comment beside a legacy flaw does not make the flaw introduced. A safe parameterized query is counterevidence to an injection signal. Preserve evidence of each comparison in the [review report](../assets/review-report.md).

Exit codes: `0` metadata collected; `1` incomplete/error. Neither exit code asserts anything about repository security. Local Git configuration is read as part of repository access; the disabled hooks/diff helpers are not a general hostile-repository sandbox. Do not execute unfamiliar code to validate a finding without inspection and isolation.
