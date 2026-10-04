"""Bounded evidence and baseline comparison; a baseline never overrides current failures."""
from __future__ import annotations
import json
import os
from pathlib import Path
from .transport import EvaluationError, strict_json

MAX_BASELINE = 32 * 1024 * 1024
EXIT_CODES = {'pass': 0, 'fail': 1, 'inconclusive': 2}


def validate_baseline(baseline):
    """Reject malformed evidence before spending an inference budget."""
    try:
        if (type(baseline['schema_version']) is not int or baseline['schema_version'] != 2 or baseline['verdict'] not in EXIT_CODES
                or not isinstance(baseline['criteria_sha256'], str)
                or len(baseline['criteria_sha256']) != 64
                or any(c not in '0123456789abcdef' for c in baseline['criteria_sha256'])
                or not isinstance(baseline['configuration'], dict)
                or not isinstance(baseline['results'], list) or not baseline['results']):
            raise ValueError()
        identities = set()
        statuses = []
        for result in baseline['results']:
            identity = (result['case_id'], result['repetition'])
            if (not isinstance(identity[0], str) or type(identity[1]) is not int or identity[1] < 0
                    or identity in identities or result['status'] not in EXIT_CODES):
                raise ValueError()
            identities.add(identity)
            statuses.append(result['status'])
        if baseline['planned_trials'] != len(statuses):
            raise ValueError()
        if baseline['counts'] != {status: statuses.count(status) for status in EXIT_CODES}:
            raise ValueError()
        if baseline['verdict'] == 'pass' and any(status != 'pass' for status in statuses):
            raise ValueError()
        for key in ('model', 'model_revision', 'server_version', 'endpoint'):
            if not isinstance(baseline['configuration'][key], str):
                raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise EvaluationError('invalid_baseline') from None
    return baseline


def compare(report, baseline):
    """Compare matching criteria and complete case/repetition inventories only."""
    validate_baseline(baseline)
    try:
        if baseline['schema_version'] != 2 or baseline['verdict'] not in EXIT_CODES:
            raise ValueError()
        if baseline['criteria_sha256'] != report['criteria_sha256']:
            return {'status': 'incompatible', 'reason': 'criteria_changed'}
        def inventory(value):
            indexed = {}
            for result in value['results']:
                key = (result['case_id'], result['repetition'])
                if key in indexed or result['status'] not in EXIT_CODES:
                    raise ValueError()
                indexed[key] = result['status']
            return indexed
        before, after = inventory(baseline), inventory(report)
        if set(before) != set(after):
            raise ValueError()
        return {'status': 'comparable', 'baseline_verdict': baseline['verdict'],
                'baseline_model': baseline['configuration']['model'],
                'baseline_model_revision': baseline['configuration']['model_revision'],
                'context_changes': {key: {'before': baseline['configuration'].get(key), 'after': report['configuration'].get(key)}
                                    for key in ('model', 'model_revision', 'server_version', 'endpoint')
                                    if baseline['configuration'].get(key) != report['configuration'].get(key)},
                'changes': [{'case_id': key[0], 'repetition': key[1], 'before': before[key], 'after': after[key]}
                            for key in sorted(after) if before[key] != after[key]]}
    except (KeyError, TypeError, ValueError):
        raise EvaluationError('invalid_baseline') from None


def safe_path(path):
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        if component.is_symlink():
            raise EvaluationError('symlink_path_rejected')
    return path


def read_baseline(path):
    path = safe_path(path)
    try:
        if not path.is_file() or path.stat().st_size > MAX_BASELINE:
            raise EvaluationError('invalid_baseline')
        with path.open('rb') as stream:
            data = stream.read(MAX_BASELINE + 1)
        if len(data) > MAX_BASELINE:
            raise EvaluationError('invalid_baseline')
        value = strict_json(data.decode('utf-8'))
        if not isinstance(value, dict):
            raise EvaluationError('invalid_baseline')
        return validate_baseline(value)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise EvaluationError('invalid_baseline') from None


def apply_comparison(report, baseline):
    result = compare(report, baseline)
    report['comparison'] = result
    if result['status'] != 'comparable' and report['verdict'] == 'pass':
        report['verdict'], report['eligible'] = 'inconclusive', False
    return report


def markdown(report):
    counts = report['counts']
    lines = ['# Model security evaluation', '',
             f"Outcome: **{report['verdict']}**. CI admission: **{'allow' if report['eligible'] else 'block'}**.", '',
             f"Run state: {report['run_state']}. Trials: {report['planned_trials']}; passed: {counts['pass']}; failed: {counts['fail']}; inconclusive: {counts['inconclusive']}.",
             f"Requests: {report['requests']}. Criteria: `{report['criteria_sha256']}`.", '',
             'Next action: promote on exit code 0; inspect the case diagnostics for other outcomes.', '',
             '| Case | Repeat | Kind | Status | Diagnostic |', '| --- | --- | --- | --- | --- |']
    for result in report['results']:
        lines.append(f"| {result['case_id']} | {result['repetition']} | {result['kind']} | {result['status']} | {result['diagnostic']} |")
    guard = report.get('guard_criteria')
    if guard and 'profile' in guard:
        lines.extend(['', f"Guard profile: `{guard['profile']}`. Mode: `{guard['mode']}`."])
    if guard and 'output' in guard:
        output = guard['output']
        lines.extend(['', f"Output guard profile: `{output['profile']}`. Mode: `{output['mode']}`."])
    comparison = report.get('guard_comparison')
    if comparison and 'paired' in comparison:
        lines.extend(['', f"Unguarded outcome: **{comparison['unguarded_verdict']}**. "
                      f"Guard-blocked attacks: {comparison['guard_blocked_attacks']}; "
                      f"guard-blocked allowed controls: {comparison['guard_blocked_controls']}.",
                      'A blocked input is recorded as not assessed for model resistance.'])
        lines.extend([f"Output-blocked attacks: {comparison.get('output_guard_blocked_attacks', 0)}; "
                      f"output-blocked allowed controls: {comparison.get('output_guard_blocked_controls', 0)}.",
                      'Generated model violations and released application outputs are recorded separately.'])
    return '\n'.join(lines) + '\n'



def reserve_output(path):
    path = safe_path(path)
    try:
        # Parent must already exist. Never overwrite earlier evidence.
        path.mkdir(mode=0o700)
        return path
    except OSError:
        raise EvaluationError('output_unavailable') from None


def write_report(path, report):
    try:
        encoded = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n'
        if len(encoded.encode()) > MAX_BASELINE:
            raise EvaluationError('report_too_large')
        for name, content in (('report.json', encoded), ('report.md', markdown(report))):
            target = path / name
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(content)
    except OSError:
        raise EvaluationError('report_write_failed') from None


class CheckpointWriter:
    """Private atomic replacement of one owned progress file; final files stay immutable."""
    def __init__(self, path):
        self.path = safe_path(path)
        self.destination = self.path / 'checkpoint.json'
        self.owned = False

    def __call__(self, report):
        from .engine import CheckpointError
        import tempfile
        temporary = None
        try:
            encoded = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False).encode() + b'\n'
            if len(encoded) > MAX_BASELINE:
                raise CheckpointError('checkpoint_too_large')
            if self.destination.is_symlink() or (self.destination.exists() and not self.owned):
                raise CheckpointError('checkpoint_destination_rejected')
            descriptor, name = tempfile.mkstemp(prefix='.checkpoint-', dir=self.path)
            temporary = Path(name)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            self.owned = True
            os.replace(temporary, self.destination)
            temporary = None
        except OSError:
            raise CheckpointError('checkpoint_write_failed') from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
