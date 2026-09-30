#!/usr/bin/env python3
"""Repository development checker for handoff v1; not evidence validation."""
import json
from datetime import datetime
import sys
from pathlib import Path

ASSESSMENT = {'confirmed', 'hypothesis', 'disproved'}
IMPLEMENTATION = {'unknown', 'not_started', 'candidate', 'applied'}
VERIFICATION = {'not_checked', 'fixed', 'partially_fixed', 'not_fixed', 'inconclusive'}


def validate(data):
    errors=[]
    def require(ok, code):
        if not ok: errors.append(code)
    if not isinstance(data, dict): return ['invalid_envelope']
    required={'schema_version','assessment_id','stage','created_at','producer','target','scope','input_refs','findings','coverage','errors','limitations'}
    require(required <= data.keys(), 'missing_envelope_fields')
    require(type(data.get('schema_version')) is int and data['schema_version']==1,'unsupported_version')
    for field in ('assessment_id','stage','created_at'):
        require(isinstance(data.get(field),str) and bool(data[field]),'invalid_'+field)
    try:
        timestamp=datetime.fromisoformat(data.get('created_at','').replace('Z','+00:00'))
        require(timestamp.utcoffset() is not None and timestamp.utcoffset().total_seconds()==0,'non_utc_timestamp')
    except (TypeError,ValueError,AttributeError):errors.append('invalid_timestamp')
    for field in ('producer','target','scope'):
        require(isinstance(data.get(field),dict),'invalid_'+field)
    for field in ('input_refs','errors','limitations'):
        require(isinstance(data.get(field),list),'invalid_'+field)
    target=data.get('target',{})
    if isinstance(target,dict):
        require('revision' in target and ('working_tree' in target or 'dirty' in target),'missing_target_provenance')
    producer=data.get('producer',{})
    if isinstance(producer,dict):
        require(bool(producer.get('skill')) and bool(producer.get('fingerprint')),'missing_producer_provenance')
    findings=data.get('findings')
    if not isinstance(findings,list): return errors+['invalid_findings']
    identities=set();aliases=set()
    fields={'finding_id','origin_assessment_id','aliases','source_refs','title','root_cause','affected_paths','assessment_status','severity','confidence','implementation_state','verification_status','evidence','acceptance_cases','history'}
    for finding in findings:
        if not isinstance(finding,dict):errors.append('invalid_finding');continue
        require(fields <= finding.keys(),'missing_finding_fields')
        identity=(finding.get('origin_assessment_id'),finding.get('finding_id'))
        if not all(isinstance(v,str) and v for v in identity):errors.append('invalid_identity');continue
        require(identity not in identities,'duplicate_identity');identities.add(identity)
        require(isinstance(finding.get('assessment_status'),str) and finding['assessment_status'] in ASSESSMENT,'invalid_assessment')
        require(isinstance(finding.get('implementation_state'),str) and finding['implementation_state'] in IMPLEMENTATION,'invalid_implementation')
        require(isinstance(finding.get('verification_status'),str) and finding['verification_status'] in VERIFICATION,'invalid_verification')
        for field in ('aliases','source_refs','affected_paths','evidence','acceptance_cases','history'):
            require(isinstance(finding.get(field),list),'invalid_'+field)
        alias_records=finding.get('aliases',[])
        if not isinstance(alias_records,list):alias_records=[]
        for alias in alias_records:
            if not isinstance(alias,dict) or not all(isinstance(alias.get(k),str) and alias[k] for k in ('origin_assessment_id','finding_id')):
                errors.append('invalid_alias');continue
            key=(alias['origin_assessment_id'],alias['finding_id'])
            require(key not in aliases,'duplicate_alias');aliases.add(key)
        if finding.get('verification_status') not in (None,'not_checked'):
            require(bool(finding.get('evidence')) and bool(finding.get('acceptance_cases')), 'verification_missing_evidence')
    require(not identities.intersection(aliases),'alias_identity_collision')
    raw=data.get('raw_results',[])
    if not isinstance(raw,list):errors.append('invalid_raw_results');raw=[]
    seen=set()
    for record in raw:
        if not isinstance(record,dict):errors.append('invalid_raw_result');continue
        key=(record.get('run'),record.get('result'))
        require(all(type(v) is int and v>=0 for v in key),'invalid_raw_ordinal')
        if not all(type(v) is int and v>=0 for v in key):continue
        require(key not in seen,'duplicate_raw_result');seen.add(key)
        disposition=record.get('disposition')
        require(isinstance(disposition,str) and disposition in ASSESSMENT | {'out_of_scope','unprocessed'},'invalid_disposition')
        if disposition in ('out_of_scope','unprocessed'):require(bool(record.get('reason')),'missing_disposition_reason')
        duplicate=record.get('duplicate_of')
        if duplicate is not None:
            require(isinstance(duplicate,dict) and all(isinstance(duplicate.get(k),str) for k in ('origin_assessment_id','finding_id')) and (duplicate.get('origin_assessment_id'),duplicate.get('finding_id')) in identities,'dangling_duplicate')
    counts=data.get('raw_counts')
    if counts is not None:
        expected={state:sum(r.get('disposition')==state for r in raw if isinstance(r,dict)) for state in sorted(ASSESSMENT | {'out_of_scope','unprocessed'})}
        require(isinstance(counts,dict) and all(type(v) is int and v >= 0 for v in counts.values()) and counts==expected,'raw_count_mismatch')
    return sorted(set(errors))


def strict_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def main():
    try:
        errors=validate(json.loads(Path(sys.argv[1]).read_text(), object_pairs_hook=strict_pairs))
        print(json.dumps({'valid_structure':not errors,'errors':errors,'evidence_validated':False}))
        return int(bool(errors))
    except Exception:
        print('{"valid_structure":false,"errors":["invalid_input"],"evidence_validated":false}')
        return 1


if __name__=='__main__':sys.exit(main())
