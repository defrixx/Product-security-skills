"""Final provider wire contract: tamper rejection and exact verified send bytes."""
import copy,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if not os.environ.get('PROMPT_INTEGRITY_TEST_INSTALLED'):sys.path.insert(0,str(ROOT/'src'))
from prompt_integrity import policy_from_dict,verify_and_send,IntegrityError


def fixture():
    baseline=json.loads((ROOT/'examples/baseline.json').read_text())
    baseline.update(adapter_id='openai-provider-text-v1',allowed_targets={'provider':'synthetic'},
                    allowed_request_fields={'temperature':0,'max_completion_tokens':64})
    baseline['data_message_policy']['roles']=['user']
    request={'model':'synthetic','messages':[{'role':'system','content':baseline['trusted_messages'][0]['text']},
             {'role':'user','content':'Synthetic café question.'}],**baseline['allowed_request_fields']}
    return baseline,request


class ProviderTests(unittest.TestCase):
    def test_exact_bytes_once_and_immutable_policy(self):
        baseline,request=fixture();policy=policy_from_dict(baseline,'synthetic-support','1');sent=[]
        class Wire:
            def send(self,alias,raw):sent.append((alias,raw));return raw
        raw=verify_and_send(policy,json.dumps(request,indent=2).encode(),'provider',Wire())
        self.assertEqual(raw,json.dumps(request,ensure_ascii=False,separators=(',',':')).encode())
        self.assertEqual(sent,[('provider',raw)])
        baseline['trusted_messages'][0]['text']='unapproved change'
        self.assertEqual(verify_and_send(policy,request,'provider',Wire()),raw)

    def test_unapproved_fields_roles_options_and_duplicate_keys_never_send(self):
        baseline,request=fixture();policy=policy_from_dict(baseline,'synthetic-support','1');sent=[]
        class Wire:
            def send(self,*args):sent.append(args)
        variants=[]
        for key,value in [('stream',True),('stream',False),('max_tokens',64),('max_completion_tokens',True),
                          ('temperature',False),('model','other'),('tools',[]),('fallbacks',[]),('extra',{})]:
            item=copy.deepcopy(request);item[key]=value;variants.append(item)
        for index,key,value in [(0,'content','changed'),(1,'role','assistant'),(1,'role','system')]:
            item=copy.deepcopy(request);item['messages'][index][key]=value;variants.append(item)
        variants.append(b'{"model":"synthetic","model":"other"}')
        for item in variants:
            with self.assertRaises(IntegrityError):verify_and_send(policy,item,'provider',Wire())
        self.assertEqual(sent,[])

    def test_provider_policy_is_closed_and_non_streaming(self):
        for mutate in [lambda b:b['allowed_targets'].update(other='other'),
                       lambda b:b['data_message_policy']['roles'].append('assistant'),
                       lambda b:b['allowed_request_fields'].update(stream=False),
                       lambda b:b['allowed_request_fields'].update(max_completion_tokens=False)]:
            baseline,_=fixture();mutate(baseline)
            with self.assertRaises(IntegrityError):policy_from_dict(baseline,'synthetic-support','1')
