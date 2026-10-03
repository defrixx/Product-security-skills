"""Include independently packaged prompt guard tests in repository regressions."""
import importlib.util
from pathlib import Path
import unittest


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1] / 'tools/prompt-guard/tests'
    suite = unittest.TestSuite()
    for path in sorted(root.glob('test_*.py')):
        name = 'prompt_guard_package_' + path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
