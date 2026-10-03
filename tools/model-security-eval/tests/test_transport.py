"""Actual loopback HTTP tests with synthetic servers; no inference or external service."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import tempfile
import signal
from pathlib import Path
import sys
import threading
import time
import unittest
if not os.environ.get('MODEL_SECURITY_EVAL_TEST_INSTALLED'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model_security_eval.transport import EvaluationError, MAX_RESPONSE, decode, endpoint_url, payload, post


@contextmanager
def server(mode='ok'):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            requests.append((self.path, {}))
            if self.path == '/api/v1/models':
                body = {'models': [{'key': 'synthetic', 'type': 'llm',
                                   'loaded_instances': [{'id': 'synthetic', 'config': {'context_length': 4096}}]}]}
            elif self.path == '/api/tags':
                body = {'models': [{'name': 'synthetic:latest', 'model': 'synthetic:latest', 'size': 512,
                                   'digest': 'a' * 64, 'details': {'quantization_level': 'Q4'}}]}
            elif self.path == '/api/version':
                body = {'version': 'fixture-server'}
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())
        def do_POST(self):
            requests.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            if mode == 'slow' or (mode == 'interrupt-model' and len([r for r in requests if r[1]]) >= 3):
                time.sleep(0.6)
            self.send_response(302 if mode == 'redirect' else 200)
            if mode == 'redirect':
                self.send_header('Location', 'https://outside.invalid/collect')
            self.end_headers()
            if mode in ('lmstudio-model', 'ollama-model', 'interrupt-model'):
                from test_engine import compliant
                backend = 'lmstudio' if mode == 'interrupt-model' else mode.split('-')[0]
                body = json.dumps(compliant(backend)('', requests[-1][1], 5)).encode()
            else:
                body = {'ok': b'{"ok":true}', 'slow': b'{"ok":true}', 'redirect': b'{}',
                    'duplicate': b'{"ok":true,"ok":false}', 'overflow': b'{"value":1e309}', 'oversize': b'x' * (MAX_RESPONSE + 1),
                    'invalid': b'{"private":"SYNTHETIC_SERVER_ERROR"'}[mode]
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{http.server_port}', requests
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)


class TransportTests(unittest.TestCase):
    def test_actual_http_payload_for_both_adapters(self):
        for backend in ('lmstudio', 'ollama'):
            with server() as (origin, requests):
                request = payload(backend, 'synthetic', [{'role': 'user', 'content': 'public'}], [], 0, 12, 17)
                self.assertEqual(post(endpoint_url(origin, backend), request, 5), {'ok': True})
                self.assertEqual(requests[0][1], request)
                self.assertEqual(requests[0][0], '/api/chat' if backend == 'ollama' else '/v1/chat/completions')
                self.assertFalse(request['stream'])

    def test_redirect_duplicate_oversize_and_errors_are_safe(self):
        for mode, code in (('redirect', 'redirect_rejected'), ('duplicate', 'invalid_response_json'),
                           ('oversize', 'response_too_large'), ('overflow', 'invalid_response_json'), ('invalid', 'invalid_response_json')):
            with server(mode) as (origin, requests):
                with self.assertRaisesRegex(EvaluationError, code) as caught:
                    post(endpoint_url(origin, 'lmstudio'), {}, 5)
                self.assertNotIn('SYNTHETIC_SERVER_ERROR', str(caught.exception))
                self.assertEqual(len(requests), 1)

    def test_whole_request_deadline(self):
        with server('slow') as (origin, requests):
            start = time.monotonic()
            with self.assertRaises(EvaluationError):
                post(endpoint_url(origin, 'ollama'), {}, 0.2)
            self.assertLess(time.monotonic() - start, 1.5)

    def test_numeric_loopback_origin_only(self):
        for origin in ('http://localhost:1234', 'http://127.0.0.1:1234/api',
                       'http://127.0.0.1:1234?x=1', 'http://u:p@127.0.0.1:1234',
                       'http://192.0.2.1:1234', 'http://127.0.0.1', 'https://127.0.0.1:1234'):
            with self.assertRaises(EvaluationError):
                endpoint_url(origin, 'lmstudio')
        self.assertEqual(endpoint_url('http://[::1]:1234', 'ollama'), 'http://[::1]:1234/api/chat')

    def test_real_cli_to_http_server_multi_round_for_both_backends(self):
        import model_security_eval
        environment = dict(os.environ, PYTHONPATH=str(Path(model_security_eval.__file__).resolve().parent.parent))
        for backend in ('lmstudio', 'ollama'):
            with server(backend + '-model') as (origin, requests), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary).resolve() / 'run'
                result = subprocess.run([sys.executable, '-m', 'model_security_eval', '--backend', backend,
                                         '--endpoint', origin, '--model', 'synthetic', '--model-revision', 'a' * 64 if backend == 'ollama' else 'fixture-v1',
                                         '--server-version', 'fixture-server', '--repetitions', '1',
                                         '--max-seconds', '60', '--output', str(output)],
                                        env=environment, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads((output / 'report.json').read_text())
                self.assertEqual(report['verdict'], 'pass')
                self.assertEqual(report['requests'], len(requests))
                self.assertTrue(any(r[1].get('messages', [{'role': ''}])[-1]['role'] == 'tool' for r in requests))
                events = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(events[-1]['verdict'], 'pass')

    def test_cli_sigterm_retains_reports_and_checkpoints(self):
        import model_security_eval
        environment = dict(os.environ, PYTHONPATH=str(Path(model_security_eval.__file__).resolve().parent.parent))
        with server('interrupt-model') as (origin, requests), tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve() / 'run'
            process = subprocess.Popen([sys.executable, '-m', 'model_security_eval', '--backend', 'lmstudio',
                                        '--endpoint', origin, '--model', 'synthetic', '--model-revision', 'fixture-v1',
                                        '--server-version', 'fixture-server', '--repetitions', '1', '--capabilities', 'chat',
                                        '--output', str(output)], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if len([r for r in requests if r[1]]) >= 3:
                        process.send_signal(signal.SIGTERM)
                        break
                    if process.poll() is not None:
                        self.fail('CLI exited before signal test')
                    time.sleep(0.01)
                else:
                    self.fail('Signal test did not reach active trial')
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 2, stdout + stderr)
                report = json.loads((output / 'report.json').read_text())
                checkpoint = json.loads((output / 'checkpoint.json').read_text())
                self.assertEqual(report['run_state'], 'interrupted')
                self.assertEqual(checkpoint['run_state'], 'interrupted')
                self.assertEqual(report['counts']['pass'], 2)
                self.assertFalse(report['eligible'])
                self.assertEqual(len(report['results']), report['planned_trials'])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_ambiguous_or_incomplete_response_is_never_complete(self):
        for backend, value in (
            ('lmstudio', {'choices': []}),
            ('lmstudio', {'choices': [{'message': {'role': 'user', 'content': 'x'}, 'finish_reason': 'stop'}]}),
            ('ollama', {'message': {'role': 'assistant', 'content': 42}, 'done': True}),
        ):
            with self.assertRaises(EvaluationError):
                decode(backend, value)
        message, complete = decode('ollama', {'message': {'role': 'assistant', 'content': 'x'}, 'done': False})
        self.assertFalse(complete)
