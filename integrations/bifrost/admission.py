"""Pinned evaluation/release binding; offline evidence is not runtime admission.

No supported proof currently binds a Bifrost completion to actual provider
weights. Consequently eligible is ALWAYS false, even for compatible evidence.
"""
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import re
from pathlib import Path
from model_security_eval import __version__
from model_security_eval.cases import suite
from model_security_eval.reporting import validate_baseline
from model_security_eval.transport import strict_json

HEX = re.compile(r'[0-9a-f]{64}\Z')
VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
ENV = re.compile(r'env\.[A-Z][A-Z0-9_]*\Z')


class AdmissionError(Exception):
    """Fixed diagnostic codes only."""


def require(value, code):
    if not value:
        raise AdmissionError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def parse(raw, limit):
    require(type(raw) is bytes and len(raw) <= limit, 'binding_resource_limit')
    try:
        value = strict_json(raw.decode('utf-8'))
        require(type(value) is dict, 'binding_invalid')
        return value
    except AdmissionError:
        raise
    except Exception:
        raise AdmissionError('binding_invalid') from None


@dataclass(frozen=True, repr=False)
class RouteSnapshot:
    encoded: bytes = field(repr=False)

    @property
    def sha256(self):
        return digest(self.encoded)

    @classmethod
    def capture(cls, boundary, gateway_config, *, route_version, image_digest,
                gateway_model, api_origin, egress_origin, credential_hmac_key=None, egress_network=''):
        """Snapshot actual frozen boundary objects plus owned declarative config.

        This is NOT discovery of Bifrost's loaded state or of model weights.
        Only the selected file-only, one-provider/key, no-cache/retry scope passes.
        """
        from egress import ProviderBoundary
        from client import LocalTransport, PrivateNetworkTransport, BoundaryError
        require(type(boundary) is ProviderBoundary, 'binding_boundary_invalid')
        require(type(route_version) is str and VERSION.fullmatch(route_version), 'route_version_invalid')
        require(type(image_digest) is str and image_digest.startswith('sha256:')
                and HEX.fullmatch(image_digest[7:]), 'gateway_image_unknown')
        try:
            LocalTransport(api_origin)
            if egress_network:
                PrivateNetworkTransport(egress_origin, network_cidr=egress_network)
            else:
                LocalTransport(egress_origin)
        except BoundaryError:
            raise AdmissionError('route_origin_invalid') from None
        config = parse(gateway_config, 1048576)
        require(set(config) <= {'$schema', 'providers', 'plugins', 'config_store', 'logs_store', 'client', 'framework'},
                'gateway_config_scope_unsupported')
        def no_fallbacks(value):
            if type(value) is dict:
                require(not any('fallback' in key.lower() for key in value), 'fallback_rejected')
                for child in value.values():no_fallbacks(child)
            elif type(value) is list:
                for child in value:no_fallbacks(child)
        no_fallbacks(config)
        require(config.get('logs_store') == {'enabled': False}, 'mutable_logs_config_rejected')
        require(type(config.get('client')) is dict and set(config['client']) <=
                {'enable_logging', 'disable_content_logging', 'dump_errors_in_console_logs'}, 'client_scope_unsupported')
        require(type(config.get('framework')) is dict and set(config['framework']) <= {'pricing'}, 'framework_scope_unsupported')
        require(config.get('config_store') == {'enabled': False}, 'mutable_gateway_config_rejected')
        require(type(config.get('plugins')) is list and config['plugins'] == [], 'gateway_plugins_rejected')
        require(type(gateway_model) is str and '/' in gateway_model, 'gateway_route_invalid')
        provider, model = gateway_model.split('/', 1)
        require(model == boundary._model, 'provider_model_mismatch')
        providers = config.get('providers')
        require(type(providers) is dict and set(providers) == {provider}, 'alternate_provider_rejected')
        value = providers[provider]
        require(type(value) is dict and set(value) <= {'custom_provider_config', 'network_config', 'keys'},
                'provider_config_scope_unsupported')
        require(value.get('custom_provider_config') == {'base_provider_type': 'openai'}, 'provider_kind_unsupported')
        network = value.get('network_config')
        require(type(network) is dict and set(network) <= {'base_url', 'max_retries',
                'default_request_timeout_in_seconds', 'allow_private_network'}, 'provider_network_scope_unsupported')
        require(not egress_network or network.get('allow_private_network') is True, 'private_network_not_enabled')
        require(network.get('base_url') == egress_origin, 'egress_route_mismatch')
        require(type(network.get('max_retries')) is int and network['max_retries'] == 0, 'retries_rejected')
        keys = value.get('keys')
        require(type(keys) is list and len(keys) == 1 and type(keys[0]) is dict, 'key_rotation_rejected')
        require(set(keys[0]) <= {'name', 'value', 'models', 'weight'}, 'key_config_scope_unsupported')
        require(type(keys[0].get('value')) is str and ENV.fullmatch(keys[0]['value']), 'literal_credential_rejected')
        require(keys[0].get('models') in ([model], ['*']), 'model_alias_scope_rejected')
        import prompt_guard, prompt_integrity, model_security_eval
        sources = {}
        for package in (prompt_guard, prompt_integrity, model_security_eval):
            root = Path(package.__file__).parent
            for path in root.rglob('*'):
                if path.is_file() and path.suffix in ('.py', '.json') and '__pycache__' not in path.parts:
                    sources[package.__name__ + '/' + path.relative_to(root).as_posix()] = digest(path.read_bytes())
        for path in Path(__file__).parent.glob('*.py'):
            sources['integration/' + path.name] = digest(path.read_bytes())
        implementation = digest(canonical(sources))
        if boundary.transport.token:
            require(type(credential_hmac_key) is bytes and 32 <= len(credential_hmac_key) <= 64,
                    'credential_binding_key_required')
            credential = hmac.new(credential_hmac_key, boundary.transport.token.encode('ascii'), hashlib.sha256).hexdigest()
        else:
            credential = 'none'
        fields = {'provider_credential_hmac': credential, 'provider_timeout': boundary.transport.timeout,
                  'provider_response_limit': boundary.transport.max_bytes, 'implementation_sha256': implementation, 'schema_version': 1, 'route_version': route_version, 'image_digest': image_digest,
                  'gateway_model': gateway_model, 'api_origin': api_origin, 'egress_origin': egress_origin,
                  'egress_network': egress_network,
                  'provider_model': boundary._model, 'provider_endpoint': boundary.transport.endpoint,
                  'provider_network': getattr(boundary.transport, 'network_cidr', ''),
                  'gateway_config_sha256': digest(canonical(config)),
                  'input_policy_sha256': digest(boundary.input_policy.encoded),
                  'output_policy_sha256': digest(boundary.output_guard.policy.encoded),
                  'output_contract_sha256': digest(boundary.output_guard.contracts),
                  'provider_integrity_sha256': digest(boundary.policy.encoded)}
        return cls(canonical(fields))


