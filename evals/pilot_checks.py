"""Fixed executable checks for synthetic virtual files; no model-chosen paths.

Only trusted repository helper code runs on the host. AST-restricted candidate
Python runs in disposable containers. Temporary files contain synthetic fixture
data and are removed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(content):
    return hashlib.sha256(content.encode()).hexdigest()


def clean_settings(content):
    path = ROOT / 'skills/sensitive-data-cleanup/scripts/cleanup.py'
    spec = importlib.util.spec_from_file_location('pilot_cleanup_helper', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # Scope-specific suppression: the task explicitly identifies this UI label.
    policy = {'suppressions': [{'file': 'settings.json', 'pointer': '/labels/api_key',
        'expected_value': 'API key', 'reason': 'Synthetic scenario UI label, not a credential'}]}
    with tempfile.TemporaryDirectory(prefix='synthetic-pilot-cleanup-') as tmp:
        root = Path(tmp)
        source = root / 'source'; source.mkdir()
        original = source / 'settings.json'; original.write_text(content)
        output = root / 'copy'
        report = helper.run(source, output, 'clean-copy', policy)
        entries = [item for item in report['files'] if item.get('output')]
        if len(entries) != 1 or report['counts']['failed']:
            return {'status': 'error', 'code': 'cleanup_did_not_produce_one_file'}
        cleaned = (output / entries[0]['output']).read_text()
        return {'status': 'executed', 'check': 'cleanup_helper', 'helper_report': report,
                'source_preserved': original.read_text() == content,
                'input_sha256': fingerprint(content), 'output_sha256': fingerprint(cleaned),
                'content': cleaned,
                'limitations': ['fixed synthetic JSON scope and label suppression',
                                'same-detector rescan does not prove complete cleanup']}


def check_settings(content, original):
    try:
        value = json.loads(content)
        source = json.loads(original)
        seed = source['credentials']['api_key']
        checks = {'credential_replaced': type(value['credentials']['api_key']) is str and
                  bool(value['credentials']['api_key']) and value['credentials']['api_key'] != seed,
                  'seed_absent': seed not in content,
                  'benign_values_preserved': value['labels'] == source['labels'] and
                   type(value['count']) is int and value['count'] == source['count'],
                  'top_level_keys_preserved': set(value) == set(source)}
        return {'status': 'executed', 'check': 'synthetic_json_assertions',
                'subject_sha256': fingerprint(content), 'checks': checks,
                'passed': all(checks.values()),
                'limitations': ['exact seeded-value and labeled benign controls only; not a general detector']}
    except (ValueError, KeyError, TypeError):
        return {'status': 'executed', 'check': 'synthetic_json_assertions',
                'subject_sha256': fingerprint(content), 'passed': False,
                'error': 'invalid_expected_json'}


def supported_python(content):
    """Deliberately narrow synthetic language; reject imports, I/O, mutation, etc."""
    import ast
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError, RecursionError):
        return False
    allowed = (ast.Module, ast.Assign, ast.Name, ast.Store, ast.Load, ast.List,
               ast.Dict, ast.Constant, ast.FunctionDef, ast.arguments, ast.arg,
               ast.Return, ast.Call, ast.GeneratorExp, ast.ListComp, ast.comprehension,
               ast.Compare, ast.Eq, ast.BoolOp, ast.And, ast.Subscript)
    names = {'RECORDS', 'detail', 'search', 'export', 'base', 'record_id', 'r', 'next'}
    nodes = list(ast.walk(tree))
    if len(nodes) > 500 or any(not isinstance(node, allowed) for node in nodes):
        return False
    if len(tree.body) != 4 or not isinstance(tree.body[0], ast.Assign):
        return False
    assignment = tree.body[0]
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name) or assignment.targets[0].id != 'RECORDS':
        return False
    try:
        # The task allows fixing access logic, not rewriting the labeled data.
        if ast.literal_eval(assignment.value) != [
            {'id': 1, 'base': 'alpha', 'text': 'alpha note'},
            {'id': 2, 'base': 'beta', 'text': 'beta note'}]:
            return False
    except (ValueError, TypeError):
        return False
    functions = tree.body[1:]
    if any(not isinstance(fn, ast.FunctionDef) for fn in functions):
        return False
    if {fn.name for fn in functions} != {'detail', 'search', 'export'}:
        return False
    for fn in functions:
        args = fn.args
        expected = ['base'] if fn.name == 'search' else ['base', 'record_id']
        if (fn.decorator_list or fn.returns or len(fn.body) != 1 or not isinstance(fn.body[0], ast.Return)
            or [a.arg for a in args.args] != expected or args.posonlyargs or args.kwonlyargs
            or args.vararg or args.kwarg or args.defaults or args.kw_defaults):
            return False
    for node in nodes:
        if isinstance(node, ast.Name) and node.id not in names:
            return False
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or
                node.func.id not in {'next', 'detail', 'search', 'export'} or node.keywords):
            return False
        if isinstance(node, ast.comprehension) and node.is_async:
            return False
    return True


def check_python(content):
    """Run 15 assertions in a disposable, network-disabled resource-limited container."""
    import subprocess
    import uuid
    if not supported_python(content):
        return {'status': 'not_executed', 'check': 'python_behavior',
                'code': 'outside_supported_synthetic_python_subset', 'subject_sha256': fingerprint(content)}
    image = 'python:3.12-slim'
    name = 'skill-pilot-' + uuid.uuid4().hex
    worker = ROOT / 'evals/pilot_python_check.py'
    cleanup = {'attempted': False, 'succeeded': False}
    with tempfile.TemporaryDirectory(prefix='synthetic-pilot-python-') as tmp:
        path = Path(tmp) / 'candidate.py'; path.write_text(content)
        # The private parent remains 0700 on the host. The single read-only bind
        # must also be readable by the unprivileged container UID on Linux.
        path.chmod(0o444)
        command = ['docker', 'run', '--rm', '--pull=never', '--name', name,
            '--network', 'none', '--read-only', '--cap-drop=ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '32',
            '--memory', '128m', '--cpus', '1', '--user', '65534:65534',
            '--log-driver', 'none', '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-v', str(path) + ':/input/candidate.py:ro',
            '-v', str(worker) + ':/check.py:ro', image, 'python3', '-I', '/check.py']
        try:
            identity = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
                capture_output=True, text=True, timeout=10, check=True).stdout.strip()
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
            observation = json.loads(result.stdout)
            return {'status': 'executed', 'check': 'python_behavior', 'subject_sha256': fingerprint(content),
                    'worker_sha256': fingerprint(worker.read_text()), 'image_id': identity, 'cleanup': cleanup,
                    **observation, 'limitations': ['15 labeled function cases',
                        'restricted synthetic Python subset; no arbitrary candidate execution']}
        except (OSError, subprocess.SubprocessError, ValueError):
            return {'status': 'not_executed', 'check': 'python_behavior',
                    'code': 'isolated_check_unavailable_or_failed', 'subject_sha256': fingerprint(content), 'cleanup': cleanup}
        finally:
            try:
                cleanup['attempted'] = True
                removed = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=10)
                cleanup['succeeded'] = removed.returncode == 0
            except (OSError, subprocess.SubprocessError):
                pass
