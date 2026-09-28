"""Real child processes, loopback sockets and temp paths under injected failures."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).resolve().parent / 'integration/lifecycle_worker.py'


def ready(process, timeout=30):
    if not select.select([process.stdout], [], [], timeout)[0]:
        raise AssertionError('worker readiness timeout')
    line = process.stdout.readline()
    if not line: raise AssertionError('worker exited before readiness')
    return json.loads(line)


def listening(port):
    with socket.socket() as probe:
        probe.settimeout(.25)
        return probe.connect_ex(('127.0.0.1', port)) == 0


class ResourceCleanupTests(unittest.TestCase):
    def test_failures_remove_owned_resources_preserve_other_scope(self):
        with tempfile.TemporaryDirectory() as output:
            sentinel_report = Path(output) / 'sentinel.json'
            sentinel = subprocess.Popen([sys.executable, str(WORKER), 'sigterm', '--report', str(sentinel_report)], stdout=subprocess.PIPE, text=True)
            try:
                other = ready(sentinel)
                for fault in ['exception', 'timeout', 'sigterm']:
                    with self.subTest(fault=fault):
                        report = Path(output) / (fault + '.json')
                        worker = subprocess.Popen([sys.executable, str(WORKER), fault, '--report', str(report)], stdout=subprocess.PIPE, text=True)
                        try:
                            owned = ready(worker)
                            if fault == 'sigterm': worker.terminate()
                            self.assertEqual(worker.wait(timeout=15), 1)
                            result = json.loads(report.read_text())
                            self.assertEqual(result['cleanup_errors'], [])
                            self.assertEqual(result['error'], {'exception': 'RuntimeError', 'timeout': 'TimeoutExpired', 'sigterm': 'InterruptedError'}[fault])
                            self.assertFalse(Path(owned['temporary']).exists())
                            self.assertFalse(listening(owned['port']))
                            with self.assertRaises(ProcessLookupError): os.kill(owned['pid'], 0)
                            self.assertIsNone(sentinel.poll())
                            self.assertTrue(listening(other['port']))
                            self.assertEqual((Path(other['temporary']) / 'owned.txt').read_text(), 'synthetic temporary output')
                        finally:
                            if worker.poll() is None:
                                worker.terminate(); worker.wait(timeout=15)
                            worker.stdout.close()
            finally:
                sentinel.terminate(); sentinel.wait(timeout=15); sentinel.stdout.close()
            self.assertEqual(json.loads(sentinel_report.read_text())['cleanup_errors'], [])
            self.assertFalse(Path(other['temporary']).exists())
            self.assertFalse(listening(other['port']))
