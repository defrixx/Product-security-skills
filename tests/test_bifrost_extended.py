"""Synthetic opt-in ingress integrity and gateway evaluation integration tests."""
from pathlib import Path
import copy
import http.server
import json
import sys
import threading
import unittest
ROOT = Path(__file__).resolve().parents[1]
for path in ['integrations/bifrost','tools/prompt-guard/src','tools/prompt-integrity/src','tools/model-security-eval/src']:
    sys.path.insert(0, str(ROOT / path))
from client import GuardedClient, BoundaryError
from integrity import GatewayIntegrity
from prompt_guard import OutputGuard, policy_from_dict as guard_policy
from prompt_integrity import policy_from_dict, IntegrityError
from evaluate_route import RouteConfig, evaluate_route
from model_security_eval.cases import PUBLIC
from model_security_eval.transport import EvaluationError


def baseline():
    value = json.loads((ROOT / 'tools/prompt-integrity/examples/baseline.json').read_text())
    value.update(adapter_id='lmstudio-chat-tools-v1', allowed_targets={'gateway': 'ollama/synthetic'},
                 allowed_request_fields={'stream': False, 'temperature': 0, 'max_tokens': 256, 'tools': []})
    value['data_message_policy']['roles'] = ['user']
    return value


def response(text='hello', model='synthetic'):
    return {'model': model, 'choices': [{'finish_reason': 'stop', 'message':
            {'role': 'assistant', 'content': text, 'refusal': None}}]}


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.value = baseline()
        self.integrity = GatewayIntegrity(policy_from_dict(self.value, 'synthetic-support', '1'), 'gateway')
        self.policy = guard_policy(json.loads((ROOT / 'tools/prompt-guard/examples/policy.json').read_text()))
        self.sent = []
        def sender(raw):
            self.sent.append(raw)
            return json.dumps(response()).encode()
        self.sender = sender
        self.system = self.value['trusted_messages'][0]['text']

    def client(self, **overrides):
        args = dict(model='ollama/synthetic', input_policy=self.policy,
                    output_guard=OutputGuard.create(self.policy), transport=self.sender,
                    system=self.system, integrity=self.integrity)
        args.update(overrides)
        return GuardedClient(**args)

    def test_composed_guard_integrity_single_send(self):
        records = b'{"messages":[{"source":"user","text":"hello"}]}'
        self.assertEqual(self.client().complete(records), 'hello')
        self.assertEqual(len(self.sent), 1)
        wire = json.loads(self.sent[0])
        self.assertEqual(wire['model'], 'ollama/synthetic')
        self.assertEqual(wire['messages'][0]['content'], self.system)
        self.assertEqual(set(wire), {'model', 'messages', 'stream', 'temperature', 'max_tokens', 'tools'})
        self.assertEqual(self.sent[0], json.dumps(wire, ensure_ascii=False, separators=(',', ':')).encode())

    def test_instruction_and_route_tamper_no_send(self):
        for overrides in [dict(system=self.system + '\n'), dict(model='ollama/other'), dict(system='')]:
            with self.assertRaises(BoundaryError):
                self.client(**overrides).complete(b'{"messages":[{"source":"user","text":"hello"}]}')
        self.assertEqual(self.sent, [])

    def test_options_duplicate_keys_fallback_and_tools_tamper(self):
        request = {'model': 'ollama/synthetic', 'messages': [{'role': 'system', 'content': self.system},
                   {'role': 'user', 'content': 'hello'}], **self.integrity.options()}
        for key, value in [('stream', True), ('temperature', False), ('max_tokens', 257),
                           ('fallbacks', []), ('n', 2), ('tools', [{'type': 'function'}])]:
            changed = copy.deepcopy(request); changed[key] = value
            with self.assertRaises(IntegrityError):
                self.integrity.send(json.dumps(changed).encode(), self.sender)
        with self.assertRaises(IntegrityError):
            self.integrity.send(b'{"model":"ollama/synthetic","model":"ollama/other"}', self.sender)
        self.assertEqual(self.sent, [])
        options = self.integrity.options(); options['max_tokens'] = 1
        self.assertEqual(self.integrity.options()['max_tokens'], 256)

    def test_composed_boundary_real_http_bytes_and_no_second_send(self):
        from client import LocalTransport
        received = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers['Content-Length'])))
                raw = json.dumps(response()).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            wire = LocalTransport('http://127.0.0.1:' + str(server.server_port))
            records = b'{"messages":[{"source":"user","text":"hello"}]}'
            self.assertEqual(self.client(transport=wire).complete(records), 'hello')
            with self.assertRaises(BoundaryError):
                self.client(transport=wire, system=self.system + ' altered').complete(records)
            self.assertEqual(len(received), 1)
            decoded = json.loads(received[0])
            self.assertEqual(received[0], json.dumps(decoded, ensure_ascii=False, separators=(',', ':')).encode())
            self.assertEqual(decoded['messages'][0]['content'], self.system)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_baseline_contract_is_closed(self):
        for mutate in [lambda v: v['data_message_policy']['roles'].append('assistant'),
                       lambda v: v['allowed_targets'].update(fallback='ollama/other'),
                       lambda v: v.update(adapter_id='ollama-chat-text-v1')]:
            value = baseline(); mutate(value)
            with self.assertRaises(IntegrityError):
                GatewayIntegrity(policy_from_dict(value, 'synthetic-support', '1'), 'gateway')


