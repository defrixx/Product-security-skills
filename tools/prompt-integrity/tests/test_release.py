"""Trusted release pinning, rotation and payload-free failure diagnostics."""
import contextlib
import importlib.util
import io
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if not os.environ.get('PROMPT_INTEGRITY_TEST_INSTALLED'):
    sys.path.insert(0, str(ROOT/'src'))
from prompt_integrity import IntegrityError, TransportError, load_policy, verify_and_send
from prompt_integrity.transport import HTTPTransport
from prompt_integrity.cli import main


class ReleaseTests(unittest.TestCase):
    def test_pin_rotation_rollback_and_frozen_request(self):
        baseline = json.loads((ROOT/'examples/baseline.json').read_text())
        request = json.loads((ROOT/'examples/request.json').read_text())
        class Wire:
            def send(self, alias, payload): return payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); path = root/'release.json'
            raw = json.dumps(baseline).encode(); pin = hashlib.sha256(raw).hexdigest()
            path.write_bytes(raw)
            policy = load_policy(path, 'synthetic-support', '1', config_root=root, expected_sha256=pin)
            altered = copy.deepcopy(baseline); altered['trusted_messages'][0]['text'] = 'changed same-version prompt'
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(IntegrityError, '^baseline_digest_mismatch$'):
                load_policy(path, 'synthetic-support', '1', config_root=root, expected_sha256=pin)
            self.assertTrue(verify_and_send(policy, request, 'primary', Wire()))
            altered['profile_version'] = '2'
            release2 = json.dumps(altered).encode(); pin2 = hashlib.sha256(release2).hexdigest()
            path.write_bytes(release2)
            rotated = load_policy(path, 'synthetic-support', '2', config_root=root, expected_sha256=pin2)
            with self.assertRaises(IntegrityError): verify_and_send(rotated, request, 'primary', Wire())
            path.write_bytes(raw)  # Old bytes cannot satisfy the current trusted release pin.
            with self.assertRaisesRegex(IntegrityError, '^baseline_digest_mismatch$'):
                load_policy(path, 'synthetic-support', '2', config_root=root, expected_sha256=pin2)
            with self.assertRaisesRegex(IntegrityError, '^baseline_pin_invalid$'):
                load_policy(path, 'synthetic-support', '1', config_root=root, expected_sha256='bad')

    def test_safe_transport_reasons_and_no_automatic_retry(self):
        transport = HTTPTransport((('primary','http://127.0.0.1:11434/api/chat'),), max_response_bytes=4)
        for error, expected in [(TimeoutError('PRIVATE'), 'transport_timeout'),
                                (ConnectionRefusedError('PRIVATE'), 'transport_connection_failed'),
                                (ValueError('PRIVATE'), 'transport_failed')]:
            with self.subTest(code=expected), patch('http.client.HTTPConnection', side_effect=error) as connect:
                with self.assertRaises(TransportError) as caught: transport.send('primary', b'PRIVATE')
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn('PRIVATE', str(caught.exception))
                self.assertEqual(connect.call_count, 1)
        for status, expected in [(302,'transport_redirect_rejected'), (503,'transport_http_rejected'),
                                 (200,'transport_response_too_large')]:
            with self.subTest(status=status), patch('http.client.HTTPConnection') as connect:
                response = connect.return_value.getresponse.return_value
                response.status = status; response.read.return_value = b'PRIVATE'
                with self.assertRaises(TransportError) as caught: transport.send('primary', b'PRIVATE')
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(connect.call_count, 1)
        with self.assertRaisesRegex(TransportError, '^transport_configuration_invalid$'):
            transport.send('unknown', b'{}')
        self.assertEqual(str(TransportError('PRIVATE')), 'transport_failed')

    def test_pinned_startup_and_cli_do_not_approve_or_refresh(self):
        spec = importlib.util.spec_from_file_location('release_app', ROOT/'examples/application.py')
        application = importlib.util.module_from_spec(spec); spec.loader.exec_module(application)
        raw = (ROOT/'examples/baseline.json').read_bytes()
        pin = hashlib.sha256(raw).hexdigest()
        sent = []
        class Wire:
            def send(self, alias, payload): sent.append(payload); return payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); path = root/'release.json'; path.write_bytes(raw)
            args = ['baseline','validate','--baseline',str(path),'--config-root',str(root),
                    '--expected-profile','synthetic-support','--expected-version','1','--expected-sha256',pin]
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(main(args), 0)
            self.assertFalse(json.loads(output.getvalue())['approved'])
            app = application.CatalogApplication.from_release(path, Wire(), config_root=root,
                       profile='synthetic-support', version='1', sha256=pin)
            self.assertTrue(app.answer('synthetic question'))
            path.write_bytes(raw+b' ')
            with self.assertRaisesRegex(IntegrityError, '^baseline_digest_mismatch$'):
                application.CatalogApplication.from_release(path, Wire(), config_root=root,
                    profile='synthetic-support', version='1', sha256=pin)
            self.assertEqual(len(sent), 1)
            output = io.StringIO()
            with contextlib.redirect_stderr(output): self.assertEqual(main(args), 1)
            self.assertEqual(json.loads(output.getvalue())['code'], 'baseline_digest_mismatch')
