"""Direct HTTP transport: no redirects, retries, proxies, or SDK mutation."""
from dataclasses import dataclass
import http.client
from urllib.parse import urlsplit
from .core import TransportError


@dataclass(frozen=True)
class HTTPTransport:
    # Tuples avoid caller-owned mutable endpoint mappings. Configuration is trusted.
    endpoints: tuple
    timeout: float = 30
    max_response_bytes: int = 4194304

    def __post_init__(self):
        if type(self.endpoints) is not tuple or any(type(item) is not tuple or len(item) != 2 for item in self.endpoints):
            raise ValueError('invalid_transport_configuration')
        if len(dict(self.endpoints)) != len(self.endpoints):
            raise ValueError('invalid_transport_configuration')
        if not 0 < self.timeout <= 300 or type(self.max_response_bytes) is not int or self.max_response_bytes <= 0:
            raise ValueError('invalid_transport_configuration')
        for alias, endpoint in self.endpoints:
            if type(alias) is not str or type(endpoint) is not str:
                raise ValueError('invalid_transport_configuration')
            url = urlsplit(endpoint)
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path != '/api/chat':
                raise ValueError('invalid_transport_configuration')
            if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'):
                raise ValueError('cleartext_requires_loopback')

    def send(self, target_alias, payload):
        connection = None
        try:
            if type(payload) is not bytes:
                raise ValueError()
            endpoint = dict(self.endpoints)[target_alias]
            url = urlsplit(endpoint)
            connection_type = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
            connection = connection_type(url.hostname, url.port, timeout=self.timeout)
            connection.request('POST', '/api/chat', body=payload, headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                raise ValueError()
            raw = response.read(self.max_response_bytes+1)
            if len(raw) > self.max_response_bytes:
                raise ValueError()
            return raw
        except Exception:
            raise TransportError('transport_failed') from None
        finally:
            if connection is not None:
                connection.close()
