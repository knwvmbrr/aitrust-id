"""Actual retained cohort and synthetic archive/refusal controls; no model imports."""
import copy
import io
import json
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import zipfile

import pytest

from tools import nli_license_cohort as cohort

ROOT = Path(__file__).resolve().parents[1]


def synthetic(members=None, *, mode=None, compression=zipfile.ZIP_STORED):
    out = io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        for name, raw in (members or [('example.py',b'# synthetic source\n'),('LICENSE',b'Synthetic notice only\n')]):
            item = zipfile.ZipInfo(name);item.compress_type = compression
            if mode is not None:item.external_attr = mode << 16
            archive.writestr(item,raw)
    return out.getvalue()


def clone(tmp_path):
    root = (tmp_path/'source').resolve();root.mkdir(mode=0o700)
    value = cohort.document((ROOT/cohort.MANIFEST).read_bytes())
    paths = set(value['sources'])|{cohort.MANIFEST,cohort.BUNDLE}
    paths |= {row['path'] for row in value['upstream']}
    paths |= {item['path'] for row in value['wheels'] for item in row['notices']}
    paths |= {row['notice_file'] for row in cohort.document((ROOT/'research/nli/notices.json').read_bytes())['notices']}
    for name in paths:
        target = root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    return root,value


def write_manifest(root,value):
    value = copy.deepcopy(value)
    value['observation_sha256'] = cohort.sha(cohort.encoded({k:v for k,v in value.items() if k!='observation_sha256'}))
    (root/cohort.MANIFEST).write_text(json.dumps(value))


def test_actual_retained_cohort_and_precise_nonclearance():
    row = cohort.verify()
    assert row['pass'] is True and row['wheel_occurrences']==44 and row['packages_per_platform']==22
    assert row['source_form_package_occurrences']==28 and row['blocked_native_package_occurrences']==16
    assert row['archive_bytes_replayed'] is False
    assert row['distribution_ready'] is False and row['permission_cleared'] is False
    assert row['model_license_evidence']=='pinned_publisher_declared_apache2'
    assert row['exact_training_base_revision_established'] is False
    value = cohort.document((ROOT/cohort.MANIFEST).read_bytes())
    assert value['model']['publisher_declared_repository_license_evidence'] is True
    assert value['model']['license_file_present_in_model_or_base_tree'] is False
    for row in value['wheels']:
        if row['name']=='onnxruntime':
            assert {r['member'] for r in row['notices']}=={'onnxruntime/LICENSE','onnxruntime/ThirdPartyNotices.txt'}
        if row['name'] in {'tokenizers','flatbuffers'}:assert row['notices']==[]
    assert b'Intel Simplified Software License' in (ROOT/cohort.BUNDLE).read_bytes()


@pytest.mark.parametrize('change', ['permission','distribution','native-coverage','accuracy','missing-wheel','extra-wheel',
                                  'wrong-platform','artifact','source-offer','native-resolved','model-license',
                                  'model-correspondence','upstream-url','upstream-hash','failed-source-promotion','observation-digest'])
def test_corrupt_or_promoted_record_refused_even_with_recomputed_self_digest(tmp_path,change):
    root,value = clone(tmp_path)
    if change=='permission':value['permission_cleared']=True
    elif change=='distribution':value['distribution_ready']=True
    elif change=='native-coverage':value['complete_native_source_coverage']=True
    elif change=='accuracy':value['independent_accuracy_evidence']=True
    elif change=='missing-wheel':value['wheels'].pop()
    elif change=='extra-wheel':value['wheels'].append(value['wheels'][0])
    elif change=='wrong-platform':value['wheels'][0]['platform']='windows'
    elif change=='artifact':value['wheels'][0]['sha256']='0'*64
    elif change=='source-offer':value['obligations'][0]['source_offer']='No obligations remain'
    elif change=='native-resolved':
        next(r for r in value['obligations'] if r['name']=='ml_dtypes')['native_obligations_resolved']=True
    elif change=='model-license':value['model']['card_license_declaration']='MIT'
    elif change=='model-correspondence':value['model']['exact_pretraining_base_revision_established']=True
    elif change=='upstream-url':value['upstream'][0]['url']='https://example.invalid/main'
    elif change=='upstream-hash':value['upstream'][0]['sha256']='0'*64
    elif change=='failed-source-promotion':value['source_retrieval_failures'][0]['http_status']=200
    else:
        value['observation_sha256']='0'*64;(root/cohort.MANIFEST).write_text(json.dumps(value))
    if change!='observation-digest':write_manifest(root,value)
    with pytest.raises((ValueError,KeyError)):cohort.verify(root)


