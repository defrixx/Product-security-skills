"""Synthetic streaming/tool contracts; no real tool side effects or model data."""
from pathlib import Path
from dataclasses import replace
import copy,http.client,http.server,json,sys,threading,time,unittest
ROOT=Path(__file__).resolve().parents[1]
for folder in ['integrations/bifrost','tools/prompt-guard/src','tools/prompt-integrity/src']:sys.path.insert(0,str(ROOT/folder))
from client import LocalTransport,BoundaryError
from agent_boundary import AgentBoundary,BufferedSSE,decode_sse
from ingress import IngressServer
from tool_gate import ToolGate,ToolGateError
from prompt_guard import OutputGuard,policy_from_dict as pg_policy
from prompt_integrity import policy_from_dict as pi_policy,verify_and_send,IntegrityError
SCHEMA={'type':'object','properties':{'record_id':{'type':'string','enum':['synthetic-record'],'maxLength':64}},'required':['record_id'],'additionalProperties':False}
TOOL={'type':'function','function':{'name':'read_record','description':'Read an authorized synthetic record.','parameters':SCHEMA}}
TOKEN='SYNTHETIC_AGENT_FRONT_TOKEN_0000001'


def fixture(stream=False,provider=False):
    base=json.loads((ROOT/'integrations/bifrost/integrity-baseline.json').read_text())
    base.update(adapter_id='openai-provider-agent-v1' if provider else 'bifrost-chat-agent-v1',allowed_targets={'primary':'synthetic' if provider else 'fixture/synthetic'})
    base['data_message_policy']['roles']=['user','assistant','tool']
    options={'temperature':0,'max_completion_tokens' if provider else 'max_tokens':64,'tools':[copy.deepcopy(TOOL)]}
    if stream or not provider:options['stream']=stream
    base['allowed_request_fields']=options
    request={'model':base['allowed_targets']['primary'],'messages':[{'role':'system','content':base['trusted_messages'][0]['text']},{'role':'user','content':'hello'}],**options}
    return base,request


def message(content='READY',calls=None):
    msg={'role':'assistant','content':content,'refusal':None}
    if calls:msg['tool_calls']=calls
    return {'model':'synthetic','choices':[{'finish_reason':'tool_calls' if calls else 'stop','message':msg}]}


def call(identifier='c1',record='synthetic-record'):
    return {'id':identifier,'type':'function','function':{'name':'read_record','arguments':json.dumps({'record_id':record})}}


