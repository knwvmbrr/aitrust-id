"""Finite offline artifact/notice controls; no license permission claim."""
import base64
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import zipfile
import pytest
from tools import c2pa_cohort as c


def wheel(extra=None):
    rows={'sample/__init__.py':b'# an inert source file\n',
          'sample-1.0.dist-info/METADATA':b'Metadata-Version: 2.4\nName: sample\nVersion: 1.0\nLicense-Expression: MIT\n',
          'sample-1.0.dist-info/WHEEL':b'Wheel-Version: 1.0\nTag: py3-none-any\n',
          'sample-1.0.dist-info/licenses/LICENSE':b'Example notice\n'}
    rows.update(extra or {})
    f=io.StringIO(newline=''); writer=csv.writer(f,lineterminator='\n')
    for n,data in sorted(rows.items()):writer.writerow([n,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='),len(data)])
    record='sample-1.0.dist-info/RECORD'; writer.writerow([record,'','']);rows[record]=f.getvalue().encode()
    return rows


def zipped(rows):
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w') as z:
        for name,data in rows:z.writestr(name,data)
    return f.getvalue()


def tarred(rows):
    f=io.BytesIO()
    with tarfile.open(fileobj=f,mode='w:gz') as t:
        for name,kind,raw in rows:
            info=tarfile.TarInfo(name);info.type=kind;info.size=len(raw)
            if kind==tarfile.SYMTYPE:info.linkname='outside'
            t.addfile(info,io.BytesIO(raw) if kind==tarfile.REGTYPE else None)
    return f.getvalue()


def test_inert_wheel_record_and_metadata_without_import():
    rows=wheel(); observed=c.archive(zipped(rows.items()),'zip')
    declaration,_=c.distribution(observed,'sample','1.0')
    assert declaration['name']=='sample' and declaration['license_declared']=='MIT'
    assert observed==rows


@pytest.mark.parametrize('name',['../escape','/absolute','folder/../escape','folder\\escape','C:/escape','a//b','a/./b','a\0b'])
def test_zip_unsafe_path_refused(name):
    raw = zipped([(name,b'inert')]) if '\0' not in name else zipped([('a_b',b'inert')]).replace(b'a_b',b'a\0b')
    with pytest.raises(ValueError):c.archive(raw,'zip')


def test_zip_duplicate_and_symlink_refused():
    with pytest.warns(UserWarning):raw=zipped([('a',b'x'),('a',b'y')])
    with pytest.raises(ValueError):c.archive(raw,'zip')
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w') as z:
        info=zipfile.ZipInfo('link');info.external_attr=(0o120777<<16);z.writestr(info,'target')
    with pytest.raises(ValueError):c.archive(f.getvalue(),'zip')


@pytest.mark.parametrize('rows',[[('../escape',tarfile.REGTYPE,b'x')],
 [('a',tarfile.REGTYPE,b'x'),('a',tarfile.REGTYPE,b'y')], [('link',tarfile.SYMTYPE,b'')],
 [('device',tarfile.CHRTYPE,b'')]])
def test_tar_unsafe_duplicate_and_nonregular_refused(rows):
    with pytest.raises(ValueError):c.archive(tarred(rows),'tar-gzip')


def test_member_count_and_size_limits_before_read(monkeypatch):
    raw=zipped([('a',b'1234')])
    monkeypatch.setattr(c,'MAX_MEMBER',3)
    with pytest.raises(ValueError):c.archive(raw,'zip')
    monkeypatch.setattr(c,'MAX_MEMBER',10);monkeypatch.setattr(c,'MAX_FILES',1)
    with pytest.raises(ValueError):c.archive(zipped([('a',b''),('b',b'')]),'zip')


@pytest.mark.parametrize('mutation', ['data','missing','extra','duplicate','self','weak_digest','size'])
def test_record_cannot_omit_or_change_members(mutation):
    rows=wheel();record='sample-1.0.dist-info/RECORD'
    if mutation=='data':rows['sample/__init__.py']=b'changed'
    if mutation=='missing':del rows['sample/__init__.py']
    if mutation=='extra':rows['unlisted.py']=b'inert'
    if mutation=='duplicate':rows[record]+=rows[record].splitlines(keepends=True)[0]
    if mutation=='self':rows[record]=rows[record].replace((record+',,').encode(),(record+',sha256=bad,1').encode())
    if mutation=='weak_digest':rows[record]=rows[record].replace(b'sha256=',b'md5=')
    if mutation=='size':
        parsed=list(csv.reader(io.StringIO(rows[record].decode()))); parsed[0][2]=str(int(parsed[0][2])+1)
        out=io.StringIO(newline='');csv.writer(out,lineterminator='\n').writerows(parsed);rows[record]=out.getvalue().encode()
    with pytest.raises(ValueError):c.records(rows,record)


def test_wrong_package_version_and_duplicate_name_refused():
    rows=wheel()
    with pytest.raises(ValueError):c.distribution(rows,'foreign','1.0')
    with pytest.raises(ValueError):c.distribution(rows,'sample','2.0')
    rows=wheel({'sample-1.0.dist-info/METADATA':b'Name: sample\nName: other\nVersion: 1.0\n'})
    with pytest.raises(ValueError):c.distribution(rows,'sample','1.0')


def copied(tmp_path):
    value=json.loads((c.ROOT/c.MANIFEST).read_text())
    names={*c.FILES,*c.INPUTS,c.MANIFEST}|{str(p.relative_to(c.ROOT)) for p in (c.ROOT/c.STORE).iterdir()}
    for name in names:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,path)
    return value


def test_current_checkout_has_no_replay_or_clearance_credit(monkeypatch):
    def refused(*args,**kwargs):raise AssertionError('network not allowed')
    monkeypatch.setattr(socket,'socket',refused)
    result=c.verify()
    assert result['packages']==10 and result['distinct_wheels']==14 and result['native_release_matches']==2
    assert result['selected_profile_slots']==20
    assert result['artifact_bytes_replayed'] is False and result['packages_executed'] is False
    assert all(result[k] is False for k in c.DISCLAIMERS)
    with pytest.raises(ValueError):c.verify(require_clearance=True)


@pytest.mark.parametrize('mutation',['lock','pin','source','notice','platform','wheel','record','extra_text','py_relation','native_omission','source_notice_omission','source_identity','nested_clearance'])
def test_changed_evidence_refuses(tmp_path,mutation):
    value=copied(tmp_path)
    if mutation=='lock':(tmp_path/c.INPUTS[0]).write_text('changed')
    if mutation=='pin':(tmp_path/c.INPUTS[1]).write_text('{}')
    if mutation=='source':(tmp_path/c.FILES[0]).write_text('changed')
    if mutation=='notice':(tmp_path/value['packages'][0]['source']['notices'][0]['path']).write_text('changed')
    if mutation=='platform':value['selected_profiles'].pop('darwin-arm64-cp312')
    if mutation=='wheel':value['wheels'].pop()
    if mutation=='record':value['wheels'][0]['members']['c2pa/__init__.py']['bytes']+=1
    if mutation=='extra_text':(tmp_path/c.STORE/('a'*64+'.txt')).write_text('unregistered')
    if mutation=='nested_clearance':value['sdk_upstream']['native_matches'][0]['permission_cleared']=True
    if mutation=='native_omission':value['wheels'][0]['native_members']=[]
    if mutation=='source_notice_omission':value['packages'][0]['source']['notices'].pop()
    if mutation=='source_identity':value['wheels'][0]['python_source_relationships'][0]['source_members']=[]
    if mutation=='py_relation':value['wheels'][0]['python_source_relationships'][0]['relationship']='source_proven'
    (tmp_path/c.MANIFEST).write_text(json.dumps(value))
    with pytest.raises(ValueError):c.verify(tmp_path)


@pytest.mark.parametrize('field',list(c.DISCLAIMERS))
def test_no_manifest_flag_can_promote_permission_or_build_claim(tmp_path,field):
    value=copied(tmp_path);value[field]=True;(tmp_path/c.MANIFEST).write_text(json.dumps(value))
    with pytest.raises(ValueError):c.verify(tmp_path)


def test_symlink_cache_and_text_refused(tmp_path):
    real=tmp_path/'real';real.write_bytes(b'upstream');link=tmp_path/'link';link.symlink_to(real)
    with pytest.raises(ValueError):c.read(link)


def test_cli_checkout_success_and_clearance_refusal():
    result=subprocess.run([sys.executable,str(c.ROOT/'scripts/verify-c2pa-cohort.py')],capture_output=True,timeout=10)
    assert result.returncode==0 and json.loads(result.stdout)['artifact_bytes_replayed'] is False
    refused=subprocess.run([sys.executable,str(c.ROOT/'scripts/verify-c2pa-cohort.py'),'--require-clearance'],capture_output=True,timeout=10)
    assert refused.returncode==2 and b'no permission' in refused.stderr


def test_zip_encrypted_flag_refused_before_open():
    raw=bytearray(zipped([('file',b'inert')]))
    local=raw.index(b'PK\x03\x04'); central=raw.index(b'PK\x01\x02')
    raw[local+6] |= 1; raw[central+8] |= 1
    with pytest.raises(ValueError):c.archive(bytes(raw),'zip')


def test_tar_extended_metadata_decompression_is_bounded(monkeypatch):
    f=io.BytesIO()
    with tarfile.open(fileobj=f,mode='w:gz',format=tarfile.PAX_FORMAT) as t:
        item=tarfile.TarInfo('file');item.size=1;item.pax_headers={'comment':'x'*200000}
        t.addfile(item,io.BytesIO(b'x'))
    monkeypatch.setattr(c,'MAX_EXPANDED',1024)
    with pytest.raises(ValueError):c.archive(f.getvalue(),'tar-gzip')


def test_finite_lock_policy_and_unknown_lines_refused(tmp_path):
    path=tmp_path/c.INPUTS[0];path.parent.mkdir(parents=True)
    original=(c.ROOT/c.INPUTS[0]).read_text()
    for changed in [original.replace('--only-binary=:all:',''),original+'unexpected option\n',
                    original.replace('c2pa-python==0.38.0','c2pa-python==0.38.1')]:
        path.write_text(changed)
        with pytest.raises(ValueError):c.locked(tmp_path)
