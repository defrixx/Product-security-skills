"""Pinned Prompt Integrity checking at Bifrost ingress, not provider egress."""
from dataclasses import dataclass, field
import json
from prompt_integrity import FrozenPolicy, IntegrityError, policy_from_dict, verify_and_send


@dataclass(frozen=True, repr=False)
class GatewayIntegrity:
    """Opt-in reuse of the existing closed Chat Completions wire contract.

    The legacy adapter ID names its original backend. Here only its request
    grammar is reused; no claim about Bifrost's final provider bytes is made.
    """
    policy: FrozenPolicy = field(repr=False)
    target_alias: str

    def __post_init__(self):
        try:
            obj = json.loads(self.policy.encoded)
            validated = policy_from_dict(obj, obj['profile_id'], obj['profile_version'])
            if (type(self.policy) is not FrozenPolicy or validated != self.policy
                    or obj['adapter_id'] != 'lmstudio-chat-tools-v1'
                    or set(obj['allowed_targets']) != {self.target_alias}
                    or obj['data_message_policy']['roles'] != ['user']
                    or obj['allowed_request_fields']['tools'] != []):
                raise ValueError()
        except Exception:
            raise IntegrityError('baseline_invalid') from None

    def options(self):
        # A fresh copy cannot mutate the frozen approved policy.
        return json.loads(self.policy.encoded)['allowed_request_fields']

    def send(self, request, transport):
        alias = self.target_alias
        class Wire:
            def send(self, target, payload):
                if target != alias:
                    raise IntegrityError('unknown_target')
                # Send the verifier-produced bytes exactly once, without JSON
                # assembly or a second model call after verification.
                return transport(payload)
        return verify_and_send(self.policy, request, alias, Wire())
