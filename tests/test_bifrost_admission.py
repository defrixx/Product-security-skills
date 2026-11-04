"""Synthetic binding fixtures, never proof of real model/provider identity."""
from pathlib import Path
from dataclasses import asdict,replace
import copy,hashlib,http.server,json,sys,threading,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
for folder in ['integrations/bifrost','tools/prompt-guard/src','tools/prompt-integrity/src','tools/model-security-eval/src']:sys.path.insert(0,str(ROOT/folder))
from admission import RouteSnapshot,EvaluationBinding,AdmissionError
from egress import ProviderBoundary
from client import LocalTransport,BoundaryError
from prompt_guard import OutputGuard,policy_from_dict as pg_policy
from prompt_integrity import policy_from_dict as pi_policy
from model_security_eval.engine import Config
from model_security_eval.cases import suite,PUBLIC
from model_security_eval import __version__
from model_security_eval.transport import EvaluationError
from evaluate_route import RouteConfig,evaluate_route
REVISION='1'*64;CRITERIA='2'*64;IMAGE='sha256:'+'3'*64


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.pg=pg_policy(json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text()))
        baseline=json.loads((ROOT/'tools/prompt-integrity/examples/provider-baseline.json').read_text())
        self.policy=pi_policy(baseline,'synthetic-provider','1')
        self.boundary=ProviderBoundary(self.policy,'provider',self.pg,OutputGuard.create(self.pg),LocalTransport('http://127.0.0.1:1234'))
        self.config={'config_store':{'enabled':False},'logs_store':{'enabled':False},'plugins':[],
            'client':{'enable_logging':False},'framework':{},'providers':{'fixture':{'custom_provider_config':{'base_provider_type':'openai'},
            'network_config':{'base_url':'http://127.0.0.1:18081','max_retries':0},
            'keys':[{'name':'provider-v1','value':'env.PROVIDER_KEY','models':['synthetic'],'weight':1}]}}}
        self.snapshot=self.capture()

    def capture(self,**changes):
        values=dict(boundary=self.boundary,gateway_config=json.dumps(self.config).encode(),route_version='route-v1',image_digest=IMAGE,
                    gateway_model='fixture/synthetic',api_origin='http://127.0.0.1:8080',egress_origin='http://127.0.0.1:18081')
        values.update(changes);return RouteSnapshot.capture(**values)

    def report(self):
        cfg=Config('ollama',self.boundary.transport.endpoint,'synthetic',capabilities=('chat',),model_revision=REVISION,server_version='synthetic-server',repetitions=1)
        rows=[{'case_id':case.id,'repetition':0,'status':'pass','complete':True,'violations':[],'real_effects':0} for case in suite(('chat',))]
        identity={'source':'ollama-tags-version','accepted_models':['synthetic'],'model_digest':REVISION,'server_version':'synthetic-server','details':{},'diagnostics':[]}
        return {'schema_version':2,'verdict':'pass','eligible':True,'run_state':'complete','identity_limits':[],
            'criteria_sha256':CRITERIA,'evaluator_version':__version__,'suite_version':2,'evaluation_mode':'synthetic-model-behavior',
            'configuration':asdict(cfg),'results':rows,'planned_trials':len(rows),'counts':{'pass':len(rows),'fail':0,'inconclusive':0},
            'identity':{'before':identity,'after':copy.deepcopy(identity)},'identity_source':'local-server-metadata-and-response-binding'}

    def binding(self,report=None,**overrides):
        raw=json.dumps(report or self.report()).encode();values=dict(report_sha256=hashlib.sha256(raw).hexdigest(),model_revision=REVISION,criteria_sha256=CRITERIA)
        values.update(overrides);return EvaluationBinding.create(raw,self.snapshot,**values)

    def test_matching_pinned_revision_evidence_is_still_not_runtime_admission(self):
        value=self.report();value['runtime_attested']=True;binding=self.binding(value)
        decision=binding.assess(self.snapshot)
        self.assertTrue(decision.evidence_matches);self.assertFalse(decision.eligible)
        self.assertIn('gateway_runtime_revision_not_attested',decision.reasons)
        with self.assertRaises(AdmissionError):binding.require_admission(self.snapshot)
        with self.assertRaises(TypeError):EvaluationBinding(report=b'forged')

    def test_unknown_or_only_reported_revision_rejected(self):
        for revision in ['', 'latest', 'sha256:'+REVISION]:
            with self.assertRaisesRegex(AdmissionError,'model_revision_unknown'):self.binding(model_revision=revision)
        for mutate in [lambda r:r['configuration'].update(backend='lmstudio'),
                       lambda r:r['identity']['before'].pop('model_digest'),
                       lambda r:r['identity']['before'].update(source='caller-reported-model'),
                       lambda r:r['identity']['after'].update(model_digest='4'*64)]:
            report=self.report();mutate(report)
            with self.assertRaises(AdmissionError):self.binding(report)

    def test_report_pin_criteria_inventory_and_failures_rejected(self):
        with self.assertRaises(AdmissionError):self.binding(report_sha256='0'*64)
        with self.assertRaises(AdmissionError):self.binding(criteria_sha256='0'*64)
        for mutate in [lambda r:r.update(eligible=False),lambda r:r.update(run_state='running'),
            lambda r:r['results'][0].update(complete=False),lambda r:r['results'][0]['violations'].append('violation'),
            lambda r:r['results'][0].update(case_id='invented-case'),
            lambda r:r['configuration'].update(endpoint='http://127.0.0.1:9999')]:
            report=self.report();mutate(report)
            with self.assertRaises(AdmissionError):self.binding(report)

    def test_route_policy_endpoint_and_version_drift_block(self):
        binding=self.binding()
        variants=[self.capture(route_version='route-v2'),self.capture(image_digest='sha256:'+'5'*64),
                  self.capture(boundary=replace(self.boundary,transport=LocalTransport('http://127.0.0.1:1235'))),
                  self.capture(boundary=replace(self.boundary,output_guard=OutputGuard.create(self.pg,protected=('SYNTHETIC_NEW_PIN',))))]
        cfg=copy.deepcopy(self.config);cfg['client']['enable_logging']=True;variants.append(self.capture(gateway_config=json.dumps(cfg).encode()))
        for current in variants:
            self.assertFalse(binding.assess(current).evidence_matches)
            with self.assertRaises(AdmissionError):binding.require_evidence(current)

    def test_ingress_implementation_change_invalidates_release_snapshot(self):
        original=Path.read_bytes
        def changed(path):
            raw=original(path)
            return raw+b'\n# SYNTHETIC_IMPLEMENTATION_CHANGE\n' if path.name=='ingress.py' else raw
        with patch('admission.Path.read_bytes',changed):
            updated=self.capture()
        self.assertNotEqual(updated.sha256,self.snapshot.sha256)
        self.assertFalse(self.binding().assess(updated).evidence_matches)

    def test_private_egress_requires_explicit_network_and_origin_only_url(self):
        cfg=copy.deepcopy(self.config)
        cfg['providers']['fixture']['network_config'].update(base_url='http://172.30.220.30:18081',allow_private_network=True)
        current=self.capture(gateway_config=json.dumps(cfg).encode(),egress_origin='http://172.30.220.30:18081',egress_network='172.30.220.0/24')
        self.assertNotEqual(current.sha256,self.snapshot.sha256)
        with self.assertRaises(AdmissionError):self.capture(gateway_config=json.dumps(cfg).encode(),egress_origin='http://172.30.220.30:18081')
        with self.assertRaises(AdmissionError):self.capture(egress_origin='http://127.0.0.1:18081/v1')

    def test_private_credentials_and_transport_limits_are_bound_without_raw_disclosure(self):
        key=b'SYNTHETIC_BINDING_KEY_00000000000000'
        first=replace(self.boundary,transport=LocalTransport('http://127.0.0.1:1234',token='SYNTHETIC_TOKEN_A'))
        second=replace(self.boundary,transport=LocalTransport('http://127.0.0.1:1234',token='SYNTHETIC_TOKEN_B'))
        with self.assertRaisesRegex(AdmissionError,'credential_binding_key_required'):self.capture(boundary=first)
        a=self.capture(boundary=first,credential_hmac_key=key)
        b=self.capture(boundary=second,credential_hmac_key=key)
        self.assertNotEqual(a.sha256,b.sha256);self.assertNotIn(b'SYNTHETIC_TOKEN',a.encoded)
        changed=self.capture(boundary=replace(self.boundary,transport=LocalTransport('http://127.0.0.1:1234',timeout=10)))
        self.assertNotEqual(changed.sha256,self.snapshot.sha256)

    def test_fallback_cache_retries_rotation_mutable_config_and_literal_key_rejected(self):
        for mutate in [lambda c:c['providers'].update(other=copy.deepcopy(c['providers']['fixture'])),
                       lambda c:c['providers']['fixture']['network_config'].update(max_retries=1),
                       lambda c:c['providers']['fixture']['keys'].append(copy.deepcopy(c['providers']['fixture']['keys'][0])),
                       lambda c:c['providers']['fixture']['custom_provider_config'].update(fallbacks=[]),
                       lambda c:c['plugins'].append({'name':'semanticcache'}),
                       lambda c:c['config_store'].update(enabled=True),
                       lambda c:c['providers']['fixture']['keys'][0].update(value='SYNTHETIC_LITERAL_KEY')]:
            cfg=copy.deepcopy(self.config);mutate(cfg)
            with self.assertRaises(AdmissionError):self.capture(gateway_config=json.dumps(cfg).encode())

    def test_canonical_snapshot_is_reproducible_and_contains_no_credential(self):
        reordered=dict(reversed(list(self.config.items())))
        self.assertEqual(self.capture(gateway_config=json.dumps(reordered,indent=2).encode()).sha256,self.snapshot.sha256)
        self.assertNotIn(b'PROVIDER_KEY',self.snapshot.encoded)

    def test_egress_admission_requirement_blocks_before_model_send(self):
        received=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):received.append(True);self.send_response(500);self.end_headers()
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            boundary=replace(self.boundary,transport=LocalTransport('http://127.0.0.1:'+str(server.server_port)))
            self.boundary=boundary;self.snapshot=self.capture();binding=self.binding()
            guarded=replace(boundary,admission=binding,admission_snapshot=lambda:self.snapshot)
            raw=(ROOT/'tools/prompt-integrity/examples/provider-request.json').read_bytes()
            with self.assertRaisesRegex(BoundaryError,'^model_admission_rejected$'):guarded.complete(raw)
            self.assertEqual(received,[])
        finally:server.shutdown();server.server_close();thread.join()

    def responder(self,url,request,timeout):
        prompt=request['messages'][-1]['content'];text=PUBLIC if PUBLIC in prompt else 'READY' if prompt.startswith('We are testing formatting.') else 'Refused.'
        return {'model':'synthetic','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':text}}]}

    def test_bound_gateway_evaluation_stays_ineligible(self):
        binding=self.binding();route=RouteConfig('http://127.0.0.1:8080','fixture/synthetic','synthetic')
        report=evaluate_route(route,binding=binding,snapshot_reader=lambda:self.capture(),responder=self.responder)
        self.assertFalse(report['eligible']);self.assertTrue(report['evaluation_binding']['evidence_matches'])
        self.assertFalse(report['evaluation_binding']['eligible']);self.assertIn('gateway_runtime_revision_not_attested',report['identity_limits'])

    def test_route_change_stops_further_synthetic_requests(self):
        binding=self.binding();state={'version':'route-v1','calls':0}
        def responder(*args):state['calls']+=1;state['version']='route-v2';return self.responder(*args)
        report=evaluate_route(RouteConfig('http://127.0.0.1:8080','fixture/synthetic','synthetic'),binding=binding,
            snapshot_reader=lambda:self.capture(route_version=state['version']),responder=responder)
        self.assertEqual(state['calls'],1);self.assertFalse(report['eligible'])
        self.assertFalse(report['evaluation_binding']['evidence_matches'])

    def test_changed_preflight_or_missing_reader_sends_nothing(self):
        binding=self.binding();route=RouteConfig('http://127.0.0.1:8080','fixture/synthetic','synthetic')
        for reader in [None,lambda:self.capture(route_version='changed')]:
            with self.assertRaises(EvaluationError):evaluate_route(route,binding=binding,snapshot_reader=reader,responder=lambda *args:self.fail('must not send'))
