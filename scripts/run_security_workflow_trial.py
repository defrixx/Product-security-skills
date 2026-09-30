#!/usr/bin/env python3
"""Record fixture observations for a manually guided skill trial, not agent scoring."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from security_workflow_fixture import observe


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False,mode=0o700)
    files=[ROOT/'tests/security_workflow_fixture.py',ROOT/'scripts/run_security_workflow_trial.py']
    for skill in ('security-fix-verification','security-report-triage'):
        files.extend(p for p in (ROOT/'skills'/skill).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    def git(*args):
        return subprocess.check_output(['git','-c','core.fsmonitor=false','-C',str(ROOT),*args],text=True).strip()
    # Copy each skill independently; the helper imports no repository resources.
    copied=output/'copied-skills';copied.mkdir()
    for skill in ('security-fix-verification','security-report-triage'):
        shutil.copytree(ROOT/'skills'/skill,copied/skill,ignore=shutil.ignore_patterns('__pycache__'))
    sarif={'version':'2.1.0','runs':[{'tool':{'driver':{'name':'synthetic-scanner','rules':[{'id':'object-access'},{'id':'alternate-object-rule'}]}},'invocations':[{'executionSuccessful':True}],'results':[
        {'ruleIndex':1 if name=='export' else 0,'level':'error','message':{'text':'synthetic object-access signal'},'locations':[{'physicalLocation':{'artifactLocation':{'uri':name},'region':{'startLine':1}}}]} for name in ('read','export','safe','independent')]}]}
    input_path=output/'synthetic-report.sarif';input_path.write_text(json.dumps(sarif))
    command=[sys.executable,str((copied/'security-report-triage/scripts/normalize_sarif.py').resolve()),'--input',str(input_path.resolve()),'--output',str((output/'normalized').resolve())]
    normalized=subprocess.run(command,capture_output=True,text=True)
    if normalized.returncode != 0:raise RuntimeError('synthetic_normalization_failed')
    report={'task':'Triage duplicate object-read signals and a safe control, then verify synthetic candidate repairs.',
            'method':'manually guided known-ground-truth trial; actual Python functions, no HTTP/provider integration',
            'date_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'git':git('--version'),
            'repository_revision':git('rev-parse','HEAD'),'working_tree':git('status','--porcelain').splitlines(),
            'fingerprints':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
            'target_revision':'synthetic fixture content fingerprint, variants are explicit function mappings',
            'normalization':{'exit_code':normalized.returncode,'summary':'normalized/normalization-summary.json','results':'normalized/normalized.json'},
            'copied_skills':['security-fix-verification','security-report-triage'],
            'observations':observe(),'substitutions':['in-memory actors and records; no authentication/deployment layer'],
            'limits':['not an independent skill evaluation','no external targets or source changes','verdicts require manual assessment of observations']}
    (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'recorded','variants':len(report['observations']),'independent_evaluation':False}))


if __name__=='__main__':main()
