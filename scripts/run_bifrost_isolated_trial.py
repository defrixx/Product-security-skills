"""Temporary real-Bifrost three-network proof with a synthetic model oracle."""
import sys
if sys.flags.optimize:
 sys.stderr.write('optimized_python_not_supported: run without -O/PYTHONOPTIMIZE\n')
 raise SystemExit(2)

class TrialFailure(RuntimeError):
 """A required property failed; never records a passed trial."""

def require(condition, code):
 if not condition:
  raise TrialFailure(code)

from pathlib import Path
import argparse,base64,hashlib,http.client,ipaddress,json,secrets,subprocess,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--agent-profile',choices=['text','json','stream'],default='text')
args=parser.parse_args()
AGENT=args.agent_profile
OUT=args.output;OUT.mkdir(parents=True,exist_ok=False,mode=0o700)
WORK_CONTEXT=tempfile.TemporaryDirectory(prefix='bifrost-isolated-trial-')
WORK=Path(WORK_CONTEXT.name)
REF='docker.io/maximhq/bifrost@sha256:5197ad08ddd34b3a60ac2c548cb84945f106e9ec49d549b644e4491debf75f53'
RUN_ID=secrets.token_hex(6)
LABEL_VALUE='bifrost-isolated-'+RUN_ID;LABEL='pss.task='+LABEL_VALUE;PREFIX='pss-'+RUN_ID+'-'
FRONT_TOKEN='SYNTHETIC_FRONT_ACCESS_TOKEN_000001';EGRESS_TOKEN='SYNTHETIC_PROVIDER_ACCESS_TOKEN_0001';SYSTEM='Reply exactly READY with no explanation.'
containers=[];networks=[];record={'resource_label':LABEL,'owned_containers':containers,'owned_networks':networks,'image':REF,'tests':[],'backend':'synthetic model oracle; gateway is the real official Bifrost v2.4.0','success':False,'agent_profile':AGENT}
def persist():
 temporary=OUT/'evidence.tmp'
 temporary.write_text(json.dumps(record,indent=2)+'\n')
 temporary.replace(OUT/'evidence.json')
persist()
def run(*args,stdin=None):
 return subprocess.check_output(['docker',*args],input=stdin.encode() if stdin is not None else None,stderr=subprocess.STDOUT,timeout=45).decode().strip()
