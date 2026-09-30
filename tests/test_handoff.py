"""Synthetic handoff records; structural checks do not establish evidence quality."""
import copy
import json
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('handoff',Path(__file__).resolve().parents[1]/'scripts/validate_handoff.py')
handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)


def record():
    return dict(schema_version=1,assessment_id='verification-1',stage='verification',created_at='2026-09-30T00:00:00Z',producer={'skill':'synthetic','fingerprint':'synthetic-fingerprint'},target={'revision':'snapshot-B','dirty':False},scope={},input_refs=[],coverage={},errors=[],limitations=['synthetic'],findings=[dict(finding_id='F-1',origin_assessment_id='triage-1',aliases=[{'finding_id':'F-2','origin_assessment_id':'triage-1'}],source_refs=[],title='Synthetic defect',root_cause='missing guard',affected_paths=['read'],assessment_status='confirmed',severity={'value':'high','rationale':'synthetic'},confidence={'value':'high','rationale':'execution'},implementation_state='candidate',verification_status='fixed',evidence=[{'observation':'unauthorized read denied'}],acceptance_cases=[{'allowed':'owner read'}],history=[])])


class HandoffTests(unittest.TestCase):
    def test_preserves_independent_statuses(self):
        data=record();before=copy.deepcopy(data)
        self.assertEqual(handoff.validate(data),[]);self.assertEqual(data,before)
        self.assertEqual(data['findings'][0]['assessment_status'],'confirmed')
        self.assertEqual(data['findings'][0]['implementation_state'],'candidate')

    def test_alias_collisions_and_missing_evidence(self):
        data=record();data['findings'][0]['aliases'][0]['finding_id']='F-1'
        self.assertIn('alias_identity_collision',handoff.validate(data))
        data=record();data['findings'][0]['evidence']=[]
        self.assertIn('verification_missing_evidence',handoff.validate(data))

    def test_missing_provenance_and_malformed_fields(self):
        data=record();data['target']={};data['producer']={};data['created_at']='unknown'
        self.assertIn('missing_target_provenance',handoff.validate(data))
        self.assertIn('missing_producer_provenance',handoff.validate(data))
        self.assertIn('invalid_timestamp',handoff.validate(data))
        data=record();data['findings'][0]['aliases']=None;data['findings'][0]['assessment_status']=[]
        self.assertIn('invalid_aliases',handoff.validate(data))
        self.assertIn('invalid_assessment',handoff.validate(data))

    def test_boolean_counts_and_duplicate_json_keys_rejected(self):
        data=record();data['raw_counts']={state:False for state in ('confirmed','hypothesis','disproved','out_of_scope','unprocessed')}
        self.assertIn('raw_count_mismatch',handoff.validate(data))
        data['raw_counts']={state:0 for state in data['raw_counts']}
        self.assertEqual(handoff.validate(data),[])
        with self.assertRaises(ValueError):
            json.loads('{"schema_version":2,"schema_version":1}',object_pairs_hook=handoff.strict_pairs)

    def test_raw_accounting(self):
        data=record();data['raw_results']=[{'run':0,'result':0,'disposition':'hypothesis','duplicate_of':{'origin_assessment_id':'unknown','finding_id':'F-1'}}]
        data['raw_counts']={}
        self.assertIn('dangling_duplicate',handoff.validate(data));self.assertIn('raw_count_mismatch',handoff.validate(data))
        data['schema_version']=2
        self.assertIn('unsupported_version',handoff.validate(data))


if __name__=='__main__':unittest.main()
