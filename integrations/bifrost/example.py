"""Synthetic local example. Running this explicitly sends one gateway request."""
import json
from pathlib import Path
from prompt_guard import load_policy, OutputGuard
from client import GuardedClient

root = Path(__file__).resolve().parents[2]
policy = load_policy(root / 'tools/prompt-guard/examples/policy.json', config_root=root,
                     expected_id='synthetic-demo', expected_version='1',
                     expected_sha256='a7f6f2d3fb89550dcf4e7330d376f01beea1254a27d9d06aa066def559d71a1d')
client = GuardedClient('ollama/local-model', policy, OutputGuard.create(policy))
if __name__ == '__main__':
    print(client.complete(json.dumps({'messages': [{'source': 'user', 'text': 'Hello'}]}).encode()))
