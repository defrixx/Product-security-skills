"""Observe effects and durable state across alternate paths and process death."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from lifecycle_fixture import Catalog, initialize_effects, issue


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def catalog(self, unsafe=False):
        c = Catalog(self.root/'authority.db', self.root/'projections.db', unsafe)
        c.initialize()
        return c

    def test_alternate_paths_preserve_scope_and_allowed_behavior(self):
        c = self.catalog()
        for route in ('detail', 'cache', 'search', 'export', 'job'):
            with self.subTest(route=route):
                self.assertEqual(c.read(route, 'alice', 'A', 'one'), 'SYNTHETIC_A')
                self.assertEqual(c.read(route, 'bob', 'B', 'two'), 'SYNTHETIC_B')
                self.assertIsNone(c.read(route, 'alice', 'A', 'two'))
                self.assertIsNone(c.read(route, 'alice', 'B', 'two'))
        c.unsafe = True
        self.assertIsNone(c.read('detail', 'alice', 'A', 'two'))
        for route in ('cache', 'search', 'export', 'job'):
            self.assertEqual(c.read(route, 'alice', 'A', 'two'), 'SYNTHETIC_B')

    def test_revocation_and_transfer_with_warm_projections(self):
        c = self.catalog()
        c.grant('alice', 'A', False)
        for route in ('detail', 'cache', 'search', 'export', 'job'):
            self.assertIsNone(c.read(route, 'alice', 'A', 'one'))
        c.grant('alice', 'A', True)
        c.change('one', scope='B')
        for route in ('cache', 'search', 'export', 'job'):
            self.assertIsNone(c.read(route, 'alice', 'A', 'one'))
            self.assertIsNone(c.read(route, 'bob', 'B', 'one'))  # Stale projection is not current output.
        c.publish(c.snapshot('one'))
        self.assertEqual(c.read('job', 'bob', 'B', 'one'), 'SYNTHETIC_NEW')
        c.unsafe = True
        self.assertEqual(c.read('export', 'alice', 'A', 'one'), 'SYNTHETIC_NEW')

    def test_late_publish_after_deletion_cannot_resurrect_output(self):
        c = self.catalog()
        old = c.snapshot('one')
        c.delete('one')
        self.assertFalse(c.publish(old))
        for route in ('detail', 'cache', 'search', 'export', 'job'):
            self.assertIsNone(c.read(route, 'alice', 'A', 'one'))
        # Reopen both durable stores; no in-memory invalidation is relied upon.
        restarted = Catalog(c.authority, c.projections)
        self.assertIsNone(restarted.read('search', 'alice', 'A', 'one'))
        restarted.unsafe = True
        self.assertTrue(restarted.publish(old))
        self.assertEqual(restarted.read('search', 'alice', 'A', 'one'), 'SYNTHETIC_A')

    def test_unpublish_and_revision_ordering(self):
        c = self.catalog()
        old = c.snapshot('one')
        c.change('one', active=0)
        self.assertFalse(c.publish(old))
        self.assertIsNone(c.read('cache', 'alice', 'A', 'one'))
        c.change('one', active=1)
        new = c.snapshot('one')
        self.assertTrue(c.publish(new))
        self.assertFalse(c.publish(old))
        self.assertEqual(c.read('search', 'alice', 'A', 'one'), 'SYNTHETIC_NEW')
        c.unsafe = True
        c.publish(old)
        self.assertEqual(c.read('search', 'alice', 'A', 'one'), 'SYNTHETIC_A')

    def effect_count(self, provider):
        with sqlite3.connect(provider) as db:
            return db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]

    def crash_worker(self, caller, provider, stage, unsafe):
        code = '''import os,sys
from lifecycle_fixture import issue
def checkpoint(stage):
    if stage == sys.argv[3]: os._exit(23)
issue(sys.argv[1],sys.argv[2],'alice','issue','key','payload',unsafe=sys.argv[4]=='1',checkpoint=checkpoint)
'''
        result = subprocess.run([sys.executable, '-c', code, str(caller), str(provider), stage, str(int(unsafe))],
                                cwd=Path(__file__).parent, timeout=15, capture_output=True)
        self.assertEqual(result.returncode, 23, result.stderr.decode())

    def test_process_crash_boundaries_and_recovery(self):
        for stage in ('intent_committed', 'effect_committed', 'completion_committed'):
            with self.subTest(stage=stage):
                caller, provider = self.root/(stage+'-caller.db'), self.root/(stage+'-provider.db')
                initialize_effects(caller, provider)
                self.crash_worker(caller, provider, stage, False)
                self.assertEqual(self.effect_count(provider), 0 if stage == 'intent_committed' else 1)
                with sqlite3.connect(caller) as db:
                    self.assertEqual(db.execute('SELECT state FROM operations').fetchone()[0],
                                     'completed' if stage == 'completion_committed' else 'pending')
                issue(caller, provider, 'alice', 'issue', 'key', 'payload')
                self.assertEqual(self.effect_count(provider), 1)
                with sqlite3.connect(caller) as db:
                    self.assertEqual(db.execute('SELECT state FROM operations').fetchone()[0], 'completed')

    def test_lost_reply_unsafe_control_duplicates_committed_effect(self):
        caller, provider = self.root/'caller.db', self.root/'provider.db'
        initialize_effects(caller, provider)
        self.crash_worker(caller, provider, 'effect_committed', True)
        self.assertEqual(self.effect_count(provider), 1)
        issue(caller, provider, 'alice', 'issue', 'key', 'payload', unsafe=True)
        self.assertEqual(self.effect_count(provider), 2)

    def test_concurrent_retry_identity_and_payload_conflict(self):
        caller, provider = self.root/'caller.db', self.root/'provider.db'
        initialize_effects(caller, provider)
        # Concurrent attempts use independent connections to both stores.
        barrier = threading.Barrier(2)
        def checkpoint(stage):
            if stage == 'intent_committed':
                barrier.wait(timeout=5)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: issue(caller, provider, 'alice', 'issue', 'key', 'payload', checkpoint=checkpoint), range(2)))
        self.assertEqual(results, ['completed', 'completed'])
        self.assertEqual(self.effect_count(provider), 1)
        with self.assertRaisesRegex(ValueError, 'payload_conflict'):
            issue(caller, provider, 'alice', 'issue', 'key', 'different')
        self.assertEqual(self.effect_count(provider), 1)
        issue(caller, provider, 'bob', 'issue', 'key', 'other actor')
        issue(caller, provider, 'alice', 'other-operation', 'key', 'other operation')
        self.assertEqual(self.effect_count(provider), 3)
