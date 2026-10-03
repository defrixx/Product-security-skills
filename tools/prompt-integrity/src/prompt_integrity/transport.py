"""Direct HTTP transport: no redirects, retries, proxies, or SDK mutation."""
from dataclasses import dataclass
import http.client
import socket
from urllib.parse import urlsplit
from .core import TransportError


@dataclass(frozen=True)
class HTTPTransport:
    # Tuples avoid caller-owned mutable endpoint mappings. Configuration is trusted.
    endpoints: tuple
    timeout: float = 30
    max_response_bytes: int = 4194304
    path: str = '/api/chat'

    def __post_init__(self):
        if type(self.endpoints) is not tuple or any(type(item) is not tuple or len(item) != 2 for item in self.endpoints):
            raise ValueError('invalid_transport_configuration')
        if len(dict(self.endpoints)) != len(self.endpoints):
            raise ValueError('invalid_transport_configuration')
        if not 0 < self.timeout <= 900 or type(self.max_response_bytes) is not int or self.max_response_bytes <= 0:
            raise ValueError('invalid_transport_configuration')
        if self.path not in ('/api/chat', '/v1/chat/completions'):
            raise ValueError('invalid_transport_configuration')
        for alias, endpoint in self.endpoints:
            if type(alias) is not str or type(endpoint) is not str:
                raise ValueError('invalid_transport_configuration')
            url = urlsplit(endpoint)
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path != self.path:
                raise ValueError('invalid_transport_configuration')
            if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'):
                raise ValueError('cleartext_requires_loopback')

    def send(self, target_alias, payload):
        connection = None
        try:
            if type(payload) is not bytes or target_alias not in dict(self.endpoints):
                raise TransportError('transport_configuration_invalid')
            endpoint = dict(self.endpoints)[target_alias]
            url = urlsplit(endpoint)
            connection_type = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
            connection = connection_type(url.hostname, url.port, timeout=self.timeout)
            connection.request('POST', self.path, body=payload, headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise TransportError('transport_redirect_rejected')
            if not 200 <= response.status < 300:
                raise TransportError('transport_http_rejected')
            raw = response.read(self.max_response_bytes+1)
            if len(raw) > self.max_response_bytes:
                raise TransportError('transport_response_too_large')
            return raw
        except TransportError:
            raise
        except (TimeoutError, socket.timeout):
            raise TransportError('transport_timeout') from None
        except (OSError, http.client.HTTPException):
            raise TransportError('transport_connection_failed') from None
        except Exception:
            raise TransportError('transport_failed') from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass  # Closing must not mask the bounded result with private details.
