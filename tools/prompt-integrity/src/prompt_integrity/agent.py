"""Pinned OpenAI chat/tool-history contracts, including buffered SSE requests."""
import copy
import json
from .core import require
from .chat import validate_options as chat_options, validate_request as chat_request

GATEWAY = 'bifrost-chat-agent-v1'
PROVIDER = 'openai-provider-agent-v1'


def validate_options(options, provider=False):
    require(type(options) is dict)
    if not provider:
        require(set(options) == {'stream', 'temperature', 'max_tokens', 'tools'})
        require(type(options['stream']) is bool)
        projected = copy.deepcopy(options); projected['stream'] = False
    else:
        require({'temperature', 'max_completion_tokens'} <= set(options)
                and set(options) <= {'temperature', 'max_completion_tokens', 'tools', 'stream', 'stream_options'})
        if 'stream' in options:
            require(options['stream'] is True)
        if 'stream_options' in options:
            require(options.get('stream') is True and type(options['stream_options']) is dict
                    and set(options['stream_options']) == {'include_usage'}
                    and options['stream_options']['include_usage'] is True)
        if 'tools' in options:
            require(type(options['tools']) is list and bool(options['tools']))
        projected = {'stream': False, 'temperature': options['temperature'],
                     'max_tokens': options['max_completion_tokens'], 'tools': copy.deepcopy(options.get('tools', []))}
    return chat_options(projected)


def validate_request(snapshot, policy):
    provider = policy['adapter_id'] == PROVIDER
    options = policy['allowed_request_fields']
    validate_options(options, provider)
    require(set(snapshot) == {'model', 'messages', *options}, 'unsupported_shape')
    for key, value in options.items():
        require(json.dumps(snapshot[key], sort_keys=True) == json.dumps(value, sort_keys=True), 'request_fields_mismatch')
    # Grammar projection only. _prepare serializes the ORIGINAL validated wire
    # request, including its streaming flag; this projection is never dispatched.
    projected_policy = copy.deepcopy(policy)
    projected_options = {'stream': False, 'temperature': options['temperature'],
                         'max_tokens': options['max_completion_tokens'] if provider else options['max_tokens'],
                         'tools': copy.deepcopy(options.get('tools', []))}
    projected_policy['allowed_request_fields'] = projected_options
    projected = {'model': snapshot['model'], 'messages': copy.deepcopy(snapshot['messages']), **projected_options}
    if provider:
        for message in projected['messages']:
            if type(message) is dict and message.get('role')=='assistant':
                for index,call in enumerate(message.get('tool_calls',[])):
                    if type(call) is dict and 'index' in call:
                        require(type(call['index']) is int and call.pop('index')==index,'tool_history_invalid')
    chat_request(projected, projected_policy)
