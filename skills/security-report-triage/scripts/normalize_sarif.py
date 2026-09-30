#!/usr/bin/env python3
"""Bounded local SARIF inventory. Never executes or resolves report content."""
import argparse
import json
import math
import os
from pathlib import Path
import stat
import sys

DEFAULTS = dict(input_bytes=20*1024*1024, runs=20, results=10000, depth=64,
                nodes=100000, text_bytes=8192, output_bytes=40*1024*1024)


class IntakeError(Exception):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise IntakeError('duplicate_key')
        result[key] = value
    return result


def decode(raw, limits):
    # Bound nesting before recursive JSON decoding; quoted braces are data.
    depth = 0
    quoted = escape = False
    for byte in raw:
        if quoted:
            if escape:
                escape = False
            elif byte == 92:
                escape = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > limits['depth']:
                raise IntakeError('depth_limit')
        elif byte in (93, 125):
            depth -= 1
    def invalid(_):
        raise IntakeError('invalid_number')
    try:
        obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                         parse_constant=invalid)
        pending = [obj]
        nodes = 0
        while pending:
            value = pending.pop()
            nodes += 1
            if nodes > limits['nodes']:
                raise IntakeError('node_limit')
            if isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
            elif isinstance(value, str):
                value.encode('utf-8', errors='strict')
            elif isinstance(value, float) and not math.isfinite(value):
                raise IntakeError('invalid_number')
        return obj
    except (ValueError, UnicodeError, RecursionError):
        raise IntakeError('invalid_json') from None


def read_input(path, limit):
    # Walk from the filesystem root using no-follow descriptors (POSIX only).
    absolute = Path(os.path.abspath(path))
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        source = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise IntakeError('unsupported_input_file')
            if before.st_size > limit:
                raise IntakeError('input_limit')
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(raw) > limit:
                raise IntakeError('input_limit')
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise IntakeError('source_changed')
            return raw
    finally:
        os.close(fd)


