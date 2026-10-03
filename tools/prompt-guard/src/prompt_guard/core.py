"""Immutable policy snapshots and bounded inspection with explicit transformations."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import re
import time
from .execution import execute, ExecutionError

SOURCES = ('user', 'retrieval', 'file', 'tool', 'assistant')
LIMITS = {'input_bytes': 1048576, 'messages': 128, 'rules': 64,
          'matches': 1024, 'timeout_ms': 2000}
LIMITS_V2 = dict(LIMITS, overall_ms=6000, memory_mb=256)
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z')


class GuardError(Exception):
    """Public diagnostic codes never carry input values or paths."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='policy_invalid'):
    if not condition:
        raise GuardError(code)


def decode(raw, limit):
    require(type(raw) is bytes and len(raw) <= limit, 'resource_limit')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'invalid_json')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(GuardError('invalid_json')))
    except GuardError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise GuardError('invalid_json') from None


@dataclass(frozen=True, repr=False)
class Policy:
    encoded: bytes

    def __repr__(self):
        return 'Policy(<private>)'


@dataclass(frozen=True)
class GuardResult:
    decision: str
    code: str
    findings: tuple = ()
    residual_findings: tuple = ()
    policy_id: str | None = None
    policy_version: str | None = None
    mode: str = 'strict'
    # Only an allow result has dispatchable content. Never include it in diagnostics.
    payload: bytes | None = field(default=None, repr=False)

    def diagnostics(self):
        return {'decision': self.decision, 'code': self.code, 'mode': self.mode,
                'policy_id': self.policy_id, 'policy_version': self.policy_version,
                'findings': list(self.findings), 'residual_findings': list(self.residual_findings)}


