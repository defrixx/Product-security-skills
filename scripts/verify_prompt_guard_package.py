#!/usr/bin/env python3
"""Build standalone distributions and verify a wheel in a disposable environment."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd, env=None, log=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    if log is not None:
        log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('package_check_failed')
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    evidence = {'task': 'Standalone sdist/wheel and isolated installation verification',
                'date_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
                'platform': platform.platform(), 'success': False}
    try:
        with tempfile.TemporaryDirectory(prefix='prompt-guard-package-') as tmp:
            temp = Path(tmp)
            source = temp / 'source'
            shutil.copytree(ROOT / 'tools/prompt-guard', source, ignore=shutil.ignore_patterns('__pycache__'))
            build = 'import setuptools.build_meta as b; b.build_sdist(' + repr(str(output)) + ')'
            evidence['phase'] = 'sdist'
            run([sys.executable, '-c', build], cwd=source, log=output / 'sdist-build.log')
            archive = next(output.glob('*.tar.gz'))
            extracted = temp / 'sdist'
            with tarfile.open(archive) as bundle:
                # Extract only regular files/directories under the archive prefix.
                for member in bundle.getmembers():
                    target = (extracted / member.name).resolve()
                    if not target.is_relative_to(extracted.resolve()) or not (member.isfile() or member.isdir()):
                        raise RuntimeError('sdist_invalid')
                bundle.extractall(extracted)
            package = next(extracted.iterdir())
            assert (package / 'tests/corpus.json').is_file()
            build = 'import setuptools.build_meta as b; b.build_wheel(' + repr(str(output)) + ')'
            evidence['phase'] = 'wheel'
            run([sys.executable, '-c', build], cwd=package, log=output / 'wheel-build.log')
            wheel = next(output.glob('*.whl'))
            with zipfile.ZipFile(wheel) as bundle:
                assert 'prompt_guard/worker.py' in bundle.namelist()
                assert len([n for n in bundle.namelist() if '/policies/' in n and n.endswith('.json')]) == 6
            runtime = temp / 'runtime'
            venv.EnvBuilder(with_pip=True).create(runtime)
            python = runtime / 'bin/python'
            evidence['phase'] = 'isolated-installation'
            environment = dict(os.environ, PROMPT_GUARD_TEST_PACKAGED='1')
            environment.pop('PYTHONPATH', None)
            run([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)], cwd=temp, env=environment)
            evidence['phase'] = 'installed-runtime-tests'
            run([str(python), '-I', '-m', 'unittest', 'discover', '-s', str(package / 'tests'), '-v'],
                cwd=temp, env=environment, log=output / 'tests.log')
            # Exercise the generated installed console script, not a source wrapper.
            source_input = temp / 'input'
            source_input.mkdir()
            (source_input / 'safe.txt').write_text('Public greeting API')
            run([str(runtime / 'bin/prompt-guard'), '--profile', 'security', '--input', str(source_input / 'safe.txt'),
                 '--input-root', str(source_input)], cwd=temp, env=environment)
            probe = ('import json,pathlib; from prompt_guard.evaluation import evaluate_corpus; '
                     'v=json.loads(pathlib.Path(' + repr(str(package / 'tests/corpus.json')) + ').read_text()); '
                     'print(json.dumps(evaluate_corpus(v["cases"],repetitions=2)))')
            evidence['phase'] = 'labeled-metrics'
            metrics = json.loads(run([str(python), '-I', '-c', probe], cwd=temp, env=environment))
            assert metrics['all_expected']
            (output / 'detector-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
            evidence.update(success=True, sdist=archive.name, wheel=wheel.name,
                            method='Build wheel from standalone sdist; install offline only in a disposable venv; run packaged runtime tests and installed console script',
                            latency_ms=metrics['latency_ms'], inputs_per_second=metrics['inputs_per_second'])
            parallel_probe = '''import json,time
from concurrent.futures import ThreadPoolExecutor
from prompt_guard import inspect,load_profile
policy=load_profile('security')
start=time.monotonic()
with ThreadPoolExecutor(max_workers=4) as pool:
    values=list(pool.map(lambda _: inspect(policy,b'Public greeting API').decision,range(40)))
elapsed=time.monotonic()-start
print(json.dumps({'workers':4,'inputs':40,'all_allowed':all(v=='allow' for v in values),'inputs_per_second':40/elapsed}))
'''
            parallel = json.loads(run([str(python), '-I', '-c', parallel_probe], cwd=temp, env=environment))
            assert parallel['all_allowed']
            evidence['parallel_measurement'] = parallel
            evidence['phase'] = 'complete'
    except Exception as error:
        evidence['failure_type'] = type(error).__name__
    finally:
        evidence['source_fingerprints'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in (ROOT / 'tools/prompt-guard').rglob('*')
                                           if p.is_file() and '__pycache__' not in p.parts}
        evidence['limits'] = ['Synthetic known-ground-truth fixtures', 'No live provider model in this package verification',
                              'Sequential and four-worker synthetic throughput; deployed load profiles are separate']
        (output / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n')
        for path in output.iterdir():
            if path.is_file():
                path.chmod(0o600)
    print(json.dumps({'success': evidence['success'], 'code': 'package_verified' if evidence['success'] else 'package_check_failed'}))
    return 0 if evidence['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
