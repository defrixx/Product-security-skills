"""Bounded buffered OpenAI chat, tool proposals, and final-wire dispatch.

No method here executes tools. Applications own history, authorization and effects.
"""
from dataclasses import dataclass,field
import hashlib,json,secrets,time
from client import BoundaryError,LocalTransport,PrivateNetworkTransport
from prompt_guard import OutputGuard,inspect
from prompt_guard.core import decode
from prompt_guard.provider_output import canonical_response,stream_response
from prompt_guard.schema import validate_schema
from prompt_integrity import FrozenPolicy,policy_from_dict,verify_and_send,IntegrityError
from prompt_integrity.agent import GATEWAY,PROVIDER
from reasoning import ReasoningOutput


def strings(value):
    if type(value) is str:return [value]
    if type(value) is list:return [text for child in value for text in strings(child)]
    if type(value) is dict:return [text for key,child in value.items() for text in [key,*strings(child)]]
    return []


@dataclass(frozen=True,repr=False)
class BufferedSSE:
    body: bytes=field(repr=False)


def encode_message(message,model,stream=False):
    calls=[{'id':call['id'],'type':'function','function':{'name':call['name'],
            'arguments':json.dumps(call['arguments'],ensure_ascii=False,separators=(',',':'))}}
           for call in message.get('tool_calls',[])]
    assistant={'role':'assistant','content':message['content']}
    if calls:assistant['tool_calls']=calls
    reason='tool_calls' if calls else 'stop'
    identity={'id':'chatcmpl-checked-'+secrets.token_hex(12),'created':int(time.time()),'model':model}
    if not stream:return {**identity,'object':'chat.completion','choices':[{'index':0,'message':assistant,'finish_reason':reason}]}
    delta=dict(assistant)
    if calls:delta['tool_calls']=[{'index':i,**call} for i,call in enumerate(calls)]
    first={**identity,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]}
    final={**identity,'object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':reason}]}
    body=b''.join(b'data: '+json.dumps(item,ensure_ascii=False).encode()+b'\n\n' for item in (first,final))+b'data: [DONE]\n\n'
    return BufferedSSE(body)


def decode_sse(raw,expected_model=None):
    """Normalize known empty metadata and collect, never release, reasoning."""
    if type(raw) is not bytes or len(raw)>1048576:raise BoundaryError('stream_resource_limit')
    parts=raw.replace(b'\r\n',b'\n').split(b'\n\n')
    if parts[-1].strip():raise BoundaryError('stream_incomplete')
    events=[];aliases={};details={}
    for record in parts[:-1]:
        lines=record.split(b'\n')
        if not all(not line or line.startswith((b'data:',b':')) for line in lines):raise BoundaryError('stream_invalid')
        data=[line[5:].lstrip(b' ') for line in lines if line.startswith(b'data:')]
        if not data:continue
        if len(events)>=4096:raise BoundaryError('stream_resource_limit')
        payload=b'\n'.join(data)
        if payload==b'[DONE]':events.append(b'data: [DONE]\n\n');continue
        value=decode(payload,1048576)
        if expected_model is not None and value.get('model')!=expected_model:raise BoundaryError('stream_model_mismatch')
        choices=value.get('choices')
        if type(choices) is list and len(choices)==1 and type(choices[0]) is dict:
            delta=choices[0].get('delta')
            if type(delta) is not dict:raise BoundaryError('stream_invalid')
            if 'refusal' in delta:
                if delta.pop('refusal') is not None:raise BoundaryError('stream_refusal')
            for key in ('reasoning','reasoning_content'):
                if key in delta:
                    text=delta.pop(key)
                    if text is not None:
                        if type(text) is not str:raise BoundaryError('stream_reasoning_invalid')
                        aliases[key]=aliases.get(key,'')+text
            incoming_details=delta.pop('reasoning_details',[])
            if type(incoming_details) is not list:raise BoundaryError('stream_reasoning_invalid')
            for item in incoming_details:
                if (type(item) is not dict or set(item)-{'index','type','id','text','summary'}
                        or type(item.get('index')) is not int or not 0<=item['index']<16):raise BoundaryError('stream_reasoning_invalid')
                index=item['index'];current=details.setdefault(index,{'index':index,'type':item.get('type')})
                if current['type']!=item.get('type'):raise BoundaryError('stream_reasoning_invalid')
                for key in ('id','text','summary'):
                    if key in item:
                        if type(item[key]) is not str:raise BoundaryError('stream_reasoning_invalid')
                        if key=='id':
                            if key in current and current[key]!=item[key]:raise BoundaryError('stream_reasoning_invalid')
                            current[key]=item[key]
                        else:current[key]=current.get(key,'')+item[key]
        events.append(b'data: '+json.dumps(value,ensure_ascii=False).encode()+b'\n\n')
    canonical=stream_response(events,'openai')
    return canonical,{**aliases,'reasoning_details':[details[i] for i in sorted(details)]}


