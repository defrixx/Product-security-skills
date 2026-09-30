"""Static instruction policy and one strict Ollama chat wire adapter."""
from dataclasses import dataclass
import json
import math
import re

ADAPTER = 'ollama-chat-text-v1'
DEFAULT_LIMITS = dict(baseline_bytes=1048576, request_bytes=4194304,
                      messages=256, depth=32, nodes=100000, text_bytes=262144)
SAFE_ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z')


class IntegrityError(Exception):
    def __init__(self, code, slot=None):
        super().__init__(code)
        self.code = code
        self.slot = slot


class TransportError(Exception):
    """Transport failure; deliberately excludes underlying payload/URL errors."""


@dataclass(frozen=True)
class CheckResult:
    decision: str
    code: str
    profile_id: str = None
    profile_version: str = None
    adapter_version: str = None
    slot: int = None


@dataclass(frozen=True)
class FrozenPolicy:
    # Immutable serialized validated policy; no caller-owned nested objects.
    encoded: bytes

    def __repr__(self):
        return 'FrozenPolicy(<private>)'


def require(condition, code='baseline_invalid', slot=None):
    if not condition:
        raise IntegrityError(code, slot)


def bounded_copy(value, limits):
    nodes = 0
    byte_count = 0
    active = set()
    def visit(item, depth):
        nonlocal nodes, byte_count
        nodes += 1
        require(nodes <= limits['nodes'] and depth <= limits['depth'], 'resource_limit')
        kind = type(item)
        if kind is str:
            try:
                length = len(item.encode('utf-8'))
            except UnicodeError:
                raise IntegrityError('unsupported_shape') from None
            byte_count += length
            require(length <= limits['text_bytes'] and byte_count <= limits['request_bytes'], 'resource_limit')
            return item
        if kind in (int, float, bool) or item is None:
            if kind is float:
                require(math.isfinite(item), 'unsupported_shape')
            if kind is int:
                require(item.bit_length() <= 64, 'resource_limit')
            return item
        require(kind in (dict, list), 'unsupported_shape')
        require(id(item) not in active, 'unsupported_shape')
        active.add(id(item))
        try:
            if kind is list:
                return [visit(x, depth+1) for x in item]
            require(all(type(k) is str for k in item), 'unsupported_shape')
            return {visit(k, depth+1): visit(v, depth+1) for k, v in item.items()}
        finally:
            active.remove(id(item))
    return visit(value, 0)


def decode(raw, limits, byte_limit):
    require(type(raw) is bytes and len(raw) <= byte_limit, 'resource_limit')
    depth = 0
    quoted = escape = False
    for b in raw:
        if quoted:
            if escape: escape = False
            elif b == 92: escape = True
            elif b == 34: quoted = False
        elif b == 34: quoted = True
        elif b in (91, 123):
            depth += 1
            require(depth <= limits['depth'], 'resource_limit')
        elif b in (93, 125): depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'invalid_json')
            result[key] = value
        return result
    def invalid(_):
        raise IntegrityError('invalid_json')
    try:
        obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
        return bounded_copy(obj, limits)
    except IntegrityError as error:
        if error.code == 'resource_limit':
            raise
        raise IntegrityError('invalid_json') from None
    except (ValueError, UnicodeError, RecursionError):
        raise IntegrityError('invalid_json') from None


def encode(value, limit):
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise IntegrityError('unsupported_shape') from None
    require(len(raw) <= limit, 'resource_limit')
    return raw


