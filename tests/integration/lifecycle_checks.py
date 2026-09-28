#!/usr/bin/env python3
"""Opt-in real Docker failure cleanup with a separately owned sentinel scope."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from resources import Resources

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_resource_cleanup import ready, listening


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = {'status': 'failed', 'cases': [], 'limits': ['no SIGKILL/host-crash guarantee', 'Docker daemon available during cleanup', 'sentinel belongs to a separate synthetic scope; no real foreign resources modified']}
    def absent(kind, identifier):
        ids = Resources.docker(kind, 'ls', *(['-aq'] if kind == 'container' else ['-q']))
        # Container ls abbreviates IDs; network IDs may also be abbreviated.
        assert not any(identifier.startswith(value) for value in ids.split()), (kind, identifier)
    try:
        result['docker'] = Resources.docker('version', '--format', '{{.Server.Version}}')
        result['image_id'] = Resources.docker('image', 'inspect', '--format', '{{.Id}}', 'python:3.12-slim')
        with Resources() as sentinel:
            network = sentinel.network()
            container = sentinel.container('python:3.12-slim', ['python', '-m', 'http.server', '8080'], ['--network', network, '-p', '127.0.0.1::8080', '--mount', 'type=volume,target=/scratch'])
            sentinel.docker('start', container)
            other = json.loads(sentinel.docker('inspect', container))[0]
            other_port = int(other['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort'])
            for attempt in range(40):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:' + str(other_port), timeout=1) as response: assert response.status == 200
                    break
                except OSError:
                    if attempt == 39: raise
                    time.sleep(.1)
            with tempfile.TemporaryDirectory(prefix='pss-lifecycle-results-') as temporary:
                for fault in ['exception', 'timeout', 'sigterm']:
                    report = Path(temporary) / (fault + '.json')
                    worker = subprocess.Popen([sys.executable, str(HERE/'lifecycle_worker.py'), fault, '--docker', '--report', str(report)], stdout=subprocess.PIPE, text=True)
                    try:
                        owned = ready(worker, 60)
                        if fault == 'sigterm': worker.terminate()
                        assert worker.wait(timeout=30) == 1
                        actual = json.loads(report.read_text())
                        assert actual['cleanup_errors'] == [], actual
                        assert actual['error'] == {'exception': 'RuntimeError', 'timeout': 'TimeoutExpired', 'sigterm': 'InterruptedError'}[fault]
                        absent('container', owned['container']); absent('network', owned['network'])
                        for volume in owned['volumes']: absent('volume', volume)
                        assert not listening(owned['port']) and not listening(owned['container_port'])
                        assert not Path(owned['temporary']).exists()
                        assert json.loads(sentinel.docker('inspect', container))[0]['State']['Running']
                        assert listening(other_port)
                        assert json.loads(sentinel.docker('network', 'inspect', network))[0]['Id'] == network
                        for mount in other['Mounts']:
                            if mount['Type'] == 'volume': sentinel.docker('volume', 'inspect', mount['Name'])
                        result['cases'].append({'fault': fault, 'status': 'passed', 'owned': owned, 'cleanup_errors': actual['cleanup_errors'], 'separate_scope_preserved': True})
                    finally:
                        if worker.poll() is None: worker.terminate(); worker.wait(timeout=30)
                        worker.stdout.close()
            for label, arguments, expected in [
                    ('runner-error', ['--inject-failure', 'after-start'], 'RuntimeError'),
                    ('runner-timeout', ['--timeout', '0.001'], 'TimeoutExpired')]:
                output = args.output / label
                execution = subprocess.run([sys.executable, str(HERE/'run_framework.py'), 'python', '--output', str(output), *arguments], capture_output=True, text=True, timeout=90)
                actual = json.loads((output/'summary.json').read_text())
                assert execution.returncode == 1 and actual['status'] == 'failed'
                assert actual['error'] == expected and actual['cleanup_ok'], actual
                for identifier in actual['containers']: absent('container', identifier)
                assert json.loads(sentinel.docker('inspect', container))[0]['State']['Running']
                assert listening(other_port)
                result['cases'].append({'fault': label, 'status': 'passed', 'observed_error': actual['error'], 'separate_scope_preserved': True})
            result['sentinel'] = {'container': container, 'network': network, 'port': other_port}
        absent('container', container); absent('network', network)
        for mount in other['Mounts']:
            if mount['Type'] == 'volume': absent('volume', mount['Name'])
        assert not listening(other_port)
        result['status'] = 'passed'
    finally:
        root = HERE.parent.parent
        result['task'] = 'Inject exception, timeout and SIGTERM; verify owned resource removal and separate scope survival'
        result['revision'] = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        result['working_tree'] = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).splitlines()
        result['python'] = sys.version
        result['date_utc'] = datetime.now(timezone.utc).isoformat()
        result['source_fingerprints'] = {str(p.relative_to(HERE.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), HERE/'resources.py', HERE/'lifecycle_worker.py', HERE.parent/'test_resource_cleanup.py']}
        (args.output/'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'fault_cases': len(result['cases'])}))

if __name__ == '__main__': main()