def normalize(document, limits):
    if not isinstance(document, dict) or document.get('version') != '2.1.0' or not isinstance(document.get('runs'), list):
        raise IntakeError('unsupported_document')
    runs = document['runs']
    if len(runs) > limits['runs']:
        raise IntakeError('run_limit')
    total = sum(len(r.get('results', [])) for r in runs
                if isinstance(r, dict) and isinstance(r.get('results', []), list))
    if total > limits['results']:
        raise IntakeError('result_limit')
    issues = set()
    records = []
    summaries = []
    opaque = {}
    def token(kind, value):
        if value is None:
            return None
        # Never emit arbitrary strings, hashes, or persisted reverse mappings.
        key = (kind, json.dumps(value, sort_keys=True, ensure_ascii=True))
        if key not in opaque:
            opaque[key] = '%s%06d' % (kind, len(opaque)+1)
        return opaque[key]
    def enum(value, allowed):
        if isinstance(value, str) and value in allowed:
            return value
        if value is not None:
            issues.add('invalid_enum')
        return None
    def unknown(obj, allowed):
        if set(obj) - set(allowed):
            issues.add('unsupported_fields')
    def location(value):
        if not isinstance(value, dict):
            issues.add('malformed_location')
            return {'id': token('L', value), 'resolution': 'not_resolved'}
        physical = value.get('physicalLocation', {})
        unknown(value, ('physicalLocation',))
        if not isinstance(physical, dict):
            issues.add('malformed_location')
            physical = {}
        unknown(physical, ('artifactLocation', 'region'))
        region = physical.get('region', {})
        if not isinstance(region, dict):
            issues.add('malformed_region')
            region = {}
        unknown(region, ('startLine', 'startColumn', 'endLine', 'endColumn'))
        coordinates = {}
        for key in ('startLine', 'startColumn', 'endLine', 'endColumn'):
            n = region.get(key)
            if type(n) is int and 0 < n < 2**31:
                coordinates[key] = n
            elif n is not None:
                issues.add('invalid_coordinate')
        artifact = physical.get('artifactLocation')
        if isinstance(artifact, dict):
            unknown(artifact, ('uri', 'uriBaseId', 'index'))
        elif artifact is not None:
            issues.add('malformed_artifact')
        return {'id': token('L', value), 'artifact_id': token('A', artifact),
                'region': coordinates, 'resolution': 'not_resolved'}
    unknown(document, ('version', '$schema', 'runs'))
    for ri, run in enumerate(runs):
        if not isinstance(run, dict):
            issues.add('malformed_run')
            summaries.append({'run': ri, 'raw_results': None, 'invocation_complete': None})
            continue
        unknown(run, ('tool', 'results', 'invocations'))
        if 'externalPropertyFileReferences' in run:
            issues.add('external_properties_not_loaded')
        tool = run.get('tool', {})
        if not isinstance(tool, dict):
            tool = {}
            issues.add('malformed_tool')
        unknown(tool, ('driver',))
        driver = tool.get('driver', {})
        if not isinstance(driver, dict):
            driver = {}
            issues.add('malformed_tool')
        unknown(driver, ('name', 'version', 'semanticVersion', 'rules'))
        rules = driver.get('rules', [])
        if not isinstance(rules, list):
            rules = []
            issues.add('malformed_rules')
        for rule in rules:
            if isinstance(rule, dict):
                unknown(rule, ('id',))
            else:
                issues.add('malformed_rule')
        invocations = run.get('invocations', [])
        complete = None
        if isinstance(invocations, list) and invocations:
            values = [i.get('executionSuccessful') if isinstance(i, dict) else None for i in invocations]
            complete = all(v is True for v in values) if all(type(v) is bool for v in values) else None
            for invocation in invocations:
                if isinstance(invocation, dict):
                    unknown(invocation, ('executionSuccessful',))
            if complete is not True:
                issues.add('invocation_incomplete')
        else:
            issues.add('invocation_unknown')
        results = run.get('results')
        if not isinstance(results, list):
            issues.add('results_unknown')
            summaries.append({'run': ri, 'raw_results': None, 'invocation_complete': complete})
            continue
        summaries.append({'run': ri, 'raw_results': len(results), 'invocation_complete': complete,
                          'tool_id': token('T', driver.get('name')), 'tool_version_id': token('V', driver.get('version', driver.get('semanticVersion')))})
        for ordinal, result in enumerate(results):
            record = {'id': 'R%04d-S%06d' % (ri, ordinal), 'run': ri, 'result': ordinal,
                      'disposition': 'hypothesis', 'locations': [], 'code_flow_locations': []}
            records.append(record)
            if not isinstance(result, dict):
                record.update(disposition='unprocessed', reason='malformed_result')
                issues.add('malformed_result')
                continue
            unknown(result, ('ruleId', 'ruleIndex', 'level', 'message', 'locations', 'codeFlows',
                             'fingerprints', 'partialFingerprints', 'baselineState', 'suppressions'))
            rule_id = result.get('ruleId')
            index = result.get('ruleIndex')
            if index is not None:
                if type(index) is int and 0 <= index < len(rules) and isinstance(rules[index], dict):
                    indexed = rules[index].get('id')
                    if rule_id is not None and indexed != rule_id:
                        issues.add('rule_mismatch')
                    rule_id = rule_id if rule_id is not None else indexed
                else:
                    issues.add('rule_index_unresolved')
            if not isinstance(rule_id, str):
                rule_id = None
                issues.add('rule_unknown')
            record['rule_id'] = token('Q', [ri, rule_id]) if rule_id is not None else None
            record['level'] = enum(result.get('level'), ('none', 'note', 'warning', 'error'))
            record['baseline_state'] = enum(result.get('baselineState'), ('new', 'unchanged', 'updated', 'absent'))
            record['message_omitted'] = 'message' in result
            message = result.get('message')
            if isinstance(message, dict):
                unknown(message, ('text', 'markdown', 'id', 'arguments'))
            elif message is not None:
                issues.add('malformed_message')
            locations = result.get('locations', [])
            if isinstance(locations, list):
                record['locations'] = [location(item) for item in locations]
            else:
                issues.add('malformed_locations')
            flows = result.get('codeFlows', [])
            if not isinstance(flows, list):
                issues.add('malformed_code_flows')
                flows = []
            for flow in flows:
                if not isinstance(flow, dict) or not isinstance(flow.get('threadFlows'), list):
                    issues.add('malformed_code_flow')
                    continue
                unknown(flow, ('threadFlows',))
                for thread in flow['threadFlows']:
                    if not isinstance(thread, dict) or not isinstance(thread.get('locations'), list):
                        issues.add('malformed_thread_flow')
                        continue
                    unknown(thread, ('locations',))
                    for item in thread['locations']:
                        if not isinstance(item, dict):
                            issues.add('malformed_thread_location')
                            continue
                        unknown(item, ('location',))
                        record['code_flow_locations'].append(location(item.get('location')))
            record['fingerprint_ids'] = []
            for key in ('fingerprints', 'partialFingerprints'):
                fp = result.get(key, {})
                if isinstance(fp, dict):
                    record['fingerprint_ids'].extend(token('P', [key, k, v]) for k, v in fp.items())
                else:
                    issues.add('malformed_fingerprints')
            record['suppressions'] = []
            suppressions = result.get('suppressions', [])
            if not isinstance(suppressions, list):
                issues.add('malformed_suppressions')
                suppressions = []
            for suppression in suppressions:
                if isinstance(suppression, dict):
                    unknown(suppression, ('kind', 'status'))
                    record['suppressions'].append({'kind': enum(suppression.get('kind'), ('inSource', 'external')),
                                                  'status': enum(suppression.get('status'), ('accepted', 'underReview', 'rejected'))})
                else:
                    issues.add('malformed_suppression')
    # Arbitrary text is omitted regardless of length; record oversized context.
    pending = [document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.keys()); pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str) and len(value.encode('utf-8')) > limits['text_bytes']:
            issues.add('text_limit_omitted')
    known = all(r['raw_results'] is not None for r in summaries)
    summary = {'schema_version': 1, 'status': 'partial' if issues else 'completed_within_subset',
               'runs': summaries, 'raw_results': len(records) if known else None,
               'normalized_results': len(records), 'issues': sorted(issues), 'limits': limits,
               'limitations': ['not_a_security_assessment', 'all_arbitrary_text_omitted',
                               'locations_not_resolved', 'opaque_ids_local_to_input', 'no_full_sarif_validation']}
    return {'schema_version': 1, 'results': records}, summary


