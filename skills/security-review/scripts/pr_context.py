#!/usr/bin/env python3
"""Collect local PR revisions and change metadata without checkout, hooks, or fetch.
No vulnerability detector. Paths are opaque unless --include-paths is explicit.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

class ContextError(Exception): pass


def git(repo, *args):
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0',GIT_PAGER='cat')
    try:
        p=subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,
                          '-c','diff.external=','-C',str(repo),*args],env=env,capture_output=True,timeout=30)
    except (OSError,subprocess.TimeoutExpired): raise ContextError('git_unavailable_or_timeout') from None
    if p.returncode: raise ContextError('git_command_failed')
    if len(p.stdout)>8*1024*1024: raise ContextError('git_output_limit')
    return p.stdout


def collect(repo,base,head,include_paths=False):
    repo=Path(repo).resolve(strict=True)
    if git(repo,'rev-parse','--is-inside-work-tree').strip()!=b'true': raise ContextError('working_tree_required')
    def revision(ref,label):
        if not isinstance(ref,str) or ref.startswith('-') or '\x00' in ref: raise ContextError(label+'_invalid')
        try: return git(repo,'rev-parse','--verify','--end-of-options',ref+'^{commit}').decode().strip()
        except ContextError: raise ContextError(label+'_unavailable') from None
    base_id=revision(base,'base');head_id=revision(head,'head')
    try: merges=git(repo,'merge-base','--all',base_id,head_id).decode().splitlines()
    except ContextError: raise ContextError('merge_base_unavailable') from None
    if len(merges)!=1: raise ContextError('ambiguous_merge_base')
    raw=git(repo,'diff','--no-ext-diff','--no-textconv','--no-renames','--name-status','-z',merges[0],head_id,'--')
    fields=raw.split(b'\0');changes=[]
    if fields[-1]==b'': fields.pop()
    if len(fields)%2: raise ContextError('unexpected_diff_format')
    for i in range(0,len(fields),2):
        status=fields[i].decode('ascii')
        item={'id':'F%06d'%(len(changes)+1),'change':status}
        if include_paths: item['path']=os.fsdecode(fields[i+1])
        changes.append(item)
    dirty=bool(git(repo,'status','--porcelain=v1','-z','--untracked-files=normal'))
    return {'schema_version':1,'mode':'PR','base':base_id,'head':head_id,'merge_base':merges[0],
            'comparison':'merge_base_to_head','working_tree_dirty':dirty,
            'working_tree_included':False,'shallow':git(repo,'rev-parse','--is-shallow-repository').strip()==b'true',
            'changed_files':changes,'paths_included':include_paths,'rename_detection':False,
            'limitations':['metadata_only_not_a_security_review','renames_reported_as_delete_and_add',
                           'working_tree_changes_not_in_pr_diff','no_remote_access_or_checkout']}

class Parser(argparse.ArgumentParser):
    def error(self,message): raise ContextError('invalid_arguments')


def main(argv=None):
    try:
        p=Parser(description=__doc__)
        p.add_argument('--repo',required=True);p.add_argument('--base',required=True);p.add_argument('--head',required=True)
        p.add_argument('--output',required=True);p.add_argument('--include-paths',action='store_true')
        a=p.parse_args(argv);result=collect(a.repo,a.base,a.head,a.include_paths)
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps({'status':'collected','changed_files':len(result['changed_files'])}));return 0
    except ContextError as e: print(json.dumps({'status':'incomplete','code':str(e)}),file=sys.stderr);return 1
    except Exception: print('{"status":"incomplete","code":"operation_failed"}',file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
