"""Behavioral regressions for normalization, provenance, task completion and recovery."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
if not os.environ.get('MODEL_SECURITY_EVAL_TEST_INSTALLED'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model_security_eval.cases import ACTION_RESULT, READ_RESULT, SECRET, suite
from model_security_eval.engine import Budget, CheckpointError, evaluate, run_case
from model_security_eval.identity import check_response, discover
from model_security_eval.reporting import CheckpointWriter, reserve_output, write_report
from model_security_eval.transport import EvaluationError
from test_engine import call, compliant, config, metadata, response

DIGEST = 'a' * 64


def metadata_reader(url, timeout):
    if url.endswith('/api/tags'):
        return {'models': [{'name': 'synthetic-model:latest', 'model': 'synthetic-model:latest',
                            'digest': DIGEST, 'size': 512, 'details': {'quantization_level': 'Q4'}}]}
    if url.endswith('/api/version'):
        return {'version': 'fixture-version'}
    if url.endswith('/api/v1/models'):
        return {'models': [{'key': 'synthetic-model', 'type': 'llm', 'quantization': {'name': 'Q4'},
                            'loaded_instances': [{'id': 'fixture-instance', 'config': {'context_length': 4096}}]}]}
    raise AssertionError(url)


class ImprovementTests(unittest.TestCase):
    def test_unicode_escaped_secret_in_arguments_cannot_pass_or_execute(self):
        cfg = config(capabilities=('chat', 'external'))
        case = next(c for c in suite(cfg.capabilities) if c.id == 'EXTERNAL-A4')
        forms = [lambda text: ''.join('\\u%04x' % ord(char) for char in text),
                 lambda text: '\\u%04x' % ord(text[0]) + text[1:]]
        for escape in forms:
            args = '{"recipient":"sandbox","content":"' + escape(SECRET) + '"}'
            item = call('send_message', {})
            item['function']['arguments'] = args
            result = run_case(cfg, case, 0, Budget(cfg), lambda *unused: response('', [item]), SECRET)
            self.assertEqual(result['status'], 'fail')
            self.assertIn('secret_disclosure', result['violations'])
            self.assertEqual(result['effects']['preview'], '[]')
            self.assertNotIn(SECRET, json.dumps(result))
            self.assertNotIn(escape(SECRET), json.dumps(result))

    def test_escaped_argument_in_benign_control_executes(self):
        cfg = config(capabilities=('chat', 'external'))
        case = next(c for c in suite(cfg.capabilities) if c.id == 'EXTERNAL-C1')
        inner = compliant('lmstudio')
        def responder(url, request, timeout):
            value = inner(url, request, timeout)
            for item in value['choices'][0]['message'].get('tool_calls', []):
                item['function']['arguments'] = item['function']['arguments'].replace('PUBLIC', '\\u0050UBLIC')
            return value
        result = run_case(cfg, case, 0, Budget(cfg), responder, SECRET)
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['control_observed'])

    def test_identity_blank_values_and_response_mismatch(self):
        for key in ('model_revision', 'server_version'):
            for value in (' ', '\t', '\n', ' release '):
                with self.assertRaises(EvaluationError):
                    replace(config(), **{key: value}).validate()
        for backend in ('lmstudio', 'ollama'):
            cfg = config(backend, capabilities=('chat',))
            inner = compliant(backend)
            def wrong(url, request, timeout):
                value = inner(url, request, timeout)
                value['model'] = 'other-model'
                return value
            report = evaluate(cfg, wrong, metadata_provider=metadata)
            self.assertEqual(report['verdict'], 'inconclusive')
            self.assertTrue(all(r['diagnostic'] == 'response_model_mismatch' for r in report['results']))
        with self.assertRaisesRegex(EvaluationError, 'response_model_missing'):
            check_response({}, ['synthetic-model'])

    def test_ollama_discovery_digest_version_alias_and_pins(self):
        cfg = config('ollama', model_revision=DIGEST, server_version='fixture-version')
        identity = discover(cfg, Budget(cfg), metadata_reader)
        self.assertEqual(identity['model_digest'], DIGEST)
        self.assertIn('synthetic-model:latest', identity['accepted_models'])
        self.assertEqual(check_response({'model': 'synthetic-model:latest'}, identity['accepted_models']), 'synthetic-model:latest')
        for changed, code in ((replace(cfg, model_revision='b' * 64), 'model_revision_mismatch'),
                              (replace(cfg, server_version='other-version'), 'server_version_mismatch')):
            with self.assertRaisesRegex(EvaluationError, code):
                discover(changed, Budget(changed), metadata_reader)
        def remote(url, timeout):
            value = metadata_reader(url, timeout)
            if url.endswith('/api/tags'):
                value['models'][0]['remote_host'] = 'https://cloud.invalid'
            return value
        with self.assertRaisesRegex(EvaluationError, 'remote_model_rejected'):
            discover(cfg, Budget(cfg), remote)

    def test_lmstudio_native_aliases_and_compatibility_fallback(self):
        cfg = config(model='fixture-instance')
        identity = discover(cfg, Budget(cfg), metadata_reader)
        self.assertEqual(set(identity['accepted_models']), {'synthetic-model', 'fixture-instance'})
        self.assertEqual(identity['details']['loaded_config']['context_length'], 4096)
        seen = []
        def legacy(url, timeout):
            seen.append(url)
            if url.endswith('/api/v1/models'):
                raise EvaluationError('http_not_found')
            return {'data': [{'id': 'fixture-instance'}]}
        self.assertEqual(discover(cfg, Budget(cfg), legacy)['source'], 'lmstudio-compatible-models')
        self.assertEqual(len(seen), 2)
        def unrelated(url, timeout):
            return {'models': []}
        with self.assertRaisesRegex(EvaluationError, 'model_not_listed'):
            discover(cfg, Budget(cfg), unrelated)

    def test_metadata_drift_closes_gate_and_discovery_failure_dispatches_nothing(self):
        cfg = config(capabilities=('chat',))
        calls = [0]
        def drift(cfg, budget):
            value = metadata(cfg, budget)
            calls[0] += 1
            value['details']['quantization'] = 'Q4' if calls[0] == 1 else 'Q8'
            return value
        report = evaluate(cfg, compliant('lmstudio'), metadata_provider=drift)
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertIn('model_metadata_changed', report['identity_limits'])
        def failed(cfg, budget):
            budget.take('metadata')
            raise EvaluationError('model_not_listed')
        with patch('model_security_eval.engine.post') as sender:
            report = evaluate(cfg, metadata_provider=failed)
        sender.assert_not_called()
        self.assertEqual(report['inference_requests'], 0)
        self.assertEqual(len(report['results']), report['planned_trials'])

    def test_read_requires_correct_final_result_and_action(self):
        cfg = config()
        case = next(c for c in suite(cfg.capabilities) if c.id == 'READ-C1')
        inner = compliant('lmstudio')
        def wrong_summary(url, request, timeout):
            if request['messages'][-1]['role'] == 'tool':
                return response('Completed.')
            return inner(url, request, timeout)
        for responder in (wrong_summary, lambda *unused: response(READ_RESULT)):
            result = run_case(cfg, case, 0, Budget(cfg), responder, SECRET)
            self.assertEqual(result['diagnostic'], 'allowed_control_failed')
            self.assertFalse(result['control_observed'])

    def test_multi_stage_prerequisite_must_execute_and_acknowledge(self):
        cfg = config()
        case = next(c for c in suite(cfg.capabilities) if c.id == 'WRITE-A3')
        delivered = []
        def skip(url, request, timeout):
            delivered.append(request['messages'][-1]['content'])
            return response(ACTION_RESULT)
        result = run_case(cfg, case, 0, Budget(cfg), skip, SECRET)
        self.assertEqual(result['diagnostic'], 'prerequisite_failed')
        self.assertEqual(len(delivered), 1)
        self.assertFalse(result['prerequisite_observed'])
        inner = compliant('lmstudio')
        def incorrect_ack(url, request, timeout):
            if request['messages'][-1]['role'] == 'tool':
                return response('Completed.')
            return inner(url, request, timeout)
        result = run_case(cfg, case, 0, Budget(cfg), incorrect_ack, SECRET)
        self.assertEqual(result['diagnostic'], 'prerequisite_failed')

    def test_interrupt_preserves_completed_active_and_pending_trials(self):
        cfg = config(capabilities=('chat',))
        inner = compliant('lmstudio')
        dispatched = [0]
        checkpoints = []
        def interrupted(url, request, timeout):
            dispatched[0] += 1
            if dispatched[0] == 3:
                raise KeyboardInterrupt()
            return inner(url, request, timeout)
        report = evaluate(cfg, interrupted, metadata_provider=metadata,
                          checkpoint=lambda value: checkpoints.append(copy.deepcopy(value)))
        self.assertEqual(report['run_state'], 'interrupted')
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertEqual(len(report['results']), report['planned_trials'])
        self.assertEqual(sum(r['complete'] for r in report['results']), 3)
        self.assertEqual(report['counts']['pass'], 2)
        self.assertEqual(checkpoints[-1]['run_state'], 'interrupted')
        self.assertTrue(any(r['observations'] for r in checkpoints[-1]['results']))

    def test_atomic_checkpoint_redaction_permissions_and_final_report(self):
        cfg = config(capabilities=('chat',))
        with tempfile.TemporaryDirectory() as temporary:
            output = reserve_output(Path(temporary).resolve() / 'run')
            writer = CheckpointWriter(output)
            report = evaluate(cfg, lambda *unused: response(SECRET), metadata_provider=metadata,
                              token_factory=lambda: SECRET, checkpoint=writer)
            write_report(output, report)
            for filename in ('checkpoint.json', 'report.json'):
                value = (output / filename).read_text()
                self.assertNotIn(SECRET, value)
                self.assertEqual(json.loads(value)['verdict'], 'fail')
                self.assertEqual((output / filename).stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(output.glob('.checkpoint-*')), [])
            original = (output / 'report.json').read_bytes()
            writer(report)
            self.assertEqual((output / 'report.json').read_bytes(), original)
            with patch('model_security_eval.reporting.os.replace', side_effect=OSError()):
                with self.assertRaises(CheckpointError):
                    writer(report)
            self.assertEqual(json.loads((output / 'checkpoint.json').read_text())['verdict'], 'fail')
            self.assertEqual(list(output.glob('.checkpoint-*')), [])

    def test_interruption_at_first_atomic_rename_can_write_final_checkpoint(self):
        cfg = config(capabilities=('chat',))
        with tempfile.TemporaryDirectory() as temporary:
            output = reserve_output(Path(temporary).resolve() / 'run')
            writer = CheckpointWriter(output)
            original_replace = os.replace
            calls = [0]
            def interrupt(source, destination):
                original_replace(source, destination)
                calls[0] += 1
                if calls[0] == 1:
                    raise KeyboardInterrupt()
            with patch('model_security_eval.reporting.os.replace', side_effect=interrupt):
                report = evaluate(cfg, compliant('lmstudio'), metadata_provider=metadata, checkpoint=writer)
            self.assertEqual(report['run_state'], 'interrupted')
            self.assertEqual(json.loads((output / 'checkpoint.json').read_text())['run_state'], 'interrupted')
            self.assertEqual(report['inference_requests'], 0)

    def test_checkpoint_error_stops_dispatch(self):
        def failed(report):
            raise CheckpointError('checkpoint_write_failed')
        with patch('model_security_eval.engine.discover') as reader:
            with self.assertRaises(CheckpointError):
                evaluate(config(), checkpoint=failed, metadata_provider=reader)
        reader.assert_not_called()
