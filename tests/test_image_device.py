"""Exact canonical projection and bounded static publisher controls; synthetic only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
b=load('image_static_builder',ROOT/'scripts/build-image-metadata-device.py')
c=load('image_synthetic_cases',ROOT/'scripts/image-metadata-device-cases.py')
COHORT=ROOT/b.COHORT
PROJECTION=json.loads((COHORT/'projection.json').read_text())

def test_exact_original_sources_and_every_node_inventory():
    for name,digest in b.APPROVED_SOURCE.items():assert b.sha((COHORT/name).read_bytes())==digest
    assert b.sha((COHORT/'source.json').read_bytes())==b.COHORT_MANIFEST_SHA
    assert b.sha((COHORT/'projection.json').read_bytes())==b.PROJECTION_MANIFEST_SHA
    for kind in ['png','jpeg']:
        raw=b.project((COHORT/f'tools/{kind}_metadata.py').read_bytes(),PROJECTION['modules'][kind],kind)
        assert b.sha(raw)==PROJECTION['modules'][kind]['projection_sha256']
        for forbidden in ['import os','import selectors','import subprocess','def inspect_file','def worker_record','Path(']:assert forbidden not in raw.decode()

def test_full_native_and_projected_records_equal_all_fixed_cases():
    projected={}
    for kind in ['png','jpeg']:
        namespace={};exec(compile(b.project((COHORT/f'tools/{kind}_metadata.py').read_bytes(),PROJECTION['modules'][kind],kind),f'<fixed-{kind}-projection>','exec'),namespace);projected[kind]=namespace
    import base64
    rows=c.cases();assert len(rows)==16
    for row in rows:
        raw=base64.b64decode(row['bytes_base64']);m=projected[row['kind']]
        try:r=m['inspect_bytes'](raw)
        except m['ImageError']as error:r=m['unavailable'](error.reason,raw)
        assert m['validate_record'](r,raw)==row['expected']
        assert c.CANARY.decode()not in json.dumps(r)
        assert r['tags']==[]and r['AI_origin']=='unknown'and r['watermark_verified']is False

def test_changed_source_and_coherent_changed_projection_refuse():
    raw=(COHORT/'tools/png_metadata.py').read_bytes();spec=PROJECTION['modules']['png']
    with pytest.raises(b.BuildError):b.project(raw+b'\nEXECUTE_NEW_CODE=True\n',spec,'png')
    q=copy.deepcopy(spec);q['nodes'][1]['include']=not q['nodes'][1]['include']
    with pytest.raises(b.BuildError):b.project(raw,q,'png')
    changed=raw.replace(b'MAX_PIXELS=4_000_000',b'MAX_PIXELS=9_000_000')
    q=copy.deepcopy(spec);q['source_sha256']=b.sha(changed)
    # Even a caller-coherently rebound source hash cannot change the fixed node/spec gate.
    with patch.dict(b.APPROVED_SOURCE,{'tools/png_metadata.py':b.sha(changed)}):
        with pytest.raises(b.BuildError):b.project(changed,q,'png')

def test_capture_refuses_oversize_before_read_links_FIFO_and_parent_links(tmp_path):
    (tmp_path/'large').write_bytes(b'x'*200001);(tmp_path/'small').write_bytes(b'abc');(tmp_path/'link').symlink_to(tmp_path/'small');os.mkfifo(tmp_path/'fifo')
    with b.Capture(tmp_path)as capture:
        with patch.object(b.os,'read',side_effect=AssertionError('read before size gate')):
            with pytest.raises(b.BuildError):capture.read('large')
        for name in ['link','fifo']:
            with pytest.raises((b.BuildError,OSError)):capture.read(name)
    directory=tmp_path/'directory';directory.mkdir();(tmp_path/'parentlink').symlink_to(directory,target_is_directory=True)
    with pytest.raises(OSError):b.Capture(tmp_path/'parentlink')

def test_capture_identity_drift_refuses(tmp_path):
    file=tmp_path/'source';file.write_bytes(b'original')
    with b.Capture(tmp_path)as capture:
        assert capture.read('source')==b'original';file.write_bytes(b'modified')
        with pytest.raises(b.BuildError):capture.check()

def setup_build(tmp_path):
    root=tmp_path/'repo';root.mkdir();shutil.copytree(COHORT,root/b.COHORT)
    for name in b.BUILD_FILES:
        file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes((ROOT/name).read_bytes())
    cache=tmp_path/'runtime';cache.mkdir();members={}
    for name in b.RUNTIME_FILES:
        raw=('INERT_NOT_EXECUTED_'+name).encode();(cache/name).write_bytes(raw);members[name]={'bytes':len(raw),'sha256':b.sha(raw)}
    policy={'pyodide_version':'314.0.7','python_version':'3.14.2','runtime_members':members};file=root/b.RUNTIME_POLICY;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(policy))
    output=tmp_path/'output'
    return root,cache,output,b.sha(file.read_bytes())

def test_static_publication_deterministic_and_bad_input_preserves_previous(tmp_path):
    root,cache,output,policy=setup_build(tmp_path)
    with patch.object(b,'RUNTIME_POLICY_SHA',policy):
        manifest=b.build(cache,output,root);before={p.name:p.read_bytes()for p in output.iterdir()};assert len(before)==4
        assert b.build(cache,output,root)==manifest;assert {p.name:p.read_bytes()for p in output.iterdir()}==before
        (cache/'pyodide.mjs').write_bytes(b'changed')
        with pytest.raises(b.BuildError):b.build(cache,output,root)
        assert {p.name:p.read_bytes()for p in output.iterdir()}==before

def test_publication_refuses_unowned_namespace_and_symlink(tmp_path):
    root,cache,output,policy=setup_build(tmp_path);output.mkdir();(output/'unknown').write_bytes(b'previous')
    with patch.object(b,'RUNTIME_POLICY_SHA',policy):
        with pytest.raises(b.BuildError):b.build(cache,output,root)
    assert (output/'unknown').read_bytes()==b'previous'
    (output/'unknown').unlink();(output/'manifest.json').symlink_to(root/b.COHORT/'source.json')
    with patch.object(b,'RUNTIME_POLICY_SHA',policy):
        with pytest.raises(b.BuildError):b.build(cache,output,root)
    assert (output/'manifest.json').is_symlink()

@pytest.mark.parametrize('target',['source','runtime'])
def test_outer_close_after_publication_is_uncertain_and_never_retries_fd(tmp_path,target):
    root,cache,output,policy=setup_build(tmp_path);real=b.Capture.close;fired=[];markers=[]
    def close(capture):
        match=target=='source'and str(root/'scripts/build-image-metadata-device.py')in [str(root/name)for name in capture.values]or target=='runtime'and 'pyodide.mjs'in capture.values
        old=list(capture.fds);real(capture)
        if match and not fired:
            fired.append(True);fd=os.open(tmp_path/'marker',os.O_CREAT|os.O_RDWR,0o600);markers.append(fd);raise OSError('synthetic after-close')
    try:
        with patch.object(b,'RUNTIME_POLICY_SHA',policy),patch.object(b.Capture,'close',close):
            with pytest.raises(b.BuildUncertain):b.build(cache,output,root)
        assert len(list(output.iterdir()))==4 and len(fired)==1
        assert os.fstat(markers[0]).st_size==0
    finally:
        for fd in markers:os.close(fd)

def test_projected_pixel_metadata_and_inflate_bounds_match_canonical():
    import struct,zlib
    for kind in ['png','jpeg']:
        ns={};exec(compile(b.project((COHORT/f'tools/{kind}_metadata.py').read_bytes(),PROJECTION['modules'][kind],kind),'<pinned-projection>','exec'),ns)
        if kind=='png':
            huge_header=b'\x89PNG\r\n\x1a\n'+c.chunk(b'IHDR',struct.pack('>IIBBBBB',4000001,1,8,2,0,0,0))+c.chunk(b'IDAT',zlib.compress(b'\0x'))+c.chunk(b'IEND',b'')
            cases=[(huge_header,'input_limit'),(c.png([(b'zTXt',b'Comment\0\0'+zlib.compress(b'x'*65537))]),'metadata_limit'),(c.png(compressed=zlib.compress(b'x'*1000000)),'corrupt_image_data')]
        else:
            raw=bytearray(c.jpeg());at=raw.index(b'\xff\xc0')+4;raw[at+1:at+5]=b'\xff'*4
            cases=[(bytes(raw),'input_limit'),(c.jpeg([(0xFE,b'')]*129),'metadata_limit')]
        canonical=c.module(kind)
        for raw,reason in cases:
            for parser,error in [(ns['inspect_bytes'],ns['ImageError']),(canonical.inspect_bytes,canonical.ImageError)]:
                with pytest.raises(error)as caught:parser(raw)
                assert caught.value.reason==reason

def test_fixed_worker_python_wrapper_compiles_without_image_execution():
    import re
    text=(ROOT/'site/src/image-metadata-worker.mjs').read_text()
    match=re.search(r'py[.]runPython\(`([^`]+)`\)',text);assert match
    wrapper=match.group(1).replace('\\n','\n')
    compile(wrapper,'<fixed-image-wrapper>','exec')
    assert "bytes(buffer)"in wrapper and 'validate_record(r,raw)'in wrapper
