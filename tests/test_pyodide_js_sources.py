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
from tools import pyodide_js_sources as js


def clone(tmp_path):
    paths=[js.MANIFEST,js.RELEASE,js.LOCK,*js.SOURCES]
    manifest=json.loads(Path(js.MANIFEST).read_text())
    paths.extend(row['path'] for row in manifest['preferred']+manifest['licenses'])
    paths.extend([manifest['source_archive']['path'],manifest['source_map']['path']])
    for name in set(paths):
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,target)
    return tmp_path


def built(tmp_path):
    root=clone(tmp_path/'repo');artifact=tmp_path/'dist';artifact.mkdir()
    m,_=js.checked(root)
    # Inert bytes cannot satisfy known runtime identities; positive actual copies
    # are exercised separately with the real installed/built runtime.
    directory=artifact/'device'/('runtime-'+js.VERSION);directory.mkdir(parents=True)
    for name in m['runtime_members']:(directory/name).write_bytes(b'not-runtime')
    js.export(artifact/'runtime-js-sources',root)
    return root,artifact


def test_exact_cohort_and_deterministic_complete_zip():
    m,raw=js.checked();a=js.outputs();assert a==js.outputs()
    assert len(m['preferred'])==10 and len(m['licenses'])==2
    assert a['NOTICES.txt'].count(b'Copyright (c) 2017 Eric Wendelin')==1
    assert b'NOT full WASM' in a['NOTICES.txt']
    with zipfile.ZipFile(io.BytesIO(a['PYODIDE-JS-SOURCES.zip'])) as z:
        assert len(z.namelist())==14 and len(set(z.namelist()))==14
        assert z.read('NOTICES.txt')==a['NOTICES.txt'] and z.read('index.json')==a['index.json']
        for row in m['preferred']:assert z.read(row['name'])==raw[row['path']]
        assert z.read('upstream/pyodide-'+js.COMMIT+'.tar.gz')==raw[m['source_archive']['path']]
        assert all(i.compress_type==zipfile.ZIP_STORED and i.date_time==(1980,1,1,0,0,0) for i in z.infolist())
    assert all(v is False for v in json.loads(a['index.json'])['claims'].values())


@pytest.mark.parametrize('change',['claim','source','map','notice','preferred','version','producer','runtime','selected_lock'])
def test_cohort_drift_refused(tmp_path,change):
    root=clone(tmp_path);p=root/js.MANIFEST;m=json.loads(p.read_text())
    if change=='claim':m['claims']['legal_clearance']=True
    elif change=='source':(root/m['source_archive']['path']).write_bytes(b'changed')
    elif change=='map':(root/m['source_map']['path']).write_bytes(b'changed')
    elif change=='notice':(root/m['licenses'][1]['path']).write_bytes(b'changed')
    elif change=='preferred':(root/m['preferred'][0]['path']).write_bytes(b'changed')
    elif change=='version':m['version']='unreviewed'
    elif change=='producer':(root/js.SOURCES[0]).write_bytes(b'changed')
    elif change=='runtime':m['runtime_members']['pyodide.mjs']['sha256']='0'*64
    elif change=='selected_lock':
        lock=root/js.LOCK;data=json.loads(lock.read_text());data['packages']['node_modules/pyodide']['version']='unknown';lock.write_text(json.dumps(data))
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):js.outputs(root)


def test_unrelated_lock_entry_does_not_invalidate_selected_cohort(tmp_path):
    root=clone(tmp_path);p=root/js.LOCK;lock=json.loads(p.read_text());lock['packages']['node_modules/unrelated-developer-package']={'version':'999'};p.write_text(json.dumps(lock))
    assert js.outputs(root)==js.outputs()


def test_wrong_archive_rejected_before_parser(monkeypatch):
    monkeypatch.setattr(js,'selected_tar',lambda *a:(_ for _ in ()).throw(AssertionError('must not parse changed archive')))
    with pytest.raises(js.SourceError):js.inspect_archives(b'not npm',b'not source')


def test_expansion_bound_before_tar_parser(monkeypatch):
    monkeypatch.setattr(js,'MAX_EXPANDED',1000)
    monkeypatch.setattr(js.tarfile,'open',lambda *a,**k:(_ for _ in ()).throw(AssertionError('parser must not run')))
    with pytest.raises(js.SourceError):js.selected_tar(gzip.compress(b'x'*1001),'root/',{'wanted'})


def tar_bytes(rows):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as t:
        for name,data in rows:
            i=tarfile.TarInfo(name);i.size=len(data);t.addfile(i,io.BytesIO(data))
    return out.getvalue()


