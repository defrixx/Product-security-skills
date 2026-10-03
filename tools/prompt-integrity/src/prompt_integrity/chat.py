"""Bounded non-streaming Chat Completions tool-history contract.

This adapter validates request integrity, not tool authorization or model output.
"""
import json
from .core import require

ADAPTER = 'lmstudio-chat-tools-v1'


def validate_options(options):
    require(type(options) is dict and set(options) == {'stream', 'temperature', 'max_tokens', 'tools'})
    require(options['stream'] is False)
    require(type(options['temperature']) in (int, float) and 0 <= options['temperature'] <= 2)
    require(type(options['max_tokens']) is int and 0 < options['max_tokens'] <= 131072)
    tools = options['tools']
    require(type(tools) is list and len(tools) <= 32)
    names = set()
    for tool in tools:
        require(type(tool) is dict and set(tool) == {'type', 'function'} and tool['type'] == 'function')
        fn = tool['function']
        require(type(fn) is dict and set(fn) == {'name', 'description', 'parameters'})
        require(type(fn['name']) is str and 0 < len(fn['name']) <= 64 and fn['name'] not in names)
        names.add(fn['name'])
        require(type(fn['description']) is str and type(fn['parameters']) is dict)
        # Schemas are trusted, exactly pinned JSON; this is not a schema engine.
    return names


def validate_request(snapshot, policy):
    options = policy['allowed_request_fields']
    names = validate_options(options)
    require(set(snapshot) == {'model', 'messages', *options}, 'unsupported_shape')
    for key, value in options.items():
        # JSON equality alone would accept True as 1 or False as 0.
        require(json.dumps(snapshot[key], sort_keys=True) ==
                json.dumps(value, sort_keys=True), 'request_fields_mismatch')
    messages = snapshot['messages']
    require(type(messages) is list, 'unsupported_shape')
    trusted = policy['trusted_messages']
    require(len(messages) >= len(trusted), 'missing_instruction')
    require(len(messages) <= policy['limits']['messages'], 'resource_limit')
    pending, used = set(), set()
    for index, message in enumerate(messages):
        require(type(message) is dict, 'unsupported_shape', index)
        role = message.get('role')
        require(type(role) is str and type(message.get('content')) is str, 'unsupported_shape', index)
        if index < len(trusted):
            require(set(message) == {'role', 'content'}, 'unsupported_shape', index)
            require(role == trusted[index]['role'], 'role_mismatch', index)
            require(message['content'] == trusted[index]['text'], 'instruction_mismatch', index)
            continue
        require(role in policy['data_message_policy']['roles'], 'unexpected_instruction', index)
        if role == 'tool':
            require(set(message) == {'role', 'content', 'tool_call_id'}, 'unsupported_shape', index)
            call_id = message['tool_call_id']
            require(type(call_id) is str and call_id in pending, 'tool_history_invalid', index)
            pending.remove(call_id)
            continue
        require(not pending, 'tool_history_invalid', index)
        if role == 'assistant' and 'tool_calls' in message:
            require(set(message) == {'role', 'content', 'tool_calls'}, 'unsupported_shape', index)
            calls = message['tool_calls']
            require(type(calls) is list and 0 < len(calls) <= 32, 'unsupported_shape', index)
            for call in calls:
                require(type(call) is dict and set(call) == {'id', 'type', 'function'}, 'unsupported_shape', index)
                call_id = call['id']
                require(type(call_id) is str and 0 < len(call_id) <= 256 and call_id not in used, 'tool_history_invalid', index)
                require(call['type'] == 'function', 'unsupported_shape', index)
                fn = call['function']
                require(type(fn) is dict and set(fn) == {'name', 'arguments'}, 'unsupported_shape', index)
                require(type(fn['name']) is str and fn['name'] in names and type(fn['arguments']) is str, 'unsupported_shape', index)
                pending.add(call_id)
                used.add(call_id)
        else:
            require(set(message) == {'role', 'content'} and role in ('user', 'assistant'), 'unsupported_shape', index)
    require(not pending, 'tool_history_invalid')
    count = len(messages) - len(trusted)
    data = policy['data_message_policy']
    require(data['min_messages'] <= count <= data['max_messages'], 'unsupported_shape')
