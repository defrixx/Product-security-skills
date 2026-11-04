"""Scoped HTTP ingress facade; deployment must exclude direct Bifrost access.

This is not a native Bifrost plugin. It protects a closed text or buffered-agent
Chat Completions route. All other routes, methods and routing headers fail closed.
"""
import hmac
import http.server
import json
import secrets
import socket
import threading
import time
from client import BoundaryError, GuardedClient, LocalTransport, PrivateNetworkTransport
from integrity import GatewayIntegrity
from prompt_integrity import check_request
from prompt_guard.core import decode


class IngressBoundary:
    def __init__(self, client):
        if (type(client) is not GuardedClient or type(client.integrity) is not GatewayIntegrity
                or type(client.transport) not in (LocalTransport, PrivateNetworkTransport)):
            raise BoundaryError('ingress_config_invalid')
        policy = json.loads(client.integrity.policy.encoded)
        trusted = policy['trusted_messages']
        if (len(trusted) != 1 or trusted[0]['text'] != client.system
                or policy['allowed_targets'][client.integrity.target_alias] != client.model):
            raise BoundaryError('ingress_config_invalid')
        self._client = client

    def complete(self, raw):
        client = self._client
        checked = check_request(client.integrity.policy, raw, client.integrity.target_alias)
        if checked.decision != 'match':
            raise BoundaryError('request_rejected')
        request = decode(raw, 1048576)
        # Integrity permits only pinned system + user records. Reserialization
        # below is followed by verify_and_send, so only checked final ingress
        # bytes are sent; this does not attest provider-side transformations.
        records = {'messages': [{'source': 'user', 'text': row['content']}
                                for row in request['messages'][1:]]}
        content = client.complete(json.dumps(records, ensure_ascii=False).encode())
        return {'id': 'chatcmpl-guard-' + secrets.token_hex(12), 'object': 'chat.completion',
                'created': int(time.time()), 'model': client.model,
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content},
                             'finish_reason': 'stop'}]}


class IngressServer(http.server.ThreadingHTTPServer):
    """Bounded, token-authenticated local facade. No incoming header is forwarded.

    Bind loopback by default. A non-loopback listener requires explicit trusted
    deployment configuration; TLS, publication and upstream isolation are owned
    by that deployment. Neither this class nor a token isolates Bifrost itself.
    """
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, boundary, token, *, max_workers=8, read_seconds=5,
                 max_body=1048576, allow_network_listener=False):
        from egress import ProviderBoundary
        from agent_boundary import AgentBoundary
        if (type(boundary) not in (IngressBoundary, ProviderBoundary, AgentBoundary) or type(token) is not str
                or not 32 <= len(token) <= 256 or any(not 33 <= ord(c) < 127 for c in token)
                or type(max_workers) is not int or not 1 <= max_workers <= 64
                or type(read_seconds) not in (float, int) or not 0 < read_seconds <= 30
                or type(max_body) is not int or not 0 < max_body <= 1048576
                or (address[0] != '127.0.0.1' and not allow_network_listener)):
            raise BoundaryError('ingress_config_invalid')
        self.boundary, self._token = boundary, token.encode('ascii')
        self.read_seconds, self.max_body = read_seconds, max_body
        self._slots = threading.BoundedSemaphore(max_workers)
        super().__init__(address, _Handler)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.settimeout(1)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def handle_error(self, request, client_address):
        # Unexpected request failures close the socket; never print request data.
        pass


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    server_version = 'GuardedIngress'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(self.server.read_seconds)
        def expire():
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._timer = threading.Timer(self.server.read_seconds, expire)
        self._timer.daemon = True
        self._timer.start()

    def finish(self):
        self._timer.cancel()
        super().finish()

    def log_message(self, *args):
        pass

    def reply(self, status, code, value=None):
        from agent_boundary import BufferedSSE
        stream = type(value) is BufferedSSE
        body = value.body if stream else json.dumps(value if value is not None else {'error': {'code': code}}).encode()
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'text/event-stream' if stream else 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)
        except OSError:
            pass

    def send_error(self, code, message=None, explain=None):
        self.reply(400 if code in (400, 414, 431) else 405, 'http_request_rejected')

    def do_POST(self):
        try:
            if self.path != '/v1/chat/completions':
                self.reply(404, 'route_rejected'); return
            allowed = {'host', 'authorization', 'content-type', 'content-length',
                       'accept', 'accept-encoding', 'connection', 'user-agent'}
            from agent_boundary import AgentBoundary
            if (type(self.server.boundary) is AgentBoundary and self.server.boundary._stream
                    and self.headers.get('Cache-Control')=='no-cache'):
                allowed.add('cache-control')
            names = [name.lower() for name in self.headers.keys()]
            if len(names) != len(set(names)) or not set(names) <= allowed:
                self.reply(400, 'headers_rejected'); return
            supplied = self.headers.get('Authorization', '').encode('latin1')
            if not hmac.compare_digest(supplied, b'Bearer ' + self.server._token):
                self.reply(401, 'authorization_rejected'); return
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                self.reply(415, 'media_rejected'); return
            length = self.headers.get('Content-Length', '')
            if not length.isascii() or not length.isdecimal() or not 0 < int(length) <= self.server.max_body:
                self.reply(413, 'body_rejected'); return
            raw = self.rfile.read(int(length))
            if len(raw) != int(length):
                self.reply(400, 'body_incomplete'); return
            self._timer.cancel()
            result = self.server.boundary.complete(raw)
            self.reply(200, 'allowed', result)
        except BoundaryError as error:
            code = str(error)
            status = 403 if code in ('request_rejected', 'input_rejected', 'system_rejected') else 502
            self.reply(status, 'policy_rejected' if status == 403 else 'upstream_rejected')
        except Exception:
            self.reply(400, 'request_rejected')
