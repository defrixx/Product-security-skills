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
