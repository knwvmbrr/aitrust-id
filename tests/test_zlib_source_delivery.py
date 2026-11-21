import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile
import pytest
from tools import zlib_source_delivery as z


def clone(root):
    m,retained=z.checked()
    names=set(retained)|set(z.SOURCES)|{z.foundation.RELEASE,z.foundation.LOCK}
    for name in names:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,target)
    return root


def test_complete_deterministic_source_and_verbatim_notices():
    m,retained=z.checked();out=z.outputs();assert out==z.outputs()
    assert all(v is False for v in m['claims'].values())
    for name in ['zlib_license','zlib_header_notice','emscripten_recipe_license']:
        assert retained[m['evidence'][name]['path']] in out['NOTICES.txt']
    assert b'1995-2024 Jean-loup Gailly and Mark Adler' in out['NOTICES.txt']
    assert b'1995-2022 Jean-loup Gailly and Mark Adler' in out['NOTICES.txt']
    with zipfile.ZipFile(io.BytesIO(out['ZLIB-SOURCES.zip'])) as archive:
        assert len(archive.namelist())==6 and len(set(archive.namelist()))==6
        assert archive.read('upstream/zlib-1.3.1.tar.gz')==retained[m['evidence']['zlib_archive']['path']]
        assert archive.read('source/LICENSE')==retained[m['evidence']['zlib_license']['path']]
        assert archive.read('source/zlib.h')==retained[m['evidence']['zlib_header_source']['path']]
        assert archive.read('NOTICES.txt')==out['NOTICES.txt'] and archive.read('index.json')==out['index.json']
        assert all(row.date_time==(1980,1,1,0,0,0) and row.compress_type==zipfile.ZIP_STORED for row in archive.infolist())


@pytest.mark.parametrize('field',['zlib_archive','zlib_license','zlib_header_source','zlib_header_notice','emscripten_recipe','emscripten_recipe_license','runtime_observation'])
def test_changed_or_missing_retained_evidence_refuses(tmp_path,field):
    root=clone(tmp_path);m=json.loads((root/z.MANIFEST).read_bytes());p=root/m['evidence'][field]['path'];p.write_bytes(b'changed')
    with pytest.raises(ValueError):z.export(root/'delivery',root)
    assert not (root/'delivery').exists();p.unlink()
    with pytest.raises((ValueError,OSError)):z.checked(root)


@pytest.mark.parametrize('change',['claims','unknown','producer','runtime','source_path','bool_claim'])
def test_closed_manifest_cannot_self_approve(tmp_path,change):
    root=clone(tmp_path);p=root/z.MANIFEST;m=json.loads(p.read_bytes())
    if change=='claims':m['claims']['global_distribution_admitted']=True
    elif change=='unknown':m['self_approved']=True
    elif change=='producer':m['producer_sha256'][z.SOURCES[0]]='0'*64
    elif change=='runtime':m['runtime_members']['pyodide.asm.wasm']['sha256']='0'*64
    elif change=='source_path':m['evidence']['zlib_archive']['path']='../private-source'
    else:m['claims']['legal_clearance']=0
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):z.checked(root)


def test_coherent_runtime_rebinding_refused_with_producer_unchanged(tmp_path):
    root=clone(tmp_path);release_path=root/z.foundation.RELEASE;release=json.loads(release_path.read_bytes());fake=b'NOT_REVIEWED_RUNTIME'
    replacement={name:{'bytes':len(fake),'sha256':z.sha(fake)} for name in release['runtime_members']}
    release['runtime_members']=replacement;release_path.write_text(json.dumps(release))
    p=root/z.MANIFEST;m=json.loads(p.read_bytes());m['runtime_members']=replacement;m['input_sha256']['release_manifest_sha256']=z.sha(release_path.read_bytes());p.write_text(json.dumps(m))
    for check in [lambda:z.checked(root),lambda:z.outputs(root),lambda:z.export(root/'out',root)]:
        with pytest.raises(ValueError):check()
    assert not (root/'out').exists()


def test_coherent_archive_and_recipe_rebinding_refused(tmp_path):
    root=clone(tmp_path);p=root/z.MANIFEST;m=json.loads(p.read_bytes());raw=b'UNREVIEWED_SOURCE';row=m['evidence']['zlib_archive'];old=root/row['path'];old.unlink();row.update(path=z.source_path(z.sha(raw),'.tar.gz'),bytes=len(raw),sha256=z.sha(raw));(root/row['path']).write_bytes(raw);m['source_sha512']=hashlib.sha512(raw).hexdigest();p.write_text(json.dumps(m))
    with pytest.raises((ValueError,OSError)):z.checked(root)


def test_wrong_compressed_bytes_refused_before_archive_parser(monkeypatch):
    monkeypatch.setattr(z.foundation,'selected_tar',lambda *a,**k:(_ for _ in ()).throw(AssertionError('must refuse before parsing')))
    with pytest.raises(ValueError):z.archive_members(b'not approved archive')
    monkeypatch.setattr(z,'preflight_recipe_tar',lambda *a:(_ for _ in ()).throw(AssertionError('must refuse before parsing')))
    with pytest.raises(ValueError):z.recipe_members(b'not approved archive')


def tar_header(size,kind=tarfile.REGTYPE):
    info=tarfile.TarInfo('authored');info.type=kind;info.size=size;return info.tobuf(format=tarfile.USTAR_FORMAT)


@pytest.mark.parametrize('raw',[tar_header(20000,tarfile.XHDTYPE),tar_header(16000001),tar_header(0)[:300],b'x'*512])
def test_declared_metadata_size_truncation_and_checksum_refused_before_tarfile(raw):
    with pytest.raises((ValueError,EOFError)):z.preflight_recipe_tar(gzip.compress(raw))


