"""Actual runner subprocess failures; fake Docker never runs containers."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'scripts/run_bifrost_isolated_trial.py'


class RunnerFailureTests(unittest.TestCase):
    def fixture(self,root):
        log=root/'docker-calls.jsonl'
        # Startup injection patches only this disposable child. It avoids
        # executable fixtures on /tmp mounts that deliberately use noexec.
        source='''import json,subprocess
from pathlib import Path
_original_output=subprocess.check_output
_original_run=subprocess.run
_log=Path('''+repr(str(log))+''')
def _reply(args):
 with _log.open('a') as f:f.write(json.dumps(args)+'\\n')
 if args[:2]==['image','inspect']:return json.dumps([{'Id':'sha256:'+'0'*64}])
 if args==['network','ls','-q']:return 'occupied'
 if args[:2]==['network','inspect']:return json.dumps([{'IPAM':{'Config':[{'Subnet':'172.16.0.0/12'},{'Subnet':'192.168.0.0/16'}]}}])
 if args[:1]==['ps'] or args[:2]==['network','ls']:return ''
 raise RuntimeError('unexpected_docker_operation')
def _output(command,*args,**kwargs):
 if command[0]=='docker':return _reply(command[1:]).encode()
 return _original_output(command,*args,**kwargs)
def _run(command,*args,**kwargs):
 if command[0]=='docker':return subprocess.CompletedProcess(command,0,stdout=_reply(command[1:]).encode(),stderr=b'')
 return _original_run(command,*args,**kwargs)
subprocess.check_output=_output
subprocess.run=_run
'''
        (root/'sitecustomize.py').write_text(source)
        env=dict(os.environ);env['PYTHONPATH']=str(root)+os.pathsep+env.get('PYTHONPATH','');env.pop('PYTHONOPTIMIZE',None)
        return env,log

    def test_optimized_mode_rejected_before_output_or_docker(self):
        for flag,optimize in [('-O',None),('-OO',None),(None,'1')]:
            with self.subTest(flag=flag,optimize=optimize),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);env,log=self.fixture(root);output=root/'output'
                if optimize:env['PYTHONOPTIMIZE']=optimize
                command=[sys.executable]+([flag] if flag else [])+[str(RUNNER),'--output',str(output)]
                result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2)
                self.assertIn('optimized_python_not_supported',result.stderr)
                self.assertFalse(output.exists());self.assertFalse(log.exists())
                self.assertNotIn('"success": true',result.stdout)

    def test_failed_required_property_cannot_be_recorded_as_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env,log=self.fixture(root);output=root/'output'
            result=subprocess.run([sys.executable,str(RUNNER),'--output',str(output)],env=env,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            evidence=json.loads((output/'evidence.json').read_text())
            self.assertIs(evidence['success'],False);self.assertIs(evidence['tests_passed'],False)
            self.assertEqual(evidence['tests'],[])
            calls=[json.loads(line) for line in log.read_text().splitlines()]
            self.assertFalse(any(row and row[0]=='run' for row in calls))
            self.assertFalse(any(row[:2]==['network','create'] for row in calls))
            self.assertEqual(evidence['cleanup'],{'containers_remaining':'','networks_remaining':''})
