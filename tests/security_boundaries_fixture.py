"""Synthetic security anti-examples and controls, never production helpers.

Only tests supply endpoints: disposable IPv4 loopback servers. The resolver is
injected, so these checks do not establish real DNS, TLS, proxy, or browser safety.
SQLite/HMAC are real; provider identities, time, and external delivery are fixtures.
"""
import hashlib
import hmac
import http.client
import ipaddress
import json
import sqlite3
from urllib.parse import urljoin, urlsplit


def authority(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.username or parsed.password
            or not parsed.hostname or parsed.fragment):
        raise ValueError('destination')
    return parsed, (parsed.hostname, parsed.port or 80)


def request(endpoint, path, headers):
    # Hard fixture safety boundary even for intentionally unsafe examples.
    if ipaddress.ip_address(endpoint[0]) != ipaddress.ip_address('127.0.0.1'):
        raise ValueError('fixture_non_loopback')
    conn = http.client.HTTPConnection(*endpoint, timeout=2)
    try:
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        return response.status, response.getheader('Location'), response.read(4096)
    finally:
        conn.close()


def fetch(url, destinations, resolve, credential_origin=None, unsafe=False):
    """Unsafe mode intentionally re-resolves after validation and trusts redirects."""
    for hop in range(4):
        parsed, origin = authority(url)
        if origin not in destinations:
            raise ValueError('destination')
        endpoint = resolve(origin)
        if not unsafe or hop == 0:
            if endpoint not in destinations[origin]:
                raise ValueError('endpoint')
        if unsafe:
            endpoint = resolve(origin)  # Deliberate check/use race anti-example.
        headers = {'Host': parsed.netloc}
        if origin == credential_origin or unsafe and credential_origin:
            headers['Authorization'] = 'SYNTHETIC_OUTBOUND_CANARY'
        status, location, body = request(endpoint, parsed.path or '/', headers)
        if status not in (301, 302, 303, 307, 308):
            return body
        if not location:
            raise ValueError('redirect')
        url = urljoin(url, location)
    raise ValueError('redirect_budget')


def initialize(db_path):
    with sqlite3.connect(db_path) as db:
        db.executescript('''
            CREATE TABLE quota (id INTEGER PRIMARY KEY, remaining INTEGER);
            INSERT INTO quota VALUES (1, 1);
            CREATE TABLE operations (
                actor TEXT, key TEXT, payload TEXT, state TEXT,
                PRIMARY KEY(actor, key));
            CREATE TABLE effects (actor TEXT, key TEXT, PRIMARY KEY(actor, key));
            CREATE TABLE objects (id TEXT PRIMARY KEY, account TEXT, version INTEGER, state TEXT);
            INSERT INTO objects VALUES ('object-a', 'account-a', 0, 'pending');
            CREATE TABLE events (account TEXT, id TEXT, PRIMARY KEY(account, id));
        ''')


def consume(db_path, barrier, unsafe=False):
    with sqlite3.connect(db_path, timeout=3) as db:
        if unsafe:
            available = db.execute('SELECT remaining FROM quota').fetchone()[0]
            barrier.wait(timeout=3)
            if available:
                db.execute('UPDATE quota SET remaining=remaining-1')
                return True
            return False
        barrier.wait(timeout=3)
        return db.execute('UPDATE quota SET remaining=remaining-1 WHERE remaining>0').rowcount == 1


def transition(current, target, approved, unsafe=False):
    if unsafe or current == 'pending' and target == 'issued' and approved:
        return target
    raise ValueError('transition')


def issue(db_path, actor, key, payload, fail_after_commit=False):
    """A local durable outbox model; external service semantics are not tested."""
    with sqlite3.connect(db_path, timeout=3) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload,state FROM operations WHERE actor=? AND key=?', (actor, key)).fetchone()
        if row and row[0] != payload:
            raise ValueError('payload_conflict')
        if not row:
            db.execute('INSERT INTO operations VALUES (?,?,?,?)', (actor, key, payload, 'pending'))
    if fail_after_commit:
        raise RuntimeError('synthetic_crash')
    recover(db_path)


