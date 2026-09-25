"""Executed inside the synthetic app container, not on a target deployment."""
import os
from pathlib import Path
assert os.geteuid() == 65534
status = Path('/proc/self/status').read_text()
assert 'CapEff:\t0000000000000000' in status
assert 'NoNewPrivs:\t1' in status
assert Path('/run/secrets/synthetic').read_text().strip() == 'SYNTHETIC_COMPOSE_CANARY_20260924'
assert not Path('/var/run/docker.sock').exists()
assert not any('SYNTHETIC_COMPOSE_CANARY' in v for v in os.environ.values())
try:
    Path('/forbidden-write').write_text('test')
except OSError:
    pass
else:
    raise AssertionError('root_filesystem_writable')
Path('/work/allowed-write').write_text('synthetic')
assert Path('/work/allowed-write').read_text() == 'synthetic'
print('PASS runtime identity, capabilities, no-new-privileges, writable boundary and secret grant')
