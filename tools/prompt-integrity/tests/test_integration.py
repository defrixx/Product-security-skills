"""Local HTTP integration, CLI, filesystem and concurrency; no model service."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if not os.environ.get('PROMPT_INTEGRITY_TEST_INSTALLED'):
    sys.path.insert(0, str(ROOT/'src'))
from prompt_integrity import IntegrityError, TransportError, load_policy, policy_from_dict, verify_and_send
from prompt_integrity.cli import main
from prompt_integrity.files import read_bytes, write_new
from prompt_integrity.transport import HTTPTransport
spec = importlib.util.spec_from_file_location('synthetic_app', ROOT/'examples/application.py')
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads((ROOT/'examples/baseline.json').read_text())
        self.policy = policy_from_dict(self.baseline, 'synthetic-support', '1')
        self.request = json.loads((ROOT/'examples/request.json').read_text())

    def test_actual_http_bytes_retries_fallback_and_block(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                raw = self.rfile.read(int(self.headers['Content-Length']))
                received.append((self.path, raw))
                self.send_response(503 if len(received) < 3 else 200)
                self.end_headers(); self.wfile.write(b'{"synthetic":true}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            endpoint = 'http://127.0.0.1:%d/api/chat' % server.server_port
            transport = HTTPTransport((('primary', endpoint), ('fallback', endpoint)))
            application = app.CatalogApplication(self.policy, transport)
            self.assertEqual(application.answer('hello'), b'{"synthetic":true}')
            self.assertEqual(len(received), 3)
            self.assertEqual([json.loads(raw)['model'] for _, raw in received], ['synthetic-model', 'synthetic-model', 'synthetic-backup'])
            self.assertTrue(all(path == '/api/chat' for path, _ in received))
            for _, raw in received:
                self.assertEqual(raw, json.dumps(json.loads(raw), ensure_ascii=False, separators=(',', ':')).encode())
            def inject(number, request): request['messages'][0]['content'] += 'injected'
            with self.assertRaises(IntegrityError): application.answer('hello', mutate_attempt=inject)
            self.assertEqual(len(received), 3)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)

    def test_retry_is_rechecked_and_bypass_detector_has_negative_control(self):
        checked=[]; sent=[]
        class FailingTransport:
            def send(self, alias, payload):
                sent.append(payload); raise TransportError('transport_failed')
        original = app.verify_and_send
        def observed(*args):
            checked.append(args[2]); return original(*args)
        def inject(number, request):
            if number == 1: request['messages'][0]['content']='changed'
        with patch.object(app, 'verify_and_send', observed):
            with self.assertRaises(IntegrityError):
                app.CatalogApplication(self.policy, FailingTransport()).answer('user', mutate_attempt=inject)
        self.assertEqual(len(checked), 2); self.assertEqual(len(sent), 1)
        # An intentionally unsafe direct transport call must fail the coverage invariant.
        def coverage_ok(attempts, dispatches): return len(dispatches) <= len(attempts)
        self.assertTrue(coverage_ok(checked, sent))
        bypass=[]
        class Spy:
            def send(self, alias, payload): bypass.append(payload)
        Spy().send('primary', b'{}')
        self.assertFalse(coverage_ok([], bypass))

    def test_concurrent_policies_do_not_mix(self):
        def run(index):
            baseline=copy.deepcopy(self.baseline); baseline['profile_id']='profile-%d'%index
            baseline['trusted_messages'][0]['text']='prompt-%d'%index
            request=copy.deepcopy(self.request); request['messages'][0]['content']='prompt-%d'%index
            policy=policy_from_dict(baseline, baseline['profile_id'], '1')
            class Spy:
                def send(self, alias, payload): return json.loads(payload)
            return verify_and_send(policy, request, 'primary', Spy())['messages'][0]['content']
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(run, range(20))), ['prompt-%d'%i for i in range(20)])

    def test_cli_roundtrip_and_private_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            for name in ('policy.json','instructions.json','request.json'):
                (root/name).write_bytes((ROOT/'examples'/name).read_bytes())
            common=['--config-root',str(root),'--expected-profile','synthetic-support','--expected-version','1']
            def call(args):
                output=io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output): code=main(args+common)
                self.assertNotIn('SYNTHETIC-PRIVATE',output.getvalue())
                return code,output.getvalue()
            create=['baseline','create','--instructions',str(root/'instructions.json'),'--policy',str(root/'policy.json'),'--output',str(root/'baseline.json')]
            self.assertEqual(call(create)[0],0); before=(root/'baseline.json').read_bytes()
            self.assertEqual(call(create)[0],1); self.assertEqual((root/'baseline.json').read_bytes(),before)
            self.assertEqual(call(['baseline','validate','--baseline',str(root/'baseline.json')])[0],0)
            check=['request','check','--baseline',str(root/'baseline.json'),'--request',str(root/'request.json'),'--target','primary']
            self.assertEqual(call(check)[0],0)
            changed=copy.deepcopy(self.request); changed['messages'][0]['content']='SYNTHETIC-PRIVATE'
            (root/'request.json').write_text(json.dumps(changed)); self.assertEqual(call(check)[0],2)
            (root/'request.json').write_text('{SYNTHETIC-PRIVATE'); self.assertEqual(call(check)[0],1)
            self.assertEqual(os.stat(root/'baseline.json').st_mode & 0o777,0o600)

    def test_filesystem_and_pin_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'baseline.json'; source.write_text(json.dumps(self.baseline))
            with self.assertRaises(IntegrityError):load_policy(source,'synthetic-support','old',config_root=root)
            frozen=load_policy(source,'synthetic-support','1',config_root=root)
            source.write_text('{}')
            class Spy:
                def send(self, alias, payload):return payload
            self.assertTrue(verify_and_send(frozen,self.request,'primary',Spy()))
            with self.assertRaises(IntegrityError):load_policy(source,'synthetic-support','1',config_root=root)
            link=root/'link';link.symlink_to(source)
            with self.assertRaises(IntegrityError):read_bytes(link,root,1024)
            with self.assertRaises(IntegrityError):write_new(source,root,b'overwrite')
            with self.assertRaises(IntegrityError):read_bytes(source,root/'other',1024)
            hard=root/'hard';os.link(source,hard)
            with self.assertRaises(IntegrityError):read_bytes(hard,root,1024)

    def test_transport_refuses_redirects_and_bounds_response(self):
        class Response:
            status=302
            def read(self, size): return b'x'*size
        class Connection:
            def __init__(self,*args,**kwargs):pass
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        transport=HTTPTransport((('primary','http://127.0.0.1:11434/api/chat'),),max_response_bytes=4)
        with patch('http.client.HTTPConnection',Connection):
            with self.assertRaises(TransportError):transport.send('primary',b'{}')
            Response.status=200
            with self.assertRaises(TransportError):transport.send('primary',b'{}')
        with self.assertRaises(ValueError):HTTPTransport((('primary','http://example.invalid/api/chat'),))


if __name__=='__main__':unittest.main()
