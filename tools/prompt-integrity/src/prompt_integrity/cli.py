"""Offline CLI; never sends a model request or approves a baseline."""
import argparse
from dataclasses import asdict
import json
import sys
from .core import DEFAULT_LIMITS, IntegrityError, check_request, decode, policy_from_dict
from .files import load_policy, read_bytes, write_new


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise IntegrityError('invalid_arguments')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        groups = parser.add_subparsers(dest='group', required=True, parser_class=Parser)
        baseline = groups.add_parser('baseline').add_subparsers(dest='operation', required=True, parser_class=Parser)
        create = baseline.add_parser('create')
        create.add_argument('--instructions', required=True)
        create.add_argument('--policy', required=True)
        create.add_argument('--output', required=True)
        validate = baseline.add_parser('validate')
        validate.add_argument('--baseline', required=True)
        requests = groups.add_parser('request').add_subparsers(dest='operation', required=True, parser_class=Parser)
        check = requests.add_parser('check')
        check.add_argument('--baseline', required=True)
        check.add_argument('--request', required=True)
        check.add_argument('--target', required=True)
        for command in (create, validate, check):
            command.add_argument('--config-root', required=True)
            command.add_argument('--expected-profile', required=True)
            command.add_argument('--expected-version', required=True)
        for command in (validate, check):
            command.add_argument('--expected-sha256')
        args = parser.parse_args(argv)
        if args.operation == 'create':
            def read(path):
                return decode(read_bytes(path, args.config_root, DEFAULT_LIMITS['baseline_bytes']), DEFAULT_LIMITS, DEFAULT_LIMITS['baseline_bytes'])
            policy = read(args.policy)
            if type(policy) is not dict or 'trusted_messages' in policy:
                raise IntegrityError('baseline_invalid')
            policy['trusted_messages'] = read(args.instructions)
            frozen = policy_from_dict(policy, args.expected_profile, args.expected_version)
            write_new(args.output, args.config_root, frozen.encoded+b'\n')
            print('{"status":"candidate_created","approved":false}')
            return 0
        policy = load_policy(args.baseline, args.expected_profile, args.expected_version, config_root=args.config_root,
                             expected_sha256=args.expected_sha256)
        if args.group == 'baseline':
            print('{"status":"structurally_valid","approved":false}')
            return 0
        raw = read_bytes(args.request, args.config_root, DEFAULT_LIMITS['request_bytes'])
        result = check_request(policy, raw, args.target)
        print(json.dumps(asdict(result)))
        return {'match': 0, 'reject': 2, 'error': 1}[result.decision]
    except IntegrityError as error:
        print(json.dumps({'status': 'error', 'code': error.code}), file=sys.stderr)
        return 1
    except Exception:
        print('{"status":"error","code":"internal_error"}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
