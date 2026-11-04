"""Application-owned, text-only Prompt Guard boundary for Bifrost OSS."""
from __future__ import annotations
from dataclasses import dataclass, field
import http.client
import ipaddress
import json
import math
import socket
import threading
import time
from urllib.parse import urlsplit
from prompt_guard import OutputGuard, inspect
from prompt_guard.core import decode


class BoundaryError(Exception):
    """Redacted failure: never attach request, response, endpoint or credentials."""


@dataclass(frozen=True, repr=False)
class LocalTransport:
    """One loopback HTTP POST; no proxies, redirects, retries or fallback."""
    endpoint: str = 'http://127.0.0.1:8080'
    timeout: float = 30
    max_bytes: int = 1048576
    token: str = field(default='', repr=False)

    def __post_init__(self):
        self._validate(loopback=True)

    def _validate(self, *, loopback):
        try:
            url = urlsplit(self.endpoint)
            valid = (url.scheme == 'http' and (ipaddress.ip_address(url.hostname).is_loopback or not loopback)
                     and not url.username and not url.password and url.path in ('', '/')
                     and not url.query and not url.fragment and url.port != 0)
            valid = valid and type(self.timeout) in (int, float) and math.isfinite(self.timeout) and 0 < self.timeout <= 120
            valid = valid and type(self.max_bytes) is int and 0 < self.max_bytes <= 1048576
            valid = valid and type(self.token) is str and all(32 <= ord(c) < 127 for c in self.token)
            if not valid:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise BoundaryError('transport_config_invalid') from None

    def __call__(self, payload):
        return self._post(payload, 'application/json')

    def stream(self, payload):
        # Entire upstream body is bounded and buffered before it reaches callers.
        return self._post(payload, 'text/event-stream')

    def _post(self, payload, media):
        url = urlsplit(self.endpoint)
        started = time.monotonic()
        conn = http.client.HTTPConnection(url.hostname, url.port or 8080, timeout=self.timeout)
        timer = None
        try:
            conn.connect()
            wire = conn.sock
            def expire():
                try:
                    wire.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            remaining = self.timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise BoundaryError('gateway_timeout')
            timer = threading.Timer(remaining, expire)
            timer.daemon = True
            timer.start()
            headers = {'Content-Type': 'application/json', 'Accept': media}
            if self.token:
                headers['Authorization'] = 'Bearer ' + self.token
            conn.request('POST', '/v1/chat/completions', body=payload, headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                raise BoundaryError('gateway_http_rejected')
            if (response.getheader('Content-Type', '').split(';')[0].strip().lower() != media
                    or response.getheader('Content-Encoding', 'identity') != 'identity'):
                raise BoundaryError('gateway_format_rejected')
            chunks, size = [], 0
            while True:
                remaining = self.timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise BoundaryError('gateway_timeout')
                wire.settimeout(remaining)
                chunk = response.read1(min(65536, self.max_bytes + 1 - size))
                size += len(chunk)
                if size > self.max_bytes:
                    raise BoundaryError('gateway_resource_limit')
                if not chunk:
                    break
                chunks.append(chunk)
                if response.length == 0:
                    break
            if response.length not in (None, 0):
                raise BoundaryError('gateway_response_incomplete')
            if time.monotonic() - started > self.timeout:
                raise BoundaryError('gateway_timeout')
            return b''.join(chunks)
        except BoundaryError:
            raise
        except Exception:
            raise BoundaryError('gateway_transport_failed') from None
        finally:
            if timer is not None:
                timer.cancel()
            conn.close()


@dataclass(frozen=True, repr=False)
class PrivateNetworkTransport(LocalTransport):
    """Trusted fixed numeric origin on a dedicated RFC1918 network, no DNS.

    This is an explicit deployment capability, never a request-selected endpoint.
    Cleartext is scoped to the named private virtual network; it is not TLS.
    """
    network_cidr: str = ''

    def __post_init__(self):
        self._validate(loopback=False)
        try:
            url = urlsplit(self.endpoint)
            address = ipaddress.ip_address(url.hostname)
            network = ipaddress.ip_network(self.network_cidr, strict=True)
            private = [ipaddress.ip_network(value) for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
            if (network.version != 4 or not 24 <= network.prefixlen <= 30 or not any(network.subnet_of(value) for value in private)
                    or address not in network or address in (network.network_address, network.broadcast_address)
                    or url.port is None):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise BoundaryError('private_transport_config_invalid') from None


@dataclass(frozen=True, repr=False)
class GuardedClient:
    """Trusted route/policies/transport; callers supply source-tagged text only.

    Returns checked assistant content only, never the gateway envelope. All
    non-allow decisions fail closed. This is not a gateway-wide control.
    """
    model: str
    input_policy: object = field(repr=False)
    output_guard: OutputGuard = field(repr=False)
    transport: LocalTransport = field(default_factory=LocalTransport, repr=False)
    system: str = field(default='', repr=False)
    integrity: object = field(default=None, repr=False)
    reasoning_mode: str = 'reject'
    _reasoning_output: object = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if (type(self.model) is not str or not 0 < len(self.model) <= 256
                or '/' not in self.model or any(ord(c) <= 32 for c in self.model)
                or type(self.system) is not str or len(self.system.encode()) > 65536
                or type(self.output_guard) is not OutputGuard or self.output_guard.mode != 'strict'
                or self.reasoning_mode not in ('reject', 'inspect-and-drop')):
            raise BoundaryError('client_config_invalid')
        if self.reasoning_mode == 'inspect-and-drop':
            from reasoning import ReasoningOutput
            object.__setattr__(self, '_reasoning_output', ReasoningOutput.create(self.output_guard))

    def complete(self, records):
        """Accept Prompt Guard's closed {messages: [{source, text}]} bytes contract."""
        try:
            # inspect snapshots bytes, validates source tags and bounds, and uses
            # isolated workers with policy deadlines. No sanitize/review release.
            result = inspect(self.input_policy, records, format='json', source=None, mode='strict')
            if result.decision != 'allow':
                raise BoundaryError('input_rejected')
            accepted = decode(result.payload, 1048576)
            if any(row['source'] == 'assistant' for row in accepted['messages']):
                raise BoundaryError('input_source_rejected')
            messages = []
            if self.system:
                trusted = inspect(self.input_policy, self.system.encode(), source='user', mode='strict')
                if trusted.decision != 'allow':
                    raise BoundaryError('system_rejected')
                messages.append({'role': 'system', 'content': self.system})
            # Source labels select inspection policy, never provider privileges.
            messages.extend({'role': 'user', 'content': row['text']} for row in accepted['messages'])
            options = {'stream': False, 'n': 1}
            if self.integrity is not None:
                from integrity import GatewayIntegrity
                if type(self.integrity) is not GatewayIntegrity:
                    raise BoundaryError('integrity_config_invalid')
                options = self.integrity.options()
            payload = json.dumps({'model': self.model, 'messages': messages, **options},
                                 ensure_ascii=False, allow_nan=False).encode()
            raw = (self.integrity.send(payload, self.transport) if self.integrity is not None
                   else self.transport(payload))
            response = decode(raw, 1048576)
            # Bifrost's ChatAssistantMessage serializes a nil *Refusal as null
            # (no omitempty). Only this empty metadata field is normalized.
            choices = response.get('choices') if type(response) is dict else None
            if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
                raise BoundaryError('output_rejected')
            assistant = choices[0].get('message')
            if type(assistant) is not dict:
                raise BoundaryError('output_rejected')
            if 'refusal' in assistant:
                if assistant['refusal'] is not None:
                    raise BoundaryError('output_rejected')
                del assistant['refusal']
            if self._reasoning_output is not None:
                try:
                    response = self._reasoning_output.normalize(response)
                except Exception:
                    raise BoundaryError('output_rejected') from None
            checked = self.output_guard.check_provider(response, 'openai')
            if checked.decision != 'allow':
                raise BoundaryError('output_rejected')
            message = decode(checked.payload, 1048576)
            # No tool execution, hidden fields, or unchecked envelope escapes.
            if message.get('tool_calls'):
                raise BoundaryError('tools_rejected')
            return message['content']
        except BoundaryError:
            raise
        except Exception:
            raise BoundaryError('boundary_failed') from None
