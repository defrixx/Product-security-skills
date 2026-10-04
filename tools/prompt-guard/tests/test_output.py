"""Synthetic release, redaction, schema, streaming and action boundary regressions."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

if not os.environ.get('PROMPT_GUARD_TEST_PACKAGED'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prompt_guard import GuardError, OutputGuard, load_profile, policy_from_dict
from prompt_guard.adapters import GuardedDispatch, GuardRejected


def literal(pattern='SYNTHETIC_PROTECTED', replacement=None):
    value = json.loads(load_profile('output-secrets').encoded)
    value['rules'] = [{'id': 'OG-FIXTURE', 'category': 'synthetic', 'kind': 'literal', 'pattern': pattern,
                       'ignore_case': False, 'sources': ['assistant'], 'action': 'block',
                       'replacement': replacement, 'view': 'raw', 'scope': 'message'}]
    return policy_from_dict(value)


STRING = {'type': 'string', 'maxLength': 256}
CONTRACT = {'type': 'object', 'properties': {'path': dict(STRING, enum=['public.txt']), 'text': STRING},
            'required': ['path', 'text'], 'additionalProperties': False}


class OutputTests(unittest.TestCase):
    def test_transformation_recheck_and_contract_failure_never_release(self):
        policy = literal('remove', '')
        value = json.loads(policy.encoded)
        value['rules'].append(dict(value['rules'][0], id='OG-RESIDUAL', pattern='SYNTHETIC_PROTECTED', replacement=None))
        boundary = OutputGuard.create(policy_from_dict(value), mode='sanitize')
        result = boundary.check_text('SYNTHETIC_removePROTECTED')
        self.assertEqual(result.decision, 'block')
        self.assertIsNone(result.payload)
        boundary = OutputGuard.create(literal('short', 'a' * 20), mode='sanitize', schema={'type': 'string', 'maxLength': 10})
        result = boundary.check_message({'content': 'short'})
        self.assertEqual(result.code, 'output_schema_rejected')
        self.assertIsNone(result.payload)

    def test_modes_and_protected_values_never_appear_in_diagnostics(self):
        guard = OutputGuard.create(literal(replacement='[REDACTED]'), mode='sanitize')
        value = 'SYNTHETIC_PROTECTED'
        result = guard.check_text(value)
        self.assertEqual(result.payload, b'[REDACTED]')
        self.assertNotIn(value, json.dumps(result.diagnostics()) + repr(result) + repr(guard))
        self.assertIsNone(OutputGuard.create(literal()).check_text(value).payload)
        guard = OutputGuard.create(load_profile('output-secrets'), protected=(value,))
        self.assertEqual(guard.check_text(value).decision, 'block')

    def test_topics_block_in_both_modes_with_normalization(self):
        for mode in ('strict', 'sanitize'):
            guard = OutputGuard.create(load_profile('output-security-and-topics'), mode=mode)
            for text in ('A news report about weapons.', 'wea\u200bpons', '\uff57\uff45\uff41\uff50\uff4f\uff4e\uff53'):
                self.assertEqual(guard.check_text(text).decision, 'block')
            self.assertEqual(guard.check_text('Public greeting API.').decision, 'allow')

    def test_structured_values_keys_and_cross_field_matches(self):
        schema = {'type': 'object', 'properties': {'first': STRING, 'second': STRING},
                  'required': ['first', 'second'], 'additionalProperties': False}
        guard = OutputGuard.create(literal(replacement='[REDACTED]'), schema=schema, mode='sanitize')
        original = {'content': {'first': 'SYNTHETIC_PROTECTED', 'second': 'public'}}
        result = guard.check_message(original)
        self.assertEqual(json.loads(result.payload)['content']['first'], '[REDACTED]')
        self.assertEqual(original['content']['first'], 'SYNTHETIC_PROTECTED')
        self.assertEqual(guard.check_message({'content': {'first': 'public', 'second': 'public', 'extra': 'public'}}).decision, 'block')
        key_schema = {'type': 'object', 'properties': {'SYNTHETIC_PROTECTED': STRING}, 'additionalProperties': False}
        key_guard = OutputGuard.create(literal(replacement='[REDACTED]'), schema=key_schema, mode='sanitize')
        self.assertEqual(key_guard.check_message({'content': {'SYNTHETIC_PROTECTED': 'public'}}).code,
                         'output_metadata_transformation_rejected')
        topic_guard = OutputGuard.create(load_profile('output-topics'), schema=schema)
        self.assertEqual(topic_guard.check_message({'content': {'first': 'credential', 'second': 'theft'}}).decision, 'block')

    def test_closed_contracts_revalidate_sanitized_arguments_before_effects(self):
        guard = OutputGuard.create(literal(replacement='[REDACTED]'), tools={'write_public': CONTRACT}, mode='sanitize')
        proposal = {'content': '', 'tool_calls': [{'id': 'fixture-1', 'name': 'write_public',
                                                 'arguments': {'path': 'public.txt', 'text': 'SYNTHETIC_PROTECTED'}}]}
        original = copy.deepcopy(proposal)
        effects = []
        diagnostics, results = guard.execute_tools(proposal, {'write_public': lambda args: effects.append(args) or 'OK'})
        self.assertEqual(diagnostics['decision'], 'allow')
        self.assertEqual(effects[0]['text'], '[REDACTED]')
        self.assertEqual(proposal, original)
        for invalid in ('../private.txt', 'https://example.invalid/upload'):
            proposal['tool_calls'][0]['arguments']['path'] = invalid
            self.assertEqual(guard.execute_tools(proposal, {'write_public': lambda args: effects.append(args)})[0]['decision'], 'block')
        self.assertEqual(len(effects), 1)
        proposal = copy.deepcopy(original)
        proposal['tool_calls'].append({'id': 'fixture-2', 'name': 'unknown', 'arguments': {}})
        guard.execute_tools(proposal, {'write_public': lambda args: effects.append(args)})
        self.assertEqual(len(effects), 1)
        proposal = copy.deepcopy(original)
        proposal['tool_calls'][0]['arguments']['extra'] = True
        self.assertEqual(guard.check_message(proposal).decision, 'block')

    def test_schema_rejects_unknown_keywords_boolean_integer_and_deep_values(self):
        for schema in ({'type': 'string', 'maxLength': 32, 'pattern': '.*'}, {'type': 'object', 'properties': {}}, {'$ref': '#'}):
            with self.assertRaises(GuardError):
                OutputGuard.create(literal(), schema=schema)
        guard = OutputGuard.create(literal(), schema={'type': 'integer', 'minimum': 0, 'maximum': 4})
        self.assertEqual(guard.check_message({'content': True}).decision, 'block')
        self.assertEqual(guard.check_message({'content': 3}).decision, 'allow')

    def test_buffered_stream_all_splits_release_nothing_for_blocked_answer(self):
        guard = OutputGuard.create(literal())
        raw = b'public SYNTHETIC_PROTECTED ending'
        for split in range(len(raw) + 1):
            emitted = []
            result = guard.stream(iter((raw[:split], raw[split:])), emitted.append)
            self.assertEqual(result['decision'], 'block')
            self.assertEqual(emitted, [])
        emitted = []
        result = OutputGuard.create(literal(replacement='[REDACTED]'), mode='sanitize').stream(
            iter((b'public SYNTHETIC_', b'PROTECTED ending')), emitted.append)
        self.assertEqual(result['decision'], 'allow')
        self.assertEqual(''.join(emitted), 'public [REDACTED] ending')

    def test_delayed_literal_every_split_withholds_protected_match(self):
        guard = OutputGuard.create(literal())
        raw = b'public SYNTHETIC_PROTECTED ending'
        for split in range(len(raw) + 1):
            emitted = []
            result = guard.stream(iter((raw[:split], raw[split:])), emitted.append, delivery='delayed')
            self.assertEqual(result['decision'], 'block')
            self.assertNotIn('SYNTHETIC_PROTECTED', ''.join(emitted))
        emitted = []
        result = guard.stream(iter((b'public greeting ', b'API')), emitted.append, delivery='delayed')
        self.assertEqual(result['decision'], 'allow')
        self.assertEqual(''.join(emitted), 'public greeting API')
        for guard in (OutputGuard.create(load_profile('output-topics')),
                      OutputGuard.create(literal(replacement='[REDACTED]'), mode='sanitize')):
            self.assertEqual(guard.stream(iter((b'public',)), emitted.append, delivery='delayed')['code'],
                             'stream_policy_requires_buffering')

    def test_stream_utf8_errors_limits_iterator_failures_and_close(self):
        guard = OutputGuard.create(literal())
        raw = 'Public \u65e5\u672c'.encode()
        emitted = []
        self.assertEqual(guard.stream(iter(bytes([b]) for b in raw), emitted.append)['decision'], 'allow')
        self.assertEqual(''.join(emitted), raw.decode())
        for chunks in ((b'public', b'\xff'), (b'public', b'\xe6')):
            emitted = []
            self.assertEqual(guard.stream(iter(chunks), emitted.append)['decision'], 'error')
            self.assertEqual(emitted, [])
        closed = []
        def broken():
            try:
                yield b'public'
                raise RuntimeError('SYNTHETIC_PROTECTED')
            finally:
                closed.append(True)
        emitted = []
        result = guard.stream(broken(), emitted.append)
        self.assertEqual(result['code'], 'stream_failed')
        self.assertEqual(closed, [True])
        self.assertEqual(emitted, [])
        self.assertEqual(guard.stream(iter((b'a', b'b')), emitted.append, max_chunks=1)['code'], 'stream_resource_limit')

    def test_provider_adapter_never_returns_raw_envelope_or_blocked_output(self):
        template = {'model': 'synthetic', 'stream': False, 'messages': [{'role': 'system', 'content': 'Trusted fixture.'}]}
        output = OutputGuard.create(literal())
        response = {'choices': [{'message': {'role': 'assistant', 'content': 'Public greeting'}, 'finish_reason': 'stop'}],
                    'internal': 'SYNTHETIC_PROTECTED'}
        adapter = GuardedDispatch.create(load_profile('security'), 'http://127.0.0.1:1234/v1/chat/completions',
                                        template, sender=lambda *args: response, output_guard=output)
        diagnostics, accepted = adapter.send_user_text('Public greeting')
        self.assertEqual(accepted, {'content': 'Public greeting', 'tool_calls': []})
        self.assertEqual(diagnostics['output']['decision'], 'allow')
        response['choices'][0]['message']['content'] = 'SYNTHETIC_PROTECTED'
        with self.assertRaises(GuardRejected):
            adapter.send_user_text('Public greeting')

    def test_complete_provider_protocol_and_structured_json(self):
        guard = OutputGuard.create(literal(), schema=CONTRACT)
        message = {'role': 'assistant', 'content': json.dumps({'path': 'public.txt', 'text': 'public'})}
        response = {'choices': [{'message': message, 'finish_reason': 'stop'}]}
        self.assertEqual(guard.check_provider(response, 'openai').decision, 'allow')
        response['choices'][0]['finish_reason'] = 'length'
        self.assertEqual(guard.check_provider(response, 'openai').decision, 'error')
        response['choices'][0]['finish_reason'] = 'stop'
        message['reasoning_content'] = 'unhandled'
        self.assertEqual(guard.check_provider(response, 'openai').decision, 'error')

    def test_sse_fragmented_tool_arguments_and_terminal_requirement(self):
        guard = OutputGuard.create(literal(), tools={'write_public': CONTRACT})
        parts = [{'index': 0, 'id': 'fixture-1', 'type': 'function', 'function': {'name': 'write_public', 'arguments': '{"path":"public.txt",'}},
                 {'index': 0, 'function': {'arguments': '"text":"public"}'}}]
        frames = [b'data: ' + json.dumps({'choices': [{'index': 0, 'delta': {'tool_calls': [p]}, 'finish_reason': None}]}).encode() + b'\r\n\r\n' for p in parts]
        frames += [b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}\r\n\r\n', b'data: [DONE]\r\n\r\n']
        wire = b''.join(frames)
        result = guard.check_provider_stream(iter(bytes([b]) for b in wire), 'openai')
        self.assertEqual(result.decision, 'allow', result.diagnostics())
        self.assertEqual(json.loads(result.payload)['tool_calls'][0]['arguments']['text'], 'public')
        self.assertEqual(guard.check_provider_stream(iter(frames[:-1]), 'openai').decision, 'error')
        parts[1]['function']['arguments'] = '"text":"SYNTHETIC_PROTECTED"}'
        frames[1] = b'data: ' + json.dumps({'choices': [{'delta': {'tool_calls': [parts[1]]}}]}).encode() + b'\n\n'
        self.assertEqual(guard.check_provider_stream(iter(frames), 'openai').decision, 'block')

    def test_ndjson_complete_response_and_truncation(self):
        guard = OutputGuard.create(literal())
        frames = [json.dumps({'message': {'role': 'assistant', 'content': text}, 'done': done}).encode() + b'\n'
                  for text, done in [('Public ', False), ('greeting', True)]]
        result = guard.check_provider_stream(iter(frames), 'ollama')
        self.assertEqual(json.loads(result.payload)['content'], 'Public greeting')
        self.assertEqual(guard.check_provider_stream(iter(frames[:1]), 'ollama').decision, 'error')


if __name__ == '__main__':
    unittest.main()