@dataclass(frozen=True)
class BindingDecision:
    evidence_matches: bool
    reasons: tuple
    eligible: bool = field(default=False, init=False)

    def diagnostics(self):
        return {'evidence_matches': self.evidence_matches, 'eligible': False, 'reasons': list(self.reasons)}


@dataclass(frozen=True, repr=False, init=False)
class EvaluationBinding:
    report: bytes = field(repr=False)
    expected: RouteSnapshot = field(repr=False)
    report_sha256: str
    model_revision: str
    criteria_sha256: str

    @classmethod
    def create(cls, report, expected, *, report_sha256, model_revision, criteria_sha256):
        require(type(expected) is RouteSnapshot, 'route_snapshot_invalid')
        require(type(report_sha256) is str and HEX.fullmatch(report_sha256), 'evaluation_pin_invalid')
        require(type(criteria_sha256) is str and HEX.fullmatch(criteria_sha256), 'criteria_pin_invalid')
        require(type(model_revision) is str and HEX.fullmatch(model_revision), 'model_revision_unknown')
        require(type(report) is bytes and len(report) <= 32 * 1024 * 1024, 'binding_resource_limit')
        require(hmac.compare_digest(digest(report), report_sha256), 'evaluation_digest_mismatch')
        data = parse(report, 32 * 1024 * 1024)
        try:
            validate_baseline(data)
            require(data['verdict'] == 'pass' and data.get('eligible') is True
                    and data.get('run_state') == 'complete' and data.get('identity_limits') == [], 'evaluation_not_eligible')
            require(data.get('evaluator_version') == __version__ and data.get('suite_version') == 2, 'evaluation_version_mismatch')
            require(data['criteria_sha256'] == criteria_sha256, 'evaluation_criteria_changed')
            require(data.get('evaluation_mode') == 'synthetic-model-behavior', 'evaluation_scope_unsupported')
            snapshot = parse(expected.encoded, 1048576)
            cfg = data['configuration']
            from model_security_eval.engine import Config
            Config(**cfg).validate()
            require(cfg.get('backend') == 'ollama', 'revision_evidence_unsupported')
            require(cfg['endpoint'] == snapshot['provider_endpoint'], 'evaluation_endpoint_unmapped')
            require(cfg['model'] == snapshot['provider_model'], 'evaluation_model_mismatch')
            require(cfg['model_revision'] in ('', model_revision, 'sha256:' + model_revision), 'evaluation_revision_mismatch')
            before, after = data['identity']['before'], data['identity']['after']
            require(canonical(before) == canonical(after), 'evaluation_identity_changed')
            for identity in (before, after):
                require(identity.get('source') == 'ollama-tags-version'
                        and identity.get('model_digest') == model_revision
                        and type(identity.get('accepted_models')) is list
                        and cfg['model'] in identity['accepted_models']
                        and identity.get('diagnostics') == []
                        and bool(identity.get('server_version')), 'model_revision_not_observed')
            require(cfg['server_version'] in ('', before['server_version']), 'evaluation_server_version_mismatch')
            require(data.get('identity_source') == 'local-server-metadata-and-response-binding', 'identity_source_unsupported')
            capabilities, repetitions = tuple(cfg['capabilities']), cfg['repetitions']
            require(type(repetitions) is int and 1 <= repetitions <= 20, 'evaluation_inventory_invalid')
            planned = {(case.id, repeat) for case in suite(capabilities) for repeat in range(repetitions)}
            observed = {(case['case_id'], case['repetition']) for case in data['results']}
            require(planned == observed and len(observed) == len(data['results']), 'evaluation_inventory_invalid')
            require(all(row['status'] == 'pass' and row.get('complete') is True
                        and row.get('violations') == [] and row.get('real_effects') == 0
                        for row in data['results']), 'evaluation_incomplete_or_unsafe')
        except AdmissionError:
            raise
        except Exception:
            raise AdmissionError('evaluation_binding_invalid') from None
        result = object.__new__(cls)
        for key, value in {'report': report, 'expected': expected, 'report_sha256': report_sha256,
                           'model_revision': model_revision, 'criteria_sha256': criteria_sha256}.items():
            object.__setattr__(result, key, value)
        return result

    @property
    def sha256(self):
        return digest(canonical({'report': self.report_sha256, 'route': self.expected.sha256,
                                 'revision': self.model_revision, 'criteria': self.criteria_sha256}))

    def assess(self, current):
        require(type(current) is RouteSnapshot, 'route_snapshot_invalid')
        matches = hmac.compare_digest(self.expected.sha256, current.sha256)
        reasons = [] if matches else ['route_or_policy_changed']
        # A native report digest and declared release snapshot cannot prove which
        # provider weights served a gateway completion. No self-asserted flag or
        # reported model can upgrade this decision into an admission permit.
        reasons += ['gateway_runtime_revision_not_attested', 'gateway_runtime_configuration_not_attested',
                    'evaluation_scope_is_direct_backend']
        return BindingDecision(matches, tuple(reasons))

    def require_evidence(self, current):
        require(self.assess(current).evidence_matches, 'route_or_policy_changed')

    def require_admission(self, current):
        decision = self.assess(current)
        raise AdmissionError(decision.reasons[0])