def start(role,network,ip=None,publish=False,bifrost=False):
 name=PREFIX+role;args=['run','--detach','--pull=never','--name',name,'--label',LABEL,'--network',network,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','256','--memory','1g','--cpus','1','--tmpfs','/tmp:rw,nosuid,nodev,size=64m']
 if ip:args+=['--ip',ip]
 if publish:args+=['-p','127.0.0.1::18080']
 if bifrost:
  args+=['--platform','linux/arm64','--user','1000:0','--tmpfs','/app/data:rw,noexec,nosuid,nodev,size=64m,uid=1000,gid=0,mode=0700',
    '--mount','type=bind,source='+str(WORK/'config.json')+',target=/fixture-config.json,readonly','--mount','type=bind,source='+str(WORK/'empty.json')+',target=/fixture-empty.json,readonly',
    '--entrypoint','/bin/sh',REF,'-c','cp /fixture-config.json /app/data/config.json && exec /app/main -app-dir /app/data -host 0.0.0.0 -port 8080 -log-level warn -log-style json']
 else:
  args+=['--mount','type=bind,source='+str(ROOT)+',target=/repo,readonly','--mount','type=bind,source='+str(ROOT/'tests/bifrost_isolated_fixture.py')+',target=/fixture.py,readonly',
         '--mount','type=bind,source='+str(ROOT/'tests/bifrost_request_probe.py')+',target=/probe.py,readonly',PYTHON_RUNTIME,'python','/fixture.py',role,GW,MODEL,AGENT]
 # Record the owned name before run so even a partially created failed start is cleaned.
 containers.append(name);persist();run(*args);return name

def probe(container,host,port,data=None):
 raw=run('exec','-i',container,'python','/probe.py',host,str(port),stdin=json.dumps(data or {}));return json.loads(raw)
def json_body(value):return json.loads(base64.b64decode(value['body']))
def metrics():return json_body(probe(model,'127.0.0.1',18082,{'path':'/metrics'}))
def host_call(request,token=FRONT_TOKEN,path='/v1/chat/completions'):
 c=http.client.HTTPConnection('127.0.0.1',front_port,timeout=20)
 try:
  c.request('POST',path,json.dumps(request),{'Content-Type':'application/json','Authorization':'Bearer '+token});r=c.getresponse();return r.status,r.read()
 finally:c.close()
def case(name,**values):record['tests'].append({'case':name,'status':'passed',**values});persist();print(json.dumps(record['tests'][-1]),flush=True)
try:
 # Pre-provisioned images only; never start Docker or download software.
 run('image','inspect',REF)
 PYTHON_RUNTIME=json.loads(run('image','inspect','python:3.11-slim'))[0]['Id']
 record['python_image_id']=PYTHON_RUNTIME
 existing=json.loads(run('network','inspect',*run('network','ls','-q').split()))
 used=[ipaddress.ip_network(c['Subnet']) for n in existing for c in (n.get('IPAM',{}).get('Config') or []) if c.get('Subnet')]
 candidates=[ipaddress.ip_network('172.30.'+str(n)+'.0/24') for n in range(220,250)]+[ipaddress.ip_network('192.168.'+str(n)+'.0/24') for n in range(220,250)]
 available=[n for n in candidates if not any(n.version==u.version and n.overlaps(u) for u in used)]
 require(len(available)>=2, 'trial_check_01');GW=str(available[0].network_address).rsplit('.',1)[0];MODEL=str(available[1].network_address).rsplit('.',1)[0]
 gw_net=PREFIX+'gateway-net';model_net=PREFIX+'model-net';front_net=PREFIX+'front-net'
 for name,cidr,internal in [(gw_net,GW+'.0/24',True),(model_net,MODEL+'.0/24',True),(front_net,None,False)]:
  args=['network','create','--label',LABEL]
  if cidr:args+=['--subnet',cidr]
  if internal:args+=['--internal']
  args+=[name];networks.append(name);persist();run(*args)
 config={'config_store':{'enabled':False},'logs_store':{'enabled':False},'client':{'enable_logging':False,'disable_content_logging':True,'dump_errors_in_console_logs':False},'plugins':[],
 'framework':{'pricing':{'pricing_url':'file:///fixture-empty.json','model_parameters_url':'file:///fixture-empty.json','mcp_library_sync_interval':0}},
 'providers':{'fixture':{'custom_provider_config':{'base_provider_type':'openai'},'network_config':{'base_url':'http://'+GW+'.30:18081','allow_private_network':True,'max_retries':0,'default_request_timeout_in_seconds':5},'keys':[{'name':'synthetic-egress','value':EGRESS_TOKEN,'models':['*'],'weight':1}]}}}
 (WORK/'config.json').write_text(json.dumps(config));(WORK/'empty.json').write_text('{}\n');(OUT/'config.json').write_text(json.dumps(config,indent=2))
 model=start('model',model_net,MODEL+'.10');egress=start('egress',gw_net,GW+'.30');run('network','connect','--ip',MODEL+'.20',model_net,egress)
 gateway=start('gateway',gw_net,GW+'.10',bifrost=True)
 front=start('front',front_net,publish=True);run('network','connect','--ip',GW+'.20',gw_net,front)
 for attempt in range(100):
  value=probe(egress,GW+'.10',8080)
  if value.get('status')==200:break
  time.sleep(.2)
 else:raise RuntimeError('gateway_not_healthy')
 info=json.loads(run('inspect',front))[0];bindings=info['NetworkSettings']['Ports']['18080/tcp'];require(len(bindings)==1 and bindings[0]['HostIp']=='127.0.0.1', 'trial_check_02');front_port=int(bindings[0]['HostPort'])
 gateway_info=json.loads(run('inspect',gateway))[0];require(not any(gateway_info['NetworkSettings']['Ports'].values()), 'trial_check_03');require(set(gateway_info['NetworkSettings']['Networks'])=={gw_net}, 'trial_check_04')
 model_info=json.loads(run('inspect',model))[0];require(not any(model_info['NetworkSettings']['Ports'].values()), 'trial_check_05');require(set(model_info['NetworkSettings']['Networks'])=={model_net}, 'trial_check_06')
 record['topology']={'gateway_network':GW+'.0/24','model_network':MODEL+'.0/24','gateway_and_model_networks_internal':True,'gateway_ports_published':False,'model_ports_published':False,'front_host_binding':bindings}
 request={'model':'fixture/synthetic','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'hello'}],'stream':False,'temperature':0,'max_tokens':64,'tools':[]}
 if AGENT!='text':
  schema={'type':'object','properties':{'record_id':{'type':'string','enum':['synthetic-record'],'maxLength':64}},'required':['record_id'],'additionalProperties':False}
  request['tools']=[{'type':'function','function':{'name':'read_record','description':'Read an authorized synthetic record.','parameters':schema}}]
  request['stream']=AGENT=='stream'
 def checked_message(raw):
  if AGENT=='stream':
   sys.path[:0]=[str(ROOT/'integrations/bifrost'),str(ROOT/'tools/prompt-guard/src'),str(ROOT/'tools/prompt-integrity/src')]
   from agent_boundary import decode_sse
   return decode_sse(raw)[0]
  from_json=json.loads(raw)['choices'][0]['message']
  for call in from_json.get('tool_calls',[]):call.pop('index',None)
  if AGENT=='text':return from_json
  sys.path[:0]=[str(ROOT/'tools/prompt-guard/src')]
  from prompt_guard.provider_output import canonical_response
  return canonical_response({'choices':[{'message':from_json,'finish_reason':'tool_calls'}]},'openai')
 before=len(metrics()['received']);status,raw=host_call(request)
 if status!=200:
  record['failure_diagnostics']={'direct_gateway':probe(front,GW+'.10',8080,{'method':'POST','path':'/v1/chat/completions','body':json.dumps(request),'headers':{'Content-Type':'application/json'}})}
 require(status==200, 'trial_check_07');require(checked_message(raw)['content']=='READY' and b'reasoning' not in raw, 'trial_check_08')
 observed=metrics()['received'];require(len(observed)==before+1, 'trial_check_09')
 audits=[json.loads(line) for line in run('exec',egress,'cat','/tmp/audit.jsonl').splitlines()];require(audits[-1]['sha256']==observed[-1]['sha256'], 'trial_check_10');require(observed[-1]['system_matches'] and observed[-1]['max_completion_tokens']==64, 'trial_check_11')
 case('real_gateway_private_ingress_and_final_provider_checked_bytes',model_requests=1,oracle_sha256=observed[-1]['sha256'],verified_sha256=audits[-1]['sha256'])
 if AGENT!='text':
  sys.path[:0]=[str(ROOT/'integrations/bifrost'),str(ROOT/'tools/prompt-guard/src'),str(ROOT/'tools/prompt-integrity/src')]
  proposal=checked_message(raw)
  require(proposal['tool_calls'][0]['arguments']=={'record_id':'synthetic-record'},'checked_tool_arguments')
  from prompt_guard import policy_from_dict,OutputGuard
  from tool_gate import ToolGate,ToolGateError
  guard=OutputGuard.create(policy_from_dict(json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text())),tools={'read_record':schema})
  gate=ToolGate(guard,guard.policy);effects=[]
  def execute(arguments,key):effects.append(key);return b'{"record":"synthetic public fixture"}'
  denied=gate.prepare(proposal)
  try:gate.execute(denied,authorize=lambda *a:False,executors={'read_record':execute},context=None)
  except ToolGateError:pass
  else:raise TrialFailure('tool_authorization_missing')
  require(not effects,'denied_tool_had_effect')
  # A separate workflow allows the same provider ID, with one explicit authorization.
  gate=ToolGate(guard,guard.policy);approved=gate.prepare(proposal)
  outcome=gate.execute(approved,authorize=lambda *a:True,executors={'read_record':execute},context={'synthetic':True})
  require(len(effects)==1,'authorized_effect_count')
  try:gate.execute(approved,authorize=lambda *a:True,executors={'read_record':execute},context=None)
  except ToolGateError:pass
  else:raise TrialFailure('tool_replay_allowed')
  assistant={'role':'assistant','content':proposal['content'],'tool_calls':[{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':json.dumps(c['arguments'])}} for c in proposal['tool_calls']]}
  follow={**request,'messages':[*request['messages'],assistant,*outcome.messages()]}
  before=len(metrics()['received']);status,raw=host_call(follow)
  if status!=200:record['tool_round_failure']={'status':status,'response':raw.decode(errors='replace')};persist()
  require(status==200 and checked_message(raw)['content']=='READY' and not checked_message(raw).get('tool_calls') and len(metrics()['received'])==before+1,'tool_result_round_trip')
  case('explicit_authorization_checked_tool_result_round_trip_no_replay',effects=1,model_requests=1)
 for label,changes,token,path in [('auth',{},'wrong','/v1/chat/completions'),('unsupported_path',{},FRONT_TOKEN,'/v1/responses'),('stream',{'stream':not request['stream']},FRONT_TOKEN,'/v1/chat/completions'),('fallback',{'fallbacks':[]},FRONT_TOKEN,'/v1/chat/completions')]:
  body={**request,**changes};before=len(metrics()['received']);status,_=host_call(body,token,path);require(status!=200 and len(metrics()['received'])==before, 'trial_check_14');case('ingress_'+label+'_zero_model_calls',http_status=status)
 # Untrusted peer has ONLY the front network, not the gateway/model networks.
 peer_code="import socket,json,sys;out={};\nfor host,port,label in [(sys.argv[1],8080,'gateway'),(sys.argv[2],18082,'model')]:\n try:\n  s=socket.create_connection((host,port),timeout=2);s.close();out[label]='reachable'\n except OSError:out[label]='blocked'\nprint(json.dumps(out))"
 peer=json.loads(run('run','--rm','--pull=never','--network',front_net,'--read-only','--cap-drop','ALL',PYTHON_RUNTIME,'python','-c',peer_code,GW+'.10',MODEL+'.10'))
 require(peer=={'gateway':'blocked','model':'blocked'}, 'trial_check_12');case('untrusted_front_peer_cannot_bypass_gateway_or_model',**peer)
 # Direct callers cannot choose provider credentials or an unapproved model.
 provider_request={'model':'synthetic','messages':request['messages'],'temperature':0,'max_completion_tokens':64}
 if AGENT!='text':
  provider_request['tools']=request['tools']
  if AGENT=='stream':provider_request.update(stream=True,stream_options={'include_usage':True})
 for label,token,changes in [('auth','wrong',{}),('model',EGRESS_TOKEN,{'model':'other'}),('extra_field',EGRESS_TOKEN,{'fallbacks':[]})]:
  before=len(metrics()['received']);reply=probe(front,GW+'.30',18081,{'method':'POST','path':'/v1/chat/completions','body':json.dumps({**provider_request,**changes}),'headers':{'Content-Type':'application/json','Authorization':'Bearer '+token}})
  require(reply.get('status')!=200 and len(metrics()['received'])==before, 'trial_check_15')
  case('egress_'+label+'_zero_model_calls',http_status=reply.get('status'))
 # A compromised/direct gateway request still cannot escape the mandatory final-wire service.
 final_request=dict(request) if AGENT!='text' else {k:v for k,v in request.items() if k!='tools'}
 for label,changes in [('altered_instruction',{'messages':[{'role':'system','content':SYSTEM+' changed'},{'role':'user','content':'hello'}]}),('altered_tokens',{'max_tokens':65}),('injected_tools',{'tools':[{'type':'function','function':{'name':'unapproved','description':'synthetic','parameters':{'type':'object'}}}]})]:
  before=len(metrics()['received']);body={**final_request,**changes};reply=probe(front,GW+'.10',8080,{'method':'POST','path':'/v1/chat/completions','body':json.dumps(body),'headers':{'Content-Type':'application/json'}})
  require(len(metrics()['received'])==before, 'trial_check_16');require(reply.get('status')!=200, 'trial_check_17');case('final_wire_'+label+'_zero_model_calls',gateway_http_status=reply.get('status'))
 bypass_code="import socket,json,sys\ntry:\n s=socket.create_connection((sys.argv[1],18082),timeout=2);s.close();print('reachable')\nexcept OSError:print('blocked')"
 # Gateway lacks Python, so a temporary cached-Python probe shares its exact namespace.
 direct=run('run','--rm','--pull=never','--network','container:'+gateway,'--read-only','--cap-drop','ALL',PYTHON_RUNTIME,'python','-c',bypass_code,MODEL+'.10');require(direct=='blocked', 'trial_check_13');case('gateway_namespace_cannot_reach_model_directly')
 for mode in (['secret','reasoning-secret','error']+(['bad-tool'] if AGENT!='text' else [])):
  probe(model,'127.0.0.1',18082,{'method':'POST','path':'/control','body':json.dumps({'mode':mode}),'headers':{'Content-Type':'application/json'}})
  before=len(metrics()['received']);status,raw=host_call(request);require(status!=200 and b'SYNTHETIC_PRIVATE_TOKEN_19' not in raw and len(metrics()['received'])==before+1, 'trial_check_18')
  case('provider_'+mode+'_blocked_without_retry',http_status=status,model_requests=1)
 record['success']=True
finally:
 for name in containers:
  try:
   (OUT/(name+'-inspect.json')).write_text(run('inspect',name));(OUT/(name+'-logs.txt')).write_text(run('logs',name))
  except Exception:pass
 for name in reversed(containers):
  found=subprocess.run(['docker','inspect',name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  if found.returncode==0 and json.loads(found.stdout)[0].get('Config',{}).get('Labels',{}).get('pss.task')==LABEL_VALUE:
   subprocess.run(['docker','rm','--force',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

 for name in reversed(networks):
  found=subprocess.run(['docker','network','inspect',name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  if found.returncode==0 and json.loads(found.stdout)[0].get('Labels',{}).get('pss.task')==LABEL_VALUE:
   subprocess.run(['docker','network','rm',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

 def remaining(*args):
  try:return run(*args)
  except Exception:return 'unknown: docker unavailable'
 record['cleanup']={'containers_remaining':remaining('ps','-a','--filter','label='+LABEL,'--format','{{.ID}}'),'networks_remaining':remaining('network','ls','--filter','label='+LABEL,'--format','{{.ID}}')}
 record['tests_passed']=record['success']
 record['success']=record['success'] and not any(record['cleanup'].values())
 WORK_CONTEXT.cleanup()
 persist();print(json.dumps({'success':record['success'],'evidence':str(OUT/'evidence.json'),'cleanup':record['cleanup']}),flush=True)

if not record['success']:raise SystemExit(1)
