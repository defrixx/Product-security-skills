"""Explicit local facade startup using the pinned synthetic example configuration."""
import os
from dataclasses import replace
from example_integrity import client
from ingress import IngressBoundary, IngressServer

if __name__ == '__main__':
    configured = replace(client, reasoning_mode=os.environ.get('BIFROST_REASONING_MODE', 'reject'))
    server = IngressServer(('127.0.0.1', 18080), IngressBoundary(configured),
                           os.environ['BIFROST_INGRESS_TOKEN'])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
