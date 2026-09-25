import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from support import pr_context
from pr_fixture import build,git

class PRReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.repo=self.root/'repo';self.ids=build(self.repo)
    def collect(self,**kwargs):return pr_context.collect(self.repo,self.ids['base'],self.ids['head'],**kwargs)
    def probe(self,revision):
        # Execute only our fixed synthetic fixture, not arbitrary target content.
        text=git(self.repo,'show',revision+':app.py');scope={};exec(compile(text,'synthetic_app.py','exec'),scope)
        db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.execute('CREATE TABLE records(name TEXT)');db.executemany('INSERT INTO records VALUES (?)',[('alpha',),('beta',)])
        return {name:len(scope[name](db,"' OR 1=1 --")) for name in ('legacy','recent','guarded')}
    def test_diverged_target_uses_merge_base(self):
        r=self.collect(include_paths=True)
        self.assertNotEqual(r['base'],r['merge_base']);self.assertEqual(r['merge_base'],self.ids['merge_base'])
        self.assertEqual([f['path'] for f in r['changed_files']],['app.py'])
    def test_introduced_existing_and_disproved_signals(self):
        base=self.probe(self.ids['base']);head=self.probe(self.ids['head']);ancestor=self.probe(self.ids['merge_base'])
        self.assertEqual((base['recent'],head['recent'],ancestor['recent']),(0,2,0))
        self.assertEqual((base['legacy'],head['legacy']),(2,2))
        self.assertEqual((base['guarded'],head['guarded']),(0,0))
    def test_dirty_and_untracked_worktree_preserved_and_not_in_pr(self):
        (self.repo/'app.py').write_text('LOCAL_UNCOMMITTED_CONTENT\n');(self.repo/'untracked.txt').write_text('LOCAL_UNTRACKED\n')
        before=git(self.repo,'status','--porcelain');r=self.collect(include_paths=True)
        self.assertTrue(r['working_tree_dirty']);self.assertFalse(r['working_tree_included'])
        self.assertEqual(before,git(self.repo,'status','--porcelain'));self.assertEqual((self.repo/'app.py').read_text(),'LOCAL_UNCOMMITTED_CONTENT\n')
        self.assertEqual([f['path'] for f in r['changed_files']],['app.py'])
    def test_missing_base_stops_without_fallback(self):
        before=git(self.repo,'rev-parse','HEAD')
        with self.assertRaisesRegex(pr_context.ContextError,'base_unavailable'):pr_context.collect(self.repo,'missing-base',self.ids['head'])
        self.assertEqual(before,git(self.repo,'rev-parse','HEAD'))
    def test_unrelated_history_is_incomplete(self):
        git(self.repo,'checkout','--orphan','unrelated')
        git(self.repo,'add','app.py');git(self.repo,'commit','-m','Unrelated synthetic root')
        other=git(self.repo,'rev-parse','HEAD')
        with self.assertRaisesRegex(pr_context.ContextError,'merge_base_unavailable'):
            pr_context.collect(self.repo,other,self.ids['head'])
    def test_missing_head_and_option_injection_rejected(self):
        for ref in ['missing-head','--help']:
            with self.subTest(ref=ref),self.assertRaises(pr_context.ContextError):pr_context.collect(self.repo,self.ids['base'],ref)
    def test_default_report_omits_paths(self):
        r=self.collect();self.assertNotIn('path',r['changed_files'][0]);self.assertNotIn('app.py',json.dumps(r))
    def test_hooks_fsmonitor_and_external_diff_not_run(self):
        sentinel=self.root/'UNEXPECTED_EXECUTION'
        script=self.root/'hook.sh';script.write_text('#!/bin/sh\ntouch "'+str(sentinel)+'"\n');script.chmod(0o700)
        git(self.repo,'config','core.fsmonitor',str(script));git(self.repo,'config','diff.external',str(script))
        git(self.repo,'config','core.hooksPath',str(self.root))
        self.collect();self.assertFalse(sentinel.exists())
    def test_cli_existing_output_not_overwritten(self):
        out=self.root/'report.json';out.write_text('keep')
        with contextlib.redirect_stderr(io.StringIO()):
            code=pr_context.main(['--repo',str(self.repo),'--base',self.ids['base'],'--head',self.ids['head'],'--output',str(out)])
        self.assertEqual(code,1);self.assertEqual(out.read_text(),'keep')
    def test_cli_missing_base_does_not_leak_ref_or_create_report(self):
        out=self.root/'report.json';err=io.StringIO()
        with contextlib.redirect_stderr(err):
            code=pr_context.main(['--repo',str(self.repo),'--base','SYNTHETIC_PRIVATE_REF','--head',self.ids['head'],'--output',str(out)])
        self.assertEqual(code,1);self.assertFalse(out.exists());self.assertNotIn('SYNTHETIC_PRIVATE_REF',err.getvalue())
    def test_valid_query_remains_functional(self):
        scope={};exec(git(self.repo,'show',self.ids['head']+':app.py'),scope)
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE records(name TEXT)');db.execute('INSERT INTO records VALUES (?)',('alpha',))
            self.assertEqual(scope['guarded'](db,'alpha'),[('alpha',)])

if __name__=='__main__':unittest.main()
