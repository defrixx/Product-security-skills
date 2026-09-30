"""Synthetic SARIF helper tests, not agent-classification evaluations."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'skills/security-report-triage/scripts/normalize_sarif.py'
spec = importlib.util.spec_from_file_location('sarif_normalizer', SCRIPT)
sarif = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sarif)
SEED = 'SYNTHETIC-PRIVATE-CONTEXT-73521'


def document():
    return {'version': '2.1.0', 'runs': [{'tool': {'driver': {'name': SEED, 'rules': [{'id': SEED}]}},
        'invocations': [{'executionSuccessful': True}], 'results': [{'ruleIndex': 0,
        'level': 'error', 'message': {'text': SEED}, 'locations': [{'physicalLocation': {
            'artifactLocation': {'uri': SEED}, 'region': {'startLine': 3}}}]}]}]}


class SarifTests(unittest.TestCase):
    def test_accounting_and_redaction(self):
        doc = document()
        doc['runs'].append(document()['runs'][0])
        doc['runs'][0]['results'].append(None)
        normalized, summary = sarif.normalize(doc, sarif.DEFAULTS)
        self.assertEqual(summary['raw_results'], 3)
        self.assertEqual(normalized['results'][1]['disposition'], 'unprocessed')
        self.assertNotEqual(normalized['results'][0]['rule_id'], normalized['results'][2]['rule_id'])
        self.assertNotIn(SEED, json.dumps([normalized, summary]))

    def test_empty_is_not_complete_scan(self):
        doc = document(); doc['runs'][0]['results'] = []; doc['runs'][0].pop('invocations')
        _, summary = sarif.normalize(doc, sarif.DEFAULTS)
        self.assertEqual(summary['raw_results'], 0)
        self.assertIn('invocation_unknown', summary['issues'])
        doc['runs'][0].pop('results')
        self.assertIsNone(sarif.normalize(doc, sarif.DEFAULTS)[1]['raw_results'])

    def test_rule_mismatch_and_external_fields(self):
        doc = document(); run = doc['runs'][0]
        run['results'][0]['ruleId'] = 'different'
        run['externalPropertyFileReferences'] = {'results': [{'location': {'uri': 'https://example.invalid/'+SEED}}]}
        _, summary = sarif.normalize(doc, sarif.DEFAULTS)
        self.assertIn('rule_mismatch', summary['issues'])
        self.assertIn('external_properties_not_loaded', summary['issues'])

    def test_paths_are_never_dereferenced(self):
        for value in ['/etc/passwd', '../outside', '%2e%2e/outside', 'https://example.invalid/x', 'link']:
            doc = document(); doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['artifactLocation']['uri'] = value
            with patch('builtins.open', side_effect=AssertionError('unexpected read')):
                normalized, _ = sarif.normalize(doc, sarif.DEFAULTS)
            self.assertEqual(normalized['results'][0]['locations'][0]['resolution'], 'not_resolved')

    def test_decode_rejections(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'"\\ud800"', b'['*65+b']'*65, b'{malformed']:
            with self.assertRaises(sarif.IntakeError): sarif.decode(raw, sarif.DEFAULTS)
        with self.assertRaises(sarif.IntakeError):
            sarif.decode(b'[1,2]', {**sarif.DEFAULTS, 'nodes': 2})

    def test_copy_cli_preserves_source_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/'input.sarif'; raw = json.dumps(document()).encode(); source.write_bytes(raw)
            copied = root/'copied'; shutil.copytree(SCRIPT.parent.parent, copied)
            cmd = [sys.executable, str(copied/'scripts/normalize_sarif.py'), '--input', str(source), '--output', str(root/'out')]
            run = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(source.read_bytes(), raw)
            self.assertFalse((root/'out/RUNNING').exists())
            combined = run.stdout+run.stderr+''.join(p.read_text() for p in (root/'out').iterdir())
            self.assertNotIn(SEED, combined)
            again = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(again.returncode, 1)
            self.assertIn('output_exists', again.stderr)

    def test_output_overlap_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/'source'; source.write_text('{}')
            link = root/'link'; link.symlink_to(source)
            with self.assertRaises(OSError): sarif.read_input(link, 1024)
            with self.assertRaises(sarif.IntakeError):
                sarif.write_output(root/'out', source, root, {'x.json': {}}, 1024)
            directory = root/'directory'; directory.mkdir(); (root/'alias').symlink_to(directory, target_is_directory=True)
            with self.assertRaises(OSError): sarif.write_output(root/'alias/out', source, None, {'x.json': {}}, 1024)

    def test_partial_write_retains_running_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/'source'; source.write_text('{}')
            real = sarif.os.open
            def fail(path, *args, **kwargs):
                if path == 'second.json': raise OSError('synthetic failure')
                return real(path, *args, **kwargs)
            with patch.object(sarif.os, 'open', side_effect=fail):
                with self.assertRaises(OSError):
                    sarif.write_output(root/'out', source, None, {'first.json': {}, 'second.json': {}}, 1024)
            self.assertTrue((root/'out/RUNNING').exists())

    def test_limits_and_safe_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/SEED; source.write_text('{'+SEED)
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                code = sarif.main(['--input', str(source), '--output', str(root/'out')])
            self.assertEqual(code, 1); self.assertNotIn(SEED, output.getvalue())
            source.write_text(json.dumps(document()))
            with self.assertRaises(sarif.IntakeError): sarif.read_input(source, 1)
            with self.assertRaises(sarif.IntakeError):
                sarif.normalize(document(), {**sarif.DEFAULTS, 'results': 0})
            with self.assertRaises(sarif.IntakeError):
                sarif.write_output(root/'out', source, None, {'x.json': {'a': 1}}, 1)

    def test_flow_suppression_and_fingerprint_preservation(self):
        doc = document(); result = doc['runs'][0]['results'][0]
        result.update(suppressions=[{'kind': 'external', 'status': 'accepted'}], fingerprints={'seed': SEED}, baselineState='absent',
                      codeFlows=[{'threadFlows': [{'locations': [{'location': result['locations'][0]}]}]}])
        normalized, summary = sarif.normalize(doc, sarif.DEFAULTS)
        record = normalized['results'][0]
        self.assertEqual(record['disposition'], 'hypothesis')
        self.assertEqual(record['baseline_state'], 'absent')
        self.assertEqual(len(record['code_flow_locations']), 1)
        self.assertEqual(len(record['fingerprint_ids']), 1)
        self.assertNotIn(SEED, json.dumps(normalized))
        self.assertEqual(summary['status'], 'completed_within_subset')


if __name__ == '__main__': unittest.main()