def test_pax_declared_metadata_cap_before_tarfile(monkeypatch):
    i=tarfile.TarInfo('PaxHeader');i.type=tarfile.XHDTYPE;i.size=20000
    raw=i.tobuf(format=tarfile.USTAR_FORMAT)+b'X'*20000+b'\0'*((-20000)%512)+b'\0'*1024
    monkeypatch.setattr(js.tarfile,'open',lambda *a,**k:(_ for _ in ()).throw(AssertionError('parser must not run')))
    with pytest.raises(js.SourceError):js.selected_tar(gzip.compress(raw),'root/',{'wanted'})


@pytest.mark.parametrize('rows',[[('root/a',b'a'),('root/a',b'a')],[('../private',b'a')],[('other/a',b'a')]])
def test_duplicate_or_unsafe_archive_paths_refused(rows):
    with pytest.raises(js.SourceError):js.selected_tar(gzip.compress(tar_bytes(rows)),'root/',{'a'})


@pytest.mark.parametrize('value',[b'{"x":1,"x":2}',b'{"x":NaN}',b'['*2000+b'0'+b']'*2000,b'{}'*100001])
def test_metadata_refusal(value):
    with pytest.raises((ValueError,RecursionError)):js.parse(value)


def test_export_writes_all_and_is_idempotent(tmp_path):
    target=tmp_path/'runtime-js-sources';a=js.export(target);assert set(p.name for p in target.iterdir())==set(js.OUTPUT_NAMES)
    assert all((target/n).read_bytes()==v for n,v in a.items());assert js.export(target)==a


def test_staging_write_failure_preserves_prior_outputs(tmp_path,monkeypatch):
    target=tmp_path/'runtime-js-sources';a=js.export(target);(target/'NOTICES.txt').write_bytes(b'old output to replace');prior={p.name:p.read_bytes() for p in target.iterdir()}
    monkeypatch.setattr(js.os,'fsync',lambda *_:(_ for _ in ()).throw(OSError('authored stage error')))
    with pytest.raises(OSError):js.export(target)
    assert {p.name:p.read_bytes() for p in target.iterdir()}==prior


def test_changed_sources_before_publication_preserve_existing(tmp_path,monkeypatch):
    target=tmp_path/'runtime-js-sources';js.export(target);(target/'NOTICES.txt').write_bytes(b'old');prior={p.name:p.read_bytes() for p in target.iterdir()}
    original=js.outputs;calls=0
    def changed(root=js.ROOT):
        nonlocal calls
        calls+=1
        if calls==2:raise js.SourceError('authored input mutation')
        return original(root)
    monkeypatch.setattr(js,'outputs',changed)
    with pytest.raises(js.SourceError):js.export(target)
    assert {p.name:p.read_bytes() for p in target.iterdir()}==prior


def test_post_move_failure_is_explicit_uncertain(tmp_path,monkeypatch):
    target=tmp_path/'runtime-js-sources';js.export(target);(target/'NOTICES.txt').write_bytes(b'old');rename=js.os.rename
    def fail(source,destination):
        if Path(source).name.startswith('.pyodide-js-stage-'):raise OSError('authored commit failure')
        return rename(source,destination)
    monkeypatch.setattr(js.os,'rename',fail)
    with pytest.raises(js.OutputUncertain):js.export(target)
    assert len(list(tmp_path.glob('.pyodide-js-old-*')))==1


def test_unknown_destination_or_link_refused(tmp_path):
    target=tmp_path/'runtime-js-sources';target.mkdir();(target/'unreviewed').write_bytes(b'x')
    with pytest.raises(js.SourceError):js.export(target)
    target2=tmp_path/'link';target2.symlink_to(target,target_is_directory=True)
    with pytest.raises(js.SourceError):js.export(target2)


def test_changed_runtime_refused(tmp_path):
    root,artifact=built(tmp_path)
    with pytest.raises(js.SourceError):js.check_built(artifact,root)


def test_extra_export_file_refused_before_accepting_runtime(tmp_path):
    root,artifact=built(tmp_path);(artifact/'runtime-js-sources/unreviewed').write_bytes(b'x')
    with pytest.raises(js.SourceError):js.check_built(artifact,root)


def test_actual_cli_unknown_and_private_path_diagnostics_fixed():
    script='scripts/pyodide-js-sources.py'
    for args in [['--PRIVATE_UNKNOWN'],['--npm-archive','/private/PRIVATE_MARKER_NOT_EXIST']]:
        p=subprocess.run([sys.executable,'-B',script,*args],capture_output=True,timeout=10)
        assert p.returncode==2 and json.loads(p.stdout)=={'pass':False,'reason':'selected_runtime_source_notice_unavailable'}
        assert p.stderr==b'' and b'PRIVATE' not in p.stdout


