"""Standalone pinned streaming/tool-history wire contract regressions."""
import copy,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if not os.environ.get('PROMPT_INTEGRITY_TEST_INSTALLED'):sys.path.insert(0,str(ROOT/'src'))
from prompt_integrity import policy_from_dict,verify_and_send,IntegrityError

class AgentWireTests(unittest.TestCase):
    def fixture(self,provider):
        base=json.loads((ROOT/'examples/baseline.json').read_text())
        base.update(adapter_id='openai-provider-agent-v1' if provider else 'bifrost-chat-agent-v1',allowed_targets={'primary':'synthetic'})
        base['data_message_policy']['roles']=['user','assistant','tool']
        tool={'type':'function','function':{'name':'read_record','description':'Read fixture.','parameters':{'type':'object','properties':{},'additionalProperties':False}}}
        options={'temperature':0,'max_completion_tokens' if provider else 'max_tokens':64,'tools':[tool],'stream':True}
        if provider:options['stream_options']={'include_usage':True}
        base['allowed_request_fields']=options
        request={'model':'synthetic','messages':[{'role':'system','content':base['trusted_messages'][0]['text']},{'role':'user','content':'Synthetic fixture.'}],**options}
        return base,request

    def test_original_streaming_bytes_sent_once_and_history_grammar(self):
        for provider in [False,True]:
            base,request=self.fixture(provider);policy=policy_from_dict(base,'synthetic-support','1');sent=[]
            class Wire:
                def send(self,alias,raw):sent.append(raw);return raw
            response=verify_and_send(policy,request,'primary',Wire())
            self.assertEqual(json.loads(response),request);self.assertTrue(json.loads(response)['stream']);self.assertEqual(sent,[response])
            history=copy.deepcopy(request)
            history['messages'] += [{'role':'assistant','content':'','tool_calls':[{'id':'c1','type':'function','function':{'name':'read_record','arguments':'{}'}}]}, {'role':'tool','tool_call_id':'c1','content':'{"value":"synthetic"}'}]
            if provider:history['messages'][-2]['tool_calls'][0]['index']=0
            result=verify_and_send(policy,history,'primary',Wire());self.assertEqual(json.loads(result),history)
            for key,value in [('stream',False),('tools',[]),('model','fallback'),('extra',True)]:
                changed=copy.deepcopy(request);changed[key]=value
                with self.assertRaises(IntegrityError):verify_and_send(policy,changed,'primary',Wire())
            history['messages'][-1]['tool_call_id']='unmatched'
            with self.assertRaises(IntegrityError):verify_and_send(policy,history,'primary',Wire())
            self.assertEqual(len(sent),2)
            if provider:
                history['messages'][-1]['tool_call_id']='c1'
                for invalid in [True,1,-1]:
                    history['messages'][-2]['tool_calls'][0]['index']=invalid
                    with self.assertRaises(IntegrityError):verify_and_send(policy,history,'primary',Wire())

    def test_unknown_options_and_stream_flags_cannot_change_profile(self):
        for provider in [False,True]:
            for change in [{'stream':1},{'fallbacks':[]},{'stream_options':{'include_usage':False}}]:
                base,_=self.fixture(provider);base['allowed_request_fields'].update(change)
                with self.assertRaises(IntegrityError):policy_from_dict(base,'synthetic-support','1')