def policy_from_dict(value, expected_profile, expected_version):
    obj = bounded_copy(value, DEFAULT_LIMITS)
    fields = {'schema_version', 'profile_id', 'profile_version', 'adapter_id', 'adapter_version',
              'allowed_targets', 'trusted_messages', 'data_message_policy', 'allowed_request_fields', 'limits'}
    require(type(obj) is dict and set(obj) == fields)
    require(type(obj['schema_version']) is int and obj['schema_version'] == 1)
    for field in ('profile_id', 'profile_version'):
        require(type(obj[field]) is str and SAFE_ID.fullmatch(obj[field]) is not None)
    require(obj['profile_id'] == expected_profile and obj['profile_version'] == expected_version, 'version_mismatch')
    require(obj['adapter_id'] == ADAPTER and obj['adapter_version'] == '1')
    limits = obj['limits']
    require(type(limits) is dict and set(limits) == set(DEFAULT_LIMITS))
    # Deployment can tighten bounds, never accidentally remove hard ceilings.
    require(all(type(v) is int and 0 < v <= DEFAULT_LIMITS[k] for k, v in limits.items()))
    trusted = obj['trusted_messages']
    require(type(trusted) is list and 0 < len(trusted) <= limits['messages'])
    slots = set()
    for item in trusted:
        require(type(item) is dict and set(item) == {'slot_id', 'role', 'text'})
        require(type(item['slot_id']) is str and SAFE_ID.fullmatch(item['slot_id']) is not None)
        require(item['slot_id'] not in slots)
        slots.add(item['slot_id'])
        require(item['role'] == 'system' and type(item['text']) is str)
    data = obj['data_message_policy']
    require(type(data) is dict and set(data) == {'roles', 'min_messages', 'max_messages'})
    require(type(data['roles']) is list and bool(data['roles']) and all(r in ('user', 'assistant') for r in data['roles']))
    require(len(set(data['roles'])) == len(data['roles']))
    require(type(data['min_messages']) is int and type(data['max_messages']) is int)
    require(0 <= data['min_messages'] <= data['max_messages'] <= limits['messages']-len(trusted))
    targets = obj['allowed_targets']
    require(type(targets) is dict and bool(targets))
    for alias, model in targets.items():
        require(SAFE_ID.fullmatch(alias) is not None and type(model) is str and 0 < len(model) <= 256)
    # Intentionally only a fixed non-streaming option. No arbitrary option bags.
    options = obj['allowed_request_fields']
    require(type(options) is dict and set(options) == {'stream'})
    stream = options['stream']
    require(type(stream) is dict and set(stream) == {'type', 'value'})
    require(stream['type'] == 'boolean' and stream['value'] is False)
    bounded_copy(obj, limits)
    raw = encode(obj, limits['baseline_bytes'])
    return FrozenPolicy(raw)


def _policy(policy):
    require(type(policy) is FrozenPolicy)
    obj = decode(policy.encoded, DEFAULT_LIMITS, DEFAULT_LIMITS['baseline_bytes'])
    # Even directly constructed FrozenPolicy values must meet the schema.
    require(type(obj) is dict)
    validated = policy_from_dict(obj, obj.get('profile_id'), obj.get('profile_version'))
    return json.loads(validated.encoded)


def _prepare(policy, request, target_alias):
    obj = _policy(policy)
    limits = obj['limits']
    snapshot = decode(request, limits, limits['request_bytes']) if type(request) is bytes else bounded_copy(request, limits)
    require(type(target_alias) is str and target_alias in obj['allowed_targets'], 'unknown_target')
    require(type(snapshot) is dict and set(snapshot) == {'model', 'messages', 'stream'}, 'unsupported_shape')
    require(snapshot['model'] == obj['allowed_targets'][target_alias], 'unknown_target')
    require(snapshot['stream'] is False, 'unsupported_shape')
    messages = snapshot['messages']
    require(type(messages) is list, 'unsupported_shape')
    require(len(messages) <= limits['messages'], 'resource_limit')
    trusted = obj['trusted_messages']
    require(len(messages) >= len(trusted), 'missing_instruction')
    for index, message in enumerate(messages):
        require(type(message) is dict and set(message) == {'role', 'content'}, 'unsupported_shape', index)
        require(type(message['role']) is str and type(message['content']) is str, 'unsupported_shape', index)
        if index < len(trusted):
            require(message['role'] == trusted[index]['role'], 'role_mismatch', index)
            require(message['content'] == trusted[index]['text'], 'instruction_mismatch', index)
        else:
            require(message['role'] in obj['data_message_policy']['roles'], 'unexpected_instruction', index)
    count = len(messages)-len(trusted)
    require(obj['data_message_policy']['min_messages'] <= count <= obj['data_message_policy']['max_messages'], 'unsupported_shape')
    # The same bytes leave the boundary; no downstream SDK reassembly.
    return obj, encode(snapshot, limits['request_bytes'])


def check_request(policy, request, target_alias):
    safe = {}
    try:
        obj = _policy(policy)
        safe = dict(profile_id=obj['profile_id'], profile_version=obj['profile_version'], adapter_version='1')
        _prepare(policy, request, target_alias)
        return CheckResult('match', 'matched', **safe)
    except IntegrityError as error:
        decision = 'error' if error.code in ('baseline_invalid', 'version_mismatch', 'resource_limit', 'invalid_json') else 'reject'
        return CheckResult(decision, error.code, slot=error.slot, **safe)
    except Exception:
        return CheckResult('error', 'internal_error', **safe)


def verify_and_send(policy, request, target_alias, transport):
    try:
        _, payload = _prepare(policy, request, target_alias)
    except IntegrityError:
        raise
    except Exception:
        raise IntegrityError('internal_error') from None
    try:
        return transport.send(target_alias, payload)
    except Exception:
        raise TransportError('transport_failed') from None
