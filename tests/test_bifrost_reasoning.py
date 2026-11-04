"""Synthetic regression cases based on the observed Bifrost reasoning envelope."""
from pathlib import Path
import copy
import json
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
for folder in ['integrations/bifrost','tools/prompt-guard/src']:
    sys.path.insert(0,str(ROOT/folder))
from client import GuardedClient,BoundaryError
from prompt_guard import OutputGuard,policy_from_dict


def envelope(content='READY',reasoning='Synthetic private deliberation.'):
    return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':content,
        'refusal':None,'reasoning':reasoning,'reasoning_content':reasoning,
        'reasoning_details':[{'index':0,'type':'reasoning.text','text':reasoning}]}}]}


class ReasoningTests(unittest.TestCase):
    def setUp(self):
        self.value=json.loads((ROOT/'tools/prompt-guard/examples/policy.json').read_text())
        self.policy=policy_from_dict(self.value)
        self.sent=[]

    def client(self,response,*,guard=None,mode='inspect-and-drop'):
        def sender(raw):
            self.sent.append(raw);return json.dumps(response).encode()
        return GuardedClient('fixture/synthetic',self.policy,guard or OutputGuard.create(self.policy),sender,reasoning_mode=mode)

    def run_response(self,response,**kwargs):
        return self.client(response,**kwargs).complete(b'{"messages":[{"source":"user","text":"hello"}]}')

    def test_observed_shape_inspected_and_only_visible_text_released(self):
        value=envelope();self.assertEqual(self.run_response(value),'READY')
        self.assertEqual(len(self.sent),1)
        self.assertIn('reasoning',value['choices'][0]['message'])

    def test_default_contract_still_rejects_reasoning(self):
        with self.assertRaisesRegex(BoundaryError,'^output_rejected$'):
            self.run_response(envelope(),mode='reject')

    def test_secret_in_each_field_blocks_whole_answer(self):
        for position in ['content','reasoning','reasoning_content','text','summary','id']:
            value=envelope();msg=value['choices'][0]['message']
            if position in ('text','summary','id'):msg['reasoning_details'][0][position]='SYNTHETIC_PRIVATE_TOKEN_19'
            else:
                msg[position]='SYNTHETIC_PRIVATE_TOKEN_19'
                if position == 'reasoning':msg.pop('reasoning_content')
                if position == 'reasoning_content':msg.pop('reasoning')
            with self.subTest(position=position),self.assertRaises(BoundaryError):self.run_response(value)

    def test_wrapper_field_names_do_not_create_artificial_policy_matches(self):
        value=copy.deepcopy(self.value)
        value['rules']=[{'id':'no-word','kind':'literal','pattern':'reasoning','ignore_case':False,
                         'sources':['assistant'],'action':'block','replacement':None}]
        self.assertEqual(self.run_response(envelope(reasoning='Synthetic notes.'),
                         guard=OutputGuard.create(policy_from_dict(value))),'READY')

    def test_protected_values_survive_combined_guard(self):
        output=OutputGuard.create(self.policy,protected=('SYNTHETIC_PROTECTED_INSTRUCTION',))
        with self.assertRaisesRegex(BoundaryError,'^output_rejected$'):
            self.run_response(envelope(reasoning='SYNTHETIC_PROTECTED_INSTRUCTION'),guard=output)

    def test_review_is_not_released(self):
        value=copy.deepcopy(self.value)
        value['rules']=[{'id':'review-output','kind':'literal','pattern':'REVIEW_ME','ignore_case':False,
                         'sources':['assistant'],'action':'review','replacement':None}]
        with self.assertRaises(BoundaryError):
            self.run_response(envelope(reasoning='REVIEW_ME'),guard=OutputGuard.create(policy_from_dict(value)))

    def test_assembled_rule_spans_visible_and_reasoning(self):
        value=copy.deepcopy(self.value);value['schema_version']=2;value['assembly_separator']=''
        value['limits'].update(overall_ms=6000,memory_mb=256)
        value['rules']=[{'id':'assembled-output','kind':'literal','pattern':'SPLIT_CANARY','ignore_case':False,
                        'sources':['assistant'],'action':'block','replacement':None,'view':'raw',
                        'scope':'assembled','category':'synthetic'}]
        with self.assertRaises(BoundaryError):
            self.run_response(envelope(content='SPLIT_',reasoning='CANARY'),guard=OutputGuard.create(policy_from_dict(value)))

    def test_unknown_opaque_malformed_incomplete_and_tools_rejected(self):
        variants=[]
        for field,value in [('extra','private'),('reasoning',[]),('reasoning_details',None),
                            ('tool_calls',[{'id':'c1'}])]:
            item=envelope();item['choices'][0]['message'][field]=value;variants.append(item)
        for detail in [{'index':0,'type':'reasoning.encrypted','data':'opaque'},
                       {'index':0,'type':'reasoning.text','text':'safe','signature':'opaque'},
                       {'index':True,'type':'reasoning.text','text':'safe'},
                       {'index':0,'type':'reasoning.text','text':42},
                       {'index':0,'type':'reasoning.content_blocks','text':'safe'}]:
            item=envelope();item['choices'][0]['message']['reasoning_details']=[detail];variants.append(item)
        item=envelope();item['choices'][0]['message']['reasoning_content']='different';variants.append(item)
        item=envelope();item['choices'][0]['finish_reason']='length';variants.append(item)
        item=envelope();item['choices'][0]['message']['reasoning_details']*=17;variants.append(item)
        for value in variants:
            with self.subTest(shape=value['choices'][0].get('finish_reason')),self.assertRaises(BoundaryError):self.run_response(value)

    def test_actual_hidden_text_worker_timeout_is_closed(self):
        value=copy.deepcopy(self.value);value['limits']['timeout_ms']=300
        value['rules']=[{'id':'bounded','kind':'regex','pattern':'(a+)+$','ignore_case':False,
                         'sources':['assistant'],'action':'block','replacement':None}]
        output=OutputGuard.create(policy_from_dict(value))
        with self.assertRaises(BoundaryError):self.run_response(envelope(reasoning='a'*10000+'!'),guard=output)
        self.assertEqual(len(self.sent),1)

    def test_guard_failure_and_resource_limit_never_release(self):
        client=self.client(envelope())
        with patch('reasoning.inspect',side_effect=RuntimeError('private')):
            with self.assertRaisesRegex(BoundaryError,'^output_rejected$'):
                client.complete(b'{"messages":[{"source":"user","text":"hello"}]}')
        with self.assertRaises(BoundaryError):self.run_response(envelope(reasoning='x'*1048576))

    def test_safe_summary_and_null_aliases_are_supported(self):
        value=envelope();msg=value['choices'][0]['message'];msg['reasoning']=None;msg['reasoning_content']=None
        msg['reasoning_details']=[{'index':0,'type':'reasoning.summary','summary':'Synthetic summary.','id':'synthetic-1'}]
        self.assertEqual(self.run_response(value),'READY')
