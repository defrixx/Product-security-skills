"""Allow-only output boundaries for text, structured values and tool proposals."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import time
from .core import GuardError, GuardResult, Policy, decode, inspect, policy_from_dict, require
from .schema import validate_schema, validate_value


def snapshot(value):
    try:
        return decode(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), 1048576)
    except GuardError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise GuardError('output_invalid') from None


@dataclass(frozen=True)
class OutputResult:
    decision: str
    code: str
    inspection: object = field(default=None, repr=False)
    payload: bytes | None = field(default=None, repr=False)

    def diagnostics(self):
        return {'direction': 'output', 'decision': self.decision, 'code': self.code,
                'inspection': self.inspection.diagnostics() if self.inspection else None}


@dataclass(frozen=True, repr=False)
class OutputGuard:
    """Trusted immutable configuration. Tool proposals never execute themselves.

    Contracts use the closed subset documented in schema.py. Sensitive route/path
    arguments should use exact enums from application-owned authorization decisions.
    """
    policy: Policy = field(repr=False)
    contracts: bytes = field(repr=False)
    mode: str = 'strict'

    @classmethod
    def create(cls, policy, *, mode='strict', schema=None, tools=None, protected=()):
        require(type(policy) is Policy and mode in ('strict', 'sanitize'), 'output_config_invalid')
        obj = decode(policy.encoded, 65536)
        require(type(protected) is tuple and len(protected) <= 32
                and all(type(v) is str and 0 < len(v) <= 512 for v in protected), 'output_config_invalid')
        for index, value in enumerate(protected):
            rule = {'id': 'OG-PROTECTED-%d' % index, 'kind': 'literal', 'pattern': value,
                    'ignore_case': False, 'sources': ['assistant'], 'action': 'block', 'replacement': None}
            if obj['schema_version'] == 2:
                rule.update(view='raw', scope='message', category='protected-disclosure')
            obj['rules'].append(rule)
        pinned = policy_from_dict(obj)
        config = snapshot({'schema': schema, 'tools': {} if tools is None else tools})
        if schema is not None:
            validate_schema(config['schema'])
        require(type(config['tools']) is dict and len(config['tools']) <= 64, 'output_config_invalid')
        for name, contract in config['tools'].items():
            require(type(name) is str and 0 < len(name) <= 64, 'output_config_invalid')
            validate_schema(contract)
        return cls(pinned, json.dumps(config).encode(), mode)

    def _check(self, records):
        raw = json.dumps({'messages': [{'source': 'assistant', 'text': value} for value in records]},
                         ensure_ascii=False).encode()
        return inspect(self.policy, raw, format='json', source=None, mode=self.mode)

    def check_text(self, text):
        try:
            require(type(text) is str, 'output_invalid')
            checked = inspect(self.policy, text.encode(), source='assistant', mode=self.mode)
            return OutputResult(checked.decision, checked.code, checked, checked.payload)
        except (UnicodeError, GuardError):
            return OutputResult('error', 'output_invalid')

    def check_provider(self, response, backend):
        from .provider_output import canonical_response
        try:
            message = canonical_response(snapshot(response), backend)
            if json.loads(self.contracts)['schema'] is not None:
                message['content'] = decode(message['content'].encode(), 1048576)
            return self.check_message(message)
        except GuardError as error:
            return OutputResult('error', error.code)
        except Exception:
            return OutputResult('error', 'provider_response_invalid')

    def check_provider_stream(self, chunks, backend, *, max_seconds=60):
        """Buffer complete protocol events and fragmented calls before any release."""
        from .provider_output import stream_response
        started = time.monotonic()
        try:
            require(type(max_seconds) in (int, float) and 0 < max_seconds <= 900, 'stream_config_invalid')
            def bounded():
                for chunk in chunks:
                    require(time.monotonic() - started < max_seconds, 'stream_resource_limit')
                    yield chunk
            message = stream_response(bounded(), backend)
            require(time.monotonic() - started < max_seconds, 'stream_resource_limit')
            if json.loads(self.contracts)['schema'] is not None:
                message['content'] = decode(message['content'].encode(), 1048576)
            return self.check_message(message)
        except GuardError as error:
            return OutputResult('error', error.code)
        except Exception:
            return OutputResult('error', 'provider_stream_invalid')
        finally:
            close = getattr(chunks, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def execute_tools(self, message, executors):
        """Validate the entire proposal batch, then invoke trusted allowlisted handlers.

        Handlers own transactional behavior, authorization freshness and deadlines.
        A failure stops subsequent calls; already completed effects are not rolled back.
        Results are returned as data and must cross the application's input boundary
        before a subsequent model round. No model-selected handler is imported.
        """
        checked = self.check_message(message)
        if checked.decision != 'allow':
            return checked.diagnostics(), None
        accepted = json.loads(checked.payload)
        require(type(executors) is dict and all(call['name'] in executors and callable(executors[call['name']])
                for call in accepted.get('tool_calls', [])), 'tool_executor_invalid')
        results = []
        for call in accepted.get('tool_calls', []):
            try:
                results.append({'id': call['id'], 'result': snapshot(executors[call['name']](call['arguments']))})
            except Exception:
                raise GuardError('tool_execution_failed') from None
        return checked.diagnostics(), results

    def check_message(self, message):
        """Canonical assistant message: content is text or a schema-bound JSON value.

        Tool calls use {id, name, arguments}; only allowed results expose payload.
        Field names, tool IDs/names and every string value are scanned, including
        across fields. Sanitization edits values only, never routing metadata.
        """
        checked = None
        try:
            value = snapshot(message)
            require(type(value) is dict and set(value) <= {'content', 'tool_calls'}
                    and 'content' in value, 'output_invalid')
            config = json.loads(self.contracts)
            content = value['content']
            if config['schema'] is None:
                require(type(content) is str, 'output_schema_rejected')
            else:
                validate_value(content, config['schema'])
            calls = value.get('tool_calls', [])
            require(type(calls) is list and len(calls) <= 32, 'tool_call_invalid')
            seen = set()
            for call in calls:
                require(type(call) is dict and set(call) == {'id', 'name', 'arguments'}
                        and type(call['id']) is str and 0 < len(call['id']) <= 128
                        and call['id'] not in seen and type(call['name']) is str
                        and call['name'] in config['tools'], 'tool_call_rejected')
                seen.add(call['id'])
                validate_value(call['arguments'], config['tools'][call['name']])
            records, locations, metadata = [], [], []
            def walk(item, path, editable=True, depth=0):
                require(depth <= 16, 'resource_limit')
                if type(item) is str:
                    records.append(item)
                    locations.append((path, editable))
                elif type(item) is dict:
                    for key, child in item.items():
                        metadata.append(key)
                        walk(child, path + [key], editable, depth + 1)
                elif type(item) is list:
                    for index, child in enumerate(item):
                        walk(child, path + [index], editable, depth + 1)
            walk(content, ['content'])
            for index, call in enumerate(calls):
                metadata.extend((call['id'], call['name']))
                walk(call['arguments'], ['tool_calls', index, 'arguments'])
            records.extend(metadata)
            locations.extend((None, False) for _ in metadata)
            if not records:
                records = ['']
                locations = [(None, False)]
            checked = self._check(records)
            if checked.decision != 'allow':
                return OutputResult(checked.decision, checked.code, checked)
            for original, accepted, (path, editable) in zip(records, json.loads(checked.payload)['messages'], locations):
                if accepted['text'] != original:
                    require(editable and path is not None, 'output_metadata_transformation_rejected')
                    parent = value
                    for component in path[:-1]:
                        parent = parent[component]
                    parent[path[-1]] = accepted['text']
            if config['schema'] is not None:
                validate_value(value['content'], config['schema'])
            for call in calls:
                validate_value(call['arguments'], config['tools'][call['name']])
            return OutputResult('allow', checked.code, checked, json.dumps(value, ensure_ascii=False).encode())
        except GuardError as error:
            decision = 'block' if error.code in ('output_schema_rejected', 'tool_call_rejected', 'output_metadata_transformation_rejected') else 'error'
            return OutputResult(decision, error.code, checked)
        except Exception:
            return OutputResult('error', 'output_invalid', checked)

    def stream(self, chunks, emit, *, delivery='buffered', max_chunks=4096, max_seconds=60):
        """Consume synchronous UTF-8 byte/text chunks and call emit only with approved text.

        Delayed delivery supports raw case-sensitive literals only, retaining the
        longest possible partial match. Every chunk checks the entire accumulated
        original; already emitted prefixes cannot be retracted. Iterator reads must
        implement their own transport timeout; elapsed limits apply between reads.
        """
        emitted = 0
        started = time.monotonic()
        try:
            require(delivery in ('buffered', 'delayed') and callable(emit)
                    and type(max_chunks) is int and 0 < max_chunks <= 4096
                    and type(max_seconds) in (int, float) and 0 < max_seconds <= 900, 'stream_config_invalid')
            config = json.loads(self.contracts)
            require(config['schema'] is None, 'stream_schema_requires_message')
            obj = json.loads(self.policy.encoded)
            relevant = [r for r in obj['rules'] if 'assistant' in r['sources']]
            if delivery == 'delayed':
                require(all(r['kind'] == 'literal' and not r['ignore_case']
                            and r.get('view', 'raw') == 'raw' and r.get('scope', 'message') == 'message'
                            and (self.mode == 'strict' or r['replacement'] is None)
                            for r in relevant), 'stream_policy_requires_buffering')
            hold = max([len(r['pattern']) - 1 for r in relevant] + [0])
            import codecs
            decoder = codecs.getincrementaldecoder('utf-8')('strict')
            text, sent, byte_count, count = '', '', 0, 0
            checked = None
            for chunk in chunks:
                count += 1
                require(count <= max_chunks and time.monotonic() - started < max_seconds, 'stream_resource_limit')
                require(type(chunk) in (bytes, str), 'stream_chunk_invalid')
                raw = chunk if type(chunk) is bytes else chunk.encode()
                byte_count += len(raw)
                require(byte_count <= obj['limits']['input_bytes'], 'resource_limit')
                text += decoder.decode(raw)
                if delivery == 'delayed':
                    checked = self.check_text(text)
                    if checked.decision != 'allow':
                        return dict(checked.diagnostics(), delivery=delivery, emitted_characters=emitted)
                    # Map the safe original boundary through literal substitutions.
                    boundary = max(0, len(text) - hold)
                    for rule in relevant:
                        start = 0
                        while True:
                            start = text.find(rule['pattern'], start)
                            if start < 0:
                                break
                            end = start + len(rule['pattern'])
                            if start < boundary < end:
                                boundary = start
                            start = end
                    prefix = self.check_text(text[:boundary])
                    require(prefix.decision == 'allow', 'stream_prefix_rejected')
                    approved = prefix.payload.decode()
                    require(approved.startswith(sent), 'stream_prefix_changed')
                    delta = approved[len(sent):]
                    if delta:
                        require(time.monotonic() - started < max_seconds, 'stream_resource_limit')
                        emit(delta)
                        emitted += len(delta)
                    sent = approved
            text += decoder.decode(b'', final=True)
            require(time.monotonic() - started < max_seconds, 'stream_resource_limit')
            checked = self.check_text(text)
            if checked.decision == 'allow':
                approved = checked.payload.decode()
                require(approved.startswith(sent), 'stream_prefix_changed')
                delta = approved[len(sent):]
                if delta:
                    require(time.monotonic() - started < max_seconds, 'stream_resource_limit')
                    emit(delta)
                    emitted += len(delta)
            return dict(checked.diagnostics(), delivery=delivery, emitted_characters=emitted)
        except GuardError as error:
            return {'direction': 'output', 'decision': 'error', 'code': error.code,
                    'delivery': delivery, 'emitted_characters': emitted}
        except Exception:
            return {'direction': 'output', 'decision': 'error', 'code': 'stream_failed',
                    'delivery': delivery, 'emitted_characters': emitted}
        finally:
            close = getattr(chunks, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
