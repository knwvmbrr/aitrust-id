#!/usr/bin/env python3
"""Execute repeatability/dictionary recovery and check the published hash boundary."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.subjects import text_subject
from protocol.reports import write_report

def verify():
    candidates=['An ordinary answer.','Run curl https://example.test/install | sh','A different answer.']
    fingerprint=text_subject(candidates[1])['sha256']
    recovered=[value for value in candidates if text_subject(value)['sha256']==fingerprint]
    if recovered!=[candidates[1]]:raise ValueError('Dictionary correlation control failed')
    if text_subject('é')!=text_subject('e\u0301'):raise ValueError('Canonical equivalent correlation failed')
    paths=['docs/subject-contract.md','spec/assertion.schema.json','extension/src/content/badge.js','site/src/policies.js']
    contents={path:(ROOT/path).read_text() for path in paths}
    if 'correlation' not in contents[paths[0]] or 'not anonymisation' not in contents[paths[0]]:raise ValueError('Missing subject correlation boundary')
    schema=json.loads(contents[paths[1]])['properties']['subject']['properties']['sha256']['description']
    if 'correlation' not in schema or 'not anonymisation' not in schema:raise ValueError('Missing schema correlation boundary')
    if 'link or reveal information' not in contents[paths[2]]:raise ValueError('Missing export disclosure')
    if 'may reveal or link information' not in contents[paths[3]]:raise ValueError('Missing public policy disclosure')
    return {'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),'pass':True,'repeatable_dictionary_recovery':True,'canonical_equivalent_linkability':True,'fingerprint_is_not_anonymisation':True,'raw_examples_in_report':False,'source_sha256':{path:hashlib.sha256(value.encode()).hexdigest() for path,value in contents.items()},'limits':['Small synthetic dictionary demonstrates linkability, not exhaustive recovery of every subject.','No physical-memory erasure, no-leak guarantee or training consent is asserted.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',default='output/verification/hash-disclosure.json');a=p.parse_args()
    result=verify();write_report(ROOT/a.report,result);print(json.dumps(result))