def sse(deltas,finish='stop',done=True):
    values=[{'model':'synthetic','choices':[{'index':0,'delta':delta,'finish_reason':None}]} for delta in deltas]
    values.append({'model':'synthetic','choices':[{'index':0,'delta':{},'finish_reason':finish}]})
    return b''.join(b'data: '+json.dumps(v).encode()+b'\n\n' for v in values)+(b'data: [DONE]\n\n' if done else b'')


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.sent=[];self.body=json.dumps(message()).encode();self.media='application/json';self.delay=0;outer=self
        class Model(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                outer.sent.append(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200);self.send_header('Content-Type',outer.media);self.send_header('Content-Length',str(len(outer.body)));self.end_headers()
                if outer.delay:time.sleep(outer.delay)
                try:self.wfile.write(outer.body)
                except OSError:pass
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.policy=pg_policy(json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text()))
        self.guard=OutputGuard.create(self.policy,tools={'read_record':SCHEMA})

    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()

    def boundary(self,stream=False,provider=False,timeout=2):
        base,request=fixture(stream,provider)
        return AgentBoundary(pi_policy(base,'synthetic-support','1'),'primary',self.policy,self.guard,LocalTransport('http://127.0.0.1:'+str(self.server.server_port),timeout)),request

    def test_json_tool_indices_must_match_position_and_boolean_is_rejected(self):
        boundary,request=self.boundary()
        for index in [0,True,1,-1]:
            value=message('',[call()]);value['choices'][0]['message']['tool_calls'][0]['index']=index
            self.body=json.dumps(value).encode()
            if type(index) is int and index==0:self.assertIn('tool_calls',boundary.complete(json.dumps(request).encode())['choices'][0]['message'])
            else:
                with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())

    def test_observer_distinguishes_gateway_from_final_provider(self):
        for provider in [False,True]:
            boundary,request=self.boundary(provider=provider);events=[]
            replace(boundary,observer=events.append).complete(json.dumps(request).encode())
            self.assertEqual(events[0]['event'],'verified_provider_bytes' if provider else 'verified_gateway_bytes')
            self.assertEqual(set(events[0]),{'event','sha256'})

    def test_tool_schema_disagreement_is_configuration_error(self):
        base,_=fixture();base['allowed_request_fields']['tools'][0]['function']['parameters']['properties']['record_id']['enum']=['other']
        with self.assertRaises(BoundaryError):AgentBoundary(pi_policy(base,'synthetic-support','1'),'primary',self.policy,self.guard,LocalTransport('http://127.0.0.1:'+str(self.server.server_port)))

    def test_nonstream_tool_proposal_checked_never_executed(self):
        self.body=json.dumps(message('',[call()])).encode();boundary,request=self.boundary()
        result=boundary.complete(json.dumps(request).encode());self.assertEqual(result['choices'][0]['message']['tool_calls'][0]['function']['name'],'read_record')
        self.assertEqual(len(self.sent),1)

    def test_fragmented_stream_and_tools_reassembled_before_release(self):
        chunks=[{'role':'assistant','content':'REA','refusal':None},{'content':'DY','tool_calls':[{'index':0,'id':'c1','type':'function','function':{'name':'read_','arguments':'{"record_'}}]},
                {'tool_calls':[{'index':0,'function':{'name':'record','arguments':'id":"synthetic-record"}'}}]}]
        self.body=sse(chunks,'tool_calls');self.media='text/event-stream';boundary,request=self.boundary(True)
        result=boundary.complete(json.dumps(request).encode());self.assertIs(type(result),BufferedSSE)
        value,_=decode_sse(result.body)
        self.assertEqual(value['content'],'READY');self.assertEqual(value['tool_calls'][0]['arguments'],{'record_id':'synthetic-record'})
        self.assertEqual(len(self.sent),1)

    def test_secret_split_over_stream_chunks_is_not_released(self):
        self.body=sse([{'content':'SYNTHETIC_PRIVATE_'},{'content':'TOKEN_19'}]);self.media='text/event-stream'
        boundary,request=self.boundary(True)
        with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())

    def test_reasoning_checked_and_removed_in_stream(self):
        self.body=sse([{'content':'READY','reasoning':'Synthetic ','reasoning_content':'Synthetic '},{'reasoning':'notes.','reasoning_content':'notes.'}]);self.media='text/event-stream'
        boundary,request=self.boundary(True);result=boundary.complete(json.dumps(request).encode())
        self.assertNotIn(b'Synthetic notes.',result.body);self.assertNotIn(b'reasoning',result.body)
        self.body=sse([{'content':'READY','reasoning':'SYNTHETIC_PRIVATE_TOKEN_19'}])
        with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())

    def test_incomplete_malformed_opaque_and_bad_tools_fail_closed(self):
        boundary,request=self.boundary(True);self.media='text/event-stream'
        variants=[sse([{'content':'safe'}],done=False),sse([{'content':'safe'}],finish='length'),
            sse([{'content':'safe','unknown':'private'}]),sse([{'content':'safe','reasoning_details':[{'index':0,'type':'reasoning.encrypted','data':'opaque'}]}]),
            sse([{'tool_calls':[{'index':0,'id':'c1','function':{'name':'read_record','arguments':'{"record_id":"outside"}'}}]}],'tool_calls')]
        for raw in variants:
            self.body=raw
            with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())

    def test_stream_reasoning_details_requires_list_even_when_empty(self):
        boundary,request=self.boundary(True);self.media='text/event-stream'
        for value in [{},'', 'not-a-list',None,False,0]:
            with self.subTest(value=value):
                self.body=sse([{'content':'READY','reasoning_details':value}])
                with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())
        self.body=sse([{'content':'READY','reasoning_details':[]}])
        self.assertIs(type(boundary.complete(json.dumps(request).encode())),BufferedSSE)

    def test_terminal_usage_error_frame_blocks_complete_stream(self):
        boundary,request=self.boundary(True);self.media='text/event-stream'
        safe=sse([{'content':'READY'}])
        for error in [{'message':'synthetic failure'},None,{},'']:
            frame=b'data: '+json.dumps({'model':'synthetic','choices':[],'usage':{},'error':error}).encode()+b'\n\n'
            self.body=safe.replace(b'data: [DONE]',frame+b'data: [DONE]')
            with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())
        self.body=safe.replace(b'data: [DONE]',b'data: {"model":"synthetic","choices":[],"usage":{}}\n\ndata: [DONE]')
        self.assertIs(type(boundary.complete(json.dumps(request).encode())),BufferedSSE)

    def test_stream_timeout_and_resource_limits(self):
        self.body=sse([{'content':'safe'}]);self.media='text/event-stream';self.delay=.15
        boundary,request=self.boundary(True,timeout=.05)
        with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())
        self.delay=0;self.body=b'x'*1048577
        with self.assertRaises(BoundaryError):boundary.complete(json.dumps(request).encode())

    def test_http_headers_and_bytes_not_released_before_stream_approval(self):
        self.body=sse([{'content':'READY'}]);self.media='text/event-stream';self.delay=.2
        boundary,request=self.boundary(True);front=IngressServer(('127.0.0.1',0),boundary,TOKEN)
        thread=threading.Thread(target=front.serve_forever,daemon=True);thread.start()
        try:
            import socket
            raw=json.dumps(request).encode();wire=socket.create_connection(('127.0.0.1',front.server_port));wire.settimeout(.08)
            wire.sendall(b'POST /v1/chat/completions HTTP/1.0\r\nAuthorization: Bearer '+TOKEN.encode()+b'\r\nContent-Type: application/json\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw)
            with self.assertRaises(socket.timeout):wire.recv(1)
            wire.settimeout(3);response=b''
            while True:
                chunk=wire.recv(65536)
                if not chunk:break
                response+=chunk
            wire.close();self.assertIn(b'text/event-stream',response);self.assertIn(b'READY',response)
        finally:front.shutdown();front.server_close();thread.join()

    def test_stream_cache_hint_is_exact_and_routing_headers_still_rejected(self):
        self.body=sse([{'content':'READY'}]);self.media='text/event-stream'
        boundary,request=self.boundary(True);front=IngressServer(('127.0.0.1',0),boundary,TOKEN)
        thread=threading.Thread(target=front.serve_forever,daemon=True);thread.start()
        try:
            for extra,expected in [({'Cache-Control':'no-cache'},200),({'Cache-Control':'public'},400),({'X-Bf-Provider':'other'},400)]:
                connection=http.client.HTTPConnection('127.0.0.1',front.server_port,timeout=3)
                connection.request('POST','/v1/chat/completions',json.dumps(request),{'Content-Type':'application/json','Authorization':'Bearer '+TOKEN,**extra})
                response=connection.getresponse();self.assertEqual(response.status,expected);response.read();connection.close()
            self.assertEqual(len(self.sent),1)
        finally:front.shutdown();front.server_close();thread.join()

    def test_request_tamper_tool_history_and_exact_provider_wire(self):
        for provider in [False,True]:
            base,request=fixture(True,provider);policy=pi_policy(base,'synthetic-support','1');sent=[]
            class Wire:
                def send(self,alias,raw):sent.append(raw);return raw
            wire=verify_and_send(policy,request,'primary',Wire());self.assertEqual(json.loads(wire),request)
            for key,value in [('stream',False),('tools',[]),('extra',True)]:
                changed=copy.deepcopy(request);changed[key]=value
                with self.assertRaises(IntegrityError):verify_and_send(policy,changed,'primary',Wire())
            broken=copy.deepcopy(request);broken['messages'].append({'role':'tool','tool_call_id':'unknown','content':'untrusted'})
            with self.assertRaises(IntegrityError):verify_and_send(policy,broken,'primary',Wire())
            self.assertEqual(len(sent),1)


class ToolAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.policy=pg_policy(json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text()))
        self.guard=OutputGuard.create(self.policy,tools={'read_record':SCHEMA});self.gate=ToolGate(self.guard,self.policy);self.effects=[]
        self.executors={'read_record':lambda args,key:(self.effects.append((args,key)) or b'{"value":"synthetic"}')}

    def proposal(self,ids=('c1',)):
        return {'content':'','tool_calls':[{'id':i,'name':'read_record','arguments':{'record_id':'synthetic-record'}} for i in ids]}

    def test_fresh_authorization_one_shot_and_checked_results(self):
        batch=self.gate.prepare(self.proposal());calls=[]
        def auth(context,call,bid):calls.append((context,bid));call['arguments']['record_id']='tampered';return True
        outcome=self.gate.execute(batch,authorize=auth,executors=self.executors,context='synthetic-owner')
        self.assertEqual(len(calls),2);self.assertEqual(self.effects[0][0],{'record_id':'synthetic-record'})
        self.assertEqual(outcome.messages()[0]['role'],'tool')
        with self.assertRaises(ToolGateError):self.gate.execute(batch,authorize=auth,executors=self.executors,context='synthetic-owner')
        self.assertEqual(len(self.effects),1)

    def test_entire_batch_authorized_before_any_effect(self):
        batch=self.gate.prepare(self.proposal(('c1','c2')))
        with self.assertRaises(ToolGateError):self.gate.execute(batch,authorize=lambda ctx,c,b:c['id']=='c1',executors=self.executors,context='owner')
        self.assertEqual(self.effects,[])

    def test_revocation_stops_later_effects_and_reports_partial_completion(self):
        batch=self.gate.prepare(self.proposal(('c1','c2')));count=[0]
        def auth(*args):count[0]+=1;return count[0]<4
        with self.assertRaises(ToolGateError) as caught:self.gate.execute(batch,authorize=auth,executors=self.executors,context='owner')
        self.assertEqual(caught.exception.completed,1);self.assertEqual(len(self.effects),1)

    def test_failure_is_not_retried_and_unknown_effect_is_explicit(self):
        batch=self.gate.prepare(self.proposal())
        def effect(args,key):self.effects.append(key);raise RuntimeError('private')
        with self.assertRaises(ToolGateError) as caught:self.gate.execute(batch,authorize=lambda *args:True,executors={'read_record':effect},context='owner')
        self.assertEqual(caught.exception.attempted,1);self.assertEqual(caught.exception.completed,0)
        self.assertTrue(caught.exception.effects_may_have_occurred);self.assertEqual(len(self.effects),1)

    def test_unknown_schema_missing_executor_and_secret_result(self):
        bad=self.proposal();bad['tool_calls'][0]['arguments']['record_id']='outside'
        with self.assertRaises(ToolGateError):self.gate.prepare(bad)
        batch=self.gate.prepare(self.proposal())
        with self.assertRaises(ToolGateError):self.gate.execute(batch,authorize=lambda *args:True,executors={},context='owner')
        self.assertEqual(self.effects,[])
        batch=self.gate.prepare(self.proposal(('c2',)))
        with self.assertRaises(ToolGateError) as caught:self.gate.execute(batch,authorize=lambda *args:True,executors={'read_record':lambda a,k:b'"SYNTHETIC_PRIVATE_TOKEN_19"'},context='owner')
        self.assertEqual(caught.exception.completed,1)