def recover(db_path):
    # This fixture's effect is in the same SQLite database. It does NOT prove
    # atomicity with a real remote API or exactly-once message delivery.
    with sqlite3.connect(db_path, timeout=3) as db:
        db.execute('BEGIN IMMEDIATE')
        pending = db.execute("SELECT actor,key FROM operations WHERE state='pending'").fetchall()
        for actor, key in pending:
            db.execute('INSERT OR IGNORE INTO effects VALUES (?,?)', (actor, key))
            db.execute("UPDATE operations SET state='completed' WHERE actor=? AND key=?", (actor, key))


EVENT_KEY = b'SYNTHETIC_EVENT_KEY_NOT_FOR_PRODUCTION'


def sign_event(body, timestamp, key=EVENT_KEY):
    return hmac.new(key, str(timestamp).encode() + b'.' + body, hashlib.sha256).hexdigest()


def event(db_path, body, timestamp, signature, now, account='account-a', unsafe=False):
    # A deliberately small signed-event protocol, NOT the Stripe protocol.
    if not unsafe:
        if not hmac.compare_digest(sign_event(body, timestamp), signature):
            raise ValueError('signature')
        if not 0 <= now - timestamp <= 30:  # Fixture-only policy, not a recommended window.
            raise ValueError('freshness')
    value = json.loads(body)
    if value['type'] != 'approved' or not isinstance(value['version'], int):
        raise ValueError('schema')
    with sqlite3.connect(db_path, timeout=3) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT account,version FROM objects WHERE id=?', (value['object'],)).fetchone()
        if not row or row[0] != account or value['account'] != account:
            raise ValueError('scope')
        if not unsafe:
            inserted = db.execute('INSERT OR IGNORE INTO events VALUES (?,?)', (account, value['id'])).rowcount
            if not inserted or value['version'] <= row[1]:
                return 'ignored'
        db.execute('UPDATE objects SET version=?,state=? WHERE id=?', (value['version'], 'approved', value['object']))
        return 'applied'


class Keys:
    """HMAC signing lifecycle fixture; no encryption or hardware guarantees."""
    def __init__(self):
        self.material = {'v1': b'SYNTHETIC_KEY_V1', 'v2': b'SYNTHETIC_KEY_V2'}
        self.states = {'v1': 'active', 'v2': 'inactive'}
        self.active = 'v1'

    def sign(self, actor, purpose, data, version=None):
        version = version or self.active
        if actor != 'writer' or purpose != 'receipt' or self.states.get(version) != 'active':
            raise ValueError('key_policy')
        key = self.material[version]  # Missing material fails; no fallback.
        return version, hmac.new(key, b'receipt:' + version.encode() + b':' + data, hashlib.sha256).digest()

    def verify(self, version, data, signature):
        if self.states.get(version) not in ('active', 'verify-only'):
            return False
        expected = hmac.new(self.material[version], b'receipt:' + version.encode() + b':' + data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)

    def rotate(self):
        self.states.update(v1='verify-only', v2='active')
        self.active = 'v2'

    def restore(self, actor, version, material):
        if actor != 'recovery-operator' or self.states.get(version) not in ('active', 'verify-only'):
            raise ValueError('recovery_policy')
        self.material[version] = material


class CachedProfiles:
    """Application cache with fixed fixture principals, not a session provider."""
    def __init__(self, unsafe=False):
        self.cache = {}
        self.allowed = {'alice'}
        self.computations = 0
        self.unsafe = unsafe

    def get(self, actor, variant='short'):
        key = '/profile' if self.unsafe else (actor, variant)
        if self.unsafe and key in self.cache:
            return self.cache[key]  # Deliberately bypasses authorization on hit.
        if actor not in self.allowed:
            raise ValueError('access')
        if key not in self.cache:
            self.computations += 1
            self.cache[key] = {'actor': actor, 'variant': variant, 'private': 'SYNTHETIC_PROFILE'}
        return self.cache[key]


def mcp_gate(origin, identity, allowed_origin, unsafe=False):
    """Selected local HTTP policy allows missing Origin only with a test identity."""
    if not unsafe and origin is not None and origin != allowed_origin:
        return 403
    if identity != 'SYNTHETIC_CLIENT':
        return 401
    return 200
