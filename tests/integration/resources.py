"""Own only resources created by this run. Never prune shared Docker state."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import uuid


class Resources:
    def __init__(self):
        self.owner = 'pss-' + uuid.uuid4().hex
        self.processes = []
        self.containers = []
        self.networks = []
        self.temporary = []
        self.cleanup_errors = []
        self.previous_signal = None

    def __enter__(self):
        self.previous_signal = signal.signal(signal.SIGTERM, self.interrupt)
        return self

    @staticmethod
    def interrupt(signum, frame):
        raise InterruptedError('runner_terminated')

    def tempdir(self):
        value = tempfile.TemporaryDirectory(prefix=self.owner + '-')
        self.temporary.append(value)
        return Path(value.name)

    def spawn(self, command, **kwargs):
        process = subprocess.Popen(command, start_new_session=True, **kwargs)
        self.processes.append(process)
        return process

    @staticmethod
    def docker(*args):
        return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE, timeout=60).strip()

    def network(self):
        identifier = self.docker('network', 'create', '--label', 'pss.owner=' + self.owner, self.owner)
        self.networks.append(identifier)
        return identifier

    def container(self, image, command, options=()):
        # Create first, so failures in start/wait still have a registered immutable ID.
        identifier = self.docker('create', '--label', 'pss.owner=' + self.owner,
                                 *options, image, *command)
        self.containers.append(identifier)
        return identifier

    def cleanup(self):
        # Finish every independent cleanup even if an earlier one fails.
        for process in reversed(self.processes):
            try:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                # Reap/terminate remaining children in the owned group after parent exit.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except Exception as error:
                self.cleanup_errors.append('process:' + type(error).__name__)
        for kind, identifiers in [('container', self.containers), ('network', self.networks)]:
            for identifier in reversed(identifiers):
                try:
                    data = json.loads(self.docker(kind, 'inspect', identifier))[0]
                    labels = data['Config']['Labels'] if kind == 'container' else data['Labels']
                    if labels.get('pss.owner') != self.owner:
                        raise RuntimeError('ownership_mismatch')
                    self.docker(kind, 'rm', *(['-f', '-v'] if kind == 'container' else []), identifier)
                    remaining = self.docker(kind, 'ls', *(['-aq'] if kind == 'container' else ['-q']), '--filter', 'id=' + identifier)
                    if remaining:
                        raise RuntimeError('resource_remains')
                except Exception as error:
                    self.cleanup_errors.append(kind + ':' + type(error).__name__)
        for temporary in reversed(self.temporary):
            try:
                temporary.cleanup()
                if Path(temporary.name).exists():
                    raise RuntimeError('temporary_directory_remains')
            except Exception as error:
                self.cleanup_errors.append('temporary:' + type(error).__name__)
        return not self.cleanup_errors

    def __exit__(self, exc_type, exc, traceback):
        # Do not let a second SIGTERM interrupt cleanup; SIGKILL cannot be handled.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            self.cleanup()
        finally:
            signal.signal(signal.SIGTERM, self.previous_signal)
        if self.cleanup_errors and exc is None:
            raise RuntimeError('resource_cleanup_failed: ' + ','.join(self.cleanup_errors))
