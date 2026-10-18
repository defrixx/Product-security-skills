# Classification and scoring

Use when the task needs CWE/OWASP classification or CVSS scoring. Classify after establishing the scenario; a taxonomy match does not confirm a vulnerability. Missing classification must not hide an actionable confirmed finding.

## CWE and OWASP

Verify the exact CWE title, root cause and mapping suitability in MITRE's current definition. Prefer the most specific supported weakness; do not assign broad categories as if they were precise root causes. Add supporting CWEs only for evidenced distinct causes. OWASP Web and Agentic labels are navigation aids with an explicit edition. Do not invent an official CWE mapping for agentic categories; label any proposed analogy as such.

## CVSS v4.0

Keep severity, confidence, remediation priority and implementation state separate. Use a verified calculator for numeric scores; do not guess a score or derive a CVSS severity band from a coarse heuristic. If calculation is unavailable, retain supported metric reasoning and contextual severity, labeling the score uncomputed.

The eleven mandatory Base metrics are AV, AC, AT, PR, UI, VC, VI, VA, SC, SI and SA. Use this vector order and record the calculator/version, scenario and rationale for non-obvious choices. Label Base scores CVSS-B; use CVSS-BT, CVSS-BE or CVSS-BTE when the corresponding Threat/Environmental groups are assessed. A third-party advisory score remains attributed with its original version; do not silently convert it.

- Distinguish evasion of security mechanisms (AC) from execution conditions such as an independently scheduled race that must be won (AT). Base AT on actual attacker control, not simply on the word race.
- Assess PR using FIRST's definitions; self-service accounts are not automatically PR:L. State the actual privileges needed before exploitation.
- Separate vulnerable-system impact from supported subsequent-system consequences. Do not score an unverified pivot as demonstrated impact.
- Distinguish intrinsic Base characteristics from deployment-specific Environmental factors. Explain the assessed configuration and use FIRST's reasonable-worst-case rules without inventing additional exploit steps.

CVSS is severity input, not the entire organizational risk or a universal release gate. Prioritize using credible exposure, affected assets, prerequisites and repair dependencies alongside the score. Apply merge/release thresholds only when established by the authorized project policy; label proposed thresholds as proposals.

## Sources

- [FIRST CVSS v4.0 specification](https://www.first.org/cvss/v4.0/specification-document), Base metrics, nomenclature and assessment; verified 2026-10-18.
- [MITRE root cause mapping guidance](https://cwe.mitre.org/documents/cwe_usage/guidance.html), mapping specificity and suitability; verified 2026-10-18. Verify each selected definition separately when classifying an actual finding.
