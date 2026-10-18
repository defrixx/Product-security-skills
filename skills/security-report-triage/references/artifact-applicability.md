# Dependency signal to delivered artifact

Load for dependency, image and bundled-component signals. Preserve scanner/advisory labels independently from applicability, exploitability and priority. This workflow uses supplied reports and local evidence; triage alone does not authorize building, downloading, running scanners or fetching remote artifacts.

Trace these links independently:

1. Advisory identity, affected/fixed versions, platform/features and publication/update date using current primary vendor evidence where available.
2. Resolved component identity, source and transitive parent; include vendored, shaded, bundled and base-image components where present. Resolve same-name/different-source ambiguity.
3. Build/package inclusion: which feature, target, build stage or plugin carries the component? A dev declaration can still affect build secrets or generated release content.
4. Exact delivered artifact identity/digest and inventory provenance. Check the image stage, architecture and package installation actually delivered. A source lockfile alone does not establish shipped content.
5. Runtime or build-time entry to the vulnerable functionality, attacker influence, guards and supported impact. Reachability missing from one tool is not evidence of absence.

For each link record observed / contradicted / unknown with evidence and the next decisive check. A content digest identifies bytes, not who built them or whether an inventory is complete. If the report and artifact refer to different revisions, assess the mismatch explicitly before reusing conclusions.

Synthetic dispositions: an affected library proven absent from the named runtime artifact contradicts that runtime-presence claim, but does not resolve build-time exposure. An applicable version with unknown feature reachability remains a hypothesis with an update/mitigation investigation action. A bundled vulnerable function reached by untrusted input can be confirmed with sufficient static or runtime proof. Do not discard advisory obligations merely because exploitation is unproven.

Add safe artifact identity, component/version/source, inclusion path, advisory applicability, reachability, evidence state and next check to the finding. Preserve all raw-result mappings when grouping multiple image layers or transitive parents.

## Source

[OWASP Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html), dependencies, final-build scanning and provenance; living document verified 2026-10-18. The evidence chain above is workflow synthesis; actual packaging semantics require matching build-system documentation.
