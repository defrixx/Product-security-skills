"""Real fixture effects used by manual triage and verification trials."""
import unittest
import json
import tempfile
from pathlib import Path
from support import cleanup
from security_workflow_fixture import observe


class WorkflowFixtureTests(unittest.TestCase):
    def test_original_partial_fixed_and_safe_control(self):
        result=observe()
        self.assertEqual(result['original']['read']['unauthorized'],'synthetic-B')
        self.assertEqual(result['original']['export']['unauthorized'],'synthetic-B')
        self.assertIsNone(result['original']['safe']['unauthorized'])
        self.assertEqual(result['original']['independent']['unauthorized'],'synthetic-B')
        self.assertEqual(result['fixed']['independent']['unauthorized'],'synthetic-B')
        self.assertIsNone(result['partial']['read']['unauthorized'])
        self.assertEqual(result['partial']['export']['unauthorized'],'synthetic-B')
        for route in ('read','export'):
            self.assertIsNone(result['fixed'][route]['unauthorized'])
            self.assertEqual(result['fixed'][route]['authorized'],'synthetic-A')
            self.assertEqual(result['cosmetic'][route]['unauthorized'],'synthetic-B')
            self.assertIsNone(result['deny_all'][route]['authorized'])

    def test_selected_delivery_cleanup_preserves_ids_and_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'selected';source.mkdir()
            report={'finding_id':'F-001','origin_assessment_id':'triage-1','verification_status':'fixed','email':'person@synthetic.invalid'}
            path=source/'handoff.json';path.write_text(json.dumps(report));before=path.read_bytes()
            result=cleanup.run(source,root/'cleaned','clean-copy',{})
            delivered=json.loads((root/'cleaned'/result['files'][0]['output']).read_text())
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(delivered['finding_id'],'F-001')
            self.assertEqual(delivered['origin_assessment_id'],'triage-1')
            self.assertEqual(delivered['verification_status'],'fixed')
            self.assertNotEqual(delivered['email'],report['email'])
            self.assertNotIn(report['email'],json.dumps(result))


if __name__=='__main__':unittest.main()