def test_coherently_rehashed_all_runtime_substitution_refused(tmp_path):
    root=clone(tmp_path/'repo');artifact=tmp_path/'dist';artifact.mkdir()
    forged={name:{'bytes':len(b'NOT_REVIEWED_RUNTIME!'),'sha256':js.sha(b'NOT_REVIEWED_RUNTIME!')} for name in js.RUNTIME_NAMES}
    release_path=root/js.RELEASE;release=json.loads(release_path.read_bytes())
    release['runtime_members']=forged;release_path.write_text(json.dumps(release))
    path=root/js.MANIFEST;m=json.loads(path.read_bytes());m['runtime_members']=forged
    m['input_sha256']['release_manifest_sha256']=js.sha(release_path.read_bytes());path.write_text(json.dumps(m))
    directory=artifact/'device'/('runtime-'+js.VERSION);directory.mkdir(parents=True)
    for name in forged:(directory/name).write_bytes(b'NOT_REVIEWED_RUNTIME!')
    # The original defect admitted this unchanged-producer, coherently rebound data.
    for operation in [lambda:js.checked(root),lambda:js.export(artifact/'runtime-js-sources',root),lambda:js.check_built(artifact,root)]:
        with pytest.raises(js.SourceError):operation()
    assert not (artifact/'runtime-js-sources').exists()


@pytest.mark.parametrize('change',['missing','extra','list','bool_size','bad_hash','extra_field'])
def test_runtime_projection_shape_refused_before_digest(change):
    value=json.loads(Path(js.RELEASE).read_bytes())['runtime_members']
    if change=='missing':value.pop('pyodide.mjs')
    elif change=='extra':value['unreviewed.bin']=value['pyodide.mjs']
    elif change=='list':value=[]
    elif change=='bool_size':value['pyodide.mjs']['bytes']=True
    elif change=='bad_hash':value['pyodide.mjs']['sha256']='not-a-digest'
    else:value['pyodide.mjs']['claimed_allowed']=True
    with pytest.raises(js.SourceError):js.reviewed_runtime(value)


def test_constructor_failure_closes_owned_output_fd(tmp_path,monkeypatch):
    original=js.os.fdopen;seen=[]
    def fail(fd,mode,*args,**kwargs):
        if mode=='wb':
            assert kwargs.get('closefd') is False;seen.append(fd);raise OSError('PRIVATE_CONSTRUCTOR')
        return original(fd,mode,*args,**kwargs)
    monkeypatch.setattr(js.os,'fdopen',fail)
    with pytest.raises(OSError):js.export(tmp_path/'source')
    assert len(seen)==1
    with pytest.raises(OSError):os.fstat(seen[0])
    assert not (tmp_path/'source').exists()


def test_release_error_does_not_close_reused_owned_descriptor(tmp_path,monkeypatch):
    marker=tmp_path/'marker';marker.write_bytes(b'owned marker');fdopen=js.os.fdopen;close=js.os.close;writers=[];attempts=[];reused=[]
    def capture(fd,mode,*args,**kwargs):
        if mode=='wb':writers.append(fd);assert kwargs.get('closefd') is False
        return fdopen(fd,mode,*args,**kwargs)
    def release_then_error(fd):
        if writers and fd==writers[0]:
            attempts.append(fd)
            if len(attempts)>1:return close(fd)
            close(fd);replacement=os.open(marker,os.O_RDONLY);reused.append(replacement);assert replacement==fd
            raise OSError('PRIVATE_CLOSE_AFTER_RELEASE')
        return close(fd)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(js.os,'fdopen',capture);patch.setattr(js.os,'close',release_then_error)
            with pytest.raises(OSError):js.export(tmp_path/'source')
            assert len(attempts)==1 and os.fstat(reused[0]).st_size==len(b'owned marker')
            assert not (tmp_path/'source').exists()
    finally:
        for fd in reused:close(fd)


def test_actual_cli_constructor_error_stays_private(tmp_path):
    code="""import importlib.util,sys
spec=importlib.util.spec_from_file_location('js_cli','scripts/pyodide-js-sources.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
original=cli.source.os.fdopen
def fail(fd,mode,*args,**kwargs):
 if mode=='wb':raise OSError('/PRIVATE_CONSTRUCTOR_PATH')
 return original(fd,mode,*args,**kwargs)
cli.source.os.fdopen=fail
raise SystemExit(cli.main(['--export',sys.argv[1]]))
"""
    result=subprocess.run([sys.executable,'-B','-c',code,str(tmp_path/'source')],capture_output=True,timeout=10)
    assert result.returncode==2 and json.loads(result.stdout)=={'pass':False,'reason':'selected_runtime_source_notice_unavailable'} and not result.stderr and b'PRIVATE' not in result.stdout
    assert not (tmp_path/'source').exists()
