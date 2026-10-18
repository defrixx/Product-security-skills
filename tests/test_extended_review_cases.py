"""Synthetic regression cases for caller exposure and compound cleanup boundaries.

The unguarded route below is intentionally unsafe; the guarded route is its
safe control. No target-project source, external services or real data is used.
"""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from pr_fixture import git
from support import cleanup


class ExtendedReviewCases(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_new_caller_exposes_unchanged_privileged_helper(self):
        repo = self.root / 'repo'
        repo.mkdir()
        git(repo, 'init', '-b', 'main')
        source = '''# Synthetic fixture: route without guard is intentionally unsafe.
def privileged_read():
    return 'SYNTHETIC_PROTECTED_RECORD'

def guarded_route(is_admin):
    return privileged_read() if is_admin else None

routes = {'admin': guarded_route}
'''
        (repo / 'app.py').write_text(source)
        git(repo, 'add', 'app.py')
        git(repo, 'commit', '-m', 'Synthetic guarded base')
        base = git(repo, 'rev-parse', 'HEAD')
        (repo / 'app.py').write_text(source + "routes['public'] = lambda is_admin: privileged_read()\n")
        git(repo, 'add', 'app.py')
        git(repo, 'commit', '-m', 'Synthetic new unguarded caller')
        head = git(repo, 'rev-parse', 'HEAD')
        before, after = {}, {}
        # Execute only fixed fixture source created above, never imported project code.
        exec(compile(git(repo, 'show', base + ':app.py'), 'synthetic-before', 'exec'), before)
        exec(compile(git(repo, 'show', head + ':app.py'), 'synthetic-after', 'exec'), after)
        self.assertNotIn('public', before['routes'])
        self.assertIsNone(before['routes']['admin'](False))
        self.assertIsNone(after['routes']['admin'](False))
        self.assertEqual(after['routes']['public'](False), 'SYNTHETIC_PROTECTED_RECORD')
        self.assertEqual(after['routes']['admin'](True), 'SYNTHETIC_PROTECTED_RECORD')
        self.assertEqual(before['privileged_read'].__code__.co_code,
                         after['privileged_read'].__code__.co_code)
        self.assertEqual(git(repo, 'diff', base, head, '--', 'app.py').count('+routes'), 1)

    def test_cross_format_entity_consistency_and_distinctness(self):
        source = self.root / 'input'
        source.mkdir()
        a, b = 'SYNTHETIC_ENTITY_ALPHA', 'SYNTHETIC_ENTITY_BETA'
        (source / 'a.json').write_text(json.dumps({'first': a, 'same': a, 'second': b, 'label': 'Entity label'}))
        (source / 'b.csv').write_text('first,second,label\n' + a + ',' + b + ',Entity label\n')
        (source / 'c.txt').write_text(a + '\n' + b + '\nEntity label\n')
        original = {p.name: p.read_bytes() for p in source.iterdir()}
        output = self.root / 'output'
        report = cleanup.run(source, output, 'clean-copy', {'sensitive_values': [a, b]})
        import csv
        emitted = {Path(f['output']).suffix: (output / f['output']).read_text()
                   for f in report['files'] if 'output' in f}
        obj = json.loads(emitted['.json'])
        row = next(csv.DictReader(io.StringIO(emitted['.csv'])))
        lines = emitted['.txt'].splitlines()
        self.assertEqual(obj['first'], obj['same'])
        self.assertEqual((obj['first'], obj['second']), (row['first'], row['second']))
        self.assertEqual((obj['first'], obj['second']), tuple(lines[:2]))
        self.assertNotEqual(obj['first'], obj['second'])
        self.assertEqual((obj['label'], row['label'], lines[2]), ('Entity label',) * 3)
        self.assertEqual(original, {p.name: p.read_bytes() for p in source.iterdir()})
        self.assertEqual(report['counts']['replacement_occurrences'], 7)
        for value in (a, b):
            self.assertNotIn(value, json.dumps(report))
            self.assertTrue(all(value not in content for content in emitted.values()))

    def test_nested_archive_and_office_container_are_omitted_without_extraction(self):
        source = self.root / 'input'
        source.mkdir()
        seed = 'SYNTHETIC_EMBEDDED_SECRET'
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as archive:
            archive.writestr('../../escape.txt', seed)
        with zipfile.ZipFile(source / 'nested.zip', 'w') as archive:
            archive.writestr('inner.zip', inner.getvalue())
            archive.comment = seed.encode()
        with zipfile.ZipFile(source / 'document.docx', 'w') as archive:
            archive.writestr('word/comments.xml', '<comment>' + seed + '</comment>')
            archive.writestr('docProps/core.xml', '<creator>' + seed + '</creator>')
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}
        report = cleanup.run(source, self.root / 'output', 'clean-copy')
        self.assertEqual(report['counts']['emitted_files'], 0)
        self.assertEqual(report['counts']['skipped'], 2)
        self.assertFalse((self.root / 'escape.txt').exists())
        self.assertNotIn(seed, json.dumps(report))
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()})


if __name__ == '__main__':
    unittest.main()