def policy_from_dict(value, *, _validate_expressions=True):
    try:
        raw = json.dumps(value, allow_nan=False).encode('utf-8')
        require(len(raw) <= 65536, 'resource_limit')
        obj = decode(raw, 65536)
        require(type(obj) is dict)
        version = obj.get('schema_version')
        require(type(version) is int and version in (1, 2))
        fields = {'schema_version', 'policy_id', 'policy_version', 'limits', 'rules'}
        if version == 2:
            fields.add('assembly_separator')
            require(type(obj.get('assembly_separator')) is str and len(obj['assembly_separator']) <= 16)
        require(set(obj) == fields)
        for key in ('policy_id', 'policy_version'):
            require(type(obj[key]) is str and ID.fullmatch(obj[key]))
        limits = obj['limits']
        ceilings = LIMITS if version == 1 else LIMITS_V2
        require(type(limits) is dict and set(limits) == set(ceilings))
        require(all(type(v) is int and 0 < v <= ceilings[k] for k, v in limits.items()))
        if version == 2:
            require(limits['memory_mb'] >= 64)
        rules = obj['rules']
        require(type(rules) is list and len(rules) <= limits['rules'])
        seen = set()
        for rule in rules:
            rule_fields = {'id', 'kind', 'pattern', 'ignore_case', 'sources', 'action', 'replacement'}
            if version == 2:
                rule_fields.update(('view', 'scope', 'category'))
            require(type(rule) is dict and set(rule) == rule_fields)
            require(type(rule['id']) is str and ID.fullmatch(rule['id']) and rule['id'] not in seen)
            seen.add(rule['id'])
            require(rule['kind'] in ('literal', 'regex') and type(rule['pattern']) is str and 0 < len(rule['pattern']) <= 512)
            require(type(rule['ignore_case']) is bool)
            require(type(rule['sources']) is list and bool(rule['sources']) and all(type(s) is str and s in SOURCES for s in rule['sources']))
            require(len(set(rule['sources'])) == len(rule['sources']))
            require(rule['action'] in ('block', 'review'))
            require(rule['replacement'] is None or (type(rule['replacement']) is str and len(rule['replacement'].encode('utf-8')) <= 1024))
            require(rule['action'] == 'block' or rule['replacement'] is None)
            if version == 2:
                require(rule['view'] in ('raw', 'normalized') and rule['scope'] in ('message', 'assembled'))
                require(type(rule['category']) is str and ID.fullmatch(rule['category']))
                require(rule['scope'] != 'assembled' or rule['replacement'] is None)
        if _validate_expressions:
            deadline = time.monotonic() + limits.get('overall_ms', 6000) / 1000
            execute({'operation': 'validate', 'rules': rules}, limits, deadline)
        return Policy(json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    except GuardError:
        raise
    except ExecutionError as error:
        raise GuardError(str(error)) from None
    except (ValueError, TypeError, UnicodeError, RecursionError, re.error):
        raise GuardError('policy_invalid') from None


def _input(raw, format, source, limits):
    require(type(raw) is bytes and len(raw) <= limits['input_bytes'], 'resource_limit')
    if format == 'text':
        require(source in SOURCES, 'source_invalid')
        try:
            return [{'source': source, 'text': raw.decode('utf-8')}]
        except UnicodeError:
            raise GuardError('invalid_utf8') from None
    require(format == 'json' and source is None, 'input_invalid')
    obj = decode(raw, limits['input_bytes'])
    require(type(obj) is dict and set(obj) == {'messages'}, 'input_invalid')
    messages = obj['messages']
    require(type(messages) is list and 0 < len(messages) <= limits['messages'], 'input_invalid')
    for message in messages:
        require(type(message) is dict and set(message) == {'source', 'text'}, 'input_invalid')
        require(type(message['source']) is str and message['source'] in SOURCES and type(message['text']) is str, 'input_invalid')
        try:
            message['text'].encode('utf-8')
        except UnicodeError:
            raise GuardError('invalid_utf8') from None
    return messages


def _scan(messages, obj, deadline):
    task = {'messages': messages, 'rules': obj['rules'], 'max_matches': obj['limits']['matches'],
            'assembly_separator': obj.get('assembly_separator', '\n')}
    try:
        result = execute(task, obj['limits'], deadline)
    except ExecutionError as error:
        raise GuardError(str(error)) from None
    return result['matches']


def _findings(matches, rules):
    counts = {}
    for message, rule, start, end in matches:
        key = (message, rule)
        counts[key] = counts.get(key, 0) + 1
    return tuple({'rule_id': rules[r]['id'], 'message_index': m if m >= 0 else None,
                  'scope': rules[r].get('scope', 'message'),
                  'category': rules[r].get('category', 'custom'),
                  'action': rules[r]['action'], 'count': count}
                 for (m, r), count in sorted(counts.items()))


def inspect(policy, raw, *, format='text', source='user', mode='strict'):
    """Return safe diagnostics and an allow-only payload; never mutate caller input."""
    safe = {'mode': mode if mode in ('strict', 'sanitize') else 'strict'}
    findings = ()
    started = time.monotonic()
    try:
        require(type(policy) is Policy, 'policy_invalid')
        obj = json.loads(policy_from_dict(decode(policy.encoded, 65536), _validate_expressions=False).encoded)
        deadline = started + obj['limits'].get('overall_ms', 6000) / 1000
        safe.update(policy_id=obj['policy_id'], policy_version=obj['policy_version'])
        require(mode in ('strict', 'sanitize'), 'mode_invalid')
        messages = _input(raw, format, source, obj['limits'])
        matches = _scan(messages, obj, deadline)
        findings = _findings(matches, obj['rules'])
        if mode == 'strict':
            decision = 'block' if any(f['action'] == 'block' for f in findings) else ('review' if findings else 'allow')
            require(time.monotonic() < deadline, 'request_timeout')
            return GuardResult(decision, 'matched' if findings else 'no_match', findings, **safe,
                               payload=raw if decision == 'allow' else None)
        edits = {}
        for message, rule, start, end in matches:
            item = obj['rules'][rule]
            if item['action'] == 'block':
                if item['replacement'] is None:
                    return GuardResult('block', 'transformation_not_authorized', findings, **safe)
                edits.setdefault(message, []).append((start, end, item['replacement']))
        for message, spans in edits.items():
            spans = sorted(set(spans))
            for left, right in zip(spans, spans[1:]):
                if left[1] > right[0]:
                    return GuardResult('block', 'overlapping_transformations', findings, **safe)
            text = messages[message]['text']
            for start, end, replacement in reversed(spans):
                text = text[:start] + replacement + text[end:]
            messages[message]['text'] = text
        payload = messages[0]['text'].encode('utf-8') if format == 'text' else json.dumps({'messages': messages}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        require(len(payload) <= obj['limits']['input_bytes'], 'resource_limit')
        residual = _findings(_scan(messages, obj, deadline), obj['rules'])
        decision = 'block' if any(f['action'] == 'block' for f in residual) else ('review' if residual else 'allow')
        require(time.monotonic() < deadline, 'request_timeout')
        return GuardResult(decision, 'residual_match' if residual else ('sanitized' if edits else 'no_match'),
                           findings, residual, **safe, payload=payload if decision == 'allow' else None)
    except GuardError as error:
        return GuardResult('error', error.code, findings, **safe)
    except Exception:
        return GuardResult('error', 'internal_error', findings, **safe)
