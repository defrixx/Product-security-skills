#!/usr/bin/env python3
"""Run synthetic behavior tests and record a reproducible PR-mode exercise.
Only writes a new output directory and disposable synthetic temporary repos.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from support import cleanup,pr_context
from pr_fixture import build,git
import requirement_evidence

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.outcomes=[]
    def addSuccess(self,test):super().addSuccess(test);self.outcomes.append({'case':test.id(),'result':'passed'})
    def addFailure(self,test,err):super().addFailure(test,err);self.outcomes.append({'case':test.id(),'result':'failed'})
    def addError(self,test,err):super().addError(test,err);self.outcomes.append({'case':test.id(),'result':'error'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.outcomes.append({'case':test.id(),'result':'skipped'})

def write(output,name,value):
    path=output/name
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
    path.chmod(0o600)

def pr_exercise(output):
    with tempfile.TemporaryDirectory(prefix='security-pr-evaluation-') as tmp:
        repo=Path(tmp)/'repo';ids=build(repo)
        context=pr_context.collect(repo,ids['base'],ids['head'],True)
        evidence={}
        for label,revision in [('base',ids['base']),('head',ids['head']),('merge_base',ids['merge_base'])]:
            namespace={};source=git(repo,'show',revision+':app.py')
            exec(compile(source,'synthetic_app.py','exec'),namespace)
            with sqlite3.connect(':memory:') as db:
                db.execute('CREATE TABLE records(name TEXT)');db.executemany('INSERT INTO records VALUES (?)',[('alpha',),('beta',)])
                evidence[label]={name:len(namespace[name](db,"' OR 1=1 --")) for name in ('legacy','recent','guarded')}
        report={'task':'Review the synthetic feature PR; distinguish new and existing injection issues and counterevidence.',
                'mode':'PR','context':context,'method':'manually designed fixture; actual Git commits and SQLite execution; no framework mocks',
                'threat_model':{'asset':'synthetic record isolation','entry':'lookup string passed by an untrusted caller',
                                'boundary':'value to SQL syntax','assumption':'a caller can control the value; no HTTP deployment is included'},
                'evidence':evidence,'findings':[
                    {'id':'PR-001','symbol':'recent','status':'confirmed','provenance':'introduced','confidence':'high within fixture',
                     'impact':'attacker input selects both records instead of no exact match','remediation':'bind the value as a parameter',
                     'fix_check':'attack input returns zero records; ordinary alpha lookup returns one'},
                    {'id':'PR-002','symbol':'legacy','status':'confirmed','provenance':'pre-existing','confidence':'high within fixture',
                     'impact':'same injection behavior on base, merge base, and head despite a nearby changed comment',
                     'remediation':'bind the value; track separately from introduced PR changes',
                     'fix_check':'attack input returns zero records; ordinary alpha lookup returns one'}],
                'disproved':[{'symbol':'guarded','reason':'bound parameter preserves input as data; attack returns no rows on every revision'}],
                'limitations':['known-ground-truth exercise, not blind agent scoring','no remote systems or real application deployment',
                               'no severity score assigned to synthetic data','hypothesis handling is evaluated by report guidance, not a model benchmark']}
        assert evidence['head']['recent']==2 and evidence['base']['recent']==0
        assert evidence['head']['legacy']==evidence['base']['legacy']==2
        assert all(evidence[x]['guarded']==0 for x in evidence)
        write(output,'pr-review.json',report)
        (output/'pr-review.md').write_text('''# Synthetic PR review

This is a known-ground-truth exercise using real local Git commits and SQLite, not independent agent scoring.

| Signal | Classification | Evidence |
| --- | --- | --- |
| `recent` lookup | Confirmed, introduced by PR | Attack returns 0 rows on base/merge base and 2 on head |
| `legacy` lookup | Confirmed, pre-existing | Attack returns 2 rows before and after the PR; only a nearby comment changes |
| `guarded` lookup | Disproved injection signal | Bound parameter returns 0 rows throughout; normal lookup succeeds |

The assumed attacker controls a lookup string; the simulated impact is reading unrelated synthetic records. Bind values to fix both confirmed issues. Verify malicious and valid inputs. No HTTP application or live data is involved, so deployment severity is not asserted.

Exact revisions, merge-base semantics, evidence, and remediation criteria are in [pr-review.json](pr-review.json). The feature excludes a target-only commit. The regression suite separately checks dirty-tree preservation, missing revisions, and disabled external Git helpers.
''')
        return ids

def cleanup_corpus(output):
    with tempfile.TemporaryDirectory(prefix='security-cleanup-corpus-') as tmp:
        root=Path(tmp);src=root/'source';src.mkdir()
        values={'labels':{'apiKey':'API key'},'credentials':{'apiKey':'SYNTHETIC_SEED_1'},'mail':'person@synthetic.invalid',
                'password':'SYNTHETIC_SEED_2','description':'API key','count':42}
        (src/'settings.json').write_text(json.dumps(values))
        policy={'suppressions':[{'file':'settings.json','pointer':'/labels/apiKey','expected_value':'API key','reason':'synthetic label'}]}
        result=cleanup.run(src,root/'output','clean-copy',policy)
        actual=json.loads((root/'output'/result['files'][0]['output']).read_text())
        sensitive=[actual['credentials']['apiKey']!=values['credentials']['apiKey'],actual['mail']!=values['mail'],actual['password']!=values['password']]
        benign=[actual['labels']['apiKey']==values['labels']['apiKey'],actual['description']==values['description'],actual['count']==values['count']]
        counts={'true_positive':sum(sensitive),'false_negative':3-sum(sensitive),'true_negative':sum(benign),'false_positive':3-sum(benign)}
        assert counts=={'true_positive':3,'false_negative':0,'true_negative':3,'false_positive':0}
        write(output,'cleanup-corpus.json',{'scope':'six labeled synthetic fields only','confusion_matrix':counts,
                                          'limitation':'does not estimate recall on an unlabeled real project','helper_counts':result['counts']})

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False,mode=0o700)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=1,resultclass=Result).run(suite)
    revisions=pr_exercise(output) if result.wasSuccessful() else None
    if result.wasSuccessful():cleanup_corpus(output)
    fingerprint={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['skills','tests','scripts'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and p.suffix in {'.md','.py','.json','.ts','.tsx','.mjs','.yaml','.yml','.txt'} and '__pycache__' not in p.parts}
    summary={'date_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
             'platform':platform.system(),'git':pr_context.git(ROOT,'--version').decode().strip(),'sqlite':sqlite3.sqlite_version,'test_count':result.testsRun,
             'success':result.wasSuccessful(),'outcomes':result.outcomes,'source_fingerprints':fingerprint,
             'repository_revision':pr_context.git(ROOT,'rev-parse','HEAD').decode().strip(),
             'working_tree':pr_context.git(ROOT,'status','--porcelain').decode().splitlines(),
             'task':'Repository synthetic regression and per-condition partial evidence inventory',
             'substitutions':['Injected outbound resolver, fixture identities and event protocol; see requirement-evidence.json'],
             'synthetic_pr_revisions':revisions,'limits':['not a blind model evaluation','no full framework/browser/container tests','no external project modified']}
    write(output,'summary.json',summary)
    coverage=requirement_evidence.build(requirement_evidence.inventory(ROOT), json.loads((ROOT/'tests/requirement_coverage.json').read_text()), result.outcomes, str(output))
    write(output,'requirement-evidence.json',coverage)
    print(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'pr_exercise':revisions is not None}))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':sys.exit(main())
