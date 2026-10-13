"""Misattributed, incomplete or embellished performance observations must fail admission."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('efficiency_check',ROOT/'scripts/verify-ps-efficiency.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
DATA=json.loads((ROOT/check.REPORT).read_text())

def test_current_observations_recompute_and_bind():
    assert check.validate(deepcopy(DATA))==DATA

@pytest.mark.parametrize('mutation', ['source','baseline','quantile','median','boolean_sample','duplicate','missing',
                                      'memory','rss','accuracy','startup','order'])
def test_unsupported_performance_evidence_refused(mutation):
    d=deepcopy(DATA); r=d['profiles'][0]
    if mutation=='source':d['sources']['services/evaluator/app.py']='0'*64
    elif mutation=='baseline':d['sources']['eval/methods/context-v6-eager.py']='0'*64
    elif mutation=='quantile':r['after']['p95_ms']+=1
    elif mutation=='median':r['paired_median_speedup']+=1
    elif mutation=='boolean_sample':r['after']['samples_ms'][0]=True
    elif mutation=='duplicate':d['profiles'][1]=deepcopy(r)
    elif mutation=='missing':d['profiles'].pop()
    elif mutation=='memory':r['after_peak_python_traced_bytes']=True
    elif mutation=='rss':r['peak_measurement_is_not_process_rss']=False
    elif mutation=='accuracy':d['independent_accuracy_evidence']=True
    elif mutation=='startup':d['scope']='Cold whole-pipeline performance'
    elif mutation=='order':d['alternating_execution_order']=False
    with pytest.raises(ValueError):check.validate(d)


@pytest.mark.parametrize('value', [None, True, 'nonsense', '2026-10-13T00:00:00',
                                 '2999-01-01T00:00:00+00:00', '2026-10-01T00:00:00+01:00'])
def test_bad_timestamp_refused(value):
    d=deepcopy(DATA);d['captured_at']=value
    with pytest.raises(ValueError):check.validate(d)

@pytest.mark.parametrize('field,value', [('system','iPhone'),('system',True),('machine','imaginary'),
    ('python','3.x'),('python',3.12),('logical_cpus',True),('logical_cpus',0),
    ('logical_cpus',4097),('logical_cpus',8.0),('logical_cpus',float('inf'))])
def test_bad_declared_host_refused(field,value):
    d=deepcopy(DATA);d['execution_host'][field]=value
    with pytest.raises(ValueError):check.validate(d)

@pytest.mark.parametrize('mutation', ['top_extra','top_missing','host_extra','host_missing','profile_extra',
                                      'profile_missing','network_float','repeat_float','host_not_object','profile_bad_type','length_bad_type'])
def test_schema_cannot_carry_extra_claims_or_missing_conditions(mutation):
    d=deepcopy(DATA)
    if mutation=='top_extra':d['certified']=True
    elif mutation=='top_missing':del d['captured_at']
    elif mutation=='host_extra':d['execution_host']['physical_phone']=True
    elif mutation=='host_missing':del d['execution_host']['python']
    elif mutation=='profile_extra':d['profiles'][0]['accuracy']=1.0
    elif mutation=='profile_missing':del d['profiles'][0]['candidate_outputs_equal']
    elif mutation=='network_float':d['network_requests']=0.0
    elif mutation=='repeat_float':d['repeats_per_profile']=21.0
    elif mutation=='host_not_object':d['execution_host']='Darwin'
    elif mutation=='profile_bad_type':d['profiles'][0]['profile']=[]
    elif mutation=='length_bad_type':d['profiles'][0]['input_codepoints']=[]
    with pytest.raises(ValueError):check.validate(d)