def write_output(output, source, target, documents, limit):
    dest = Path(os.path.abspath(output))
    source = Path(source).resolve(strict=True)
    if dest.exists() or dest.is_symlink():
        raise IntakeError('output_exists')
    if source == dest or source.is_relative_to(dest):
        raise IntakeError('output_overlap')
    if target:
        root = Path(target).resolve(strict=True)
        resolved = dest.resolve()
        if resolved == root or resolved.is_relative_to(root) or root.is_relative_to(resolved):
            raise IntakeError('output_overlap')
    buffers = {name: (json.dumps(doc, indent=2, ensure_ascii=True)+'\n').encode() for name, doc in documents.items()}
    if sum(map(len, buffers.values())) > limit:
        raise IntakeError('output_limit')
    parent = os.open(dest.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in dest.parts[1:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = new
        os.mkdir(dest.name, 0o700, dir_fd=parent)
        folder = os.open(dest.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            def write(name, data):
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
            write('RUNNING', b'incomplete\n')
            for name, data in buffers.items():
                write(name, data)
            os.unlink('RUNNING', dir_fd=folder)
        finally:
            os.close(folder)
    finally:
        os.close(parent)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise IntakeError('invalid_arguments')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--input', required=True)
        parser.add_argument('--output', required=True)
        parser.add_argument('--target-root')
        for name, value in DEFAULTS.items():
            parser.add_argument('--max-'+name.replace('_', '-'), type=int, default=value)
        args = parser.parse_args(argv)
        limits = {key: getattr(args, 'max_'+key) for key in DEFAULTS}
        if any(value <= 0 for value in limits.values()):
            raise IntakeError('invalid_limit')
        raw = read_input(args.input, limits['input_bytes'])
        normalized, summary = normalize(decode(raw, limits), limits)
        write_output(args.output, args.input, args.target_root,
                     {'normalized.json': normalized, 'normalization-summary.json': summary}, limits['output_bytes'])
        print(json.dumps({'status': summary['status'], 'results': summary['normalized_results']}))
        return 2 if summary['issues'] else 0
    except IntakeError as error:
        print(json.dumps({'status': 'error', 'code': str(error)}), file=sys.stderr)
        return 1
    except Exception:
        print('{"status":"error","code":"operation_failed"}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
