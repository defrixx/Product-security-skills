"""CI exit semantics, offline inventory, private fresh reports and evidence retention."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
if not os.environ.get('MODEL_SECURITY_EVAL_TEST_INSTALLED'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model_security_eval import cli
from model_security_eval.engine import evaluate
from model_security_eval.reporting import read_baseline, reserve_output, write_report
from model_security_eval.transport import EvaluationError
from test_engine import compliant, config, response, SECRET, metadata


class CLITests(unittest.TestCase):
    def args(self, output):
        return ['--backend', 'lmstudio', '--model', 'synthetic', '--model-revision', 'fixture-v1',
                '--server-version', 'fixture-server', '--capabilities', 'chat', '--repetitions', '1',
                '--output', str(output)]

    def test_ci_exit_codes_and_json_logs(self):
        for responder, expected in ((compliant('lmstudio'), 0), (lambda *args: response(SECRET), 1),
                                    (lambda *args: response(complete=False), 2)):
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary).resolve() / 'run'
                stream = io.StringIO()
                def fake_evaluate(cfg, **kwargs):
                    return evaluate(cfg, responder=responder, token_factory=lambda: SECRET, metadata_provider=metadata, **kwargs)
                with patch.object(cli, 'evaluate', side_effect=fake_evaluate), redirect_stdout(stream):
                    code = cli.main(self.args(output))
                self.assertEqual(code, expected)
                events = [json.loads(line) for line in stream.getvalue().splitlines()]
                self.assertEqual(events[-1]['eligible'], expected == 0)
                self.assertNotIn(SECRET, stream.getvalue())
                report = json.loads((output / 'report.json').read_text())
                self.assertEqual(report['eligible'], expected == 0)
                self.assertEqual((output.stat().st_mode & 0o777), 0o700)
                self.assertEqual(((output / 'report.json').stat().st_mode & 0o777), 0o600)

    def test_inventory_never_calls_model_or_creates_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve() / 'unused'
            with patch.object(cli, 'evaluate') as mocked, redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(self.args(output) + ['--list-cases']), 0)
            mocked.assert_not_called()
            self.assertFalse(output.exists())

    def test_existing_output_and_symlink_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = reserve_output(root / 'run')
            report = evaluate(config(capabilities=('chat',)), compliant('lmstudio'), token_factory=lambda: SECRET, metadata_provider=metadata)
            write_report(output, report)
            original = (output / 'report.json').read_bytes()
            with self.assertRaises(EvaluationError):
                reserve_output(output)
            link = root / 'link'
            link.symlink_to(output, target_is_directory=True)
            with self.assertRaises(EvaluationError):
                reserve_output(link / 'new')
            with self.assertRaises(EvaluationError):
                read_baseline(link / 'report.json')
            self.assertEqual((output / 'report.json').read_bytes(), original)

    def test_malformed_baseline_rejected_before_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            baseline = root / 'bad.json'
            baseline.write_text('{"verdict":"pass","verdict":"fail"}')
            with patch.object(cli, 'evaluate') as mocked, redirect_stdout(io.StringIO()):
                code = cli.main(self.args(root / 'run') + ['--baseline', str(baseline)])
            self.assertEqual(code, 2)
            mocked.assert_not_called()
            self.assertFalse((root / 'run').exists())

    def test_structurally_invalid_baseline_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            baseline = root / 'bad.json'
            baseline.write_text('{}')
            with patch.object(cli, 'evaluate') as mocked, redirect_stdout(io.StringIO()):
                code = cli.main(self.args(root / 'run') + ['--baseline', str(baseline)])
            self.assertEqual(code, 2)
            mocked.assert_not_called()
            self.assertFalse((root / 'run').exists())

    def test_module_entrypoint_without_install(self):
        import model_security_eval
        environment = dict(os.environ, PYTHONPATH=str(Path(model_security_eval.__file__).resolve().parent.parent))
        result = subprocess.run([sys.executable, '-m', 'model_security_eval', *self.args('/unused'), '--list-cases'],
                                env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['event'], 'case_inventory')