def test_export_idempotent_and_prewrite_failure_preserves_previous(tmp_path,monkeypatch):
    target=tmp_path/'source';out=z.export(target);assert z.export(target)==out
    (target/'NOTICES.txt').write_bytes(b'old');before={p.name:p.read_bytes() for p in target.iterdir()}
    monkeypatch.setattr(z.os,'fsync',lambda *_:(_ for _ in ()).throw(OSError('authored stage failure')))
    with pytest.raises(OSError):z.export(target)
    assert {p.name:p.read_bytes() for p in target.iterdir()}==before


def test_input_mutation_refused_before_replacement(tmp_path,monkeypatch):
    target=tmp_path/'source';z.export(target);(target/'NOTICES.txt').write_bytes(b'old');before={p.name:p.read_bytes() for p in target.iterdir()};original=z.outputs;calls=0
    def changed(root=z.ROOT):
        nonlocal calls
        calls+=1
        if calls==2:raise z.DeliveryError('authored source mutation')
        return original(root)
    monkeypatch.setattr(z,'outputs',changed)
    with pytest.raises(ValueError):z.export(target)
    assert {p.name:p.read_bytes() for p in target.iterdir()}==before


def test_post_move_failure_reports_uncertain_and_retains_backup(tmp_path,monkeypatch):
    target=tmp_path/'source';z.export(target);(target/'NOTICES.txt').write_bytes(b'old');rename=z.os.rename
    def fail(source,destination):
        if Path(source).name.startswith('.zlib-stage-'):raise OSError('authored replacement failure')
        return rename(source,destination)
    monkeypatch.setattr(z.os,'rename',fail)
    with pytest.raises(z.OutputUncertain):z.export(target)
    assert len(list(tmp_path.glob('.zlib-old-*')))==1


def test_unknown_destination_and_link_refused(tmp_path):
    target=tmp_path/'source';target.mkdir();(target/'unreviewed').write_bytes(b'x')
    with pytest.raises(ValueError):z.export(target)
    link=tmp_path/'link';link.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError):z.export(link)


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'['*3000+b']'*3000])
def test_ambiguous_nonfinite_deep_metadata_refused(raw,tmp_path):
    root=clone(tmp_path);(root/z.MANIFEST).write_bytes(raw)
    with pytest.raises((ValueError,RecursionError)):z.checked(root)


def test_actual_cli_diagnostics_never_echo_private_flags_or_paths():
    for args in [['--PRIVATE_UNKNOWN'],['--replay-cache','/private/PRIVATE_SOURCE'],['--export','/private/PRIVATE_SOURCE']]:
        p=subprocess.run([sys.executable,'-B','scripts/zlib-source-delivery.py',*args],capture_output=True,timeout=10)
        assert p.returncode==2 and json.loads(p.stdout)=={'pass':False,'reason':'zlib_source_notice_unavailable'} and p.stderr==b''
        assert b'PRIVATE' not in p.stdout


def test_fdopen_constructor_failure_closes_owned_raw_descriptor(tmp_path,monkeypatch):
    original=z.os.fdopen;seen=[]
    def fail(fd,mode,*args,**kwargs):
        if mode=='wb':
            assert kwargs.get('closefd') is False;seen.append(fd);raise OSError('PRIVATE_CONSTRUCTOR_ERROR')
        return original(fd,mode,*args,**kwargs)
    monkeypatch.setattr(z.os,'fdopen',fail)
    with pytest.raises(OSError):z.export(tmp_path/'source')
    assert len(seen)==1
    with pytest.raises(OSError):os.fstat(seen[0])
    assert not (tmp_path/'source').exists()


def test_close_error_never_recloses_reused_owned_marker(tmp_path,monkeypatch):
    marker=tmp_path/'marker';marker.write_bytes(b'owned inert marker')
    fdopen=z.os.fdopen;close=z.os.close;opened=[];replacement=[];attempts=[]
    def capture(fd,mode,*args,**kwargs):
        if mode=='wb':opened.append(fd);assert kwargs.get('closefd') is False
        return fdopen(fd,mode,*args,**kwargs)
    def release_then_error(fd):
        if opened and fd==opened[0]:
            attempts.append(fd)
            if len(attempts)>1:return close(fd)
            close(fd);new=os.open(marker,os.O_RDONLY);replacement.append(new)
            assert new==fd
            raise OSError('PRIVATE_CLOSE_ERROR_AFTER_RELEASE')
        return close(fd)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(z.os,'fdopen',capture);patch.setattr(z.os,'close',release_then_error)
            with pytest.raises(OSError):z.export(tmp_path/'source')
            assert attempts==opened and len(attempts)==1 and os.fstat(replacement[0]).st_size==len(b'owned inert marker')
            assert not (tmp_path/'source').exists()
    finally:
        for fd in replacement:close(fd)


def test_actual_cli_injected_constructor_error_is_fixed_and_private(tmp_path):
    code="""import importlib.util,sys
spec=importlib.util.spec_from_file_location('zlib_cli','scripts/zlib-source-delivery.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
original=cli.delivery.os.fdopen
def fail(fd,mode,*args,**kwargs):
 if mode=='wb':raise OSError('/PRIVATE_CONSTRUCTOR_MARKER')
 return original(fd,mode,*args,**kwargs)
cli.delivery.os.fdopen=fail
raise SystemExit(cli.main(['--export',sys.argv[1]]))
"""
    p=subprocess.run([sys.executable,'-B','-c',code,str(tmp_path/'out')],capture_output=True,timeout=10)
    assert p.returncode==2 and json.loads(p.stdout)=={'pass':False,'reason':'zlib_source_notice_unavailable'} and not p.stderr and b'PRIVATE' not in p.stdout
    assert not (tmp_path/'out').exists()
