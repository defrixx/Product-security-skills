"""Evaluator-only checks for structured claims against labeled synthetic evidence.

Claims must be extracted/reviewed by an evaluator. This does not parse prose,
verify the authenticity of evidence, or score arbitrary real security reports.
"""


def assess(claim, evidence):
    """Return stable discrepancy codes; unknown evidence never implies success."""
    issues = []
    provenance = claim.get('provenance', 'unknown')
    history = evidence.get('history', {})
    if provenance in ('pre-existing', 'introduced'):
        required = True if provenance == 'pre-existing' else False
        if not (history.get('compared') is True and history.get('before_revision')
                and history.get('after_revision') == claim.get('revision')
                and history.get('same_finding') is True
                and history.get('before_present') is required
                and history.get('after_present') is True):
            issues.append('unsupported_provenance')
    elif provenance not in ('unknown', 'not_assessed'):
        issues.append('invalid_provenance')
    checks = evidence.get('checks', [])
    # The evaluator supplies the bounded relevant dependency set, not the report.
    # Missing entries cannot be treated as evidence of unchanged configuration.
    dependencies = evidence.get('required_dependencies', {})
    def current(check):
        return (bool(claim.get('revision')) and claim.get('revision') != 'unknown'
                and check.get('revision') == claim.get('revision')
                and all(check.get('dependencies', {}).get(key) == value
                        for key, value in dependencies.items()))

    for condition in claim.get('verified_conditions', []):
        if not any(c.get('condition') == condition and c.get('result') == 'passed'
                   and c.get('executed') is True and current(c)
                   for c in checks) or any(c.get('condition') == condition and current(c)
                   and c.get('executed') is True and c.get('result') == 'failed' for c in checks):
            issues.append('unsupported_coverage:' + condition)
    state = claim.get('implementation', 'unknown')
    if state == 'applied':
        application = evidence.get('application', {})
        if not (application.get('observed') is True and application.get('target')
                and application.get('target') == claim.get('target')
                and application.get('revision') == claim.get('revision')):
            issues.append('unsupported_applied_state')
    elif state not in ('candidate', 'proposed', 'unchanged', 'unknown'):
        issues.append('invalid_implementation_state')
    if claim.get('verdict') == 'fixed':
        # Fixture-required paths include the exploit, alternate path and allowed behavior.
        required = evidence.get('required_cases', [])
        if not required or not all(any(c.get('case') == case and c.get('executed') is True
                and c.get('result') == 'passed' and current(c)
                for c in checks) and not any(c.get('case') == case and current(c)
                and c.get('executed') is True and c.get('result') == 'failed'
                for c in checks) for case in required):
            issues.append('unsupported_fixed_verdict')
    return issues
