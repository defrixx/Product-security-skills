"""Read-only local model discovery and response identity binding."""
from __future__ import annotations
import re
from .transport import EvaluationError, endpoint_url, get


def identifier(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 256:
        raise EvaluationError('invalid_reported_identity')
    if any(ord(character) < 32 for character in value):
        raise EvaluationError('invalid_reported_identity')
    return value


def discover(config, budget, reader=get):
    endpoint_url(config.endpoint, config.backend)
    # endpoint_url has already validated the origin; preserve IPv6 and explicit port.
    origin = config.endpoint.rstrip('/')
    diagnostics = []
    if config.backend == 'ollama':
        models = reader(origin + '/api/tags', budget.take('metadata'))
        version = reader(origin + '/api/version', budget.take('metadata'))
        server_version = identifier(version.get('version'))
        rows = models.get('models')
        if not isinstance(rows, list):
            raise EvaluationError('invalid_model_metadata')
        requested = {config.model}
        if ':' not in config.model.rsplit('/', 1)[-1]:
            requested.add(config.model + ':latest')
        matches = [row for row in rows if isinstance(row, dict)
                   and (row.get('name') in requested or row.get('model') in requested)]
        if len(matches) != 1:
            raise EvaluationError('model_metadata_ambiguous' if matches else 'model_not_listed')
        row = matches[0]
        if row.get('remote_host') or row.get('remote_model') or row.get('size') == 0:
            raise EvaluationError('remote_model_rejected')
        aliases = {config.model}
        for key in ('name', 'model'):
            if row.get(key) is not None:
                aliases.add(identifier(row[key]))
        digest = row.get('digest')
        if not isinstance(digest, str) or not re.fullmatch(r'(?:sha256:)?[0-9a-fA-F]{64}', digest):
            raise EvaluationError('invalid_model_digest')
        digest = digest.removeprefix('sha256:').lower()
        revision = config.model_revision.removeprefix('sha256:').lower()
        if revision and revision != digest:
            raise EvaluationError('model_revision_mismatch')
        if config.server_version and config.server_version != server_version:
            raise EvaluationError('server_version_mismatch')
        return {'source': 'ollama-tags-version', 'accepted_models': sorted(aliases), 'model_digest': digest,
                'server_version': server_version, 'details': row.get('details', {}), 'diagnostics': diagnostics}
    # Native metadata gives model key, loaded instance IDs and effective load configuration.
    try:
        metadata = reader(origin + '/api/v1/models', budget.take('metadata'))
    except EvaluationError as error:
        if str(error) not in ('http_not_found', 'http_method_rejected'):
            raise
        diagnostics.append(str(error))
        metadata = reader(origin + '/v1/models', budget.take('metadata'))
        rows = metadata.get('data')
        if not isinstance(rows, list):
            raise EvaluationError('invalid_model_metadata')
        matches = [row for row in rows if isinstance(row, dict) and row.get('id') == config.model]
        if len(matches) != 1:
            raise EvaluationError('model_metadata_ambiguous' if matches else 'model_not_listed')
        return {'source': 'lmstudio-compatible-models', 'accepted_models': [config.model],
                'server_version': config.server_version, 'details': {}, 'diagnostics': diagnostics}
    rows = metadata.get('models')
    if not isinstance(rows, list):
        raise EvaluationError('invalid_model_metadata')
    matches = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('loaded_instances'), list):
            raise EvaluationError('invalid_model_metadata')
        instances = row['loaded_instances']
        if any(not isinstance(instance, dict) or not isinstance(instance.get('id'), str) or not instance['id'].strip() for instance in instances):
            raise EvaluationError('invalid_model_metadata')
        if row.get('key') == config.model:
            if len(instances) > 1:
                raise EvaluationError('model_metadata_ambiguous')
            if not instances:
                raise EvaluationError('model_not_loaded')
            matches.append((row, instances[0]))
        else:
            for instance in instances:
                if isinstance(instance, dict) and instance.get('id') == config.model:
                    matches.append((row, instance))
    if len(matches) != 1:
        raise EvaluationError('model_metadata_ambiguous' if matches else 'model_not_listed')
    row, instance = matches[0]
    if row.get('type') != 'llm':
        raise EvaluationError('model_type_rejected')
    aliases = {config.model}
    if len(row['loaded_instances']) == 1:
        aliases.add(identifier(row.get('key')))
    if instance is not None:
        if not isinstance(instance, dict):
            raise EvaluationError('invalid_model_metadata')
        aliases.add(identifier(instance.get('id')))
    details = {key: row[key] for key in ('architecture', 'quantization', 'size_bytes', 'format', 'selected_variant') if key in row}
    if instance is not None:
        details['loaded_config'] = instance.get('config', {})
    return {'source': 'lmstudio-native-models', 'accepted_models': sorted(aliases),
            'server_version': config.server_version, 'details': details, 'diagnostics': diagnostics}


def check_response(response, accepted_models):
    model = response.get('model')
    if model is None:
        raise EvaluationError('response_model_missing')
    identifier(model)
    if model not in accepted_models:
        raise EvaluationError('response_model_mismatch')
    return model