@dataclass(frozen=True,repr=False)
class AgentBoundary:
    policy: FrozenPolicy=field(repr=False)
    target_alias: str
    input_policy: object=field(repr=False)
    output_guard: OutputGuard=field(repr=False)
    transport: object=field(repr=False)
    reasoning_mode: str='inspect-and-drop'
    admission: object=field(default=None,repr=False)
    admission_snapshot: object=field(default=None,repr=False)
    observer: object=field(default=None,repr=False)
    _model: str=field(default='',init=False,repr=False)
    _provider: bool=field(default=False,init=False,repr=False)
    _stream: bool=field(default=False,init=False,repr=False)
    _reasoning: object=field(default=None,init=False,repr=False)

    def __post_init__(self):
        try:
            value=json.loads(self.policy.encoded)
            if (type(self.policy) is not FrozenPolicy or policy_from_dict(value,value['profile_id'],value['profile_version'])!=self.policy
                    or value['adapter_id'] not in (GATEWAY,PROVIDER) or set(value['allowed_targets'])!={self.target_alias}
                    or type(self.transport) not in (LocalTransport,PrivateNetworkTransport)
                    or type(self.output_guard) is not OutputGuard or self.output_guard.mode!='strict'
                    or self.reasoning_mode not in ('reject','inspect-and-drop')
                    or (self.observer is not None and not callable(self.observer))):raise ValueError()
            offered={item['function']['name'] for item in value['allowed_request_fields'].get('tools',[])}
            contracts=json.loads(self.output_guard.contracts)
            if contracts['schema'] is not None or set(contracts['tools'])!=offered:raise ValueError()
            for schema in contracts['tools'].values():validate_schema(schema)
            for item in value['allowed_request_fields'].get('tools',[]):
                if item['function']['parameters']!=contracts['tools'][item['function']['name']]:raise ValueError()
            if self.admission is not None:
                from admission import EvaluationBinding
                if type(self.admission) is not EvaluationBinding or not callable(self.admission_snapshot):raise ValueError()
            elif self.admission_snapshot is not None:raise ValueError()
            object.__setattr__(self,'_model',value['allowed_targets'][self.target_alias])
            object.__setattr__(self,'_provider',value['adapter_id']==PROVIDER)
            object.__setattr__(self,'_stream',value['allowed_request_fields'].get('stream') is True)
            object.__setattr__(self,'_reasoning',ReasoningOutput.create(self.output_guard))
        except Exception:raise BoundaryError('agent_config_invalid') from None

    def complete(self,raw):
        if self.admission is not None:
            try:self.admission.require_admission(self.admission_snapshot())
            except Exception:raise BoundaryError('model_admission_rejected') from None
        outer=self
        class Wire:
            def send(self,alias,payload):
                if alias!=outer.target_alias:raise BoundaryError('request_rejected')
                request=decode(payload,1048576);records=[]
                for message in request['messages']:
                    # All history is untrusted data; caller-chosen roles cannot
                    # bypass user-input policy. Tool records also get tool policy.
                    text='\n'.join(strings(message));records.append({'source':'user','text':text})
                    if message['role']=='tool':records.append({'source':'tool','text':text})
                    if message['role']=='assistant' and message.get('tool_calls'):
                        prior_message=json.loads(json.dumps(message))
                        if outer._provider:
                            for index,call in enumerate(prior_message['tool_calls']):
                                if 'index' in call:
                                    if type(call['index']) is not int or call.pop('index')!=index:raise ValueError()
                        prior=canonical_response({'choices':[{'finish_reason':'tool_calls','message':prior_message}]},'openai')
                        if outer.output_guard.check_message(prior).decision!='allow':raise BoundaryError('request_rejected')
                checked=inspect(outer.input_policy,json.dumps({'messages':records},ensure_ascii=False).encode(),format='json',source=None,mode='strict')
                if checked.decision!='allow':raise BoundaryError('request_rejected')
                if outer.observer:outer.observer({'event':'verified_provider_bytes' if outer._provider else 'verified_gateway_bytes','sha256':hashlib.sha256(payload).hexdigest()})
                return outer.transport.stream(payload) if outer._stream else outer.transport(payload)
        try:
            response=verify_and_send(self.policy,raw,self.target_alias,Wire())
            if self._stream:canonical,reasoning=decode_sse(response,self._model if self._provider else None)
            else:
                envelope=decode(response,1048576)
                if self._provider and envelope.get('model')!=self._model:raise ValueError()
                message=envelope['choices'][0]['message']
                if set(message)-{'role','content','tool_calls','refusal','reasoning','reasoning_content','reasoning_details'}:raise ValueError()
                if 'refusal' in message and message.pop('refusal') is not None:raise ValueError()
                reasoning={key:message.pop(key) for key in ('reasoning','reasoning_content','reasoning_details') if key in message}
                for index,call in enumerate(message.get('tool_calls',[])):
                    if 'index' in call:
                        if type(call['index']) is not int or call.pop('index')!=index:raise ValueError()
                canonical=canonical_response(envelope,'openai')
            if self.reasoning_mode=='reject' and reasoning and any(reasoning.values()):raise ValueError()
            reason_records=self._reasoning.records(reasoning)
            checked=self.output_guard.check_message(canonical)
            if checked.decision!='allow':raise ValueError()
            accepted=decode(checked.payload,1048576)
            self._reasoning.inspect_records([*strings(accepted),*reason_records])
            return encode_message(accepted,self._model,self._stream)
        except IntegrityError:raise BoundaryError('request_rejected') from None
        except Exception:raise BoundaryError('agent_boundary_rejected') from None
