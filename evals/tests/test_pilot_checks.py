"""Synthetic executable-check properties; ordinary tests never require Docker."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals'))
import pilot_checks as checks
from run_model_pilot import APP, PATCHED


class ExecutableChecksTests(unittest.TestCase):
    def test_python_subset_rejects_execution_escape_and_accepts_fixture(self):
        self.assertTrue(checks.supported_python(APP))
        self.assertTrue(checks.supported_python(PATCHED))
        for changed in ('import os\n' + APP, APP + '\nprint(1)',
                        APP.replace('return detail(base, record_id)', 'return base.__class__'),
                        APP.replace('return detail(base, record_id)', 'return open(base)'),
                        APP.replace('"alpha note"', '"changed data"'),
                        APP.replace('def detail', '@next\ndef detail')):
            self.assertFalse(checks.supported_python(changed))
            with patch.object(subprocess, 'run') as proc:
                result = checks.check_python(changed)
                self.assertEqual(result['status'], 'not_executed')
                proc.assert_not_called()

    def test_container_contract_and_cleanup_on_success_and_timeout(self):
        invocations = []
        def command(args, **kwargs):
            invocations.append(args)
            if args[1] == 'image':
                return subprocess.CompletedProcess(args, 0, 'sha256:synthetic-image\n', '')
            if args[1] == 'run':
                self.assertIn('--network', args)
                self.assertEqual(args[args.index('--network') + 1], 'none')
                for flag in ('--read-only', '--cap-drop=ALL', '--pull=never'):
                    self.assertIn(flag, args)
                mounts = [args[i+1] for i, arg in enumerate(args) if arg == '-v']
                self.assertEqual(len(mounts), 2)
                self.assertTrue(all(m.endswith(':ro') for m in mounts))
                candidate = Path(mounts[0].split(':/input')[0])
                self.assertEqual(candidate.read_text(), APP)
                self.assertEqual(candidate.stat().st_mode & 0o777, 0o444)
                self.assertEqual(candidate.parent.stat().st_mode & 0o777, 0o700)
                return subprocess.CompletedProcess(args, 0, json.dumps({'cases': [], 'passed': False}), '')
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(subprocess, 'run', command):
            result = checks.check_python(APP)
        self.assertEqual(result['status'], 'executed')
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup']['succeeded'])
        self.assertEqual(invocations[-1][1:3], ['rm', '-f'])
        self.assertEqual(invocations[-1][-1], invocations[1][invocations[1].index('--name')+1])
        original = command
        def timeout(args, **kwargs):
            if args[1] == 'run': raise subprocess.TimeoutExpired(args, 30)
            return original(args, **kwargs)
        with patch.object(subprocess, 'run', timeout):
            result = checks.check_python(APP)
        self.assertEqual(result['status'], 'not_executed')
        self.assertTrue(result['cleanup']['succeeded'])
