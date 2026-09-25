#!/usr/bin/env python3
"""Run a uniquely named synthetic Compose project and remove only its resources."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    project = 'pss_test_' + uuid.uuid4().hex[:12]
    image = project + ':synthetic'
    compose = ['docker', 'compose', '-p', project, '-f', str(HERE/'compose.yaml')]
    log = []
    def run(cmd, input=None):
        result = subprocess.run(cmd, input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        log.append(result.stdout.decode(errors='replace'))
        if result.returncode: raise RuntimeError('command_failed: ' + ' '.join(cmd[:3]))
        return result.stdout
    result = {'status': 'failed', 'checks': [], 'limits': ['synthetic deployment only', 'no public-network attack', 'base image tags are mutable']}
    try:
        result['docker'] = run(['docker', 'version', '--format', '{{.Server.Version}}']).decode().strip()
        result['compose'] = run(['docker', 'compose', 'version', '--short']).decode().strip()
        run(compose + ['up', '-d'])
        run(compose + ['exec', '-T', 'app', 'python', '-'], (HERE/'runtime_checks.py').read_bytes())
        result['checks'].append('SD-COMPOSE-004: nonroot, zero effective capabilities, no-new-privileges, denied root write, allowed tmpfs write')
        run(compose + ['exec', '-T', 'isolated', 'python', '-c', "from pathlib import Path; assert not Path('/run/secrets/synthetic').exists()"])
        result['checks'].append('SD-COMPOSE-002: intended service reads canary; ungranted service has no secret mount')
        ids = run(compose + ['ps', '-q']).decode().split()
        containers = json.loads(run(['docker', 'inspect'] + ids))
        for container in containers:
            service = container['Config']['Labels']['com.docker.compose.service']
            ports = container['NetworkSettings']['Ports'] or {}
            if service == 'isolated': assert not any(ports.values())
            else:
                mappings = ports['8080/tcp']
                assert len(mappings) == 1 and mappings[0]['HostIp'] == '127.0.0.1'
                address = 'http://127.0.0.1:' + mappings[0]['HostPort']
                for attempt in range(30):
                    try:
                        with urllib.request.urlopen(address, timeout=2) as response: assert response.status == 200
                        break
                    except OSError:
                        if attempt == 29: raise
                        time.sleep(.2)
        result['checks'].append('SD-COMPOSE-001: inspected loopback-only binding, successful HTTP, no secondary published ports')
        run(['docker', 'build', '--network=none', '--secret', 'id=synthetic,src='+str(HERE/'synthetic-secret.txt'), '-t', image, str(HERE)])
        canary = (HERE/'synthetic-secret.txt').read_bytes().strip()
        history = run(['docker', 'history', '--no-trunc', image])
        assert canary not in history
        assert canary not in run(['docker', 'image', 'inspect', image])
        run(['docker', 'run', '--rm', '--network=none', image, 'python', '-c', "from pathlib import Path; assert not Path('/run/secrets/synthetic').exists(); assert Path('/build-result').read_text() == 'authenticated synthetic step completed'"])
        with tempfile.TemporaryDirectory(prefix='pss-image-') as temp:
            archive = Path(temp)/'image.tar'
            run(['docker', 'save', '-o', str(archive), image])
            scanned = 0
            with tarfile.open(archive) as outer:
                for entry in outer:
                    if not entry.isfile(): continue
                    data = outer.extractfile(entry).read()
                    assert canary not in data
                    # Docker archive layers are tar; OCI exports may store compressed blobs.
                    try:
                        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as layer:
                            for member in layer:
                                if member.isfile():
                                    assert canary not in layer.extractfile(member).read()
                                    scanned += 1
                    except tarfile.ReadError:
                        pass
            assert scanned > 0, 'no_image_layer_files_scanned'
            result['layer_files_scanned'] = scanned
        assert all(canary.decode() not in entry for entry in log), 'canary_in_tool_logs'
        result['checks'].append('SD-COMPOSE-003: consumed BuildKit secret; absent from saved layers, history, config, runtime and captured logs')
        result['status'] = 'passed'
    finally:
        cleanup = subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], capture_output=True, timeout=60)
        result['compose_cleanup_ok'] = cleanup.returncode == 0
        subprocess.run(['docker', 'image', 'rm', image], capture_output=True, timeout=60)
        (args.output/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
        (args.output/'run.log').write_text('\n'.join(log))
    assert result['compose_cleanup_ok']
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
