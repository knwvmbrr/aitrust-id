"""Exact published source cohort/build/refusal controls; no MT accuracy labels."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
ROOT=Path(__file__).resolve().parents[1]
COHORT=ROOT/'integrations/mt-choice-reference/1.3.0'
spec=importlib.util.spec_from_file_location('choice_device_builder',ROOT/'scripts/build-mt-choice-device.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def test_exact_retained_source_notice_cohort_and_no_legacy_changes():
    manifest=json.loads((COHORT/'source.json').read_bytes())
    assert manifest['source_commit']==b.SOURCE_COMMIT
    for name,expected in b.APPROVED_SOURCE.items():
        raw=(COHORT/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==expected==manifest['source_files'][name]['sha256']
    # Main keeps1.2; native/browser practice owns its exact separately pinned1.3.
    main=(ROOT/'tools/choice_framing.py').read_bytes()
    assert b'caller-bound-choice-framing-observation/1.2.0' in main
    assert b'caller-bound-choice-framing-observation/1.2.0' in (ROOT/'tools/mt_workflow.py').read_bytes()


def test_actual_native_canonical_cohort_complete_records_and_unicode_binding():
    rows=json.loads(subprocess.check_output([sys.executable,'-I','-S','-B',str(ROOT/'scripts/mt-choice-device-cases.py')],timeout=10))
    assert len(rows)==11
    for row in rows:
        value=row['expected'];assert value['method']=='caller-bound-choice-framing-observation/1.3.0'
        assert value['source_sha256']=={p:b.APPROVED_SOURCE[p]for p in b.METHOD_FILES}
        assert not value['intent_established']and not value['truth_established']and value['tags']==[]
        assert value['request_sha256']==b.sha(row['wire'].encode())
    additive=next(x for x in rows if x['id']=='additive')['expected']
    assert additive['counts']['additive_frames']==1 and additive['counts']['other_paired_frames']==0
    assert additive['original']['observations'][0]['proposed_signal']is None
    nfc=next(x for x in rows if x['id']=='unicode_NFC')['expected']
    assert nfc['raw_subject_sha256']!=nfc['subject_sha256']


@pytest.mark.parametrize('kind',['symlink','fifo','hardlink','oversized'])
def test_source_capture_refuses_before_reading_unsafe_member(tmp_path,kind):
    root=tmp_path.resolve();p=root/'source';p.write_bytes(b'public')
    if kind=='symlink':
        (root/'target').write_bytes(b'PRIVATE_CANARY');p.unlink();p.symlink_to(root/'target')
    elif kind=='fifo':p.unlink();os.mkfifo(p)
    elif kind=='hardlink':(root/'other').hardlink_to(p)
    else:p.write_bytes(b'x'*11)
    with b.Capture(root)as capture:
        with pytest.raises((ValueError,OSError)):capture.read('source',10 if kind=='oversized'else 100)


def test_source_capture_detects_file_and_parent_replacement(tmp_path):
    root=tmp_path.resolve();(root/'sub').mkdir();(root/'sub/x').write_bytes(b'public')
    with b.Capture(root)as capture:
        capture.read('sub/x');(root/'sub').rename(root/'old');(root/'sub').mkdir()
        with pytest.raises(ValueError):capture.check()


def files():
    return {'manifest.json':b'{}','mt-choice-worker.mjs':b'public','project-notices.txt':b'notices','method-'+('a'*64)+'.json':b'{}'}


def test_fixed_publication_idempotence_and_source_refusal_preserve_prior_outputs(tmp_path):
    root=tmp_path.resolve();out=root/'device';b.publish(out,files(),lambda:None)
    before={p.name:p.read_bytes()for p in out.iterdir()}
    def changed():raise b.BuildError('source drift')
    with pytest.raises(b.BuildError):b.publish(out,files(),changed)
    assert before=={p.name:p.read_bytes()for p in out.iterdir()}
    b.publish(out,files(),lambda:None);assert before=={p.name:p.read_bytes()for p in out.iterdir()}


def test_changed_source_after_staging_keeps_existing_final_bytes(tmp_path):
    root=tmp_path.resolve();out=root/'device';b.publish(out,files(),lambda:None)
    before={p.name:p.read_bytes()for p in out.iterdir()};calls=0
    def stable():
        nonlocal calls
        calls+=1
        if calls==2:raise b.BuildError('source drift')
    with pytest.raises(b.BuildError):b.publish(out,{**files(),'manifest.json':b'{"new":true}'},stable)
    assert before=={p.name:p.read_bytes()for p in out.iterdir()}


def test_static_output_symlink_and_unexpected_member_refused(tmp_path):
    root=tmp_path.resolve();out=root/'device';out.mkdir();target=root/'other';target.write_bytes(b'keep')
    (out/'manifest.json').symlink_to(target)
    with pytest.raises(b.BuildError):b.publish(out,files(),lambda:None)
    assert target.read_bytes()==b'keep'
    (out/'manifest.json').unlink();(out/'unexpected').write_bytes(b'keep')
    with pytest.raises(b.BuildError):b.publish(out,files(),lambda:None)
    assert(out/'unexpected').read_bytes()==b'keep'


def test_close_after_release_never_retries_same_numeric_descriptor(tmp_path):
    root=tmp_path.resolve();out=root/'device';real=os.close;opened=[];seen=[]
    def close(fd):
        info=os.fstat(fd)
        if __import__('stat').S_ISREG(info.st_mode)and not seen:
            seen.append(fd);real(fd);opened.append(os.open(root,os.O_RDONLY));raise OSError('PRIVATE_EXCEPTION')
        real(fd)
    try:
        with patch.object(b.os,'close',side_effect=close):
            with pytest.raises(b.BuildError):b.publish(out,files(),lambda:None)
        assert len(seen)==1 and opened;os.fstat(opened[0])
    finally:
        for fd in opened:real(fd)


def build_fixture(tmp_path):
    """Inert tiny runtime bytes exercise real descriptors, not WASM execution."""
    root=tmp_path/'source';root.mkdir();runtime=tmp_path/'runtime';runtime.mkdir()
    names=[b.COHORT+'/'+n for n in b.APPROVED_SOURCE]+[b.COHORT+'/source.json',*b.BUILD_FILES]
    for name in names:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    pins={}
    for name in b.RUNTIME_FILES:
        raw=('inert-fixture-'+name).encode();(runtime/name).write_bytes(raw)
        pins[name]={'bytes':len(raw),'sha256':b.sha(raw)}
    policy={'pyodide_version':'314.0.7','python_version':'3.14.2','runtime_members':pins}
    path=root/b.RUNTIME_POLICY;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(policy))
    return root,runtime,b.sha(path.read_bytes())


@pytest.mark.parametrize('target',['source','runtime'])
def test_outer_capture_close_after_full_publication_is_explicitly_uncertain(tmp_path,target):
    root,runtime,pin=build_fixture(tmp_path);destination=tmp_path/'output';real=b.Capture.close;seen=[]
    selected=root if target=='source'else runtime
    def close(capture):
        info=os.fstat(capture.root);matches=(info.st_dev,info.st_ino)==(selected.stat().st_dev,selected.stat().st_ino)
        real(capture)
        if matches and not seen:seen.append(True);raise b.BuildError('PRIVATE_CLOSE_ERROR')
    with patch.object(b,'RUNTIME_POLICY_SHA',pin),patch.object(b.Capture,'close',close):
        with pytest.raises(b.BuildUncertain):b.build(runtime,destination,root)
    assert len(seen)==1 and len(list(destination.iterdir()))==4
    assert not list(destination.glob('.choice-*'))


def test_checksum_refusal_precedes_publication_and_preserves_existing_outputs(tmp_path):
    root,runtime,pin=build_fixture(tmp_path);destination=tmp_path/'output';b.publish(destination,files(),lambda:None)
    before={p.name:p.read_bytes()for p in destination.iterdir()}
    (runtime/b.RUNTIME_FILES[0]).write_bytes(b'changed')
    with patch.object(b,'RUNTIME_POLICY_SHA',pin):
        with pytest.raises(b.BuildError)as error:b.build(runtime,destination,root)
    assert not isinstance(error.value,b.BuildUncertain)
    assert before=={p.name:p.read_bytes()for p in destination.iterdir()}
