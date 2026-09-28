"""Repository-only evidence inventory; partial tests never certify a condition."""
import re
from pathlib import Path


def inventory(root):
    result = {}
    for path in sorted((root / 'skills').rglob('*.md')):
        for identifier in re.findall(r'^### (SD-[A-Z0-9]+-\d{3}\.C\d{2})\b', path.read_text(), re.M):
            result[identifier] = str(path.relative_to(root))
        if path.parent.name == 'stacks' or path.name == 'acceptance-conditions.md':
            for identifier in re.findall(r'^## ((?:SD-[A-Z0-9]+|CLEAN|REVIEW)-\d{3})\b', path.read_text(), re.M):
                result[identifier] = str(path.relative_to(root))
    return result


def build(inventory, mappings, outcomes, run):
    known = {item['case']: item['result'] for item in outcomes}
    by_id = {identifier: [] for identifier in inventory}
    for mapping in mappings:
        if mapping['case'] not in known:
            raise ValueError('Unexecuted or unknown mapped case: ' + mapping['case'])
        for identifier in mapping['conditions']:
            if identifier not in by_id:
                raise ValueError('Unknown mapped condition: ' + identifier)
            by_id[identifier].append(dict(mapping, result=known[mapping['case']]))
    return {'run': run, 'kind': 'known-answer synthetic/helper evaluation; no agent evaluation',
            'conditions': {identifier: {'source': path,
                'status': 'partial_evidence' if by_id[identifier] else 'not_exercised_in_this_run',
                'evidence': by_id[identifier],
                'untested': 'All clauses and target implementations beyond the exact mapped behavior. No full-condition pass is inferred.'}
                for identifier, path in inventory.items()}}
