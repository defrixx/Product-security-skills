#!/usr/bin/env python3
"""Container-only synthetic behavior checker for a narrowly accepted candidate.

The host validates the AST before invoking this worker. No real project files
are mounted. Only Boolean assertions are emitted, never candidate values.
"""
import json
from pathlib import Path


def check(source):
    namespace = {}
    exec(compile(source, 'synthetic_candidate', 'exec'), namespace)
    results = []
    for symbol in ('detail', 'export'):
        for base, identifier, allowed in (
            ('alpha', 1, True), ('beta', 2, True), ('alpha', 2, False),
            ('beta', 1, False), ('missing', 1, False), ('alpha', 999, False)):
            try:
                value = namespace[symbol](base, identifier)
                expected = {'id': identifier, 'base': base, 'text': base + ' note'} if allowed else None
                passed = value == expected
            except Exception:
                passed = False
            results.append({'case': '%s:%s:%s' % (symbol, base, identifier), 'passed': bool(passed)})
    for base in ('alpha', 'beta', 'missing'):
        try:
            value = namespace['search'](base)
            expected = [] if base == 'missing' else [{'id': 1 if base == 'alpha' else 2,
                        'base': base, 'text': base + ' note'}]
            passed = value == expected
        except Exception:
            passed = False
        results.append({'case': 'search:' + base, 'passed': bool(passed)})
    return {'cases': results, 'passed': all(item['passed'] for item in results)}


if __name__ == '__main__':
    print(json.dumps(check(Path('/input/candidate.py').read_text())))
