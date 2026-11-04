"""Local synthetic final-provider service; running it explicitly opens a listener."""
import os
from pathlib import Path
from prompt_integrity import load_policy
from prompt_guard import OutputGuard
from example import policy
from client import LocalTransport
from egress import ProviderBoundary
from ingress import IngressServer

root = Path(__file__).resolve().parents[2]
baseline = load_policy(root / 'tools/prompt-integrity/examples/provider-baseline.json',
                       'synthetic-provider', '1', config_root=root,
                       expected_sha256='a11041578811398f5f4ea09fd9795877bf1bfbee9986187961550bace14804da')
boundary = ProviderBoundary(baseline, 'provider', policy, OutputGuard.create(policy),
                            LocalTransport('http://127.0.0.1:18082'))
if __name__ == '__main__':
    server = IngressServer(('127.0.0.1', 18081), boundary,
                           os.environ['BIFROST_PROVIDER_TOKEN'])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
