#!/usr/bin/env python3
"""Run opt-in synthetic integrations; retain failure and owned-resource cleanup evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from resources import Resources

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import requirement_evidence
IMAGES = {'python': 'python:3.12-slim', 'next': 'mcr.microsoft.com/playwright:v1.55.1-noble',
          'protocols': 'python:3.12-slim'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stack', choices=IMAGES)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--inject-failure', choices=['after-start'])
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('timeout must be positive')
    args.output.mkdir(mode=0o700, exist_ok=False)
    fixture = HERE / args.stack
    image = IMAGES[args.stack]
    resources = Resources()
    report = {'stack': args.stack, 'date_utc': datetime.now(timezone.utc).isoformat(), 'status': 'failed',
              'exit_code': 1, 'owner': resources.owner, 'cleanup_ok': False,
              'limits': ['synthetic integrations, not independent agent or target-project evaluation',
                         'dependency installation requires network; no host port published',
                         'SIGKILL, host crash and unavailable Docker daemon cannot guarantee cleanup',
                         'protocol issuer and accounts are synthetic; see fixture documentation']}
    started = None
    try:
        with resources:
            report['docker'] = resources.docker('version', '--format', '{{.Server.Version}}')
            report['image'] = image
            report['image_id'] = resources.docker('image', 'inspect', '--format', '{{.Id}}', image)
            options = ['--mount', 'type=bind,source=' + str(fixture) + ',target=/fixture,readonly']
            if args.stack in ('python', 'protocols'):
                shell = 'pip install --disable-pip-version-check -r /fixture/requirements.txt && pip freeze && python /fixture/checks.py'
                if args.stack == 'protocols':
                    network = resources.network()
                    mongo_image = 'mongo:8.0.15'
                    report['mongo_image_id'] = resources.docker('image', 'inspect', '--format', '{{.Id}}', mongo_image)
                    mongo = resources.container(mongo_image, ['mongod', '--bind_ip_all'], ['--network', network, '--network-alias', 'synthetic-mongo'])
                    resources.docker('start', mongo)
                    for attempt in range(60):
                        try:
                            resources.docker('exec', mongo, 'mongosh', '--quiet', '--eval', 'db.adminCommand({ping:1})')
                            break
                        except subprocess.CalledProcessError:
                            if attempt == 59: raise
                            time.sleep(.25)
                    options += ['--network', network, '-e', 'SYNTHETIC_MONGO_URI=mongodb://synthetic-mongo:27017']
            else:
                options += ['-e', 'NEXT_TELEMETRY_DISABLED=1', '-e', 'SYNTHETIC_PRIVATE_CREDENTIAL=SYNTHETIC_BROWSER_CANARY_20260924']
                shell = 'cp -R /fixture /tmp/app && cd /tmp/app && npm ci --ignore-scripts --no-audit --no-fund && npm run build && node checks.mjs'
            container = resources.container(image, ['sh', '-c', shell], options)
            with (args.output / 'run.log').open('w') as log:
                started = resources.spawn(['docker', 'start', '-a', container], stdout=log, stderr=subprocess.STDOUT)
                if args.inject_failure:
                    raise RuntimeError('injected_after_start')
                code = started.wait(timeout=args.timeout)
            report.update(exit_code=code, status='passed' if code == 0 else 'failed')
    except (Exception, KeyboardInterrupt) as error:
        report.update(error=type(error).__name__, exit_code=1, status='failed')
    finally:
        report['cleanup_ok'] = not resources.cleanup_errors
        report['cleanup_errors'] = resources.cleanup_errors
        report['containers'] = resources.containers
        report['networks'] = resources.networks
        if resources.cleanup_errors:
            report.update(status='failed', exit_code=1)
        files = list(fixture.rglob('*')) + list((ROOT/'skills').rglob('*.md')) + [Path(__file__), HERE/'resources.py', HERE/'coverage.json', ROOT/'scripts/requirement_evidence.py']
        report['source_fingerprints'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in files if p.is_file() and '__pycache__' not in p.parts}
        report['revision'] = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        report['working_tree'] = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).splitlines()
        mappings = [row for row in json.loads((HERE/'coverage.json').read_text()) if row['stack'] == args.stack]
        log_path = args.output/'run.log'
        observed = {}
        if log_path.exists():
            for line in log_path.read_text(errors='replace').splitlines():
                if 'PSS_CASE ' in line:
                    item = json.loads(line.split('PSS_CASE ', 1)[1])
                    observed[item['case']] = item
        report['outcomes'] = [observed.get(row['case'], {'case': row['case'], 'result': 'not_observed'}) for row in mappings]
        if mappings and any(item['result'] != 'passed' for item in report['outcomes']):
            report.update(status='failed', exit_code=1)
        if mappings:
            evidence = requirement_evidence.build(requirement_evidence.inventory(ROOT), mappings, report['outcomes'], str(args.output))
            evidence['kind'] = 'synthetic framework integration; no agent evaluation'
            (args.output/'requirement-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        (args.output/'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'stack': args.stack, 'status': report['status'], 'cleanup_ok': report['cleanup_ok']}))
    return report['exit_code']

if __name__ == '__main__':
    sys.exit(main())
