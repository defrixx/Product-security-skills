"""Run bounded behavioral trials on an explicitly selected Bifrost text route.

Observed behavior and caller-configured response model binding are recorded.
No native backend metadata, provider revision or gateway route attestation is
invented. This integration never produces an eligible admission verdict.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from model_security_eval.engine import Config, evaluate, fingerprint
from model_security_eval.transport import EvaluationError, strict_json
from client import LocalTransport, BoundaryError


@dataclass(frozen=True, repr=False)
class RouteConfig:
    endpoint: str
    model: str
    reported_model: str
    repetitions: int = 1
    max_requests: int = 100
    max_seconds: float = 300
    request_timeout: float = 30
    max_tokens: int = 256
    token: str = field(default='', repr=False)


def evaluate_route(route, *, responder=None, binding=None, snapshot_reader=None):
    """Explicit invocation sends synthetic cases to the configured gateway.

    Optional responder injection is for labeled tests only. Defaults to the real
    HTTP transport. The existing engine's lmstudio codec is the supported
    OpenAI-style wire grammar, not a claim that the gateway is LM Studio.
    """
    if type(route) is not RouteConfig:
        raise EvaluationError('invalid_route_config')
    for value in (route.model, route.reported_model):
        if (type(value) is not str or not 0 < len(value) <= 256
                or any(ord(c) <= 32 for c in value)):
            raise EvaluationError('invalid_route_model')
    if '/' not in route.model:
        raise EvaluationError('invalid_route_model')
    LocalTransport(route.endpoint, route.request_timeout, token=route.token)
    config = Config('lmstudio', route.endpoint, route.model, capabilities=('chat',),
                    repetitions=route.repetitions, max_requests=route.max_requests,
                    max_seconds=route.max_seconds, request_timeout=route.request_timeout,
                    max_tokens=route.max_tokens)
    config.validate()
    expected_url = route.endpoint.rstrip('/') + '/v1/chat/completions'
    bound_snapshot = None
    if binding is not None:
        from admission import EvaluationBinding, AdmissionError
        if type(binding) is not EvaluationBinding or not callable(snapshot_reader):
            raise EvaluationError('route_binding_invalid')
        try:
            bound_snapshot = snapshot_reader()
            binding.require_evidence(bound_snapshot)
            snapshot = json.loads(bound_snapshot.encoded)
            if snapshot['gateway_model'] != route.model or snapshot['api_origin'] != route.endpoint:
                raise ValueError()
        except Exception:
            raise EvaluationError('route_binding_rejected') from None
    elif snapshot_reader is not None:
        raise EvaluationError('route_binding_invalid')

    def declared_identity(config, budget):
        return {'source': 'caller-configured-gateway-route',
                'accepted_models': [route.reported_model], 'server_version': '',
                'details': {'requested_model': route.model, 'endpoint': route.endpoint},
                'diagnostics': ['provider_identity_not_attested']}

    def send(url, request, timeout):
        if url != expected_url or request.get('model') != route.model:
            raise EvaluationError('route_binding_mismatch')
        if binding is not None:
            try:
                binding.require_evidence(snapshot_reader())
            except Exception:
                raise EvaluationError('route_configuration_changed') from None
        if responder is not None:
            return responder(url, request, timeout)
        try:
            wire = LocalTransport(route.endpoint, timeout=min(timeout, 120), token=route.token)
            raw = wire(json.dumps(request, ensure_ascii=False, allow_nan=False).encode())
            value = strict_json(raw.decode('utf-8'))
            if type(value) is not dict:
                raise ValueError()
            return value
        except Exception:
            raise EvaluationError('gateway_transport_failed') from None

    report = evaluate(config, responder=send, metadata_provider=declared_identity)
    if binding is not None:
        try:
            final_snapshot = snapshot_reader()
            decision = binding.assess(final_snapshot).diagnostics()
            decision['snapshot_sha256'] = final_snapshot.sha256
        except Exception:
            decision = {'evidence_matches': False, 'eligible': False,
                        'reasons': ['route_snapshot_unavailable']}
        report['evaluation_binding'] = {**decision, 'binding_sha256': binding.sha256,
                                         'initial_snapshot_sha256': bound_snapshot.sha256}
        report['identity_limits'].extend(decision['reasons'])
    report['evaluation_mode'] = 'synthetic-gateway-text-route'
    report['identity_source'] = 'caller-configured-gateway-route-and-response-model-binding'
    report['identity_limits'].append('gateway_provider_identity_and_routing_not_attested')
    report['eligible'] = False
    if report['verdict'] != 'fail':
        report['verdict'] = 'inconclusive'
    public_route = {k: v for k, v in asdict(route).items() if k != 'token'}
    report['gateway_route'] = public_route
    report['configuration']['backend'] = 'bifrost-openai-chat'
    report['engine_wire_codec'] = 'lmstudio'
    integration_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['criteria_sha256'] = fingerprint({'engine': report['criteria_sha256'],
                                             'route': public_route, 'integration': integration_hash})
    if binding is not None:
        report['criteria_sha256'] = fingerprint({'route_criteria': report['criteria_sha256'],
                                                  'evaluation_binding': binding.sha256})
    report['limits'] = [v for v in report['limits'] if not v.startswith('Metadata is reported')]
    report['limits'] += ['Route and accepted response model are caller configuration, not discovered provider identity.',
                         'Gateway internal cache, retries, keys and fallbacks are not observed or attested.',
                         'No route-wide admission decision is issued; eligible is always false.']
    report['substitutions'].append('caller-declared response-model binding; no metadata discovery')
    if responder is not None:
        report['substitutions'].append('injected test responder; not a live gateway run')
    return report


if __name__ == '__main__':
    import argparse
    import sys
    from model_security_eval.reporting import reserve_output, write_report
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--reported-model', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        output = reserve_output(args.output)
        report = evaluate_route(RouteConfig(args.endpoint, args.model, args.reported_model))
        write_report(output, report)
        print(json.dumps({'verdict': report['verdict'], 'eligible': False, 'counts': report['counts']}))
        sys.exit(1 if report['verdict'] == 'fail' else 2)
    except (EvaluationError, ValueError, BoundaryError):
        print(json.dumps({'verdict': 'inconclusive', 'eligible': False, 'code': 'route_evaluation_failed'}))
        sys.exit(2)
