"""Bounded regex compilation, detection views and matching; spans only on output."""
import json
import re
import resource
import signal
import sys
import unicodedata


def view(text, normalized=False, fold=False):
    """Normalize base/combining clusters and map each output character to its origin."""
    if not normalized:
        return text, [(i, i + 1) for i in range(len(text))]
    output, mapping = [], []
    index = 0
    while index < len(text):
        start = index
        index += 1
        while index < len(text) and (unicodedata.category(text[index]).startswith('M') or unicodedata.category(text[index]) == 'Cf'):
            index += 1
        cluster = ''.join(c for c in text[start:index] if unicodedata.category(c) != 'Cf')
        cluster = unicodedata.normalize('NFKC', cluster)
        if fold:
            cluster = cluster.casefold()
        output.append(cluster)
        mapping.extend([(start, index)] * len(cluster))
    return ''.join(output), mapping


def main():
    try:
        task = json.load(sys.stdin)
        try:
            maximum = task['memory_mb'] * 1024 * 1024
            if sys.platform == 'darwin':
                # macOS rejects low RLIMIT_AS values for its reserved address space.
                # Check peak resident memory on recurring interpreter signal checks.
                def check_memory(signum, frame):
                    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > maximum:
                        raise MemoryError()
                signal.signal(signal.SIGALRM, check_memory)
                signal.setitimer(signal.ITIMER_REAL, 0.01, 0.01)
                check_memory(None, None)
            else:
                _, hard = resource.getrlimit(resource.RLIMIT_AS)
                if hard != resource.RLIM_INFINITY:
                    maximum = min(maximum, hard)
                resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
        except (ValueError, OSError):
            print(json.dumps({'error': 'memory_limit_unavailable'}))
            return
        compiled = []
        for rule in task['rules']:
            normalized = rule.get('view', 'raw') == 'normalized'
            pattern = rule['pattern']
            if rule['kind'] == 'literal':
                pattern = view(pattern, normalized, rule['ignore_case'])[0]
                if not pattern:
                    raise ValueError()
                pattern = re.escape(pattern)
            expression = re.compile(pattern, re.IGNORECASE if rule['ignore_case'] else 0)
            if expression.search('') is not None:
                raise ValueError()
            compiled.append(expression)
        if task.get('operation') == 'validate':
            print(json.dumps({'validated': True}))
            return
        matches = []
        for rule_index, (rule, expression) in enumerate(zip(task['rules'], compiled)):
            selected = [(i, m['text']) for i, m in enumerate(task['messages']) if m['source'] in rule['sources']]
            if rule.get('scope', 'message') == 'assembled':
                selected = [(-1, task.get('assembly_separator', '\n').join(text for _, text in selected))]
            for index, text in selected:
                normalized = rule.get('view', 'raw') == 'normalized'
                detected, mapping = view(text, normalized, rule['ignore_case'])
                for match in expression.finditer(detected):
                    if match.start() == match.end():
                        print(json.dumps({'error': 'empty_match'}))
                        return
                    start, end = mapping[match.start()][0], mapping[match.end() - 1][1]
                    matches.append([index, rule_index, start, end])
                    if len(matches) > task['max_matches']:
                        print(json.dumps({'error': 'match_limit'}))
                        return
        print(json.dumps({'matches': matches}))
    except MemoryError:
        print('{"error":"memory_limit"}')
    except (ValueError, TypeError, KeyError, re.error, RecursionError):
        print('{"error":"policy_invalid"}')


if __name__ == '__main__':
    main()
