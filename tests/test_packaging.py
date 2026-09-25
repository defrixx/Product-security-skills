import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from support import ROOT

class PackagingTests(unittest.TestCase):
    def test_copied_cleanup_skill_runs_without_repo_dependencies(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);skill=root/'skill';shutil.copytree(ROOT/'skills/sensitive-data-cleanup',skill,ignore=shutil.ignore_patterns('__pycache__'))
            src=root/'input';src.mkdir();(src/'sample.json').write_text('{"api_key":"SYNTHETIC_ONLY"}')
            p=subprocess.run([sys.executable,str(skill/'scripts/cleanup.py'),'--source',str(src),'--output',str(root/'result'),'--mode','clean-copy'],cwd=root,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('SYNTHETIC_ONLY',p.stdout+p.stderr)
            self.assertEqual(json.loads((root/'result/report.json').read_text())['counts']['replacement_occurrences'],1)
    def test_copied_pr_helper_has_no_sibling_dependency(self):
        from pr_fixture import build
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);skill=root/'skill';shutil.copytree(ROOT/'skills/security-review',skill,ignore=shutil.ignore_patterns('__pycache__'))
            repo=root/'repo';ids=build(repo)
            p=subprocess.run([sys.executable,str(skill/'scripts/pr_context.py'),'--repo',str(repo),'--base',ids['base'],'--head',ids['head'],'--output',str(root/'report.json')],cwd=root,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads((root/'report.json').read_text())['merge_base'],ids['merge_base'])
