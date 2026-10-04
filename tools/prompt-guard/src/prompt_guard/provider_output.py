"""Closed provider response decoding; raw envelopes never cross the output boundary."""
import json
from .core import decode, require


def canonical_response(value, backend):
    require(type(value) is dict and backend in ('openai', 'ollama'), 'provider_response_invalid')
    if backend == 'openai':
        choices = value.get('choices')
        require(type(choices) is list and len(choices) == 1 and choices[0].get('finish_reason') in ('stop', 'tool_calls'),
                'provider_response_incomplete')
        message = choices[0].get('message')
    else:
        require(value.get('done') is True and value.get('done_reason', 'stop') in ('stop', 'tool_calls'), 'provider_response_incomplete')
        message = value.get('message')
    require(type(message) is dict and set(message) <= {'role', 'content', 'tool_calls'}
            and message.get('role') == 'assistant', 'provider_response_invalid')
    content = message.get('content')
    calls = message.get('tool_calls', [])
    require(content is None or type(content) is str, 'provider_response_invalid')
    require(type(calls) is list, 'provider_response_invalid')
    canonical = []
    for index, call in enumerate(calls):
        require(type(call) is dict and set(call) <= {'id', 'type', 'function'}
                and call.get('type', 'function') == 'function', 'provider_response_invalid')
        function = call.get('function')
        require(type(function) is dict and set(function) == {'name', 'arguments'}, 'provider_response_invalid')
        arguments = function['arguments']
        if backend == 'openai':
            require(type(arguments) is str and type(call.get('id')) is str, 'provider_response_invalid')
            arguments = decode(arguments.encode(), 1048576)
        canonical.append({'id': call.get('id', 'call-%d' % index), 'name': function['name'], 'arguments': arguments})
    require(content is not None or bool(canonical), 'provider_response_invalid')
    return {'content': content or '', 'tool_calls': canonical}


def stream_response(chunks, backend, *, max_bytes=1048576, max_events=4096):
    """Collect SSE or NDJSON transport bytes, including fragmented tool arguments.

    Return one canonical complete assistant message. No provider event is emitted.
    The caller owns transport read deadlines and closes the iterator on failure.
    """
    require(backend in ('openai', 'ollama'), 'provider_response_invalid')
    buffer, total, count = b'', 0, 0
    require(type(max_bytes) is int and 0 < max_bytes <= 1048576
            and type(max_events) is int and 0 < max_events <= 4096, 'stream_config_invalid')
    content, calls, finished, terminal = '', {}, False, False
    def event(raw):
        nonlocal count, content, finished, terminal
        count += 1
        require(count <= max_events and not terminal, 'provider_stream_invalid')
        if backend == 'openai' and raw == b'[DONE]':
            require(finished, 'provider_response_incomplete')
            terminal = True
            return
        value = decode(raw, max_bytes)
        require(type(value) is dict, 'provider_stream_invalid')
        if backend == 'ollama':
            require(not finished and type(value.get('done')) is bool, 'provider_stream_invalid')
            message = value.get('message')
            require(type(message) is dict and set(message) <= {'role', 'content', 'tool_calls'}
                    and message.get('role') == 'assistant' and type(message.get('content', '')) is str, 'provider_stream_invalid')
            content += message.get('content', '')
            require(type(message.get('tool_calls', [])) is list, 'provider_stream_invalid')
            for call in message.get('tool_calls', []):
                calls[len(calls)] = call
            if value['done']:
                require(value.get('done_reason', 'stop') in ('stop', 'tool_calls'), 'provider_response_incomplete')
                finished = terminal = True
        else:
            choices = value.get('choices')
            if choices == [] and finished and type(value.get('usage')) is dict:
                return
            require(type(choices) is list and len(choices) == 1 and not finished, 'provider_stream_invalid')
            choice = choices[0]
            require(type(choice) is dict and type(choice.get('index', 0)) is int and choice.get('index', 0) == 0, 'provider_stream_invalid')
            delta = choice.get('delta')
            require(type(delta) is dict and set(delta) <= {'role', 'content', 'tool_calls'}
                    and delta.get('role', 'assistant') == 'assistant', 'provider_stream_invalid')
            require(delta.get('content') is None or type(delta.get('content')) is str, 'provider_stream_invalid')
            content += delta.get('content') or ''
            require(type(delta.get('tool_calls', [])) is list, 'provider_stream_invalid')
            for part in delta.get('tool_calls', []):
                require(type(part) is dict and set(part) <= {'index', 'id', 'type', 'function'}
                        and type(part.get('index')) is int and 0 <= part['index'] < 32
                        and part.get('type', 'function') == 'function', 'provider_stream_invalid')
                call = calls.setdefault(part['index'], {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                function = part.get('function', {})
                require(type(function) is dict and set(function) <= {'name', 'arguments'}, 'provider_stream_invalid')
                for key in ('name', 'arguments'):
                    require(type(function.get(key, '')) is str, 'provider_stream_invalid')
                    call['function'][key] += function.get(key, '')
                require(type(part.get('id', '')) is str, 'provider_stream_invalid')
                call['id'] += part.get('id', '')
            reason = choice.get('finish_reason')
            if reason is not None:
                require(reason in ('stop', 'tool_calls'), 'provider_response_incomplete')
                finished = True
    for chunk in chunks:
        require(type(chunk) is bytes, 'provider_stream_invalid')
        total += len(chunk)
        require(total <= max_bytes, 'resource_limit')
        buffer += chunk
        if backend == 'openai':
            buffer = buffer.replace(b'\r\n', b'\n')
            while b'\n\n' in buffer:
                record, buffer = buffer.split(b'\n\n', 1)
                lines = record.split(b'\n')
                require(all(line.startswith(b'data:') or line.startswith(b':') or not line for line in lines), 'provider_stream_invalid')
                data = [line[5:].lstrip(b' ') for line in lines if line.startswith(b'data:')]
                if data:
                    event(b'\n'.join(data))
        else:
            while b'\n' in buffer:
                record, buffer = buffer.split(b'\n', 1)
                if record.strip():
                    event(record)
    if backend == 'ollama' and buffer.strip():
        event(buffer)
        buffer = b''
    require(not buffer.strip() and terminal, 'provider_response_incomplete')
    ordered = [calls[i] for i in sorted(calls)]
    require(len(ordered) <= 32, 'resource_limit')
    if backend == 'openai':
        return canonical_response({'choices': [{'message': {'role': 'assistant', 'content': content, 'tool_calls': ordered},
                                                 'finish_reason': 'tool_calls' if ordered else 'stop'}]}, backend)
    return canonical_response({'message': {'role': 'assistant', 'content': content, 'tool_calls': ordered}, 'done': True}, backend)
