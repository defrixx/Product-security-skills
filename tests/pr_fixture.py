"""Build a disposable known-ground-truth repository; never run this on user repos.
SQL interpolation below is intentionally vulnerable test material. Parameter
binding in the guarded function is the secure control case.
"""
import os
from pathlib import Path
import subprocess

BASE='''# Synthetic evaluation code; intentionally vulnerable legacy lookup.
def legacy(db, value):
    # Existing issue, unrelated to the new feature.
    return db.execute("SELECT name FROM records WHERE name = '" + value + "'").fetchall()

def recent(db, value):
    return db.execute("SELECT name FROM records WHERE name = ?", (value,)).fetchall()

def guarded(db, value):
    return db.execute("SELECT name FROM records WHERE name = ?", (value,)).fetchall()
'''
HEAD=BASE.replace('# Existing issue, unrelated to the new feature.', '# Updated comment near an existing issue.').replace(
    'def recent(db, value):\n    return db.execute("SELECT name FROM records WHERE name = ?", (value,)).fetchall()',
    'def recent(db, value):\n    # Deliberate regression for the evaluation corpus.\n    return db.execute("SELECT name FROM records WHERE name = \'" + value + "\'").fetchall()')

def git(repo,*args):
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_NOSYSTEM='1',
               GIT_AUTHOR_DATE='2026-01-01T00:00:00+00:00',GIT_COMMITTER_DATE='2026-01-01T00:00:00+00:00',
               GIT_AUTHOR_NAME='Synthetic Author',GIT_COMMITTER_NAME='Synthetic Author',
               GIT_AUTHOR_EMAIL='author@fixture.invalid',GIT_COMMITTER_EMAIL='author@fixture.invalid')
    return subprocess.run(['git','-c','core.hooksPath='+os.devnull,'-c','core.fsmonitor=false','-c','commit.gpgsign=false','-C',str(repo),*args],
                          env=env,check=True,capture_output=True,text=True).stdout.strip()

def build(repo):
    repo=Path(repo);repo.mkdir()
    git(repo,'init','-b','main')
    (repo/'app.py').write_text(BASE);git(repo,'add','app.py');git(repo,'commit','-m','Synthetic base')
    ancestor=git(repo,'rev-parse','HEAD')
    git(repo,'checkout','-b','feature')
    (repo/'app.py').write_text(HEAD);git(repo,'add','app.py');git(repo,'commit','-m','Synthetic feature regression')
    head=git(repo,'rev-parse','HEAD')
    git(repo,'checkout','main')
    (repo/'target-only.txt').write_text('Target branch change, not part of the feature.\n')
    git(repo,'add','target-only.txt');git(repo,'commit','-m','Advance target branch')
    base=git(repo,'rev-parse','HEAD')
    return {'base':base,'head':head,'merge_base':ancestor}
