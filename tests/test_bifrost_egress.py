"""Real local HTTP oracle checks the final egress boundary; synthetic only."""
from pathlib import Path
import copy,hashlib,http.server,json,sys,threading,unittest
ROOT=Path(__file__).resolve().parents[1]
for folder in ['integrations/bifrost','tools/prompt-guard/src','tools/prompt-integrity/src']:sys.path.insert(0,str(ROOT/folder))
from client import LocalTransport,PrivateNetworkTransport,BoundaryError
from egress import ProviderBoundary
from prompt_guard import policy_from_dict as pg_policy,OutputGuard
from prompt_integrity import policy_from_dict as pi_policy


class EgressTests(unittest.TestCase):
    def setUp(self):
        self.received=[];self.audit=[];self.content='READY';self.status=200;self.model='synthetic';self.reasoning='Synthetic hidden notes.';self.observer_failure=False;outer=self
        class Model(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']));outer.received.append(raw)
                body=json.dumps({'model':outer.model,'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':outer.content,'refusal':None,'reasoning':outer.reasoning,'reasoning_content':outer.reasoning,'reasoning_details':[{'index':0,'type':'reasoning.text','text':outer.reasoning}]}}]}).encode()
                self.send_response(outer.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        self.model_server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model)
        self.thread=threading.Thread(target=self.model_server.serve_forever,daemon=True);self.thread.start()
        baseline=json.loads((ROOT/'integrations/bifrost/integrity-baseline.json').read_text())
        baseline.update(adapter_id='openai-provider-text-v1',allowed_targets={'provider':'synthetic'},allowed_request_fields={'temperature':0,'max_completion_tokens':64})
        self.baseline=baseline
        self.request={'model':'synthetic','messages':[{'role':'system','content':baseline['trusted_messages'][0]['text']},{'role':'user','content':'hello'}],**baseline['allowed_request_fields']}
        self.policy=pg_policy(json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text()))
        def observer(value):
            if self.observer_failure:raise RuntimeError('private')
            self.audit.append(value)
        self.boundary=ProviderBoundary(pi_policy(baseline,'synthetic-support','1'),'provider',self.policy,OutputGuard.create(self.policy),LocalTransport('http://127.0.0.1:'+str(self.model_server.server_port)),observer)

    def tearDown(self):self.model_server.shutdown();self.model_server.server_close();self.thread.join()

    def test_exact_verified_bytes_match_oracle_single_send(self):
        result=self.boundary.complete(json.dumps(self.request,indent=2).encode())
        self.assertEqual(result['choices'][0]['message'],{'role':'assistant','content':'READY'})
        self.assertNotIn('reasoning',json.dumps(result));self.assertEqual(len(self.received),1)
        expected=json.dumps(self.request,ensure_ascii=False,separators=(',',':')).encode()
        self.assertEqual(self.received,[expected])
        self.assertEqual(self.audit,[{'event':'verified_provider_bytes','sha256':hashlib.sha256(expected).hexdigest()}])

    def test_tamper_secret_and_audit_error_produce_no_model_call(self):
        for key,value in [('model','other'),('stream',True),('max_completion_tokens',65),('tools',[])]:
            item=copy.deepcopy(self.request);item[key]=value
            with self.assertRaises(BoundaryError):self.boundary.complete(json.dumps(item).encode())
        item=copy.deepcopy(self.request);item['messages'][0]['content']+=' changed'
        with self.assertRaises(BoundaryError):self.boundary.complete(json.dumps(item).encode())
        item=copy.deepcopy(self.request);item['messages'][1]['content']='SYNTHETIC_PRIVATE_TOKEN_19'
        with self.assertRaises(BoundaryError):self.boundary.complete(json.dumps(item).encode())
        self.observer_failure=True
        with self.assertRaises(BoundaryError):self.boundary.complete(json.dumps(self.request).encode())
        self.assertEqual(self.received,[])

    def test_model_error_wrong_identity_and_secret_output_do_not_release_or_retry(self):
        for status,model,content,reasoning in [(500,'synthetic','READY','safe'),(200,'other','READY','safe'),
            (200,'synthetic','SYNTHETIC_PRIVATE_TOKEN_19','safe'),(200,'synthetic','READY','SYNTHETIC_PRIVATE_TOKEN_19')]:
            self.status,self.model,self.content,self.reasoning=status,model,content,reasoning
            before=len(self.received)
            with self.assertRaises(BoundaryError):self.boundary.complete(json.dumps(self.request).encode())
            self.assertEqual(len(self.received),before+1)

    def test_private_transport_is_explicit_numeric_fixed_and_rfc1918_only(self):
        PrivateNetworkTransport('http://172.30.230.10:8080',network_cidr='172.30.230.0/24')
        for endpoint,network in [('http://example.com:8080','172.30.230.0/24'),('http://169.254.1.1:8080','169.254.1.0/24'),
            ('http://8.8.8.8:8080','8.8.8.0/24'),('http://172.30.231.10:8080','172.30.230.0/24'),
            ('http://172.30.230.10','172.30.230.0/24'),('http://172.30.230.10:8080','172.30.0.0/16')]:
            with self.assertRaises(BoundaryError):PrivateNetworkTransport(endpoint,network_cidr=network)
        with self.assertRaises(BoundaryError):LocalTransport('http://172.30.230.10:8080')
