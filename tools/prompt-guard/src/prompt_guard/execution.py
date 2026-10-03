"""Process-wide admission and deadline-bound worker execution."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

CAPACITY = 4
_slots = threading.BoundedSemaphore(CAPACITY)


class ExecutionError(Exception):
    pass


def execute(task, limits, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ExecutionError('request_timeout')
    if not _slots.acquire(blocking=False):
        raise ExecutionError('worker_capacity_exhausted')
    try:
        task = dict(task, memory_mb=limits.get('memory_mb', 256))
        timeout = min(limits['timeout_ms'] / 1000, remaining)
        try:
            process = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('worker.py'))],
                                     input=json.dumps(task, ensure_ascii=True).encode(),
                                     capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise ExecutionError('request_timeout' if time.monotonic() >= deadline else 'scan_timeout') from None
        except OSError:
            raise ExecutionError('worker_failed') from None
        if time.monotonic() >= deadline:
            raise ExecutionError('request_timeout')
        if process.returncode != 0 or len(process.stdout) > 131072:
            raise ExecutionError('worker_failed')
        try:
            value = json.loads(process.stdout)
        except (ValueError, UnicodeError):
            raise ExecutionError('worker_failed') from None
        if not isinstance(value, dict):
            raise ExecutionError('worker_failed')
        if 'error' in value:
            code = value['error']
            if code not in ('policy_invalid', 'empty_match', 'match_limit', 'memory_limit', 'memory_limit_unavailable'):
                code = 'worker_failed'
            raise ExecutionError(code)
        return value
    finally:
        _slots.release()
