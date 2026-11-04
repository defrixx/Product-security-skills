"""Explicit loopback buffered-agent facade; synthetic read tool proposals only.

No tool is executed here. The application must own history and ToolGate executors.
"""
import argparse,json,os
from pathlib import Path
from prompt_integrity import load_policy
from prompt_guard import OutputGuard
from example import policy
from agent_boundary import AgentBoundary
from client import LocalTransport
from ingress import IngressServer
ROOT=Path(__file__).resolve().parents[2]
PINS={'gateway': '57d0ac289063547517c980cc2f758d148732f40ac054b654facf71df1312b871', 'provider': 'b37cc4a6f6928829124f42e39ab92f5cce3bf0a1b754ab66db25b8c7114309ac'}

def build(kind):
    baseline=load_policy(ROOT/('integrations/bifrost/'+kind+'-agent-baseline.json'),
        'synthetic-support','1',config_root=ROOT,expected_sha256=PINS[kind])
    config=json.loads(baseline.encoded)
    contracts={item['function']['name']:item['function']['parameters'] for item in config['allowed_request_fields']['tools']}
    return AgentBoundary(baseline,'primary',policy,OutputGuard.create(policy,tools=contracts),
                         LocalTransport('http://127.0.0.1:'+('8080' if kind=='gateway' else '18082')))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=['gateway','provider']);args=parser.parse_args()
    token=os.environ['BIFROST_INGRESS_TOKEN' if args.kind=='gateway' else 'BIFROST_PROVIDER_TOKEN']
    server=IngressServer(('127.0.0.1',18080 if args.kind=='gateway' else 18081),build(args.kind),token)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
