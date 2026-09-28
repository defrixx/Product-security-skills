"""Synthetic local issuer + real Authlib/PyJWT, MongoDB and Jinja integrations.
Issuer is intentionally minimal, not an OAuth server reference implementation.
HTTP loopback and fixture keys/accounts are test-only. No external identities.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import os
import secrets
import threading
import time
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

from authlib.integrations.requests_client import OAuth2Session
from cryptography.hazmat.primitives.asymmetric import rsa
from jinja2 import Environment, StrictUndefined
import jwt
from pymongo import MongoClient
import requests

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only this isolated fixture's HTTP issuer.
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)
REDIRECT = 'http://127.0.0.1:49123/callback'  # Parsed callback; no listener on this port.
CLIENT = 'synthetic-client'


class Issuer:
    def __init__(self):
        self.codes = {}
        self.refresh = {}
        self.lock = threading.Lock()
        self.token_requests = 0
        self.key_source_requests = 0
        self.sessions = 0
        self.override = {}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def reply(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def do_GET(self):
                parts = urlsplit(self.path)
                if parts.path == '/untrusted-jwks':
                    owner.key_source_requests += 1
                    return self.reply(200, {'keys': []})
                q = {key: values[0] for key, values in parse_qs(parts.query).items()}
                if parts.path != '/authorize' or q.get('redirect_uri') != REDIRECT or q.get('client_id') != CLIENT or q.get('code_challenge_method') != 'S256':
                    return self.reply(400, {'error': 'invalid_request'})
                code = secrets.token_urlsafe(24)
                owner.codes[code] = q
                self.send_response(302)
                self.send_header('Location', REDIRECT + '?' + urlencode({'code': code, 'state': q['state']}))
                self.end_headers()
            def do_POST(self):
                q = {key: values[0] for key, values in parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode()).items()}
                with owner.lock:
                    owner.token_requests += 1
                    if q.get('grant_type') == 'authorization_code':
                        transaction = owner.codes.get(q.get('code'))
                        digest = base64.urlsafe_b64encode(hashlib.sha256(q.get('code_verifier', '').encode()).digest()).rstrip(b'=').decode()
                        if not transaction or q.get('redirect_uri') != REDIRECT or q.get('client_id') != CLIENT or digest != transaction['code_challenge']:
                            return self.reply(400, {'error': 'invalid_grant'})
                        del owner.codes[q['code']]
                        nonce = transaction['nonce']
                    elif q.get('grant_type') == 'refresh_token':
                        if not owner.refresh.pop(q.get('refresh_token'), None):
                            return self.reply(400, {'error': 'invalid_grant'})
                        nonce = 'refresh-no-login'
                    else:
                        return self.reply(400, {'error': 'unsupported_grant_type'})
                    refresh = secrets.token_urlsafe(24)
                    owner.refresh[refresh] = True
                    claims = owner.claims(nonce=nonce, **owner.override)
                    self.reply(200, {'access_token': owner.sign(owner.claims(aud='synthetic-api', token_use='access')),
                                     'id_token': owner.sign(claims), 'token_type': 'Bearer', 'expires_in': 60,
                                     'refresh_token': refresh, 'scope': 'openid read'})
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()

    def claims(self, **overrides):
        return dict({'iss': self.url, 'aud': CLIENT, 'sub': 'synthetic-alice', 'iat': int(time.time()),
                     'exp': int(time.time()) + 60, 'token_use': 'id'}, **overrides)

    @staticmethod
    def sign(claims, key=KEY, headers=None):
        return jwt.encode(claims, key, algorithm='RS256', headers=headers or {'kid': 'fixture-key'})

    def verify(self, token, audience=CLIENT, purpose='id', nonce=None):
        header = jwt.get_unverified_header(token)
        if header.get('kid') != 'fixture-key' or any(key in header for key in ('jku', 'jwk', 'x5u')):
            raise ValueError('untrusted_key_selector')
        claims = jwt.decode(token, KEY.public_key(), algorithms=['RS256'], issuer=self.url,
                            audience=audience, options={'require': ['iss', 'aud', 'sub', 'exp', 'iat', 'token_use']})
        if claims['token_use'] != purpose or (nonce is not None and claims.get('nonce') != nonce):
            raise ValueError('wrong_purpose_or_nonce')
        return claims

    def begin(self):
        client = OAuth2Session(CLIENT, scope='openid read', redirect_uri=REDIRECT,
                               token_endpoint_auth_method='none', code_challenge_method='S256')
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(24)
        url, state = client.create_authorization_url(self.url + '/authorize', code_verifier=verifier, nonce=nonce)
        # Restore initiating transaction into the callback client explicitly.
        client.close()
        client = OAuth2Session(CLIENT, scope='openid read', redirect_uri=REDIRECT, state=state,
                               token_endpoint_auth_method='none', code_challenge_method='S256')
        response = requests.get(url, allow_redirects=False, timeout=3)
        assert response.status_code == 302
        return client, verifier, nonce, response.headers['Location']

    def login(self, client, verifier, nonce, callback):
        tokens = client.fetch_token(self.url + '/token', authorization_response=callback, code_verifier=verifier, timeout=3)
        identity = self.verify(tokens['id_token'], nonce=nonce)
        self.sessions += 1
        return tokens, identity


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.issuer = Issuer()
        self.addCleanup(self.issuer.close)

    def test_code_flow_state_pkce_redirect_and_replay(self):
        issuer = self.issuer
        client, verifier, nonce, callback = issuer.begin()
        self.addCleanup(client.close)
        before = issuer.token_requests
        with self.assertRaises(Exception) as failure:
            issuer.login(client, verifier, nonce, callback.replace('state=', 'state=wrong'))
        self.assertEqual(failure.exception.error, 'mismatching_state')
        self.assertEqual(issuer.token_requests, before)  # Authlib rejects state before exchange.
        with self.assertRaises(Exception) as failure:
            issuer.login(client, 'wrong-verifier', nonce, callback)
        self.assertEqual(failure.exception.error, 'invalid_grant')
        self.assertEqual(issuer.sessions, 0)
        client.redirect_uri = REDIRECT + '/wrong'
        with self.assertRaises(Exception) as failure:
            issuer.login(client, verifier, nonce, callback)
        self.assertEqual(failure.exception.error, 'invalid_grant')
        client.redirect_uri = REDIRECT
        tokens, identity = issuer.login(client, verifier, nonce, callback)
        self.assertEqual(identity['sub'], 'synthetic-alice')
        with self.assertRaises(Exception) as failure:
            issuer.login(client, verifier, nonce, callback)
        self.assertEqual(failure.exception.error, 'invalid_grant')
        self.assertEqual(issuer.sessions, 1)
        self.assertEqual(issuer.verify(tokens['access_token'], 'synthetic-api', 'access')['sub'], 'synthetic-alice')

    def test_unbound_state_is_an_unsafe_control(self):
        issuer = self.issuer
        client, verifier, nonce, callback = issuer.begin()
        self.addCleanup(client.close)
        client.state = None  # UNSAFE: discard the initiating transaction.
        issuer.login(client, verifier, nonce, callback.replace('state=', 'state=wrong'))
        self.assertEqual(issuer.sessions, 1)  # Reproduction, not a passed security control.

    def test_oidc_issuer_nonce_fail_before_session(self):
        issuer = self.issuer
        for override in ({'iss': 'https://wrong.synthetic.invalid'}, {'nonce': 'wrong'}):
            client, verifier, nonce, callback = issuer.begin()
            self.addCleanup(client.close)
            # Nonce override is applied by replacing the recorded authorization transaction.
            if 'nonce' in override:
                code = parse_qs(urlsplit(callback).query)['code'][0]
                issuer.codes[code]['nonce'] = 'wrong'
                issuer.override = {}
            else:
                issuer.override = override
            with self.assertRaises((ValueError, jwt.InvalidTokenError)):
                issuer.login(client, verifier, nonce, callback)
            self.assertEqual(issuer.sessions, 0)

    def test_jwt_real_signature_claims_and_key_source(self):
        issuer = self.issuer
        self.assertEqual(issuer.verify(issuer.sign(issuer.claims()))['sub'], 'synthetic-alice')
        attacks = [issuer.sign(issuer.claims(), key=OTHER),
                   jwt.encode(issuer.claims(), 'synthetic-only-key-32-bytes-long!!', algorithm='HS256', headers={'kid': 'fixture-key'}),
                   jwt.encode(issuer.claims(), '', algorithm='none', headers={'kid': 'fixture-key'})]
        for change in ({'iss': issuer.url + '/other'}, {'aud': 'other'}, {'exp': 1}, {'nbf': int(time.time()) + 600}, {'token_use': 'access'}):
            attacks.append(issuer.sign(issuer.claims(**change)))
        claims = issuer.claims(); del claims['exp']
        attacks.append(issuer.sign(claims))
        for header in ({'kid': '../../key'}, {'kid': 'fixture-key', 'jku': issuer.url + '/untrusted-jwks'}, {'kid': 'fixture-key', 'x5u': issuer.url + '/untrusted-jwks'}):
            attacks.append(issuer.sign(issuer.claims(), headers=header))
        for token in attacks:
            with self.assertRaises((ValueError, jwt.InvalidTokenError)):
                issuer.verify(token)
        self.assertEqual(issuer.key_source_requests, 0)
        # Deliberately unsafe decoding accepts the wrong issuer; not passing evidence.
        self.assertEqual(jwt.decode(attacks[3], options={'verify_signature': False})['iss'], issuer.url + '/other')

    def test_refresh_single_use_concurrency_and_recipient(self):
        issuer = self.issuer
        client, verifier, nonce, callback = issuer.begin()
        self.addCleanup(client.close)
        tokens, _ = issuer.login(client, verifier, nonce, callback)
        def refresh(_):
            with OAuth2Session(CLIENT, token_endpoint_auth_method='none') as session:
                try:
                    return session.refresh_token(issuer.url + '/token', refresh_token=tokens['refresh_token'], timeout=3)
                except Exception as error:
                    self.assertEqual(error.error, 'invalid_grant')
                    return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(refresh, range(2)))
        self.assertEqual(sum(value is not None for value in results), 1)
        replacement = next(value for value in results if value)
        with self.assertRaises(jwt.InvalidAudienceError):
            issuer.verify(replacement['access_token'], 'other-api', 'access')
        with self.assertRaises(ValueError):
            issuer.verify(replacement['id_token'], CLIENT, 'access')
        issuer.refresh.clear()  # Synthetic issuer-side revocation, not local client deletion.
        with self.assertRaises(Exception) as failure:
            client.refresh_token(issuer.url + '/token', refresh_token=replacement['refresh_token'], timeout=3)
        self.assertEqual(failure.exception.error, 'invalid_grant')


class InterpreterTests(unittest.TestCase):
    def test_mongodb_operator_injection_and_literal_control(self):
        with MongoClient(os.environ['SYNTHETIC_MONGO_URI'], serverSelectionTimeoutMS=5000) as client:
            collection = client.synthetic.records
            collection.delete_many({})
            collection.insert_many([{'owner': 'alice', 'value': 'A'}, {'owner': 'bob', 'value': 'B'}, {'owner': '$ne', 'value': 'literal'}])
            print('MongoDB version:', client.server_info()['version'])
            # UNSAFE: caller-supplied object becomes a query predicate.
            self.assertEqual(collection.count_documents({'owner': {'$ne': None}}), 3)
            def safe(value):
                if not isinstance(value, str):
                    raise ValueError('string_required')
                return list(collection.find({'owner': {'$eq': value}}, {'_id': 0}))
            self.assertEqual(safe('alice'), [{'owner': 'alice', 'value': 'A'}])
            self.assertEqual(safe('$ne'), [{'owner': '$ne', 'value': 'literal'}])
            for value in ({'$ne': None}, {'$regex': '.*'}, ['alice'], None):
                with self.assertRaises(ValueError): safe(value)
            self.assertEqual(safe('{"$ne":null}'), [])
            collection.drop()

    def test_jinja_data_does_not_become_template_source(self):
        environment = Environment(undefined=StrictUndefined, autoescape=True)
        sentinel = {'secret': 'SYNTHETIC_TEMPLATE_SENTINEL'}
        attack = '{{ sentinel.secret }} / {{ 7 * 7 }}'
        # UNSAFE: interpolating attacker text into template source executes it.
        unsafe = environment.from_string('<p>' + attack + '</p>').render(sentinel=sentinel)
        self.assertIn(sentinel['secret'], unsafe)
        self.assertIn('49', unsafe)
        template = environment.from_string('<p>{{ label }}</p>')
        safe = template.render(label=attack, sentinel=sentinel)
        self.assertIn('{{ 7 * 7 }}', safe)
        self.assertNotIn(sentinel['secret'], safe)
        self.assertEqual(template.render(label='ordinary'), '<p>ordinary</p>')
        self.assertNotIn('<script>', template.render(label='<script>synthetic()</script>'))


if __name__ == '__main__':
    print(json.dumps({name: importlib.metadata.version(name) for name in ['Authlib', 'PyJWT', 'Jinja2', 'pymongo', 'requests', 'cryptography']}), flush=True)
    class EvidenceResult(unittest.TextTestResult):
        def record(self, test, result):
            print('PSS_CASE ' + json.dumps({'case': test.id().replace('__main__.', ''), 'result': result}), flush=True)
        def addSuccess(self, test):
            super().addSuccess(test); self.record(test, 'passed')
        def addFailure(self, test, error):
            super().addFailure(test, error); self.record(test, 'failed')
        def addError(self, test, error):
            super().addError(test, error); self.record(test, 'error')
    unittest.main(verbosity=2, testRunner=unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult))
