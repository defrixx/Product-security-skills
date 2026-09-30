# Finding handoff contract v1

Use equivalent fields in a human-readable report or UTF-8 JSON for machine handoff. JSON is optional for manual work. Unknown major versions are incompatible; absent values mean unknown, not passed. Preserve optional extensions as inert data only.

## Envelope

Required fields: schema_version (integer 1), assessment_id (unique run ID), stage, created_at (UTC), producer (skill name/fingerprint and helper versions), target (safe ID, revision or unknown, dirty state and included changes), scope (task/components/findings, exclusions, assumptions, authorized operations), input_refs (safe upstream identities/fingerprints/revisions), findings (array), coverage, errors, and limitations.

## Finding

Required fields: finding_id, origin_assessment_id, aliases, source_refs, title, root_cause, affected_paths, assessment_status, severity, confidence, implementation_state, verification_status, evidence, acceptance_cases, history. Use explicit unknowns where necessary. Global identity is origin assessment plus finding ID. Aliases refer to that same identity pair, not ambiguous bare IDs.

- assessment_status: confirmed / hypothesis / disproved at the recorded original revision.
- severity and confidence: independent values with rationale; unknown permitted; keep scanner severity separately.
- implementation_state: unknown / not_started / candidate / applied.
- verification_status: not_checked / fixed / partially_fixed / not_fixed / inconclusive at the checked revision.
- evidence: kind, safe relative artifact/location, revision, observation, assumptions, limits.
- acceptance_cases: original failure, relevant alternate path, allowed behavior, expected outcomes.
- history: upstream assessment references and explained changes; never overwrite historical evidence.

Merges retain prior IDs as aliases. Splits create child IDs linked to the original with rationale. Scanner fingerprints are hints, not proof of identity. Do not hash raw sensitive values as redaction. Relative attachments must remain within the selected delivery root and be inspected for sensitive content.

## Stage extensions

Triage includes raw_results with run/result ordinals, exactly one disposition (confirmed / hypothesis / disproved / out_of_scope / unprocessed), reason, and optional duplicate_of canonical identity. Count raw dispositions separately from unique findings. Fatal parsing can yield unknown counts.

Verification includes original/patched target references and a case matrix with expected/observed outcomes, evidence kinds, gaps, and verdict rationale per finding. Candidate state survives successful verification. A fixed later revision does not rewrite historical confirmation.

## Composition and resumption

Run only stages authorized by the task. Triage/review produces evidence; implementation changes implementation state/revision; verification produces a new verdict; optional cleanup works on a separate selected delivery copy. No stage authorizes remote writes or publication. Existing authorization for a combined local workflow persists across stages.

Recheck fingerprints, revisions, working snapshot, scope, and completion markers on resume. Preserve finished assessments and invalidate affected evidence on drift. Reconcile contradictions using revision-specific evidence or retain inconclusive status. Applied patches, closed tickets, suppressions, and absent scanner results never automatically imply fixed. Same-assistant implementation and verification is self-verification, not an independent evaluation.
