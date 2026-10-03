"""Trusted request templates, provenance assignment and allow-only provider dispatch."""
from dataclasses import dataclass, field
import http.client
import ipaddress
import json
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

    @classmethod
    def create(cls, policy, endpoint, template, sender=None, *, mode='strict', integrity_sender=None):
        validate_endpoint(endpoint)
        value = _snapshot(template)
        require(type(value) is dict and type(value.get('messages')) is list and bool(value['messages']), 'template_invalid')
        require(all(type(m) is dict and set(m) == {'role', 'content'} and m['role'] in ('system', 'developer')
                    and type(m['content']) is str for m in value['messages']), 'template_invalid')
        require(mode in ('strict', 'sanitize'), 'mode_invalid')
        return cls(policy, endpoint, json.dumps(value, ensure_ascii=True).encode(), sender or local_post, mode, integrity_sender)

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
            require(set(message) <= {'role', 'content', 'tool_calls', 'tool_call_id'}, 'request_invalid')
            data.append({'source': source, 'text': message['content']})
            indexes.append((index, 'content', message['content']))
            if 'tool_calls' in message:
                require(message['role'] == 'assistant' and type(message['tool_calls']) is list, 'request_invalid')
                metadata = json.dumps(message['tool_calls'], ensure_ascii=False)
                data.append({'source': source, 'text': metadata})
                indexes.append((index, 'tool_calls', metadata))
        require(bool(data), 'request_invalid')
        result = inspect(self.policy, json.dumps({'messages': data}, ensure_ascii=False).encode(),
                         format='json', source=None, mode=self.mode)
        if result.decision != 'allow':
            raise GuardRejected(result)
        accepted = json.loads(result.payload)['messages']
        for (index, field_name, original), message in zip(indexes, accepted):
            if field_name == 'tool_calls':
                require(message['text'] == original, 'metadata_transformation_not_supported')
            else:
                messages[index]['content'] = message['text']
        return result, snapshot

    def send(self, request, timeout=30, *, sources=None):
        result, snapshot = self.prepare(request, sources=sources)
        if self.integrity_sender is not None:
            response = self.integrity_sender(snapshot, timeout)
        else:
            response = self.sender(self.endpoint, snapshot, timeout)
        return result.diagnostics(), response

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
