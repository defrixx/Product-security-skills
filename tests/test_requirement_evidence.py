"""Evidence reporting must preserve failures and never promote partial coverage."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('evidence', Path(__file__).resolve().parents[1] / 'scripts/requirement_evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def test_partial_failure_and_absence_stay_distinct(self):
        mapping = [{'case': 'case-a', 'conditions': ['A'], 'behavior': 'one clause', 'limitations': 'others untested'}]
        result = evidence.build({'A': 'a.md', 'B': 'b.md'}, mapping, [{'case': 'case-a', 'result': 'failed'}], 'run-1')
        self.assertEqual(result['conditions']['A']['status'], 'partial_evidence')
        self.assertEqual(result['conditions']['A']['evidence'][0]['result'], 'failed')
        self.assertEqual(result['conditions']['B']['status'], 'not_exercised_in_this_run')
        self.assertEqual(result['run'], 'run-1')

    def test_unknown_condition_or_unexecuted_case_rejected(self):
        for mapping, outcomes in [([{'case': 'a', 'conditions': ['missing']}], [{'case': 'a', 'result': 'passed'}]),
                                  ([{'case': 'missing', 'conditions': ['A']}], [])]:
            with self.assertRaises(ValueError):
                evidence.build({'A': 'a.md'}, mapping, outcomes, 'run')
