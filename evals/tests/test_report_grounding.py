"""Behavioral checks for demonstrated reporting errors and valid counterexamples."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('report_grounding', ROOT/'evals/report_grounding.py')
grounding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grounding)


class ReportGroundingTests(unittest.TestCase):
    def test_labeled_claims_and_controls(self):
        fixture = json.loads((ROOT/'evals/fixtures/report-grounding.json').read_text())
        for case in fixture['cases']:
            with self.subTest(case=case['id']):
                self.assertEqual(grounding.assess(case['claim'], case['evidence']), case['expected'])

    def test_missing_evidence_does_not_support_strong_claims(self):
        claim = {'revision':'B', 'target':'demo', 'provenance':'pre-existing',
                 'implementation':'applied', 'verdict':'fixed', 'verified_conditions':['input-schema']}
        self.assertEqual(grounding.assess(claim, {}), ['unsupported_provenance',
            'unsupported_coverage:input-schema', 'unsupported_applied_state', 'unsupported_fixed_verdict'])

    def test_configuration_drift_invalidates_unchanged_code_evidence(self):
        import hashlib
        old = hashlib.sha256(b'scope-filter=on').hexdigest()
        new = hashlib.sha256(b'scope-filter=off').hexdigest()
        claim = {'revision': 'same-code', 'verdict': 'fixed', 'verified_conditions': ['scope']}
        check = {'revision': 'same-code', 'executed': True, 'result': 'passed',
                 'case': 'export', 'condition': 'scope', 'dependencies': {'policy': old}}
        evidence = {'required_cases': ['export'], 'checks': [check], 'required_dependencies': {'policy': old}}
        self.assertEqual(grounding.assess(claim, evidence), [])
        evidence['required_dependencies']['policy'] = new
        self.assertEqual(grounding.assess(claim, evidence), ['unsupported_coverage:scope', 'unsupported_fixed_verdict'])
        check['dependencies'] = {}
        self.assertEqual(len(grounding.assess(claim, evidence)), 2)
        check['dependencies']['policy'] = new
        self.assertEqual(grounding.assess(claim, evidence), [])

    def test_conflicting_current_observations_do_not_support_fixed(self):
        claim = {'revision': 'B', 'verdict': 'fixed', 'verified_conditions': ['scope']}
        passed = {'case': 'export', 'condition': 'scope', 'revision': 'B', 'executed': True, 'result': 'passed'}
        failed = dict(passed, result='failed')
        evidence = {'required_cases': ['export'], 'checks': [passed, failed]}
        self.assertEqual(grounding.assess(claim, evidence), ['unsupported_coverage:scope', 'unsupported_fixed_verdict'])
        failed['revision'] = 'A'
        self.assertEqual(grounding.assess(claim, evidence), [])

    def test_unknown_revision_does_not_support_reused_check(self):
        claim = {'verdict': 'fixed', 'verified_conditions': ['scope']}
        evidence = {'required_cases': ['export'], 'checks': [
            {'case': 'export', 'condition': 'scope', 'executed': True, 'result': 'passed'}]}
        self.assertEqual(grounding.assess(claim, evidence), ['unsupported_coverage:scope', 'unsupported_fixed_verdict'])
