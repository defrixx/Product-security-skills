"""Trusted request templates, provenance assignment and allow-only provider dispatch."""
from dataclasses import dataclass, field
import http.client
import ipaddress
import json
import socket
import threading
import time
from urllib.parse import urlsplit
from .core import GuardError, decode, inspect, require


class GuardRejected(GuardError):
    def __init__(self, result):
        super().__init__('guard_' + result.decision)
        self.result = result


def _snapshot(value):
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False).encode()
        return decode(raw, 4194304)
    except GuardError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise GuardError('request_invalid') from None


@dataclass(frozen=True, repr=False)
class GuardedDispatch:
    """The template, source assignments and downstream sender are trusted configuration.

    template includes exact static prefix messages and all provider options.
    sender receives (approved_url, checked_request, timeout). An optional integrity
    callback receives checked_request and timeout and owns final-byte dispatch.
    """
    policy: object = field(repr=False)
    endpoint: str = field(repr=False)
    template_bytes: bytes = field(repr=False)
    sender: object = field(repr=False)
    mode: str = 'strict'
    integrity_sender: object = field(default=None, repr=False)
    output_guard: object = field(default=None, repr=False)

    @classmethod
    def create(cls, policy, endpoint, template, sender=None, *, mode='strict', integrity_sender=None, output_guard=None):
        validate_endpoint(endpoint)
        value = _snapshot(template)
        require(type(value) is dict and type(value.get('messages')) is list and bool(value['messages']), 'template_invalid')
        require(all(type(m) is dict and set(m) == {'role', 'content'} and m['role'] in ('system', 'developer')
                    and type(m['content']) is str for m in value['messages']), 'template_invalid')
        require(mode in ('strict', 'sanitize'), 'mode_invalid')
        if output_guard is not None:
            from .output import OutputGuard
            require(type(output_guard) is OutputGuard and type(value.get('stream')) is bool, 'output_config_invalid')
        return cls(policy, endpoint, json.dumps(value, ensure_ascii=True).encode(), sender or local_post, mode, integrity_sender, output_guard)

    def prepare(self, request, *, sources=None):
        snapshot = _snapshot(request)
        template = json.loads(self.template_bytes)
        require(type(snapshot) is dict and set(snapshot) == set(template), 'request_invalid')
        require(all(json.dumps(snapshot[k], sort_keys=True) == json.dumps(template[k], sort_keys=True)
                    for k in template if k != 'messages'), 'request_fields_mismatch')
        messages = snapshot['messages']
        prefix = template['messages']
        require(type(messages) is list and messages[:len(prefix)] == prefix, 'instruction_mismatch')
        data, indexes = [], []
        sources = {} if sources is None else sources
        require(type(sources) is dict and all(type(i) is int and len(prefix) <= i < len(messages) for i in sources), 'source_invalid')
        for index in range(len(prefix), len(messages)):
            message = messages[index]
            require(type(message) is dict and message.get('role') in ('user', 'assistant', 'tool')
                    and type(message.get('content')) is str, 'request_invalid')
            # Provenance never comes from provider payload fields or embedded text.
            allowed = {'user': ('user', 'retrieval', 'file'), 'assistant': ('assistant',), 'tool': ('tool', 'retrieval', 'file')}
            source = sources.get(index, message['role'])
            require(source in allowed[message['role']], 'source_invalid')
            require(set(message) <= {'role', 'content', 'tool_calls', 'tool_call_id', 'tool_name'}, 'request_invalid')
            data.append({'source': source, 'text': message['content']})
            indexes.append((index, 'content', message['content']))
            if 'tool_calls' in message:
                require(message['role'] == 'assistant' and type(message['tool_calls']) is list, 'request_invalid')
                metadata = json.dumps(message['tool_calls'], ensure_ascii=False)
                data.append({'source': source, 'text': metadata})
                indexes.append((index, 'tool_calls', metadata))
            for name in ('tool_call_id', 'tool_name'):
                if name in message:
                    require(message['role'] == 'tool' and type(message[name]) is str, 'request_invalid')
                    data.append({'source': source, 'text': message[name]})
                    indexes.append((index, name, message[name]))
        require(bool(data), 'request_invalid')
        result = inspect(self.policy, json.dumps({'messages': data}, ensure_ascii=False).encode(),
                         format='json', source=None, mode=self.mode)
        if result.decision != 'allow':
            raise GuardRejected(result)
        accepted = json.loads(result.payload)['messages']
        for (index, field_name, original), message in zip(indexes, accepted):
            if field_name != 'content':
                require(message['text'] == original, 'metadata_transformation_not_supported')
            else:
                messages[index]['content'] = message['text']
        return result, snapshot

    def send(self, request, timeout=30, *, sources=None):
        result, snapshot = self.prepare(request, sources=sources)
        require(self.output_guard is None or snapshot.get('stream') is False, 'stream_dispatch_required')
        if self.integrity_sender is not None:
            response = self.integrity_sender(snapshot, timeout)
        else:
            response = self.sender(self.endpoint, snapshot, timeout)
        diagnostics = result.diagnostics()
        if self.output_guard is not None:
            backend = 'ollama' if urlsplit(self.endpoint).path == '/api/chat' else 'openai'
            checked = self.output_guard.check_provider(response, backend)
            if checked.decision != 'allow':
                raise GuardRejected(checked)
            diagnostics['output'] = checked.diagnostics()
            response = json.loads(checked.payload)
        return diagnostics, response

    def send_stream(self, request, emit, timeout=30, *, sources=None, stream_sender=None):
        """Buffer provider SSE/NDJSON and release one checked canonical message.

        emit is application-owned and is never called on block/review/error. Tool
        proposals are returned as data, not executed by this method. An integrity
        callback requires an explicit streaming sender owning final-byte integrity.
        """
        require(self.output_guard is not None and callable(emit), 'output_config_invalid')
        result, snapshot = self.prepare(request, sources=sources)
        require(snapshot.get('stream') is True, 'stream_dispatch_required')
        require(self.integrity_sender is None or stream_sender is not None, 'stream_integrity_sender_required')
        backend = 'ollama' if urlsplit(self.endpoint).path == '/api/chat' else 'openai'
        chunks = (stream_sender or local_stream_post)(self.endpoint, snapshot, timeout)
        checked = self.output_guard.check_provider_stream(chunks, backend, max_seconds=timeout)
        if checked.decision != 'allow':
            raise GuardRejected(checked)
        accepted = json.loads(checked.payload)
        emit(accepted)
        return dict(result.diagnostics(), output=checked.diagnostics())

    def send_user_text(self, text, timeout=30, *, documents=()):
        """Build roles/provenance from trusted application routes, never input JSON."""
        require(type(text) is str and type(documents) is tuple and all(type(d) is str for d in documents), 'request_invalid')
        request = json.loads(self.template_bytes)
        request['messages'].append({'role': 'user', 'content': text})
        sources = {}
        for document in documents:
            index = len(request['messages'])
            request['messages'].append({'role': 'user', 'content': document})
            sources[index] = 'retrieval'
        return self.send(request, timeout, sources=sources)


