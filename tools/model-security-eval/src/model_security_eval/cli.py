"""CI entry point: stdout JSON events; no provider text or raw errors in logs."""
from __future__ import annotations
import argparse
import json
import signal
import threading
from .engine import Config, evaluate
from .reporting import CheckpointWriter, EXIT_CODES, apply_comparison, read_baseline, reserve_output, write_report
from .transport import EvaluationError


def parser():
    result = argparse.ArgumentParser(description='Synthetic local-model security regression gate; no real tool execution.')
    result.add_argument('--backend', required=True, choices=('lmstudio', 'ollama'))
    result.add_argument('--endpoint', help='Numeric loopback HTTP origin; defaults to backend local port.')
    result.add_argument('--model', required=True)
    result.add_argument('--model-revision', default='', help='Expected Ollama digest or LM Studio release identity.')
    result.add_argument('--server-version', default='', help='Expected Ollama version or LM Studio server version.')
    result.add_argument('--capabilities', default='chat,read,write,command,external', help='Comma-separated subset; chat is required.')
    result.add_argument('--output', required=True, help='Fresh directory under an existing parent.')
    result.add_argument('--baseline', help='Previous report.json; incompatible criteria close the gate.')
    result.add_argument('--repetitions', type=int, default=3)
    result.add_argument('--max-requests', type=int, default=300)
    result.add_argument('--max-seconds', type=float, default=1800)
    result.add_argument('--request-timeout', type=float, default=120)
    result.add_argument('--max-steps', type=int, default=6)
    result.add_argument('--max-tokens', type=int, default=2048)
    result.add_argument('--temperature', type=float, default=0)
    result.add_argument('--seed', type=int, default=17)
    result.add_argument('--list-cases', action='store_true', help='Print selected inventory without contacting inference server or creating output.')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    endpoint = args.endpoint or ('http://127.0.0.1:1234' if args.backend == 'lmstudio' else 'http://127.0.0.1:11434')
    config = Config(args.backend, endpoint, args.model,
                    tuple(sorted(item.strip() for item in args.capabilities.split(','))),
                    args.model_revision, args.server_version, args.repetitions, args.max_requests,
                    args.max_seconds, args.request_timeout, args.max_steps, args.max_tokens,
                    args.temperature, args.seed)
    previous_term = None
    if threading.current_thread() is threading.main_thread():
        previous_term = signal.getsignal(signal.SIGTERM)
        def terminate(signum, frame):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, terminate)
    try:
        config.validate()
        if args.list_cases:
            from .cases import suite
            print(json.dumps({'event': 'case_inventory', 'cases': [
                {'id': case.id, 'category': case.category, 'capability': case.capability,
                 'kind': 'attack' if case.attack else 'safe-control'} for case in suite(config.capabilities)]}))
            return 0
        baseline = read_baseline(args.baseline) if args.baseline else None
        output = reserve_output(args.output)
        print(json.dumps({'event': 'evaluation_started', 'capabilities': config.capabilities}), flush=True)
        def progress(result):
            print(json.dumps({'event': 'case_finished', 'case_id': result['case_id'],
                              'repetition': result['repetition'], 'status': result['status'],
                              'diagnostic': result['diagnostic']}), flush=True)
        report = evaluate(config, on_result=progress, checkpoint=CheckpointWriter(output))
        if baseline is not None:
            apply_comparison(report, baseline)
        write_report(output, report)
        print(json.dumps({'event': 'evaluation_finished', 'verdict': report['verdict'], 'eligible': report['eligible'],
                          'counts': report['counts'], 'requests': report['requests'], 'run_state': report['run_state'],
                          'criteria_sha256': report['criteria_sha256']}), flush=True)
        return EXIT_CODES[report['verdict']]
    except EvaluationError as error:
        print(json.dumps({'event': 'evaluation_error', 'verdict': 'inconclusive', 'eligible': False, 'code': str(error)}), flush=True)
        return 2
    except KeyboardInterrupt:
        print(json.dumps({'event': 'evaluation_error', 'verdict': 'inconclusive', 'eligible': False, 'code': 'interrupted'}), flush=True)
        return 2
    except Exception:
        print(json.dumps({'event': 'evaluation_error', 'verdict': 'inconclusive', 'eligible': False, 'code': 'unexpected_error'}), flush=True)
        return 2

    finally:
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
