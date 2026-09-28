"""Fault-injection subprocess, only used by synthetic lifecycle tests."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from resources import Resources

SERVER = '''import socket,signal,time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
s=socket.socket();s.bind(('127.0.0.1',0));s.listen()
print(s.getsockname()[1],flush=True)
time.sleep(300)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fault', choices=['exception', 'timeout', 'sigterm'])
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--docker', action='store_true')
    args = parser.parse_args()
    resources = Resources()
    evidence = {'owner': resources.owner}
    try:
        with resources:
            temporary = resources.tempdir()
            (temporary / 'owned.txt').write_text('synthetic temporary output')
            child = resources.spawn([sys.executable, '-u', '-c', SERVER], stdout=subprocess.PIPE, text=True)
            port = int(child.stdout.readline())
            evidence.update(temporary=str(temporary), pid=child.pid, port=port)
            if args.docker:
                network = resources.network()
                container = resources.container('python:3.12-slim', ['python', '-m', 'http.server', '8080'],
                    ['--network', network, '-p', '127.0.0.1::8080', '--mount', 'type=volume,target=/scratch'])
                resources.docker('start', container)
                details = json.loads(resources.docker('inspect', container))[0]
                evidence.update(container=container, network=network,
                    volumes=[mount['Name'] for mount in details['Mounts'] if mount['Type'] == 'volume'],
                    container_port=int(details['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']))
                for attempt in range(40):
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:' + str(evidence['container_port']), timeout=1) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        if attempt == 39: raise
                        time.sleep(.1)
            print(json.dumps(evidence), flush=True)
            if args.fault == 'exception':
                raise RuntimeError('injected_failure')
            if args.fault == 'timeout':
                child.wait(timeout=.05)
            else:
                while True: time.sleep(.1)
    except (Exception, KeyboardInterrupt) as error:
        evidence['error'] = type(error).__name__
    finally:
        if 'child' in locals(): child.stdout.close()
        evidence['cleanup_errors'] = resources.cleanup_errors
        args.report.write_text(json.dumps(evidence))
    return 1

if __name__ == '__main__':
    sys.exit(main())
