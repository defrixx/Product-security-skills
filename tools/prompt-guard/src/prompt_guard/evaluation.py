"""Labeled local detector metrics and descriptive latency measurements."""
import hashlib
import json
import platform
import statistics
import time
from .core import inspect, require
from .profiles import load_profile


def evaluate_corpus(cases, *, repetitions=1):
    require(type(cases) is list and 0 < len(cases) <= 1000, 'corpus_invalid')
    require(type(repetitions) is int and 1 <= repetitions <= 10, 'corpus_invalid')
    policies, seen = {}, set()
    for case in cases:
        require(type(case) is dict and type(case.get('id')) is str and case['id'] not in seen, 'corpus_invalid')
        seen.add(case['id'])
        require(case.get('expected') in ('allow', 'block') and type(case.get('category')) is str, 'corpus_invalid')
        policies.setdefault(case['profile'], None)
    for name in policies:
        policies[name] = load_profile(name)
    results, latencies = [], []
    by_category = {}
    started = time.monotonic()
    for repetition in range(repetitions):
        for case in cases:
            sample = time.monotonic()
            if case.get('direction') == 'output':
                from .output import OutputGuard
                boundary = OutputGuard.create(policies[case['profile']], mode=case.get('mode', 'strict'))
                result = boundary.check_text(case['text'])
            elif 'messages' in case:
                result = inspect(policies[case['profile']], json.dumps({'messages': case['messages']}).encode(),
                                 format='json', source=None)
            else:
                result = inspect(policies[case['profile']], case['text'].encode('utf-8'), source=case['source'])
            latency = (time.monotonic() - sample) * 1000
            latencies.append(latency)
            counts = by_category.setdefault(case['category'], dict(true_positive=0, true_negative=0,
                                           false_positive=0, false_negative=0, review=0, error=0))
            if result.decision in ('review', 'error'):
                counts[result.decision] += 1
            else:
                positive = result.decision == 'block'
                correct = result.decision == case['expected']
                counts[('true_' if correct else 'false_') + ('positive' if positive else 'negative')] += 1
            results.append({'case_id': case['id'], 'category': case['category'], 'repetition': repetition,
                            'expected': case['expected'], 'decision': result.decision, 'code': result.code,
                            'elapsed_ms': round(latency, 3)})
    elapsed = time.monotonic() - started
    ordered = sorted(latencies)
    return {'kind': 'synthetic-labeled-detector-evaluation', 'by_category': by_category, 'results': results,
            'policy_fingerprints': {name: hashlib.sha256(p.encoded).hexdigest() for name, p in policies.items()},
            'latency_ms': {'median': round(statistics.median(latencies), 3),
                           'p95': round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 3)},
            'inputs_per_second': round(len(results) / elapsed, 3),
            'runtime': {'python': platform.python_version(), 'platform': platform.system()},
            'all_expected': all(r['decision'] == r['expected'] for r in results)}
