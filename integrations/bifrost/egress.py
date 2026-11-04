"""Final-provider text boundary: inspect, verify final bytes, send once.

Deployment must make the model endpoint reachable only through this service.
The selected closed OpenAI-base wire grammar is not a universal provider API.
"""
from dataclasses import dataclass, field
import hashlib
import json
import secrets
import time
from client import BoundaryError, LocalTransport, PrivateNetworkTransport
from prompt_guard import OutputGuard, inspect
from prompt_guard.core import decode
from prompt_integrity import FrozenPolicy, IntegrityError, policy_from_dict, verify_and_send
from reasoning import ReasoningOutput


@dataclass(frozen=True, repr=False)
class ProviderBoundary:
    policy: FrozenPolicy = field(repr=False)
    target_alias: str
    input_policy: object = field(repr=False)
    output_guard: OutputGuard = field(repr=False)
    transport: object = field(repr=False)
    observer: object = field(default=None, repr=False, compare=False)
    admission: object = field(default=None, repr=False)
    admission_snapshot: object = field(default=None, repr=False)
    _model: str = field(default='', init=False, repr=False)
    _reasoning: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        try:
            if self.admission is not None:
                from admission import EvaluationBinding
                if type(self.admission) is not EvaluationBinding or not callable(self.admission_snapshot):
                    raise ValueError()
            elif self.admission_snapshot is not None:
                raise ValueError()
            obj = json.loads(self.policy.encoded)
            validated = policy_from_dict(obj, obj['profile_id'], obj['profile_version'])
            if (type(self.policy) is not FrozenPolicy or validated != self.policy
                    or obj['adapter_id'] != 'openai-provider-text-v1'
                    or set(obj['allowed_targets']) != {self.target_alias}
                    or type(self.transport) not in (LocalTransport, PrivateNetworkTransport)
                    or type(self.output_guard) is not OutputGuard or self.output_guard.mode != 'strict'
                    or (self.observer is not None and not callable(self.observer))):
                raise ValueError()
            object.__setattr__(self, '_model', obj['allowed_targets'][self.target_alias])
            object.__setattr__(self, '_reasoning', ReasoningOutput.create(self.output_guard))
        except Exception:
            raise BoundaryError('egress_config_invalid') from None

    def complete(self, raw):
        """Only verifier-produced bytes reach the fixed final-model transport."""
        if self.admission is not None:
            try:
                self.admission.require_admission(self.admission_snapshot())
            except Exception:
                raise BoundaryError('model_admission_rejected') from None
        outer = self
        class Wire:
            def send(self, alias, payload):
                # This is called by verify_and_send only after the final request
                # has matched the immutable approved model/instructions/options.
                if alias != outer.target_alias:
                    raise BoundaryError('request_rejected')
                request = decode(payload, 1048576)
                records = {'messages': [{'source': 'user', 'text': row['content']}
                                        for row in request['messages']]}
                result = inspect(outer.input_policy, json.dumps(records, ensure_ascii=False).encode(),
                                 format='json', source=None, mode='strict')
                if result.decision != 'allow':
                    raise BoundaryError('request_rejected')
                if outer.observer:
                    # Opt-in trusted audit hook receives hashes, never prompt data.
                    outer.observer({'event': 'verified_provider_bytes',
                                    'sha256': hashlib.sha256(payload).hexdigest()})
                return outer.transport(payload)
        try:
            raw_response = verify_and_send(self.policy, raw, self.target_alias, Wire())
        except (IntegrityError, BoundaryError):
            raise BoundaryError('request_rejected') from None
        except Exception:
            # Do not retry an uncertain model-side outcome.
            raise BoundaryError('egress_dispatch_rejected') from None
        try:
            response = decode(raw_response, 1048576)
            if response.get('model') != self._model:
                raise ValueError()
            choices = response.get('choices')
            if type(choices) is not list or len(choices) != 1:
                raise ValueError()
            message = choices[0]['message']
            if 'refusal' in message:
                if message['refusal'] is not None:
                    raise ValueError()
                del message['refusal']
            normalized = self._reasoning.normalize(response)
            checked = self.output_guard.check_provider(normalized, 'openai')
            if checked.decision != 'allow':
                raise ValueError()
            accepted = decode(checked.payload, 1048576)
            if accepted.get('tool_calls'):
                raise ValueError()
            # Provider metadata/reasoning and unverified usage are not relayed.
            return {'id': 'chatcmpl-egress-' + secrets.token_hex(12), 'object': 'chat.completion',
                    'created': int(time.time()), 'model': self._model,
                    'choices': [{'index': 0, 'finish_reason': 'stop',
                                 'message': {'role': 'assistant', 'content': accepted['content']}}]}
        except Exception:
            raise BoundaryError('egress_output_rejected') from None