class RouteEvaluationTests(unittest.TestCase):
    def config(self, **values):
        args = dict(endpoint='http://127.0.0.1:8080', model='ollama/synthetic', reported_model='synthetic')
        args.update(values)
        return RouteConfig(**args)

    def test_behavior_passes_never_become_route_admission(self):
        def responder(url, request, timeout):
            prompt = request['messages'][-1]['content']
            return response(PUBLIC if PUBLIC in prompt else 'READY' if prompt.startswith('We are testing formatting.') else 'Refused.')
        report = evaluate_route(self.config(token='SYNTHETIC_CREDENTIAL'), responder=responder)
        self.assertEqual(report['counts']['fail'], 0)
        self.assertGreater(report['counts']['pass'], 0)
        self.assertFalse(report['eligible'])
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertIn('caller-configured-gateway-route', report['identity_source'])
        self.assertNotIn('SYNTHETIC_CREDENTIAL', json.dumps(report))
        self.assertEqual(report['metadata_requests'], 0)

    def test_response_model_mismatch_cannot_pass(self):
        report = evaluate_route(self.config(), responder=lambda *args: response(model='other'))
        self.assertFalse(report['eligible'])
        self.assertTrue(any(r['status'] == 'inconclusive' for r in report['results']))

    def test_route_is_part_of_criteria(self):
        responder = lambda *args: response()
        first = evaluate_route(self.config(), responder=responder)
        second = evaluate_route(self.config(model='ollama/other'), responder=responder)
        self.assertNotEqual(first['criteria_sha256'], second['criteria_sha256'])

    def test_invalid_endpoint_and_route_rejected_before_send(self):
        for values in [dict(endpoint='http://example.com:8080'), dict(model='unprefixed')]:
            with self.assertRaises((EvaluationError, BoundaryError)):
                evaluate_route(self.config(**values), responder=lambda *args: self.fail('must not send'))

    def test_real_http_transport_fixture_not_bifrost(self):
        seen = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((self.path, request))
                raw = json.dumps(response()).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            report = evaluate_route(self.config(endpoint='http://127.0.0.1:' + str(server.server_port)))
            self.assertGreater(report['inference_requests'], 0)
            self.assertNotIn('gateway_transport_failed', json.dumps(report))
            self.assertEqual(report['metadata_requests'], 0)
            self.assertTrue(all(path == '/v1/chat/completions' for path, _ in seen))
            self.assertFalse(report['eligible'])
            self.assertNotIn('injected test responder; not a live gateway run', report['substitutions'])
        finally:
            server.shutdown(); server.server_close(); thread.join()
