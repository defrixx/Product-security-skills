"""Offline policy checks; stdout contains diagnostics only."""
import argparse
import json
import os
from pathlib import Path
import sys
from .core import GuardError, LIMITS, SOURCES, decode, inspect, policy_from_dict, require
from .files import load_policy, read_bytes, write_new
from .profiles import PROFILES, load_profile


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GuardError('arguments_invalid')


def main(argv=None):
    parser = Parser(description=__doc__)
    policy_group = parser.add_mutually_exclusive_group(required=True)
    policy_group.add_argument('--policy')
    policy_group.add_argument('--profile', choices=PROFILES)
    parser.add_argument('--config-root')
    parser.add_argument('--expected-policy')
    parser.add_argument('--expected-version')
    parser.add_argument('--expected-sha256')
    parser.add_argument('--input', required=True)
    parser.add_argument('--input-root', required=True)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--source', choices=SOURCES)
    parser.add_argument('--mode', choices=('strict', 'sanitize'), default='strict')
    parser.add_argument('--direction', choices=('input', 'output'), default='input')
    parser.add_argument('--output-contract', help='Trusted JSON object containing schema and tools; requires --config-root.')
    parser.add_argument('--output')
    parser.add_argument('--output-root')
    try:
        args = parser.parse_args(argv)
        require(not args.policy or args.config_root, 'arguments_invalid')
        pins = (args.expected_policy, args.expected_version, args.expected_sha256)
        require(not any(pins) or (all(pins) and args.policy), 'arguments_invalid')
        require(bool(args.output) == bool(args.output_root), 'arguments_invalid')
        require(not args.output or args.mode == 'sanitize' or args.direction == 'output', 'arguments_invalid')
        require(not args.output_contract or (args.direction == 'output' and args.config_root and args.format == 'json'), 'arguments_invalid')
        require(args.direction != 'output' or args.source in (None, 'assistant'), 'arguments_invalid')
        require(args.format != 'json' or args.source is None, 'arguments_invalid')
        if args.output:
            output = Path(os.path.abspath(args.output))
            input_root = Path(os.path.abspath(args.input_root))
            require(not output.is_relative_to(input_root), 'path_boundary')
            if args.config_root:
                require(not output.is_relative_to(Path(os.path.abspath(args.config_root))), 'path_boundary')
        if args.profile:
            policy = load_profile(args.profile)
        elif all(pins):
            policy = load_policy(args.policy, config_root=args.config_root, expected_id=args.expected_policy,
                                 expected_version=args.expected_version, expected_sha256=args.expected_sha256)
        else:
            policy = policy_from_dict(decode(read_bytes(args.policy, args.config_root, 65536), 65536))
        raw = read_bytes(args.input, args.input_root, LIMITS['input_bytes'])
        if args.direction == 'output':
            from .output import OutputGuard
            contract = {'schema': None, 'tools': {}}
            if args.output_contract:
                contract = decode(read_bytes(args.output_contract, args.config_root, 65536), 65536)
                require(type(contract) is dict and set(contract) == {'schema', 'tools'}, 'output_config_invalid')
            boundary = OutputGuard.create(policy, mode=args.mode, **contract)
            if args.format == 'text':
                try:
                    result = boundary.check_text(raw.decode('utf-8'))
                except UnicodeError:
                    raise GuardError('invalid_utf8') from None
            else:
                result = boundary.check_message(decode(raw, LIMITS['input_bytes']))
        else:
            result = inspect(policy, raw, format=args.format,
                             source=(args.source or 'user') if args.format == 'text' else None,
                             mode=args.mode)
        diagnostics = result.diagnostics()
        diagnostics['output_written'] = False
        if args.output and result.decision == 'allow':
            write_new(args.output, args.output_root, result.payload)
            diagnostics['output_written'] = True
        print(json.dumps(diagnostics))
        return {'allow': 0, 'block': 1, 'review': 2, 'error': 3}[result.decision]
    except GuardError as error:
        print(json.dumps({'decision': 'error', 'code': error.code, 'output_written': False}))
        return 3
    except Exception:
        print(json.dumps({'decision': 'error', 'code': 'internal_error', 'output_written': False}))
        return 3


if __name__ == '__main__':
    sys.exit(main())
