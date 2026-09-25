"""Helpers for synthetic regression tests; no target-project dependencies."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
cleanup=module('cleanup','skills/sensitive-data-cleanup/scripts/cleanup.py')
pr_context=module('pr_context','skills/security-review/scripts/pr_context.py')
