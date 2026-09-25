#!/usr/bin/env python3
"""Run an opt-in synthetic framework check and retain exact evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stack', choices=['python', 'next'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    fixture = HERE / args.stack
    image = 'python:3.12-slim' if args.stack == 'python' else 'mcr.microsoft.com/playwright:v1.55.1-noble'
    name = 'pss-framework-' + uuid.uuid4().hex[:12]
    command = ['docker', 'run', '--rm', '--name', name, '--mount', 'type=bind,source='+str(fixture)+',target=/fixture,readonly']
    if args.stack == 'python':
        shell = 'pip install --disable-pip-version-check -r /fixture/requirements.txt && python /fixture/checks.py'
    else:
        command += ['-e', 'NEXT_TELEMETRY_DISABLED=1', '-e', 'SYNTHETIC_PRIVATE_CREDENTIAL=SYNTHETIC_BROWSER_CANARY_20260924']
        shell = 'cp -R /fixture /tmp/app && cd /tmp/app && npm ci --ignore-scripts --no-audit --no-fund && npm run build && node checks.mjs'
    command += [image, 'sh', '-c', shell]
    image_id = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], text=True).strip()
    try:
        with (args.output/'run.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    report = {'stack': args.stack, 'date_utc': datetime.now(timezone.utc).isoformat(),
              'exit_code': result.returncode, 'status': 'passed' if result.returncode == 0 else 'failed',
              'image': image, 'image_id': image_id,
              'source_fingerprints': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()},
              'limits': ['synthetic app; not target-project verification', 'network allowed for dependency installation', 'see run.log for exact versions and individual checks']}
    (args.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'stack': args.stack, 'status': report['status']}))
    raise SystemExit(result.returncode)

if __name__ == '__main__': main()
