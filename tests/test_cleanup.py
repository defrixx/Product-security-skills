import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from support import cleanup

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.src=self.root/'input';self.src.mkdir()
    def write(self,name,value):
        p=self.src/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(value if isinstance(value,bytes) else value.encode());return p
    def run_clean(self,policy=None,mode='clean-copy',limits=None):
        return cleanup.run(self.src,self.root/'output',mode,policy,limits)
    def emitted(self,report,index=0):
        return (self.root/'output'/report['files'][index]['output']).read_text()
    def test_json_label_and_secret_same_file(self):
        secret='SYNTHETIC_SECRET_ONLY_01'
        self.write('settings.json',json.dumps({'labels':{'apiKey':'API key'},'credentials':{'apiKey':secret},'literal':'API key'}))
        policy={'suppressions':[{'file':'settings.json','pointer':'/labels/apiKey','expected_value':'API key','reason':'UI label'}]}
        report=self.run_clean(policy);out=json.loads(self.emitted(report))
        self.assertEqual(out['labels']['apiKey'],'API key');self.assertEqual(out['literal'],'API key')
        self.assertNotEqual(out['credentials']['apiKey'],secret)
        self.assertNotIn(secret,json.dumps(report));self.assertEqual(report['counts']['replacement_occurrences'],1)
    def test_changed_suppression_is_not_a_blanket_exemption(self):
        self.write('settings.json',json.dumps({'apiKey':'SYNTHETIC_NEW_SECRET'}))
        r=self.run_clean({'suppressions':[{'file':'settings.json','pointer':'/apiKey','expected_value':'API key','reason':'label'}]})
        self.assertEqual(r['files'][0]['reason'],'suppression_value_changed');self.assertEqual(r['counts']['emitted_files'],0)
    def test_broad_suppression_rejected(self):
        with self.assertRaises(cleanup.CleanupError):self.run_clean({'suppressions':[{'file':'*.json','pointer':'/token','expected_value':'x','reason':'bad'}]})
        self.assertFalse((self.root/'output').exists())
    def test_unused_suppression_is_reported(self):
        self.write('a.json','{}')
        r=self.run_clean({'suppressions':[{'file':'other.json','pointer':'/apiKey','expected_value':'API key','reason':'label'}]})
        self.assertIn('unused_suppression',r['issues'])
    def test_consistent_across_files_and_distinct_values(self):
        self.write('a.json',json.dumps({'token':'SYNTHETIC_ALPHA','email':'SYNTHETIC_ALPHA','password':'SYNTHETIC_BETA'}))
        self.write('b.txt','SYNTHETIC_ALPHA')
        r=self.run_clean({'sensitive_values':['SYNTHETIC_ALPHA']});obj=json.loads(self.emitted(r));text=self.emitted(r,1)
        self.assertEqual(obj['token'],obj['email']);self.assertEqual(obj['token'],text);self.assertNotEqual(obj['token'],obj['password'])
    def test_cross_file_identity_references_survive_replacement(self):
        ids = ['alice@synthetic.invalid', 'bob@synthetic.invalid']
        people = {'people': [{'email': value, 'label': 'Email address'} for value in ids]}
        edges = {'links': [{'from': ids[0], 'to': ids[1]}, {'from': ids[1], 'to': ids[0]}]}
        first = self.write('a.json', json.dumps(people))
        second = self.write('b.json', json.dumps(edges))
        originals = [first.read_bytes(), second.read_bytes()]
        report = self.run_clean()
        cleaned_people = json.loads(self.emitted(report, 0))['people']
        cleaned_edges = json.loads(self.emitted(report, 1))['links']
        new_ids = [person['email'] for person in cleaned_people]
        self.assertEqual(len(set(new_ids)), 2)
        self.assertEqual(cleaned_edges, [{'from': new_ids[0], 'to': new_ids[1]},
                                         {'from': new_ids[1], 'to': new_ids[0]}])
        self.assertTrue(all(person['label'] == 'Email address' for person in cleaned_people))
        for value in ids:
            self.assertNotIn(value, json.dumps(report))
            self.assertNotIn(value, self.emitted(report, 0) + self.emitted(report, 1))
        self.assertEqual([first.read_bytes(), second.read_bytes()], originals)
        # Unsafe control: parseable, independently replaced references lose their targets.
        broken = json.loads(json.dumps(cleaned_edges))
        broken[0]['to'] = 'UNRELATED_SYNTHETIC_ID'
        self.assertFalse(all(edge[k] in new_ids for edge in broken for k in ('from', 'to')))

    def test_original_bytes_names_and_permissions_preserved(self):
        p=self.write('hidden/.env','API_KEY=SYNTHETIC_SECRET\n');p.chmod(0o640)
        before=(p.read_bytes(),stat.S_IMODE(p.stat().st_mode));r=self.run_clean()
        self.assertEqual(before,(p.read_bytes(),stat.S_IMODE(p.stat().st_mode)));self.assertEqual(r['counts']['checked'],1)
        self.assertEqual(stat.S_IMODE((self.root/'output').stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE((self.root/'output/report.json').stat().st_mode),0o600)
    def test_hidden_env(self):
        self.write('.env','PASSWORD=SYNTHETIC_ONLY\n');r=self.run_clean();self.assertEqual(r['counts']['replacement_occurrences'],1)
    def test_scan_only_never_emits_copy(self):
        self.write('a.json','{"token":"SYNTHETIC_ONLY"}');r=self.run_clean(mode='scan-only')
        self.assertEqual(r['counts']['replacement_occurrences'],0);self.assertEqual(r['counts']['proposed_occurrences'],1)
        self.assertFalse((self.root/'output/files').exists())
    def test_symlink_file_and_directory_are_not_followed(self):
        outside=self.root/'outside';outside.mkdir();(outside/'secret.txt').write_text('password=SYNTHETIC_ONLY')
        (self.src/'link.txt').symlink_to(outside/'secret.txt');(self.src/'linked').symlink_to(outside,target_is_directory=True)
        r=self.run_clean();self.assertEqual(r['counts']['checked'],0);self.assertEqual(r['counts']['skipped'],2)
    def test_hardlink_is_skipped(self):
        p=self.root/'outside';p.write_text('password=SYNTHETIC_ONLY');os.link(p,self.src/'inside.txt')
        r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'hardlink');self.assertEqual(p.read_text(),'password=SYNTHETIC_ONLY')
    def test_fifo_does_not_block(self):
        os.mkfifo(self.src/'fifo.txt');r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'symlink_or_nonregular')
    def test_nested_output_rejected(self):
        with self.assertRaises(cleanup.CleanupError):cleanup.run(self.src,self.src/'nested','clean-copy')
        self.assertFalse((self.src/'nested').exists())
    def test_ancestor_and_same_output_rejected(self):
        for out in [self.src,self.root]:
            with self.subTest(out=out.name),self.assertRaises(cleanup.CleanupError):cleanup.run(self.src,out)
    def test_existing_output_not_overwritten(self):
        out=self.root/'output';out.mkdir();p=out/'keep';p.write_text('keep')
        with self.assertRaises(cleanup.CleanupError):self.run_clean()
        self.assertEqual(p.read_text(),'keep')
    def test_symlink_root_rejected(self):
        link=self.root/'alias';link.symlink_to(self.src,target_is_directory=True)
        with self.assertRaises(cleanup.CleanupError):cleanup.run(link,self.root/'output')
    def test_output_alias_nested_in_source_rejected(self):
        link=self.root/'alias';link.symlink_to(self.src,target_is_directory=True)
        with self.assertRaises(cleanup.CleanupError):cleanup.run(self.src,link/'nested')
    def test_malformed_formats_omitted(self):
        self.write('a.json','{"password":"SYNTHETIC_ONLY",');self.write('b.csv','a,b\n1\n');self.write('c.jsonl','{}\n{broken')
        r=self.run_clean();self.assertEqual(r['counts']['failed'],3);self.assertEqual(r['counts']['emitted_files'],0)
    def test_duplicate_json_key_omitted(self):
        self.write('a.json','{"token":"first","token":"second"}');r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'duplicate_json_key')
    def test_json_nonfinite_omitted(self):
        self.write('a.json','{"x":NaN}');r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'nonfinite_json_number')
    def test_nested_sensitive_field_cannot_bypass_detection(self):
        self.write('a.json',json.dumps({'api_key':['SYNTHETIC_ONLY']}))
        self.write('b.json',json.dumps({'password':{'value':'SYNTHETIC_ONLY'}}))
        r=self.run_clean();self.assertEqual(r['counts']['emitted_files'],0)
        self.assertTrue(all(f['reason']=='sensitive_nonstring_field' for f in r['files']))
    def test_numeric_sensitive_value_fails_instead_of_changing_type(self):
        self.write('a.json','{"phone":123456789}');r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'sensitive_nonstring_field')
    def test_utf8_bom_escaped_values_and_types(self):
        self.write('a.json',b'\xef\xbb\xbf{"password":"synth\\u0065tic","number":42,"flag":true}')
        r=self.run_clean();out=json.loads(self.emitted(r));self.assertNotEqual(out['password'],'synthetic');self.assertIs(out['flag'],True);self.assertEqual(out['number'],42)
    def test_jsonl_preserves_record_order(self):
        self.write('a.jsonl','{"token":"SYNTHETIC_A","n":1}\n{"token":"SYNTHETIC_B","n":2}\n')
        r=self.run_clean();self.assertEqual([json.loads(x)['n'] for x in self.emitted(r).splitlines()],[1,2])
    def test_csv_quotes_and_multiline_values(self):
        self.write('a.csv','name,token,note\nsynthetic,SYNTHETIC_ONLY,"two\nlines, quoted"\n')
        r=self.run_clean();out=list(cleanup.csv.reader(io.StringIO(self.emitted(r))));self.assertEqual(out[1][2],'two\nlines, quoted');self.assertNotIn('SYNTHETIC_ONLY',self.emitted(r))
    def test_pem_and_certificate_complete_blocks(self):
        self.write('a.txt','-----BEGIN PRIVATE KEY-----\nSYNTHETIC_NOT_A_KEY\n-----END PRIVATE KEY-----\n-----BEGIN CERTIFICATE-----\nSYNTHETIC_NOT_A_CERT\n-----END CERTIFICATE-----')
        r=self.run_clean();self.assertEqual(r['counts']['replacement_occurrences'],2);self.assertNotIn('SYNTHETIC_NOT',self.emitted(r))
    def test_incomplete_pem_omitted(self):
        self.write('a.txt','-----BEGIN PRIVATE KEY-----\nSYNTHETIC_ONLY')
        r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'incomplete_pem_block')
    def test_network_and_personal_detectors(self):
        self.write('a.txt','10.23.45.67 fd00::1234 service.synthetic.internal person@synthetic.invalid')
        r=self.run_clean();self.assertEqual(r['counts']['replacement_occurrences'],4)
    def test_network_policy_can_preserve_operational_constants(self):
        self.write('a.txt','127.0.0.1 host.docker.internal');r=self.run_clean({'redact_network':False});self.assertEqual(self.emitted(r),'127.0.0.1 host.docker.internal')
    def test_secret_paths_never_enter_report_or_output_names(self):
        sensitive='person@synthetic.invalid';self.write(sensitive+'.json','{"ok":1}')
        r=self.run_clean();self.assertNotIn(sensitive,json.dumps(r));self.assertNotIn(sensitive,' '.join(str(p) for p in (self.root/'output').rglob('*')))
    def test_unsupported_and_binary_omitted(self):
        self.write('a.zip',b'PK');self.write('b.txt',b'\x00SYNTHETIC_ONLY');self.write('c.txt',b'\xff')
        r=self.run_clean();self.assertEqual(r['counts']['emitted_files'],0);self.assertEqual(r['status'],'partial')
    def test_resource_limits(self):
        self.write('a.txt','123456');self.write('b.txt','123456');r=self.run_clean(limits={'max_total_bytes':8})
        self.assertEqual(r['counts']['checked'],1);self.assertEqual(r['files'][1]['reason'],'total_byte_limit')
    def test_file_size_limit(self):
        self.write('a.txt','12345');r=self.run_clean(limits={'max_file_bytes':4});self.assertEqual(r['files'][0]['reason'],'file_size_limit')
    def test_entry_limit_reports_incomplete_coverage(self):
        for i in range(4):self.write(str(i)+'.txt','x')
        r=self.run_clean(limits={'max_entries':2});self.assertIn('entry_limit',r['issues']);self.assertEqual(r['status'],'partial')
    def test_depth_and_record_limits(self):
        self.write('a.json','{"a":{"b":{"c":1}}}');r=self.run_clean(limits={'max_depth':1});self.assertEqual(r['files'][0]['reason'],'structure_depth_limit')
    def test_git_excluded_but_hidden_data_included(self):
        self.write('.git/config','SYNTHETIC_ONLY');self.write('.hidden.txt','password=SYNTHETIC_ONLY')
        r=self.run_clean();self.assertEqual(r['counts']['excluded_trees'],1);self.assertEqual(r['counts']['checked'],1)
    def test_custom_text_format_requires_opt_in(self):
        self.write('a.yaml','token: SYNTHETIC_ONLY');r=self.run_clean({'text_extensions':['.yaml']});self.assertEqual(r['counts']['checked'],1)
    def test_source_mutation_detected(self):
        p=self.write('a.txt','password=SYNTHETIC_ONE');real=cleanup.transform
        def change(*args,**kwargs):
            result=real(*args,**kwargs);p.write_text('password=SYNTHETIC_TWO');return result
        with patch.object(cleanup,'transform',change):r=self.run_clean()
        self.assertEqual(r['files'][0]['reason'],'source_changed');self.assertEqual(r['counts']['emitted_files'],0)
    def test_report_errors_do_not_leak_input(self):
        secret='SYNTHETIC_PRIVATE_IDENTIFIER';self.write(secret+'.json','{"token":"'+secret+'",')
        r=self.run_clean();self.assertNotIn(secret,json.dumps(r))
    def test_cli_partial_and_explicit_limits(self):
        self.write('a.txt','password=SYNTHETIC_ONLY');stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code=cleanup.main(['--source',str(self.src),'--output',str(self.root/'output'),'--mode','clean-copy','--max-file-bytes','1'])
        self.assertEqual(code,2);self.assertNotIn('SYNTHETIC_ONLY',stdout.getvalue())
        self.assertEqual(json.loads((self.root/'output/report.json').read_text())['limits']['max_file_bytes'],1)
    def test_cli_rejects_nonpositive_limits_before_creating_output(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code=cleanup.main(['--source',str(self.src),'--output',str(self.root/'output'),'--max-depth','0'])
        self.assertEqual(code,1);self.assertFalse((self.root/'output').exists())
    def test_cli_error_does_not_echo_path(self):
        stream=io.StringIO()
        with contextlib.redirect_stderr(stream):code=cleanup.main(['--source','SYNTHETIC_PRIVATE_PATH','--output',str(self.root/'output')])
        self.assertEqual(code,1);self.assertNotIn('SYNTHETIC_PRIVATE_PATH',stream.getvalue())
    def test_reserved_markers_cannot_collide(self):
        self.write('a.txt','REDACTED_CREDENTIAL_000001 password=SYNTHETIC_ONLY')
        r=self.run_clean();self.assertEqual(r['files'][0]['reason'],'reserved_marker_in_input')
    def test_deterministic_output_on_same_snapshot(self):
        self.write('a.json','{"token":"SYNTHETIC_A"}');r=self.run_clean()
        r2=cleanup.run(self.src,self.root/'again','clean-copy')
        self.assertEqual(r,r2);self.assertEqual(self.emitted(r),(self.root/'again'/r2['files'][0]['output']).read_text())
    def test_suppression_does_not_publish_its_reason_or_expected_value(self):
        value='SYNTHETIC_REVIEWED_LABEL';self.write('a.json',json.dumps({'token':value}))
        r=self.run_clean({'suppressions':[{'file':'a.json','pointer':'/token','expected_value':value,'reason':'PRIVATE_REASON'}]})
        self.assertNotIn(value,json.dumps(r));self.assertNotIn('PRIVATE_REASON',json.dumps(r))
    def test_known_corpus_detects_seeds_without_benign_replacements(self):
        # Ground truth only for this corpus: three positives, three benign controls.
        self.write('a.json',json.dumps({'labels':{'apiKey':'API key'},'settings':{'apiKey':'SYNTHETIC_KEY'},'text':'person@synthetic.invalid','password':'SYNTHETIC_PASS','documentation':'API key','answer':42}))
        r=self.run_clean({'suppressions':[{'file':'a.json','pointer':'/labels/apiKey','expected_value':'API key','reason':'label'}]})
        obj=json.loads(self.emitted(r));self.assertEqual(r['counts']['replacement_occurrences'],3)
        self.assertEqual((obj['labels']['apiKey'],obj['documentation'],obj['answer']),('API key','API key',42))


class AdditionalBoundaryTests(CleanupTests):
    # unittest inherits base cases; loader below intentionally uses only new cases.
    def test_finding_limit_omits_file(self):
        self.write('a.txt','password=SYNTHETIC_A\npassword=SYNTHETIC_B\n')
        r=self.run_clean(limits={'max_findings':1});self.assertEqual(r['files'][0]['reason'],'finding_limit');self.assertEqual(r['counts']['emitted_files'],0)
    def test_output_size_limit_omits_file_without_publishing_events(self):
        self.write('a.json','{"token":"SYNTHETIC_A"}')
        r=self.run_clean(limits={'max_output_bytes':1});self.assertEqual(r['files'][0]['reason'],'output_byte_limit');self.assertEqual(r['counts']['emitted_files'],0);self.assertNotIn('events',r['files'][0])
    def test_directory_depth_limit_reports_exclusion(self):
        self.write('one/two/a.txt','password=SYNTHETIC_A');r=self.run_clean(limits={'max_depth':1})
        self.assertEqual(r['counts']['checked'],0);self.assertEqual(r['excluded_trees'][0]['reason'],'directory_depth_limit')
    def test_record_limit_omits_file(self):
        self.write('a.json','[1,2,3]');r=self.run_clean(limits={'max_records':2});self.assertEqual(r['files'][0]['reason'],'record_limit')
    def test_overlapping_detectors_do_not_leave_suffix(self):
        self.write('a.txt','password=person@synthetic.invalid');r=self.run_clean();self.assertEqual(r['counts']['replacement_occurrences'],1);self.assertNotIn('synthetic.invalid',self.emitted(r))
    def test_dangling_output_symlink_rejected(self):
        (self.root/'output').symlink_to(self.root/'missing')
        with self.assertRaises(cleanup.CleanupError):self.run_clean()
    def test_file_becomes_symlink_between_inventory_and_open(self):
        p=self.write('a.txt','password=SYNTHETIC_A');outside=self.root/'outside';outside.write_text('DO_NOT_READ_SYNTHETIC')
        original=cleanup.read_regular
        def swap(fd,name,limit):
            p.unlink();p.symlink_to(outside);return original(fd,name,limit)
        with patch.object(cleanup,'read_regular',swap):r=self.run_clean()
        self.assertEqual(r['counts']['emitted_files'],0);self.assertNotIn('DO_NOT_READ_SYNTHETIC',json.dumps(r))
    def test_interrupted_write_keeps_running_marker_and_no_success_report(self):
        self.write('a.txt','password=SYNTHETIC_A');real=cleanup.private_write
        def fail(fd,name,content):
            if name!='RUNNING':raise OSError('SYNTHETIC_ERROR_VALUE')
            return real(fd,name,content)
        with patch.object(cleanup,'private_write',fail),self.assertRaises(OSError):self.run_clean()
        self.assertTrue((self.root/'output/RUNNING').exists());self.assertFalse((self.root/'output/report.json').exists())
    def test_invalid_arguments_never_echo_value(self):
        err=io.StringIO()
        with contextlib.redirect_stderr(err):code=cleanup.main(['--unknown','SYNTHETIC_PRIVATE_ARGUMENT'])
        self.assertEqual(code,1);self.assertNotIn('SYNTHETIC_PRIVATE_ARGUMENT',err.getvalue())

# Keep base and new cases once each rather than duplicating inherited tests.
def load_tests(loader, tests, pattern):
    suite=loader.loadTestsFromTestCase(CleanupTests)
    suite.addTests(AdditionalBoundaryTests(name) for name in AdditionalBoundaryTests.__dict__ if name.startswith('test_'))
    return suite

if __name__=='__main__': unittest.main()
