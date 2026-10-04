"""Schema v2, detection span mapping, assembled context, pins and worker budgets."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if not os.environ.get('PROMPT_GUARD_TEST_PACKAGED'):
    sys.path.insert(0, str(ROOT / 'src'))
from prompt_guard import GuardError, inspect, load_policy, load_profile, policy_from_dict
from prompt_guard.core import LIMITS_V2
from prompt_guard import execution
from prompt_guard.evaluation import evaluate_corpus


def policy(pattern='BAD', **changes):
    rule = dict(id='PG-NORMALIZED', category='synthetic', kind='literal', pattern=pattern, ignore_case=True,
                sources=['user', 'retrieval', 'tool'], action='block', replacement='[REMOVED]',
                view='normalized', scope='message')
    rule.update(changes)
    return dict(schema_version=2, policy_id='synthetic-v2', policy_version='1', assembly_separator='\n',
                limits=dict(LIMITS_V2), rules=[rule])


class ProfileTests(unittest.TestCase):
    def test_normalized_spans_preserve_surrounding_original(self):
        p = policy_from_dict(policy())
        for text in ('public \uff22\uff21\uff24 end', 'public B\u200bAD end', 'public bad end'):
            raw = text.encode()
            result = inspect(p, raw, mode='sanitize')
            self.assertEqual(result.payload, b'public [REMOVED] end')
            self.assertEqual(raw, text.encode())
        p = policy_from_dict(policy('ffi'))
        self.assertEqual(inspect(p, 'before \ufb03 after'.encode(), mode='sanitize').payload, b'before [REMOVED] after')
        p = policy_from_dict(policy('caf\u00e9'))
        for text in ('cafe\u0301', 'cafe\u200b\u0301'):
            self.assertEqual(inspect(p, text.encode(), mode='sanitize').payload, b'[REMOVED]')

    def test_assembled_scope_and_forbidden_edits(self):
        value = policy('BAD', scope='assembled', replacement=None)
        value['assembly_separator'] = ''
        p = policy_from_dict(value)
        raw = json.dumps({'messages': [{'source': 'user', 'text': 'BA'}, {'source': 'tool', 'text': 'D'}]}).encode()
        result = inspect(p, raw, format='json', source=None)
        self.assertEqual(result.decision, 'block')
        self.assertEqual(result.findings[0]['scope'], 'assembled')
        self.assertIsNone(result.findings[0]['message_index'])
        self.assertEqual(inspect(p, raw, format='json', source=None, mode='sanitize').decision, 'block')
        with self.assertRaises(GuardError):
            policy_from_dict(policy(scope='assembled'))

    def test_policy_release_pin_rotation_and_no_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            path = folder / 'policy.json'
            raw = json.dumps(policy()).encode()
            path.write_bytes(raw)
            kwargs = dict(config_root=folder, expected_id='synthetic-v2', expected_version='1',
                          expected_sha256=hashlib.sha256(raw).hexdigest())
            p = load_policy(path, **kwargs)
            path.write_bytes(raw + b' ')
            with self.assertRaisesRegex(GuardError, '^policy_digest_mismatch$'):
                load_policy(path, **kwargs)
            self.assertEqual(inspect(p, b'BAD').decision, 'block')
            kwargs['expected_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            kwargs['expected_version'] = '2'
            with self.assertRaisesRegex(GuardError, '^policy_identity_mismatch$'):
                load_policy(path, **kwargs)
            rotated = policy('NEW')
            rotated['policy_version'] = '2'
            rotated_raw = json.dumps(rotated).encode()
            path.write_bytes(rotated_raw)
            kwargs['expected_sha256'] = hashlib.sha256(rotated_raw).hexdigest()
            selected = load_policy(path, **kwargs)
            self.assertEqual(inspect(selected, b'NEW').decision, 'block')
            self.assertEqual(inspect(selected, b'BAD').decision, 'allow')
            path.write_bytes(raw)
            with self.assertRaisesRegex(GuardError, '^policy_digest_mismatch$'):
                load_policy(path, **kwargs)
            rolled_back = load_policy(path, config_root=folder, expected_id='synthetic-v2', expected_version='1',
                                      expected_sha256=hashlib.sha256(raw).hexdigest())
            self.assertEqual(inspect(rolled_back, b'BAD').decision, 'block')

    def test_capacity_exhaustion_does_not_start_worker(self):
        p = policy_from_dict(policy())
        for _ in range(execution.CAPACITY):
            self.assertTrue(execution._slots.acquire(blocking=False))
        try:
            with patch('prompt_guard.execution.subprocess.run') as run:
                result = inspect(p, b'public')
            self.assertEqual(result.code, 'worker_capacity_exhausted')
            run.assert_not_called()
        finally:
            for _ in range(execution.CAPACITY):
                execution._slots.release()
        self.assertEqual(inspect(p, b'public').decision, 'allow')

    def test_overall_deadline_and_validation_exhaustion(self):
        value = policy('(a+)+$', kind='regex')
        value['limits']['overall_ms'] = 150
        p = policy_from_dict(value)
        started = time.monotonic()
        result = inspect(p, b'a' * 10000 + b'!')
        self.assertEqual(result.code, 'request_timeout')
        self.assertLess(time.monotonic() - started, 2)
        # Validation itself is contained: no repeat executes in the caller process.
        value = policy('(a?){100000000}', kind='regex')
        value['limits']['memory_mb'] = 64
        value['limits']['timeout_ms'] = 500
        with self.assertRaises(GuardError) as caught:
            policy_from_dict(value)
        self.assertIn(caught.exception.code, ('memory_limit', 'scan_timeout', 'request_timeout'))

    def test_strict_topics_block_educational_mentions(self):
        p = load_profile('restricted-topics')
        for text in ('News about violence prevention', 'Explain phishing defenses', 'History of weapons', 'Fraud prevention', 'CSAM reporting policy'):
            result = inspect(p, text.encode())
            self.assertEqual(result.decision, 'block')
            self.assertTrue(result.findings[0]['category'].startswith('topic-'))
        self.assertEqual(inspect(p, b'Children learning mathematics').decision, 'allow')

    def test_labeled_multilingual_corpus(self):
        cases = json.loads((ROOT / 'tests/corpus.json').read_text())['cases']
        report = evaluate_corpus(cases)
        failures = [r for r in report['results'] if r['decision'] != r['expected']]
        self.assertEqual(failures, [])
        self.assertEqual(len(report['results']), len(cases))
        self.assertTrue(report['all_expected'])
        self.assertIn('topic-violence', report['by_category'])
        self.assertGreater(report['by_category']['topic-violence']['true_negative'], 0)
        self.assertGreater(report['by_category']['instruction-override']['true_negative'], 0)
        self.assertGreater(report['latency_ms']['p95'], 0)
        self.assertNotIn('text', report['results'][0])


if __name__ == '__main__':
    unittest.main()
