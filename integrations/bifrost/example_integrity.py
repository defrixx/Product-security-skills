"""Synthetic opt-in ingress-integrity configuration; one request only on execution."""
import json
from pathlib import Path
from prompt_integrity import load_policy
from example import policy
from prompt_guard import OutputGuard
from client import GuardedClient
from integrity import GatewayIntegrity

root = Path(__file__).resolve().parent
baseline = load_policy(root / 'integrity-baseline.json', 'synthetic-support', '1',
                       config_root=root,
                       expected_sha256='c83a2d6c7c851af46be5b35d584000aac0e79f7e178567f455c5a22d1125bb54')
integrity = GatewayIntegrity(baseline, 'gateway')
client = GuardedClient('ollama/local-model', policy, OutputGuard.create(policy),
                       system='Answer questions about the synthetic demo catalog.', integrity=integrity)
if __name__ == '__main__':
    print(client.complete(json.dumps({'messages': [{'source': 'user', 'text': 'Hello'}]}).encode()))
