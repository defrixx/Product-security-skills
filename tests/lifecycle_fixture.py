"""Synthetic lifecycle fixtures with intentionally unsafe and safe controls.

Catalog projections use a second SQLite file. The receipt provider is another
SQLite database, committed independently of the caller's operation log. These
are bounded protocol simulations, not provider SDK or distributed-engine tests.
"""
import sqlite3
from contextlib import closing


def connect(path):
    return sqlite3.connect(path, timeout=5)


class Catalog:
    def __init__(self, authority, projections, unsafe=False):
        self.authority, self.projections, self.unsafe = authority, projections, unsafe

    def initialize(self):
        with closing(connect(self.authority)) as db, db:
            db.executescript('''
                CREATE TABLE documents(id TEXT PRIMARY KEY, scope TEXT, revision INTEGER, active INTEGER, body TEXT);
                INSERT INTO documents VALUES ('one','A',1,1,'SYNTHETIC_A'), ('two','B',1,1,'SYNTHETIC_B');
                CREATE TABLE grants(actor TEXT, scope TEXT, PRIMARY KEY(actor,scope));
                INSERT INTO grants VALUES ('alice','A'), ('bob','B');
            ''')
        with closing(connect(self.projections)) as db, db:
            db.execute('CREATE TABLE copies(route TEXT, id TEXT, scope TEXT, revision INTEGER, body TEXT, PRIMARY KEY(route,id))')
        for doc in ('one', 'two'):
            self.publish(self.snapshot(doc))

    def snapshot(self, doc):
        with closing(connect(self.authority)) as db:
            return db.execute('SELECT id,scope,revision,active,body FROM documents WHERE id=?', (doc,)).fetchone()

    def publish(self, event):
        if event is None:
            return False
        if not self.unsafe and (self.snapshot(event[0]) != event or not event[3]):
            return False
        with closing(connect(self.projections)) as db, db:
            for route in ('cache', 'search', 'export', 'job'):
                db.execute('INSERT OR REPLACE INTO copies VALUES (?,?,?,?,?)',
                           (route, event[0], event[1], event[2], event[4]))
        return True

    def grant(self, actor, scope, enabled):
        with closing(connect(self.authority)) as db, db:
            if enabled:
                db.execute('INSERT OR IGNORE INTO grants VALUES (?,?)', (actor, scope))
            else:
                db.execute('DELETE FROM grants WHERE actor=? AND scope=?', (actor, scope))

    def change(self, doc, *, active=1, scope='A', body='SYNTHETIC_NEW'):
        with closing(connect(self.authority)) as db, db:
            db.execute('UPDATE documents SET revision=revision+1,active=?,scope=?,body=? WHERE id=?',
                       (active, scope, body, doc))

    def delete(self, doc):
        with closing(connect(self.authority)) as db, db:
            db.execute('DELETE FROM documents WHERE id=?', (doc,))

    def read(self, route, actor, scope, doc):
        if route not in ('detail', 'cache', 'search', 'export', 'job'):
            raise ValueError('unknown_route')
        with closing(connect(self.authority)) as db:
            granted = db.execute('SELECT 1 FROM grants WHERE actor=? AND scope=?', (actor, scope)).fetchone()
        current = self.snapshot(doc)
        allowed = bool(granted and current and current[1] == scope and current[3])
        if route == 'detail':  # Partial repair: even the unsafe control protects detail.
            return current[4] if allowed else None
        with closing(connect(self.projections)) as db:
            copy = db.execute('SELECT scope,revision,body FROM copies WHERE route=? AND id=?', (route, doc)).fetchone()
        if self.unsafe:
            return copy[2] if copy else None
        if not allowed or not copy or (copy[0], copy[1]) != (scope, current[2]):
            return None
        return copy[2]


def initialize_effects(caller, provider):
    with closing(connect(caller)) as db, db:
        db.execute('CREATE TABLE operations(actor TEXT, operation TEXT, key TEXT, payload TEXT, state TEXT, PRIMARY KEY(actor,operation,key))')
    with closing(connect(provider)) as db, db:
        db.execute('CREATE TABLE effects(id INTEGER PRIMARY KEY, actor TEXT, operation TEXT, key TEXT, payload TEXT, UNIQUE(actor,operation,key))')


def issue(caller, provider, actor, operation, key, payload, *, unsafe=False, checkpoint=lambda stage: None):
    # Intent commit and provider commit are deliberately separate transactions.
    with closing(connect(caller)) as db, db:
        db.execute('INSERT OR IGNORE INTO operations VALUES (?,?,?,?,?)', (actor, operation, key, payload, 'pending'))
        stored = db.execute('SELECT payload,state FROM operations WHERE actor=? AND operation=? AND key=?', (actor, operation, key)).fetchone()
        if stored[0] != payload:
            raise ValueError('payload_conflict')
        if stored[1] == 'completed':
            return 'completed'
    checkpoint('intent_committed')
    with closing(connect(provider)) as db, db:
        # Unsafe: request identity changes on delivery, so a lost reply duplicates an effect.
        provider_key = key
        if unsafe:
            db.execute('BEGIN IMMEDIATE')
            provider_key = key + ':' + str(db.execute('SELECT COUNT(*) FROM effects').fetchone()[0])
        db.execute('INSERT OR IGNORE INTO effects(actor,operation,key,payload) VALUES (?,?,?,?)',
                   (actor, operation, provider_key, payload))
        stored = db.execute('SELECT payload FROM effects WHERE actor=? AND operation=? AND key=?',
                            (actor, operation, provider_key)).fetchone()
        if stored[0] != payload:
            raise ValueError('provider_payload_conflict')
    checkpoint('effect_committed')
    with closing(connect(caller)) as db, db:
        db.execute("UPDATE operations SET state='completed' WHERE actor=? AND operation=? AND key=?", (actor, operation, key))
    checkpoint('completion_committed')
    return 'completed'
