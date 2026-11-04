"""Disposable deployment fixture. Model is synthetic; gateway is real Bifrost."""
import hashlib,http.server,io,json,os,sys,threading
from pathlib import Path
for f in ['integrations/bifrost','tools/prompt-guard/src','tools/prompt-integrity/src']:sys.path.insert(0,'/repo/'+f)
from client import GuardedClient,PrivateNetworkTransport
from ingress import IngressBoundary,IngressServer
from agent_boundary import AgentBoundary
from egress import ProviderBoundary
from integrity import GatewayIntegrity
from prompt_guard import policy_from_dict as pg_policy,OutputGuard
from prompt_integrity import policy_from_dict as pi_policy
role=sys.argv[1];GATEWAY=sys.argv[2];MODELNET=sys.argv[3]
AGENT=sys.argv[4] if len(sys.argv)>4 else 'text'
SCHEMA={'type':'object','properties':{'record_id':{'type':'string','enum':['synthetic-record'],'maxLength':64}},'required':['record_id'],'additionalProperties':False}
TOOL={'type':'function','function':{'name':'read_record','description':'Read an authorized synthetic record.','parameters':SCHEMA}}
SYSTEM='Reply exactly READY with no explanation.'
FRONT_TOKEN='SYNTHETIC_FRONT_ACCESS_TOKEN_000001';EGRESS_TOKEN='SYNTHETIC_PROVIDER_ACCESS_TOKEN_0001'

def baseline(kind):
 value=json.loads(Path('/repo/integrations/bifrost/integrity-baseline.json').read_text())
 value['trusted_messages'][0]['text']=SYSTEM
 if kind=='provider':value.update(adapter_id='openai-provider-text-v1',allowed_targets={'provider':'synthetic'},allowed_request_fields={'temperature':0,'max_completion_tokens':64})
 else:value['allowed_targets']={'gateway':'fixture/synthetic'};value['allowed_request_fields']['max_tokens']=64
 if AGENT!='text':
  value['adapter_id']='openai-provider-agent-v1' if kind=='provider' else 'bifrost-chat-agent-v1'
  value['data_message_policy']['roles']=['user','assistant','tool']
  value['allowed_request_fields']['tools']=[TOOL]
  if AGENT=='stream':
   value['allowed_request_fields']['stream']=True
   if kind=='provider':value['allowed_request_fields']['stream_options']={'include_usage':True}
 return value

if role=='model':
 state={'received':[],'mode':'safe'}
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   value=state if self.path=='/metrics' else {'data':[{'id':'synthetic','object':'model'}]}
   raw=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def do_POST(self):
   raw=self.rfile.read(int(self.headers['Content-Length']));obj=json.loads(raw)
   if self.path=='/control':state['mode']=obj['mode'];body=b'{}';status=200
   else:
    state['received'].append({'sha256':hashlib.sha256(raw).hexdigest(),'model':obj.get('model'),'fields':sorted(obj),'system_matches':obj.get('messages',[{}])[0].get('content')==SYSTEM,'max_completion_tokens':obj.get('max_completion_tokens')})
    mode=state['mode'];status=500 if mode=='error' else 200
    content='SYNTHETIC_PRIVATE_TOKEN_19' if mode=='secret' else 'READY'
    reasoning='SYNTHETIC_PRIVATE_TOKEN_19' if mode=='reasoning-secret' else 'Synthetic private deliberation.'
    tool_calls=[]
    if AGENT!='text' and obj['messages'][-1]['role']!='tool':
     tool_calls=[{'id':'c1','type':'function','function':{'name':'read_record','arguments':json.dumps({'record_id':'outside' if mode=='bad-tool' else 'synthetic-record'})}}]
    msg={'role':'assistant','content':content,'refusal':None,'reasoning':reasoning,'reasoning_content':reasoning,'reasoning_details':[{'index':0,'type':'reasoning.text','text':reasoning}]}
    if tool_calls:msg['tool_calls']=tool_calls
    value={'id':'chatcmpl-fixture','object':'chat.completion','created':0,'model':'synthetic','choices':[{'index':0,'finish_reason':'tool_calls' if tool_calls else 'stop','message':msg}]}
    body=json.dumps(value).encode()
    if AGENT=='stream':
     delta=dict(msg)
     if tool_calls:delta['tool_calls']=[{'index':i,**call} for i,call in enumerate(tool_calls)]
     frames=[{'model':'synthetic','object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]},
             {'model':'synthetic','object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':'tool_calls' if tool_calls else 'stop'}]}]
     body=b''.join(b'data: '+json.dumps(frame).encode()+b'\n\n' for frame in frames)+b'data: [DONE]\n\n'

   self.send_response(status);self.send_header('Content-Type','text/event-stream' if AGENT=='stream' and self.path!='/control' else 'application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 http.server.ThreadingHTTPServer(('0.0.0.0',18082),Handler).serve_forever()
else:
 policy=pg_policy(json.loads(Path('/repo/tools/prompt-guard/examples/policy.json').read_text()));output=OutputGuard.create(policy,tools={'read_record':SCHEMA} if AGENT!='text' else {})
 if role=='egress':
  def observe(value):
   with open('/tmp/audit.jsonl','a') as f:f.write(json.dumps(value)+'\n')
  if AGENT=='text':boundary=ProviderBoundary(pi_policy(baseline('provider'),'synthetic-support','1'),'provider',policy,output,
      PrivateNetworkTransport('http://'+MODELNET+'.10:18082',timeout=5,network_cidr=MODELNET+'.0/24'),observe)
  else:boundary=AgentBoundary(pi_policy(baseline('provider'),'synthetic-support','1'),'provider',policy,output,PrivateNetworkTransport('http://'+MODELNET+'.10:18082',timeout=5,network_cidr=MODELNET+'.0/24'),observer=observe)
  from ingress import _Handler
  class ObservedHandler(_Handler):
   def do_POST(self):
    print(json.dumps({'event':'provider_ingress_shape','path':self.path,'header_names':sorted(k.lower() for k in self.headers)}),flush=True)
    if AGENT!='text':
     body=self.rfile.read(int(self.headers.get('Content-Length','0')))
     print(json.dumps({'event':'synthetic_provider_request','request':json.loads(body)}),flush=True)
     self.rfile=io.BytesIO(body)
    super().do_POST()
  server=IngressServer(('0.0.0.0',18081),boundary,EGRESS_TOKEN,allow_network_listener=True)
  server.RequestHandlerClass=ObservedHandler
  server.serve_forever()
 elif role=='front':
  if AGENT=='text':client=GuardedClient('fixture/synthetic',policy,output,PrivateNetworkTransport('http://'+GATEWAY+'.10:8080',timeout=10,network_cidr=GATEWAY+'.0/24'),SYSTEM,
      GatewayIntegrity(pi_policy(baseline('gateway'),'synthetic-support','1'),'gateway'),reasoning_mode='inspect-and-drop')
  boundary=IngressBoundary(client) if AGENT=='text' else AgentBoundary(pi_policy(baseline('gateway'),'synthetic-support','1'),'gateway',policy,output,PrivateNetworkTransport('http://'+GATEWAY+'.10:8080',timeout=10,network_cidr=GATEWAY+'.0/24'))
  IngressServer(('0.0.0.0',18080),boundary,FRONT_TOKEN,allow_network_listener=True).serve_forever()
