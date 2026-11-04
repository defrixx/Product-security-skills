"""Closed non-streaming OpenAI final-provider text request contract.

Matches the Bifrost v2.4.0 OpenAI-base wire shape observed in bounded text chat.
No default stream flag, tools, fallback metadata or arbitrary option bags pass.
"""
import json
from .core import require

ADAPTER = 'openai-provider-text-v1'


def validate_options(options):
    require(type(options) is dict and set(options) == {'temperature', 'max_completion_tokens'})
    require(type(options['temperature']) in (int, float) and 0 <= options['temperature'] <= 2)
    require(type(options['max_completion_tokens']) is int and 0 < options['max_completion_tokens'] <= 131072)


def validate_request(snapshot, policy):
    options = policy['allowed_request_fields']
    validate_options(options)
    require(set(snapshot) == {'model', 'messages', *options}, 'unsupported_shape')
    for key, value in options.items():
        require(json.dumps(snapshot[key], sort_keys=True) == json.dumps(value, sort_keys=True), 'request_fields_mismatch')
    messages, trusted = snapshot['messages'], policy['trusted_messages']
    require(type(messages) is list and len(messages) >= len(trusted), 'missing_instruction')
    require(len(messages) <= policy['limits']['messages'], 'resource_limit')
    for index, message in enumerate(messages):
        require(type(message) is dict and set(message) == {'role', 'content'}
                and type(message['role']) is str and type(message['content']) is str, 'unsupported_shape', index)
        if index < len(trusted):
            require(message['role'] == trusted[index]['role'], 'role_mismatch', index)
            require(message['content'] == trusted[index]['text'], 'instruction_mismatch', index)
        else:
            require(message['role'] == 'user', 'unexpected_instruction', index)
    count = len(messages) - len(trusted)
    data = policy['data_message_policy']
    require(data['min_messages'] <= count <= data['max_messages'], 'unsupported_shape')