@pytest.mark.parametrize('change',['notice','source','missing','symlink','extra-file','bundle','lock'])
def test_actual_file_identity_and_inventory_refusals(tmp_path,change):
    root,value = clone(tmp_path)
    notice = root/next(item['path'] for row in value['wheels'] if row['name']=='onnxruntime' for item in row['notices'])
    if change=='notice':notice.write_bytes(notice.read_bytes()+b'changed')
    elif change=='source':(root/value['upstream'][0]['path']).write_bytes(b'changed')
    elif change=='missing':notice.unlink()
    elif change=='symlink':
        raw=notice.read_bytes();notice.unlink();other=root/'other';other.write_bytes(raw);notice.symlink_to(other)
    elif change=='extra-file':(root/cohort.STORE/'unregistered.txt').write_bytes(b'PRIVATE')
    elif change=='bundle':(root/cohort.BUNDLE).write_bytes(b'changed')
    else:(root/'research/nli/requirements-mac.lock').write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):cohort.verify(root)


def test_real_archive_parser_recognizes_source_native_and_root_notices_without_imports():
    raw = synthetic([('package.py',b'raise RuntimeError("MUST NOT EXECUTE")\n'),
                     ('package/ThirdPartyNotices.txt',b'Original synthetic notice\n'),
                     ('package/native.so',b'\x7fELF'+b'not executable')])
    row,notices = cohort.wheel(raw,cohort.sha(raw))
    assert row['python_source_count']==1 and row['member_count']==3
    assert row['native_members'][0]['member']=='package/native.so'
    assert notices=={'package/ThirdPartyNotices.txt':b'Original synthetic notice\n'}


@pytest.mark.parametrize('kind',['traversal','absolute','backslash','symlink','fifo','bad-utf8','encrypted-kind','oversized','crc','hash'])
def test_malformed_wheels_refused(kind):
    raw=synthetic()
    if kind=='traversal':raw=synthetic([('../escape.py',b'private')])
    elif kind=='absolute':raw=synthetic([('/escape.py',b'private')])
    elif kind=='backslash':raw=synthetic([('private\\escape.py',b'private')])
    elif kind=='symlink':raw=synthetic(mode=stat.S_IFLNK|0o777)
    elif kind=='fifo':raw=synthetic(mode=stat.S_IFIFO|0o600)
    elif kind=='bad-utf8':raw=synthetic([('LICENSE',b'\xff')])
    elif kind=='encrypted-kind':raw=synthetic(compression=zipfile.ZIP_BZIP2)
    elif kind=='oversized':
        changed=bytearray(raw);central=changed.index(b'PK\x01\x02');struct.pack_into('<I',changed,central+24,cohort.MAX_WHEEL+1);raw=bytes(changed)
    elif kind=='crc':
        changed=bytearray(raw);offset=changed.index(b'# synthetic source');changed[offset]=ord('!');raw=bytes(changed)
    expected='0'*64 if kind=='hash' else cohort.sha(raw)
    with pytest.raises((ValueError,zipfile.BadZipFile)):cohort.wheel(raw,expected)


def test_existing_collection_refused_without_overwriting():
    before=(ROOT/cohort.MANIFEST).read_bytes()
    with pytest.raises(ValueError):cohort.collect(ROOT,{},ROOT)
    assert (ROOT/cohort.MANIFEST).read_bytes()==before


