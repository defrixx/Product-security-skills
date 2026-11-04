"""Closed reasoning-text inspection with final-content-only release.

Recognizes Bifrost v2.4.0 text/summary reasoning fields. Encrypted, signed,
content-block and unknown payloads are rejected rather than silently dropped.
"""
from dataclasses import dataclass, field
import json
from prompt_guard import OutputGuard, inspect
from prompt_guard.core import GuardError


@dataclass(frozen=True, repr=False)
class ReasoningOutput:
    policy: object = field(repr=False)

    @classmethod
    def create(cls, output):
        if type(output) is not OutputGuard or output.mode != 'strict':
            raise GuardError('output_config_invalid')
        # Reuse the exact effective immutable policy, including protected-value
        # rules. Public inspect uses the same assistant-record contract as
        # OutputGuard, without adding artificial JSON keys to inspected text.
        return cls(output.policy)

    def normalize(self, response):
        choice = response['choices'][0]
        message = choice['message']
        allowed = {'role', 'content', 'tool_calls', 'reasoning', 'reasoning_content', 'reasoning_details'}
        if (set(message) - allowed or message.get('role') != 'assistant'
                or type(message.get('content')) is not str or message.get('tool_calls', []) != []):
            raise GuardError('provider_response_invalid')
        records = self.records(message)
        self.inspect_records([message['content'], *records])
        clean = {key: value for key, value in message.items()
                 if key not in ('reasoning', 'reasoning_content', 'reasoning_details')}
        # Return only the final-content envelope to the original output guard.
        # Neither checked nor unchecked reasoning is exposed to the application.
        return {**response, 'choices': [{**choice, 'message': clean}]}

    def records(self, message):
        """Collect supported reasoning strings; collection alone is not approval."""
        records = []
        aliases = []
        for key in ('reasoning', 'reasoning_content'):
            value = message.get(key)
            if value is not None:
                if type(value) is not str:
                    raise GuardError('provider_response_invalid')
                records.append(value)
                if value:
                    aliases.append(value)
        if len(aliases) == 2 and aliases[0] != aliases[1]:
            raise GuardError('provider_response_invalid')
        details = message.get('reasoning_details', [])
        if type(details) is not list or len(details) > 16:
            raise GuardError('provider_response_invalid')
        indices = set()
        for detail in details:
            if (type(detail) is not dict or set(detail) - {'id', 'index', 'type', 'text', 'summary'}
                    or type(detail.get('index')) is not int or not 0 <= detail['index'] < 16
                    or detail['index'] in indices
                    or detail.get('type') not in ('reasoning.text', 'reasoning.summary')):
                raise GuardError('provider_response_invalid')
            indices.add(detail['index'])
            field_name = 'text' if detail['type'] == 'reasoning.text' else 'summary'
            if type(detail.get(field_name)) is not str:
                raise GuardError('provider_response_invalid')
            for key in ('id', 'summary', 'text'):
                if key in detail:
                    if type(detail[key]) is not str:
                        raise GuardError('provider_response_invalid')
                    records.append(detail[key])
        return records

    def inspect_records(self, values):
        raw = json.dumps({'messages': [{'source': 'assistant', 'text': value}
                                       for value in values]}, ensure_ascii=False).encode()
        result = inspect(self.policy, raw, format='json', source=None, mode='strict')
        if result.decision != 'allow':
            raise GuardError('output_rejected')
