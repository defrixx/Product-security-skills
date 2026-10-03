"""Include independently packaged evaluation tests in repository regressions."""
import importlib.util
from pathlib import Path
import sys
import unittest


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1] / 'tools/model-security-eval/tests'
    sys.path.insert(0, str(root))
    suite = unittest.TestSuite()
    for path in sorted(root.glob('test_*.py')):
        name = 'model_eval_package_' + path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
