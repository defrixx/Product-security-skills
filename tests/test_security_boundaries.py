"""Real loopback HTTP/SQLite/HMAC checks on explicitly synthetic designs.

Unsafe controls deliberately reproduce flaws; their success is not a security
pass. These fixtures do not test autonomous skill behavior or a target app.
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

import security_boundaries_fixture as fixture


class SecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-boundaries-')
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'state.db'
        fixture.initialize(self.db)

    def server(self, route=None):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, dict(self.headers)))
                status, headers, body = route(self) if route else (200, {}, b'SYNTHETIC_OK')
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.addCleanup(stop)
        return server.server_address, requests

    def test_outbound_pins_checked_endpoint(self):
        allowed, allowed_hits = self.server()
        excluded, excluded_hits = self.server()
        origin = ('partner.invalid', 80)
        destinations = {origin: {allowed}}

        def changing_resolver():
            answers = iter([allowed, excluded])
            return lambda _: next(answers)

        # Unsafe: validation and connection use different fixture resolutions.
        fixture.fetch('http://partner.invalid/', destinations, changing_resolver(), unsafe=True)
        self.assertEqual(len(excluded_hits), 1)
        excluded_hits.clear()
        self.assertEqual(fixture.fetch('http://partner.invalid/', destinations, changing_resolver()), b'SYNTHETIC_OK')
        self.assertEqual(len(allowed_hits), 1)
        self.assertEqual(excluded_hits, [])
        for url in ['http://2130706433/', 'file:///sentinel', 'http://partner.invalid:81/', 'http://user@partner.invalid/']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                fixture.fetch(url, destinations, lambda _: allowed)
        self.assertEqual(len(allowed_hits), 1)

    def test_redirect_confinement_and_budget(self):
        excluded, excluded_hits = self.server()
        first, first_hits = self.server(lambda _: (302, {'Location': 'http://excluded.invalid/'}, b''))
        origins = {('first.invalid', 80): {first}, ('excluded.invalid', 80): set()}
        resolve = lambda origin: first if origin[0] == 'first.invalid' else excluded
        fixture.fetch('http://first.invalid/', origins, resolve, unsafe=True)
        self.assertEqual(len(excluded_hits), 1)
        excluded_hits.clear()
        with self.assertRaises(ValueError):
            fixture.fetch('http://first.invalid/', origins, resolve)
        self.assertEqual(excluded_hits, [])
        final, final_hits = self.server()
        # Explicit policy change makes this an allowed partner redirect.
        origins[('excluded.invalid', 80)] = {final}
        self.assertEqual(fixture.fetch('http://first.invalid/', origins, lambda o: first if o[0] == 'first.invalid' else final), b'SYNTHETIC_OK')
        self.assertEqual(len(final_hits), 1)
        loop, loop_hits = self.server(lambda _: (302, {'Location': '/'}, b''))
        with self.assertRaisesRegex(ValueError, 'redirect_budget'):
            fixture.fetch('http://loop.invalid/', {('loop.invalid', 80): {loop}}, lambda _: loop)
        self.assertEqual(len(loop_hits), 4)

    def test_redirect_does_not_forward_recipient_credential(self):
        recipient, recipient_hits = self.server()
        initial, initial_hits = self.server(lambda _: (302, {'Location': 'http://other.invalid/'}, b''))
        origins = {('initial.invalid', 80): {initial}, ('other.invalid', 80): {recipient}}
        resolve = lambda o: initial if o[0] == 'initial.invalid' else recipient
        fixture.fetch('http://initial.invalid/', origins, resolve, ('initial.invalid', 80), unsafe=True)
        self.assertIn('Authorization', recipient_hits[-1][1])
        recipient_hits.clear()
        fixture.fetch('http://initial.invalid/', origins, resolve, ('initial.invalid', 80))
        self.assertIn('Authorization', initial_hits[-1][1])
        self.assertNotIn('Authorization', recipient_hits[-1][1])

    def test_concurrent_consumption_preserves_quota(self):
        def run(unsafe):
            barrier = threading.Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: fixture.consume(self.db, barrier, unsafe), range(2)))
            with sqlite3.connect(self.db) as db:
                remaining = db.execute('SELECT remaining FROM quota').fetchone()[0]
            return sum(results), remaining

        self.assertEqual(run(True), (2, -1))  # Deliberately vulnerable control.
        with sqlite3.connect(self.db) as db:
            db.execute('UPDATE quota SET remaining=1')
        self.assertEqual(run(False), (1, 0))

    def test_authoritative_transition(self):
        self.assertEqual(fixture.transition('draft', 'issued', False, unsafe=True), 'issued')
        self.assertEqual(fixture.transition('pending', 'issued', True), 'issued')
        for state, approved in [('draft', True), ('pending', False), ('issued', True), ('expired', True)]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                fixture.transition(state, 'issued', approved)

    def test_retry_identity_and_durable_recovery(self):
        with self.assertRaises(RuntimeError):
            fixture.issue(self.db, 'alice', 'operation-1', 'payload-a', fail_after_commit=True)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM effects').fetchone()[0], 0)
        # Reopen the database in recovery, as a fresh worker would; no live object state.
        fixture.recover(self.db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: fixture.issue(self.db, 'alice', 'operation-1', 'payload-a'), range(2)))
        with self.assertRaises(ValueError):
            fixture.issue(self.db, 'alice', 'operation-1', 'different-payload')
        fixture.issue(self.db, 'bob', 'operation-1', 'payload-b')
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT actor,key FROM effects ORDER BY actor').fetchall(), [('alice', 'operation-1'), ('bob', 'operation-1')])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM operations WHERE state='completed'").fetchone()[0], 2)

    @staticmethod
    def body(**updates):
        value = {'id': 'event-1', 'account': 'account-a', 'object': 'object-a', 'version': 2, 'type': 'approved'}
        value.update(updates)
        return json.dumps(value).encode()

    def test_event_verification_scope_and_freshness(self):
        body = self.body()
        for payload, timestamp, signature in [
            (body, 100, 'wrong-proof'),
            (body + b' ', 100, fixture.sign_event(body, 100)),
            (body, 69, fixture.sign_event(body, 69)),
            (body, 101, fixture.sign_event(body, 101)),
            (self.body(account='account-b'), 100, fixture.sign_event(self.body(account='account-b'), 100)),
            (self.body(object='object-b'), 100, fixture.sign_event(self.body(object='object-b'), 100)),
            (self.body(type='unsupported'), 100, fixture.sign_event(self.body(type='unsupported'), 100)),
        ]:
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                fixture.event(self.db, payload, timestamp, signature, 100)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT version FROM objects').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)
        self.assertEqual(fixture.event(self.db, body, 100, fixture.sign_event(body, 100), 100), 'applied')

    def test_event_duplicates_and_reordering(self):
        body = self.body()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: fixture.event(self.db, body, 100, fixture.sign_event(body, 100), 100), range(2)))
        self.assertEqual(sorted(results), ['applied', 'ignored'])
        # A renewed delivery signature must not bypass durable event deduplication.
        self.assertEqual(fixture.event(self.db, body, 110, fixture.sign_event(body, 110), 110), 'ignored')
        older = self.body(id='older', version=1)
        self.assertEqual(fixture.event(self.db, older, 110, fixture.sign_event(older, 110), 110), 'ignored')
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT version FROM objects').fetchone()[0], 2)
        # Deliberately unsafe control accepts unverified and regressive delivery.
        self.assertEqual(fixture.event(self.db, older, 0, 'invalid', 110, unsafe=True), 'applied')
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT version FROM objects').fetchone()[0], 1)

    def test_key_purpose_rotation_revocation_and_recovery(self):
        keys = fixture.Keys()
        old_version, old_signature = keys.sign('writer', 'receipt', b'message')
        for actor, purpose, version in [('reader', 'receipt', 'v1'), ('writer', 'other', 'v1'), ('writer', 'receipt', 'unknown')]:
            with self.subTest(actor=actor, purpose=purpose), self.assertRaises(ValueError):
                keys.sign(actor, purpose, b'message', version)
        keys.rotate()
        self.assertEqual(keys.sign('writer', 'receipt', b'message')[0], 'v2')
        self.assertTrue(keys.verify(old_version, b'message', old_signature))
        with self.assertRaises(ValueError):
            keys.sign('writer', 'receipt', b'message', 'v1')
        self.assertFalse(keys.verify('v2', b'message', old_signature))
        self.assertFalse(keys.verify('v1', b'changed', old_signature))
        keys.states['v1'] = 'revoked'
        # Raw mathematical verification alone still accepts a revoked key.
        raw = hmac.new(keys.material['v1'], b'receipt:v1:message', hashlib.sha256).digest()
        self.assertTrue(hmac.compare_digest(raw, old_signature))
        self.assertFalse(keys.verify('v1', b'message', old_signature))
        recovery_material = keys.material.pop('v2')
        with self.assertRaises(KeyError):
            keys.sign('writer', 'receipt', b'message')
        with self.assertRaises(ValueError):
            keys.restore('writer', 'v2', recovery_material)
        keys.restore('recovery-operator', 'v2', recovery_material)
        version, signature = keys.sign('writer', 'receipt', b'message')
        self.assertTrue(keys.verify(version, b'message', signature))
        with self.assertRaises(ValueError):
            keys.restore('recovery-operator', 'v1', b'SYNTHETIC_RETIRED')

    def test_cache_hit_isolation_variants_and_revocation(self):
        unsafe = fixture.CachedProfiles(unsafe=True)
        unsafe.get('alice')
        self.assertEqual(unsafe.get('bob')['actor'], 'alice')
        self.assertEqual(unsafe.get(None)['actor'], 'alice')
        safe = fixture.CachedProfiles()
        self.assertEqual(safe.get('alice'), safe.get('alice'))
        self.assertEqual(safe.computations, 1)
        self.assertEqual(safe.get('alice', 'full')['variant'], 'full')
        self.assertEqual(safe.computations, 2)
        for actor in ['bob', None]:
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                safe.get(actor)
        safe.allowed.clear()
        with self.assertRaises(ValueError):
            safe.get('alice')

    def test_mcp_http_origin_denied_before_effect(self):
        effects = []
        allowed = 'https://client.example.test'

        def route(handler):
            status = fixture.mcp_gate(handler.headers.get('Origin'), handler.headers.get('Authorization'), allowed)
            if status == 200:
                effects.append('SYNTHETIC_TOOL_EFFECT')
            return status, {}, b'fixture'

        endpoint, _ = self.server(route)
        self.assertEqual(fixture.mcp_gate('https://untrusted.invalid', 'SYNTHETIC_CLIENT', allowed, unsafe=True), 200)
        for origin, token, expected in [
            (allowed, 'SYNTHETIC_CLIENT', 200), (None, 'SYNTHETIC_CLIENT', 200),
            ('https://untrusted.invalid', 'SYNTHETIC_CLIENT', 403),
            ('https://client.example.test.attacker.invalid', 'SYNTHETIC_CLIENT', 403),
            ('null', 'SYNTHETIC_CLIENT', 403), (None, 'wrong', 401),
        ]:
            conn = http.client.HTTPConnection(*endpoint, timeout=2)
            try:
                headers = {'Authorization': token}
                if origin is not None:
                    headers['Origin'] = origin
                conn.request('GET', '/', headers=headers)
                response = conn.getresponse()
                self.assertEqual(response.status, expected)
                response.read()
            finally:
                conn.close()
        self.assertEqual(len(effects), 2)


if __name__ == '__main__':
    unittest.main()