def validate_endpoint(endpoint):
    require(type(endpoint) is str, 'endpoint_invalid')
    try:
        url = urlsplit(endpoint)
        require(url.scheme == 'http' and ipaddress.ip_address(url.hostname).is_loopback and url.port is not None
                and url.path in ('/api/chat', '/v1/chat/completions') and not url.username and not url.password
                and not url.query and not url.fragment, 'endpoint_invalid')
    except (ValueError, TypeError):
        raise GuardError('endpoint_invalid') from None


def local_post(endpoint, request, timeout):
    """Numeric loopback HTTP only; no redirects, proxies or automatic retries."""
    validate_endpoint(endpoint)
    require(type(timeout) in (float, int) and 0 < timeout <= 900, 'timeout_invalid')
    raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode()
    require(len(raw) <= 4194304, 'resource_limit')
    url = urlsplit(endpoint)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)
    try:
        connection.request('POST', url.path, raw, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        require(response.status == 200, 'provider_http_rejected')
        body = response.read(2097153)
        return decode(body, 2097152)
    except GuardError:
        raise
    except (OSError, http.client.HTTPException):
        raise GuardError('provider_transport_failed') from None
    finally:
        connection.close()


def local_stream_post(endpoint, request, timeout):
    """Bounded numeric-loopback stream; closing the iterator closes the socket."""
    validate_endpoint(endpoint)
    require(type(timeout) in (float, int) and 0 < timeout <= 900, 'timeout_invalid')
    raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode()
    require(len(raw) <= 4194304, 'resource_limit')
    url = urlsplit(endpoint)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)
    deadline = time.monotonic() + timeout
    timer = None
    try:
        connection.connect()
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'provider_transport_failed')
        transport_socket = connection.sock
        def expire():
            try:
                transport_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        timer = threading.Timer(remaining, expire)
        timer.daemon = True
        timer.start()
        connection.request('POST', url.path, raw, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        require(response.status == 200, 'provider_http_rejected')
        expected = 'application/x-ndjson' if url.path == '/api/chat' else 'text/event-stream'
        require(response.getheader('Content-Type', '').split(';')[0].strip().lower() == expected, 'provider_stream_invalid')
        while True:
            require(time.monotonic() < deadline, 'provider_transport_failed')
            chunk = response.read1(4096)
            if not chunk:
                break
            yield chunk
    except GuardError:
        raise
    except (OSError, http.client.HTTPException):
        raise GuardError('provider_transport_failed') from None
    finally:
        if timer is not None:
            timer.cancel()
            timer.join()
        connection.close()
