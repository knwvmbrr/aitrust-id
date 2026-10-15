"""Bounded archive observations are not license clearance or runtime support."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
from datetime import datetime,timezone
import pytest

from tools import native_inventory as module


def archive(members):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz') as t:
        for name,raw,kind in members:
            info=tarfile.TarInfo(name);info.size=len(raw);info.type=kind
            if kind==tarfile.SYMTYPE:info.linkname='/private-canary'
            t.addfile(info,io.BytesIO(raw) if kind==tarfile.REGTYPE else None)
    raw=output.getvalue()
    row={'integrity':'sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode(),
         'artifact_sha256':hashlib.sha256(raw).hexdigest()}
    return raw,row


def test_actual_binary_and_declarations_are_bound_to_the_same_archive():
    readme=b'# Native build\n\n## Licensing\nLibrary A uses MIT.\n'
    raw,row=archive([('package/binary.node',b'\x7fELF'+b'x'*1024,tarfile.REGTYPE),
        ('package/README.md',readme,tarfile.REGTYPE),
        ('package/versions.json',b'{"a":"1.2.3"}',tarfile.REGTYPE),
        ('package/nested.zip',b'opaque-nested-archive',tarfile.REGTYPE)])
    result,blobs=module.inspect(raw,row)
    assert result['native_candidates']==[{'member':'package/binary.node','bytes':1028,
        'sha256':hashlib.sha256(b'\x7fELF'+b'x'*1024).hexdigest(),'format':'elf'}]
    assert len(result['declarations'])==2 and len(result['uninspected_nested_archives'])==1
    assert readme in blobs.values()
    assert 'permissions_reviewed' not in result


@pytest.mark.parametrize('head,expected',[(b'\x00asm','wasm'),(b'MZ','pe-candidate'),
    (b'\xcf\xfa\xed\xfe','macho-or-fat-candidate'),(b'!<arch>\n','ar')])
def test_native_magic_without_a_filename_extension(head,expected):
    raw,row=archive([('package/no-extension',head+b'body',tarfile.REGTYPE)])
    assert module.inspect(raw,row)[0]['native_candidates'][0]['format']==expected


def test_named_script_is_not_misrepresented_as_proven_native_code():
    raw,row=archive([('package/bin/esbuild',b'#!/usr/bin/env node\n',tarfile.REGTYPE),
                     ('package/README.md',b'Ordinary README; not a license.',tarfile.REGTYPE)])
    value,blobs=module.inspect(raw,row)
    assert value['native_candidates'][0]['format']=='script'
    assert value['declarations']==[] and blobs=={}


@pytest.mark.parametrize('name',['../private','/private','package/../private','package/./private',
                                 'package/x\\y','package/\nprivate','outside/file'])
def test_unsafe_or_wrong_root_archive_member_is_refused(name):
    raw,row=archive([(name,b'x',tarfile.REGTYPE)])
    with pytest.raises(ValueError):module.inspect(raw,row)


@pytest.mark.parametrize('kind',[tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE])
def test_links_and_special_files_are_not_followed(kind):
    raw,row=archive([('package/link',b'',kind)])
    with pytest.raises(ValueError,match='special files'):module.inspect(raw,row)


def test_duplicate_members_refused():
    raw,row=archive([('package/x',b'1',tarfile.REGTYPE),('package/x',b'2',tarfile.REGTYPE)])
    with pytest.raises(ValueError,match='Duplicate'):module.inspect(raw,row)


def test_changed_bytes_and_fake_integrity_are_refused():
    raw,row=archive([('package/x',b'1',tarfile.REGTYPE)])
    for field in ('artifact_sha256','integrity'):
        changed=copy.deepcopy(row)
        changed[field]='0'*64 if field=='artifact_sha256' else 'sha512-'+base64.b64encode(b'x'*64).decode()
        with pytest.raises(ValueError,match='pinned observation'):module.inspect(raw,changed)


@pytest.mark.parametrize('body',[b'{"a":"1","a":"2"}',b'{"a":1}',b'NaN'])
def test_ambiguous_or_non_string_version_declarations_refused(body):
    raw,row=archive([('package/versions.json',body,tarfile.REGTYPE)])
    with pytest.raises(ValueError):module.inspect(raw,row)


def test_member_and_expansion_limits_apply_before_reading_large_bodies(monkeypatch):
    raw,row=archive([('package/x',b'x'*100,tarfile.REGTYPE)])
    monkeypatch.setattr(module,'MAX_TOTAL',50)
    with pytest.raises(ValueError,match='expanded byte limit'):module.inspect(raw,row)


def fixture(tmp_path,monkeypatch):
    root=tmp_path/'repo';target=root/'sbom/native';(target/'sources').mkdir(parents=True)
    raw,row=archive([('package/binary.node',b'\x7fELFcontent',tarfile.REGTYPE),
                     ('package/README.md',b'## Licensing\nMIT\n',tarfile.REGTYPE)])
    row.update(lock='package-lock.json',package_path='node_modules/example',version='1.0',license_declared='MIT')
    observed,blobs=module.inspect(raw,row)
    for digest,text in blobs.items():(target/'sources'/(digest+'.txt')).write_bytes(text)
    value={'profile':module.PROFILE,'captured_at':datetime.now(timezone.utc).isoformat(),
        'observed_by':'Codex','sources':{'fixture':'a'*64},'artifacts':[row|observed],
        'permissions_reviewed':False,'complete_transitive_coverage':False,'independent_accuracy_evidence':False}
    (target/'manifest.json').write_text(json.dumps(value))
    monkeypatch.setattr(module,'source_hashes',lambda root:{'fixture':'a'*64})
    monkeypatch.setattr(module,'inputs',lambda root,snapshot=None:[row])
    cache=tmp_path/'cache';cache.mkdir()
    (cache/(module.sha(row['integrity'].encode())+'.tgz')).write_bytes(raw)
    return root,value,cache


def save(root,value):
    (root/'sbom/native/manifest.json').write_text(json.dumps(value))


def test_actual_archive_replay_is_distinct_from_offline_inventory_check(tmp_path,monkeypatch):
    root,value,cache=fixture(tmp_path,monkeypatch)
    assert module.verify(root)['binary_bytes_replayed'] is False
    assert module.verify(root,cache)['binary_bytes_replayed'] is True
    # Without archive bytes, a well-formed observation is not authenticated.
    value['artifacts'][0]['native_candidates'][0]['sha256']='0'*64;save(root,value)
    assert module.verify(root)['observation_authenticated'] is False
    with pytest.raises(ValueError,match='does not reproduce'):module.verify(root,cache)


@pytest.mark.parametrize('field',['permissions_reviewed','complete_transitive_coverage','independent_accuracy_evidence'])
def test_inventory_cannot_promote_permission_or_accuracy(tmp_path,monkeypatch,field):
    root,value,_=fixture(tmp_path,monkeypatch);value[field]=True;save(root,value)
    with pytest.raises(ValueError,match='promotion'):module.verify(root)


def test_missing_and_unknown_artifact_coverage_refused(tmp_path,monkeypatch):
    root,value,_=fixture(tmp_path,monkeypatch)
    changed=copy.deepcopy(value);changed['artifacts']=[];save(root,changed)
    with pytest.raises(ValueError,match='Missing artifact'):module.verify(root)
    value['artifacts'][0]['package_path']='node_modules/unknown';save(root,value)
    with pytest.raises(ValueError,match='Unknown/duplicate'):module.verify(root)


def test_changed_declaration_and_orphan_file_refused(tmp_path,monkeypatch):
    root,value,_=fixture(tmp_path,monkeypatch)
    file=next((root/'sbom/native/sources').iterdir());original=file.read_bytes();file.write_bytes(b'forged')
    with pytest.raises(ValueError,match='Declaration bytes'):module.verify(root)
    file.write_bytes(original);(file.parent/'orphan.txt').write_bytes(b'orphan')
    with pytest.raises(ValueError,match='orphan'):module.verify(root)


def test_changed_inputs_require_recollection(tmp_path,monkeypatch):
    root,_,_=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'source_hashes',lambda root:{'fixture':'b'*64})
    with pytest.raises(ValueError,match='source drift'):module.verify(root)


@pytest.mark.parametrize('same_member',[True,False])
def test_size_exception_is_bound_to_exact_archive_and_member(monkeypatch,same_member):
    name='package/allowed.node' if same_member else 'package/other.node'
    raw,row=archive([(name,b'\x7fELF'+b'x'*20,tarfile.REGTYPE)])
    monkeypatch.setattr(module,'MAX_MEMBER',8)
    monkeypatch.setattr(module,'MEMBER_OVERRIDES',{row['artifact_sha256']:{'package/allowed.node':24}})
    if same_member:
        assert module.inspect(raw,row)[0]['native_candidates'][0]['bytes']==24
    else:
        with pytest.raises(ValueError,match='member limit'):module.inspect(raw,row)


def test_committed_locked_inventory_is_inspectable_offline():
    result=module.verify()
    assert result['pass'] and result['artifacts']==205
    assert result['native_candidates']>100
    assert result['licensing_declarations']>0
    assert result['uninspected_nested_archives']>=1
    assert all(result[k] is False for k in ('binary_bytes_replayed','observation_authenticated',
        'permission_cleared','complete_transitive_coverage','independent_accuracy_evidence'))
