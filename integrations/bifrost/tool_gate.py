"""Explicit tool authorization and one-shot dispatch; never an automatic agent.

Executors are trusted application code. They own atomic authorization,
transactionality, deadlines and durable idempotency at the effect boundary.
"""
from dataclasses import dataclass,field
import hashlib,json,secrets,threading
from prompt_guard import OutputGuard,inspect
from prompt_guard.core import decode,Policy


class ToolGateError(Exception):
    def __init__(self,code,*,attempted=0,completed=0):
        super().__init__(code);self.attempted=attempted;self.completed=completed
        self.effects_may_have_occurred=attempted>0


@dataclass(frozen=True,repr=False,init=False)
class ToolBatch:
    identifier: str
    encoded: bytes=field(repr=False)
    policy_sha256: str


@dataclass(frozen=True,repr=False)
class ToolOutcome:
    encoded: bytes=field(repr=False)
    def messages(self):return decode(self.encoded,1048576)


class ToolGate:
    def __init__(self,output_guard,input_policy,*,max_calls=1024):
        if (type(input_policy) is not Policy or type(output_guard) is not OutputGuard or output_guard.mode!='strict'
                or type(max_calls) is not int or not 1<=max_calls<=4096):raise ToolGateError('tool_config_invalid')
        self._guard=output_guard;self._input=input_policy;self._max=max_calls
        self._pending={};self._used=set();self._lock=threading.Lock()

    def _fingerprint(self):return hashlib.sha256(self._guard.policy.encoded+b'\0'+self._guard.contracts+self._input.encoded).hexdigest()

    def prepare(self,message):
        result=self._guard.check_message(message)
        if result.decision!='allow':raise ToolGateError('tool_proposal_rejected')
        value=decode(result.payload,1048576)
        if not value.get('tool_calls'):raise ToolGateError('tool_proposal_empty')
        batch=object.__new__(ToolBatch)
        for key,item in {'identifier':secrets.token_hex(16),'encoded':result.payload,'policy_sha256':self._fingerprint()}.items():object.__setattr__(batch,key,item)
        with self._lock:
            if len(self._pending)>=32 or len(self._used)>=self._max:raise ToolGateError('tool_resource_limit')
            self._pending[batch.identifier]=hashlib.sha256(batch.encoded).digest()
        return batch

    def execute(self,batch,*,authorize,executors,context):
        attempted=completed=0
        try:
            if type(batch) is not ToolBatch or not callable(authorize) or type(executors) is not dict:raise ToolGateError('tool_config_invalid')
            value=decode(batch.encoded,1048576);calls=value['tool_calls']
            with self._lock:
                expected=self._pending.pop(batch.identifier,None)
                ids={call['id'] for call in calls}
                if (expected!=hashlib.sha256(batch.encoded).digest() or batch.policy_sha256!=self._fingerprint()
                        or ids & self._used or len(self._used|ids)>self._max):raise ToolGateError('tool_replay_or_policy_change')
                # Consume before authorization/effects. Denials and uncertain
                # effects are not silently retried; IDs cannot be reused here.
                self._used.update(ids)
            if self._guard.check_message(value).decision!='allow':raise ToolGateError('tool_proposal_rejected')
            handlers=dict(executors)
            if any(call['name'] not in handlers or not callable(handlers[call['name']]) for call in calls):raise ToolGateError('tool_executor_missing')
            def permission(call):
                # Authorizer receives a fresh copy; mutation cannot change args.
                return authorize(context,json.loads(json.dumps(call)),batch.identifier) is True
            if not all(permission(call) for call in calls):raise ToolGateError('tool_not_authorized')
            results=[]
            for call in calls:
                # Re-check freshness immediately before each dispatch. The actual
                # executor must still make its effect/authorization atomic.
                if not permission(call):raise ToolGateError('tool_authorization_expired')
                attempted+=1
                key=batch.identifier+':'+call['id']
                returned=handlers[call['name']](json.loads(json.dumps(call['arguments'])),key)
                completed+=1
                # Executors must bound their I/O and return JSON bytes, not an
                # arbitrarily large object or executable serialization hook.
                decoded=decode(returned,1048576)
                content=json.dumps(decoded,ensure_ascii=False,separators=(',',':'))
                result=inspect(self._input,content.encode(),source='tool',mode='strict')
                if result.decision!='allow':raise ToolGateError('tool_result_rejected')
                results.append({'role':'tool','tool_call_id':call['id'],'content':content})
            combined=json.dumps({'messages':[{'source':'tool','text':item['content']} for item in results]},ensure_ascii=False).encode()
            if inspect(self._input,combined,format='json',source=None,mode='strict').decision!='allow':raise ToolGateError('tool_result_rejected')
            raw=json.dumps(results,ensure_ascii=False).encode()
            decode(raw,1048576)
            return ToolOutcome(raw)
        except ToolGateError as error:
            raise ToolGateError(str(error),attempted=attempted,completed=completed) from None
        except Exception:
            raise ToolGateError('tool_execution_failed',attempted=attempted,completed=completed) from None