@pytest.mark.parametrize('kind',['declared-count','lying-count','central-bytes'])
def test_central_limits_refuse_before_zipfile_filelist_allocation(monkeypatch,kind):
    raw=synthetic([('a.py',b'x'),('b.py',b'x'),('c.py',b'x')]);changed=bytearray(raw)
    end=changed.rfind(b'PK\x05\x06')
    if kind=='declared-count':monkeypatch.setattr(cohort,'MAX_FILES',2)
    elif kind=='lying-count':
        monkeypatch.setattr(cohort,'MAX_FILES',2)
        struct.pack_into('<HH',changed,end+8,1,1)
    else:monkeypatch.setattr(cohort,'MAX_CENTRAL',1)
    def must_not_allocate(*args,**kwargs):raise AssertionError('ZipFile constructed before bound')
    monkeypatch.setattr(cohort.zipfile,'ZipFile',must_not_allocate)
    raw=bytes(changed)
    with pytest.raises(ValueError):cohort.wheel(raw,cohort.sha(raw))


@pytest.mark.parametrize('kind',['both-nul','central-nul','local-nul','local-zip64-contradiction','local-zip64-truncated','central-zip64','raw-duplicate'])
def test_ambiguous_raw_headers_refused_before_zipinfo_normalization(monkeypatch,kind):
    raw=synthetic([('a_b.py',b'# inert'),('c_d.py',b'# inert')])
    if kind.startswith('local-zip64'):
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as archive:
            with archive.open('file.py','w',force_zip64=True) as stream:stream.write(b'# inert')
        raw=output.getvalue()
        changed=bytearray(raw)
        if kind=='local-zip64-contradiction':struct.pack_into('<Q',changed,30+7+4,8)
        else:struct.pack_into('<H',changed,28,19)
        raw=bytes(changed)
    elif kind=='both-nul':raw=raw.replace(b'a_b.py',b'a\x00b.py')
    else:
        changed=bytearray(raw);central=changed.index(b'PK\x01\x02')
        if kind=='central-zip64':struct.pack_into('<I',changed,central+24,0xffffffff)
        elif kind=='central-nul':changed[central+46:central+52]=b'a\x00b.py'
        elif kind=='local-nul':changed[30:36]=b'a\x00b.py'
        else:
            second=changed.index(b'PK\x01\x02',central+4);changed[second+46:second+52]=b'a_b.py'
        raw=bytes(changed)
    def must_not_allocate(*args,**kwargs):raise AssertionError('ZipInfo normalization reached')
    monkeypatch.setattr(cohort.zipfile,'ZipFile',must_not_allocate)
    with pytest.raises(ValueError):cohort.wheel(raw,cohort.sha(raw))


def test_bounded_local_zip64_sizes_match_classic_central_directory():
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        with archive.open('file.py','w',force_zip64=True) as stream:stream.write(b'# inert')
    raw=output.getvalue();row,_=cohort.wheel(raw,cohort.sha(raw))
    assert row['python_source_count']==1 and row['member_count']==1
    # The locked Linux protobuf wheel uses redundant local sizes/version20.
    changed=bytearray(raw);central=changed.index(b'PK\x01\x02')
    struct.pack_into('<H',changed,4,20);struct.pack_into('<H',changed,central+6,20)
    struct.pack_into('<II',changed,18,7,7);raw=bytes(changed)
    row,_=cohort.wheel(raw,cohort.sha(raw))
    assert row['python_source_count']==1


@pytest.mark.parametrize('flags',[['--PRIVATE-CANARY'],['--wheel-mac','PRIVATE-CANARY']])
def test_actual_cli_malformed_flags_do_not_echo_values(flags):
    result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/verify-nli-license-cohort.py'),*flags],
                          capture_output=True,timeout=10)
    assert result.returncode==2 and result.stdout==b''
    assert result.stderr==b'NLI license cohort refused; use --help.\n'


def test_actual_cli_distribution_gate_stays_nonpassing():
    result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/verify-nli-license-cohort.py'),
                           '--require-distribution-ready'],capture_output=True,timeout=15)
    assert result.returncode==1 and result.stderr==b''
    row=json.loads(result.stdout)
    assert row['pass'] is True and row['distribution_gate_pass'] is False
