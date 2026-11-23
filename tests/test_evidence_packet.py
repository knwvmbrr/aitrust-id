"""The downloadable evidence index must expose failures without granting release."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import evidence_packet as module


def fixture(tmp_path):
    state = {'current_engineering_revalidation': {c: 'runs/'+c+'.json' for c in module.CAPABILITIES}}
    ledger = {'records': [{'id': 'F-'+str(i), 'percent_complete': 100 if i else 80,
                          'required_acceptance': [] if i else ['Independent human review.']}
                         for i in range(202)]}
    for name in module.BASE:
        path = tmp_path/name;path.parent.mkdir(parents=True, exist_ok=True)
        value = state if name == 'state.json' else ledger if name in ('docs/scope-progress.json', 'docs/master-scope.json') else {}
        path.write_text(json.dumps(value))
    for c in module.CAPABILITIES:
        path=tmp_path/('runs/'+c+'.json');path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'captured_at':'2026-10-10T10:00:00Z', 'fingerprint': {'sources': {}}}))
    return state


def controls(monkeypatch, fail=None):
    monkeypatch.setattr(module, 'assess', lambda receipt, c, root: {
        'pass': c != fail, 'failures': [] if c != fail else ['source_dependency_fixture_or_check_changed'],
        'release_approved': False, 'independent_accuracy_evidence': False})
    monkeypatch.setattr(module, 'fingerprint', lambda c, root: {'sources': {}})


def test_current_packet_keeps_human_gate_open(tmp_path, monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    result=module.build(tmp_path)
    assert result['packet_valid'] and result['engineering_checks_current']
    assert len(result['receipts'])==5 and len(result['open_records'])==1
    assert result['open_records'][0]['required_acceptance']==['Independent human review.']
    assert result['records_preserved']==202
    assert all(result[k] is False for k in ('release_assessed','release_approved',
        'independent_accuracy_evidence','certification'))


@pytest.mark.parametrize('failure',['stale','missing','malformed'])
def test_failed_or_missing_receipt_does_not_disappear(tmp_path, monkeypatch, failure):
    fixture(tmp_path);controls(monkeypatch,'PS' if failure=='stale' else None)
    path=tmp_path/'runs/PS.json'
    if failure=='missing':path.unlink()
    if failure=='malformed':path.write_text('{"private-canary":')
    result=module.build(tmp_path)
    assert result['packet_valid'] and result['engineering_checks_current'] is False
    assert len(result['receipts'])==5
    assert next(c for c in result['receipts'] if c['capability']=='PS')['pass'] is False
    assert 'private-canary' not in json.dumps(result)


@pytest.mark.parametrize('name',['../private.json','runs/../state.json','/tmp/private.json','runs/x.json?token=x'])
def test_unsafe_selected_reference_refused(tmp_path,monkeypatch,name):
    state=fixture(tmp_path);controls(monkeypatch)
    state['current_engineering_revalidation']['PS']=name
    (tmp_path/'state.json').write_text(json.dumps(state))
    with pytest.raises(ValueError, match='public execution receipts'):
        module.build(tmp_path)


def test_mid_inspection_source_change_refuses_packet(tmp_path,monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    original=module.assess
    def change(receipt,c,root):
        (tmp_path/'state.json').write_text('{}')
        return original(receipt,c,root)
    monkeypatch.setattr(module,'assess',change)
    result=module.build(tmp_path)
    assert result['packet_valid'] is False and result['engineering_checks_current'] is False


def test_actual_current_repository_packet_and_cli():
    result=module.build()
    assert result['packet_valid'] and result['records_preserved']==202
    assert len(result['receipts'])==5 and len(result['files'])>100
    cli=subprocess.run([sys.executable,str(ROOT/'scripts/build-evidence-packet.py'),'--require-current'],
                       capture_output=True,timeout=65)
    value=json.loads(cli.stdout)
    assert not cli.stderr
    assert cli.returncode==(0 if value['engineering_checks_current'] else 1)
    assert value['release_approved'] is False


def test_source_edit_after_assessment_cannot_become_the_accepted_snapshot(tmp_path,monkeypatch):
    import hashlib
    fixture(tmp_path);controls(monkeypatch)
    source=tmp_path/'selected.py';source.write_bytes(b'old')
    snapshot={'sources':{'selected.py':hashlib.sha256(b'old').hexdigest()}}
    for c in module.CAPABILITIES:
        p=tmp_path/('runs/'+c+'.json');v=json.loads(p.read_text());v['fingerprint']=snapshot;p.write_text(json.dumps(v))
    monkeypatch.setattr(module,'fingerprint',lambda c,root:snapshot)
    original=module.assess
    def edit_after_assessment(receipt,c,root):
        result=original(receipt,c,root)
        source.write_bytes(b'new')
        return result
    monkeypatch.setattr(module,'assess',edit_after_assessment)
    result=module.build(tmp_path)
    assert result['packet_valid'] is False
    assert result['engineering_checks_current'] is False


def test_new_matching_source_after_assessment_invalidates_snapshot(tmp_path,monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    calls=0
    def changing_fingerprint(c,root):
        nonlocal calls
        calls+=1
        return {'sources':{}} if calls<=len(module.CAPABILITIES) else {'sources':{'new-source.py':'a'*64}}
    monkeypatch.setattr(module,'fingerprint',changing_fingerprint)
    result=module.build(tmp_path)
    assert result['packet_valid'] is False and result['engineering_checks_current'] is False


def source_fixture(tmp_path, monkeypatch, raw=b''):
    import hashlib
    fixture(tmp_path); controls(monkeypatch)
    source=tmp_path/'shared.py';source.write_bytes(raw)
    snapshot={'sources':{'shared.py':hashlib.sha256(raw).hexdigest()}}
    for c in module.CAPABILITIES:
        p=tmp_path/('runs/'+c+'.json');v=json.loads(p.read_text());v['fingerprint']=snapshot;p.write_text(json.dumps(v))
    monkeypatch.setattr(module,'fingerprint',lambda c,root:snapshot)
    return source,snapshot


def test_declared_empty_source_is_valid_and_captured_twice(tmp_path,monkeypatch):
    source_fixture(tmp_path,monkeypatch)
    original=module.empty_source;reads=[]
    def tracked(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(module,'empty_source',tracked)
    result=module.build(tmp_path)
    assert result['packet_valid'] and result['engineering_checks_current']
    assert result['files']['shared.py']==module.EMPTY_SHA256
    assert reads==[tmp_path/'shared.py',tmp_path/'shared.py']
    # Empty JSON still goes through the strict original evidence reader.
    (tmp_path/'runs/PS.json').write_bytes(b'')
    result=module.build(tmp_path)
    assert not result['engineering_checks_current']
    assert next(r for r in result['receipts']if r['capability']=='PS')['pass'] is False


@pytest.mark.parametrize('kind',['missing','nonempty','symlink','hardlink','fifo'])
def test_empty_source_type_substitutions_refused(tmp_path,kind):
    import os
    source=tmp_path/'source';target=tmp_path/'target';target.write_bytes(b'')
    if kind=='nonempty':source.write_bytes(b'x')
    elif kind=='symlink':source.symlink_to(target)
    elif kind=='hardlink':os.link(target,source)
    elif kind=='fifo':os.mkfifo(source)
    with pytest.raises(ValueError):module.empty_source(source)


def test_shared_capture_reuse_keeps_all_fingerprints_and_final_read(tmp_path,monkeypatch):
    source,snapshot=source_fixture(tmp_path,monkeypatch,b'shared source')
    original=module.read_file;reads=[];fingerprints=[]
    def tracked(path,limit):
        if path==source:reads.append(path)
        return original(path,limit)
    def current(c,root):fingerprints.append(c);return snapshot
    def assessment(receipt,c,root):
        current(c,root)
        return {'pass':True,'release_approved':False,'independent_accuracy_evidence':False}
    monkeypatch.setattr(module,'read_file',tracked)
    monkeypatch.setattr(module,'fingerprint',current)
    monkeypatch.setattr(module,'assess',assessment)
    result=module.build(tmp_path)
    assert result['engineering_checks_current'] and reads==[source,source]
    assert len(fingerprints)==15
    assert all(fingerprints.count(c)==3 for c in module.CAPABILITIES)


def test_conflicting_per_capability_digest_is_persistent_drift(tmp_path,monkeypatch):
    source,snapshot=source_fixture(tmp_path,monkeypatch,b'original')
    def current(c,root):
        return snapshot if c!=sorted(module.CAPABILITIES)[1] else {'sources':{'shared.py':'a'*64}}
    monkeypatch.setattr(module,'fingerprint',current)
    result=module.build(tmp_path)
    assert not result['packet_valid'] and not result['engineering_checks_current']


def test_source_mutation_after_capture_is_not_hidden_by_reuse(tmp_path,monkeypatch):
    source,snapshot=source_fixture(tmp_path,monkeypatch,b'old')
    calls=0
    def assessment(receipt,c,root):
        nonlocal calls
        calls+=1
        if calls==2:source.write_bytes(b'new')
        return {'pass':True,'release_approved':False,'independent_accuracy_evidence':False}
    monkeypatch.setattr(module,'assess',assessment)
    result=module.build(tmp_path)
    assert not result['packet_valid'] and not result['engineering_checks_current']


@pytest.mark.parametrize('bound',['deadline','inputs','bytes'])
def test_exhausted_operation_bound_escapes_stale_row_fallback(tmp_path,monkeypatch,bound):
    source_fixture(tmp_path,monkeypatch,b'example')
    if bound=='deadline':
        ticks=iter([0,0,0,0,0,1000])
        monkeypatch.setattr(module,'monotonic',lambda:next(ticks,1000))
    elif bound=='inputs':monkeypatch.setattr(module,'MAX_INPUTS',len(module.BASE))
    else:monkeypatch.setattr(module,'MAX_CAPTURED_BYTES',1)
    with pytest.raises(module.InspectionBoundError):module.build(tmp_path)


def test_empty_source_close_failure_attempts_all_owned_closes_once(tmp_path,monkeypatch):
    import os
    source=tmp_path/'source';source.write_bytes(b'')
    original=module.os.close;closed=[]
    def close(fd):
        original(fd);closed.append(fd)
        if len(closed)==1:raise OSError('after real close')
    with monkeypatch.context()as local:
        local.setattr(module.os,'close',close)
        with pytest.raises(ValueError,match='close unavailable'):module.empty_source(source)
    assert len(closed)==len(source.absolute().parts)
    assert len(set(closed))==len(closed)


def test_base_read_deadline_refuses_before_next_read(tmp_path,monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    now=[0];reads=[];original=module.read_file
    def read(path,limit):
        raw=original(path,limit);reads.append(path);now[0]=61
        return raw
    monkeypatch.setattr(module,'read_file',read)
    monkeypatch.setattr(module,'monotonic',lambda:now[0])
    with pytest.raises(module.InspectionBoundError):module.build(tmp_path)
    assert reads==[tmp_path/module.BASE[0]]


@pytest.mark.parametrize('name,occurrence',[
    ('state.json',2),('docs/scope-progress.json',2),
    ('runs/PII_REDACTED.json',1),('docs/master-scope.json',2)])
def test_json_read_deadline_refuses_before_next_read(tmp_path,monkeypatch,name,occurrence):
    fixture(tmp_path);controls(monkeypatch)
    now=[0];reads=[];original=module.read_file
    def read(path,limit):
        raw=original(path,limit);reads.append(path)
        if reads.count(tmp_path/name)==occurrence:now[0]=61
        return raw
    monkeypatch.setattr(module,'read_file',read)
    monkeypatch.setattr(module,'monotonic',lambda:now[0])
    with pytest.raises(module.InspectionBoundError):module.build(tmp_path)
    assert reads[-1]==tmp_path/name
    assert reads.count(tmp_path/name)==occurrence
