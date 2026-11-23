"""Source/projection and inert received-resource boundaries; no SDK or native UI."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import warnings
import zipfile
from unittest.mock import patch
import pytest
from tools import ios_runtime_obligations as m


@pytest.fixture
def private(tmp_path):
    base=tmp_path.resolve(); base.chmod(0o700); return base


@pytest.fixture(scope='module')
def actual(): return m.projection()


def test_actual_projection_complete_and_exact_source_bytes(actual):
    notices=actual['notices']; assert len(notices)==17 and len(m.MAPPING)==14
    b=m.web.Budget(m.ROOT)
    try:
        manifest=b.initialize(); original=m.web.expected(b,manifest)
        assert {m.MAPPING[n]:raw for n,raw in original.items()} == {n:raw for n,raw in notices.items() if n in m.MAPPING.values()}
    finally: b.close()
    assert notices['Notices/Project-NOTICE.txt']==(m.ROOT/'NOTICE').read_bytes()
    assert actual['license']==(m.ROOT/'LICENSE').read_bytes()
    assert notices['Notices/SourceOffers.txt']==m.SOURCE_OFFERS
    assert all(v is False for v in actual['report']['claims'].values())
    assert actual['report']['resources']['logical_read_bytes']<m.MAX_LOGICAL
    assert actual['report']['resources']['peak_held_fds']<=m.MAX_FDS


def test_source_pin_refuses_changed_notice_before_writes(private):
    original=m.evidence.Capture.read
    def read(c,path,limit,private=True):
        raw=original(c,path,limit,private=private)
        return raw+b'x' if Path(path).name=='NOTICE' else raw
    with patch.object(m.evidence.Capture,'read',read),pytest.raises(m.Unavailable):m.prepare(private/'out')
    assert not (private/'out').exists()


def test_closed_source_identity_rewalk_detects_change(private):
    file=private/'source';file.write_bytes(b'original')
    b=m.Budget()
    with m.evidence.Capture() as c:
        c.read(file,32,private=False);b.remember(c)
    file.write_bytes(b'changed!')
    with pytest.raises(m.Unavailable): b.recheck()


def test_prepare_private_exact_and_nooverwrite(private,actual):
    target=private/'out';report=m.prepare(target)
    assert report['pass'] and stat.S_IMODE(target.stat().st_mode)==0o700
    assert report['resources']['logical_operations']==actual['report']['resources']['logical_operations']+17
    assert report['resources']['logical_read_bytes']==actual['report']['resources']['logical_read_bytes']+sum(map(len,actual['notices'].values()))
    assert {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}==set(actual['notices'])
    for n,raw in actual['notices'].items():
        assert (target/n).read_bytes()==raw and stat.S_IMODE((target/n).stat().st_mode)==0o600
    with pytest.raises(m.Unavailable):m.prepare(target)
    assert (target/'Notices/Project-NOTICE.txt').read_bytes()==actual['notices']['Notices/Project-NOTICE.txt']


def test_prepare_disk_floor_before_creation(private):
    with patch.object(m.shutil,'disk_usage',return_value=type('Usage',(),{'free':m.DISK_FLOOR-1})()),pytest.raises(m.Unavailable):m.prepare(private/'out')
    assert not (private/'out').exists()


def test_late_git_refuses_and_preserves_private_outputs(private):
    original=m.evidence.verify_written; once=[]
    def written(fd,raw):
        original(fd,raw)
        if not once: once.append(True);(private/'.git').mkdir()
    with patch.object(m.evidence,'verify_written',written),pytest.raises(m.OutputUncertain):m.prepare(private/'out')
    assert (private/'out').is_dir() and any((private/'out').rglob('*'))


def test_output_close_error_is_uncertain_and_never_retried(private):
    original=m.evidence.Capture.close;calls=[];marker=[]
    def close(c):
        output=any(Path(*p).is_relative_to(private/'out') for p in c.directory_cache)
        original(c)
        if output:
            calls.append(True);marker.append(os.open(private/'marker',os.O_CREAT|os.O_RDWR,0o600));raise OSError('inert close fault')
    try:
        with patch.object(m.evidence.Capture,'close',close),pytest.raises(m.OutputUncertain):m.prepare(private/'out')
        assert len(calls)==1 and len(marker)==1;os.fstat(marker[0])
    finally:
        for fd in marker:os.close(fd)


def test_write_fault_retains_owned_bytes(private):
    with patch.object(m.evidence,'verify_written',side_effect=OSError('inert')),pytest.raises(m.OutputUncertain):m.prepare(private/'out')
    assert (private/'out').exists()


def test_existing_destination_link_preserved(private):
    sentinel=private/'keep';sentinel.mkdir(mode=0o700);(sentinel/'sentinel').write_bytes(b'keep')
    (private/'out').symlink_to(sentinel,target_is_directory=True)
    with pytest.raises(m.Unavailable):m.prepare(private/'out')
    assert (sentinel/'sentinel').read_bytes()==b'keep'


@pytest.fixture
def inert(monkeypatch):
    # Tiny INERT stand-ins isolate container/I/O controls. They are never called
    # native runtime qualification or authentic app evidence.
    notices={n:('inert:'+n).encode() for n in m.projection()['notices']}
    license_raw=b'inert license'; runtime={n:('inert:'+n).encode() for n in m.web.RUNTIME}
    def project(root,b):return notices,license_raw,{n:m.row(raw) for n,raw in runtime.items()}
    monkeypatch.setattr(m,'_project',project)
    wanted={**notices,'AppLicense.txt':license_raw,**{'Assets/runtime/'+n:raw for n,raw in runtime.items()}}
    return wanted


def directory_fixture(base,wanted):
    for n,raw in wanted.items():
        p=base/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)


def zip_fixture(path,wanted,mutation=None):
    roots=('Payload/Fixture.app/','Payload/Fixture.app/PlugIns/FixtureShare.appex/')
    members={prefix+n:raw for prefix in roots for n,raw in wanted.items()}
    if mutation=='missing': del members[roots[1]+'Notices/Project-NOTICE.txt']
    if mutation=='altered':members[roots[1]+'Notices/SourceOffers.txt']=b'changed'
    if mutation=='coherent':
        members[roots[0]+'Notices/SourceOffers.txt']=b'changed'
        members[roots[0]+'Notices/native-runtime-index.json']=b'{"changed":"consistent but not trusted"}'
    if mutation=='extra': members[roots[1]+'Notices/unreviewed.txt']=b'no'
    if mutation=='ratio':members['Payload/Fixture.app/unselected']=b'x'*600000
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for n,raw in members.items():z.writestr(n,raw)
            if mutation=='duplicate':z.writestr(next(iter(members)),b'other')
    if mutation in ('trailing','truncated'):
        raw=path.read_bytes();path.write_bytes(raw+b'trailing' if mutation=='trailing' else raw[:-10])
    if mutation=='symlink':
        raw=bytearray(path.read_bytes());at=raw.index(b'PK\x01\x02');struct.pack_into('<L',raw,at+38,0o120777<<16);path.write_bytes(raw)
    if mutation=='crc':
        raw=bytearray(path.read_bytes());at=raw.index(b'PK\x01\x02');struct.pack_into('<L',raw,at+16,1);path.write_bytes(raw)
    if mutation=='encrypted':
        raw=bytearray(path.read_bytes());at=raw.index(b'PK\x01\x02');struct.pack_into('<H',raw,at+8,1);path.write_bytes(raw)
    return path


def test_inert_selected_directories_positive_and_runtime_link_refusal(private,inert):
    app,share=private/'App',private/'Share'
    directory_fixture(app,inert);directory_fixture(share,inert)
    report=m.check_directories(app,share);assert report['received_files_verified']==46
    leaf=share/'Assets/runtime/pyodide.mjs';leaf.unlink();leaf.symlink_to(app/'Assets/runtime/pyodide.mjs')
    with pytest.raises(m.Unavailable):m.check_directories(app,share)


def test_inert_directories_extra_and_parent_link_refusal(private,inert):
    app,share=private/'App',private/'Share';directory_fixture(app,inert);directory_fixture(share,inert)
    (share/'Notices/extra').write_bytes(b'no')
    with pytest.raises(m.Unavailable):m.check_directories(app,share)
    (share/'Notices/extra').unlink();alias=private/'alias';alias.symlink_to(share,target_is_directory=True)
    with pytest.raises(m.Unavailable):m.check_directories(app,alias)


def test_inert_ipa_positive_and_missing_carrying_refusal(private,inert):
    archive=zip_fixture(private/'fixture.ipa',inert)
    report=m.check_ipa(archive);assert report['received_files_verified']==46 and not report['claims']['whole_ipa_inspected']
    zip_fixture(archive,inert,'missing')
    with pytest.raises(m.IncompleteCarrying) as error:m.check_ipa(archive)
    assert error.value.runtime_files_verified==10 and error.value.missing_required_resources==1


@pytest.mark.parametrize('mutation',['altered','coherent','extra','ratio','duplicate','trailing','truncated','symlink','crc','encrypted'])
def test_inert_ipa_refuses_changed_or_unreviewed_selected_structure(private,inert,mutation):
    archive=zip_fixture(private/'fixture.ipa',inert,mutation)
    with pytest.raises(m.Unavailable):m.check_ipa(archive)


def test_257_entries_refused_before_zipfile_allocation(private,inert):
    path=private/'many.ipa'
    with zipfile.ZipFile(path,'w') as z:
        for i in range(257):z.writestr('member'+str(i),b'x')
    with patch.object(m.zipfile,'ZipFile',side_effect=AssertionError('constructor must not run')),pytest.raises(m.Unavailable):m.check_ipa(path)


def test_central_range_refused_before_zipfile_allocation(private,inert):
    path=zip_fixture(private/'fixture.ipa',inert);raw=bytearray(path.read_bytes());at=raw.rfind(b'PK\x05\x06')
    struct.pack_into('<L',raw,at+12,m.MAX_CENTRAL+1);path.write_bytes(raw)
    with patch.object(m.zipfile,'ZipFile',side_effect=AssertionError('constructor must not run')),pytest.raises(m.Unavailable):m.check_ipa(path)


def test_global_deadline_inside_source_producer():
    original=m.web.expected
    def expired(source,manifest):
        with patch.object(m.time,'monotonic',return_value=10**15):source.tick()
        return original(source,manifest)
    with patch.object(m.web,'expected',expired),pytest.raises(m.Unavailable):m.projection()


def test_optional_projection_failure_does_not_disable_canonical_ps():
    with patch.object(m.web,'expected',side_effect=ValueError('inert missing helper data')),pytest.raises(m.Unavailable):m.projection()
    result=subprocess.run([sys.executable,'-I','-S','-B',str(m.ROOT/'scripts/check-ps.py'),'--worker'],input=b'An ordinary answer.',capture_output=True,timeout=5)
    assert result.returncode==0
    observed=json.loads(result.stdout)
    assert observed['state']=='NO_FINDING' and observed['independently_validated'] is False
    assert observed['text_included'] is False


def test_zip_constructor_failure_closes_only_owned_duplicate(private,inert):
    path=zip_fixture(private/'fixture.ipa',inert); duplicates=[]; original=os.dup
    def duplicate(fd):
        owned=original(fd); duplicates.append(owned); return owned
    with patch.object(m.os,'dup',duplicate),patch.object(m.zipfile,'ZipFile',side_effect=OSError('inert constructor')),pytest.raises(m.Unavailable):m.check_ipa(path)
    assert len(duplicates)==1
    with pytest.raises(OSError):os.fstat(duplicates[0])


def test_source_close_fault_does_not_retry_released_numeric_fd(private):
    original=m.web.Budget.close; markers=[]; calls=[]
    def close(source):
        original(source); calls.append(True)
        markers.append(os.open(private/'marker',os.O_CREAT|os.O_RDWR,0o600));raise OSError('inert close after release')
    try:
        with patch.object(m.web.Budget,'close',close),pytest.raises(m.Unavailable):m.projection()
        assert len(calls)==1;os.fstat(markers[0])
    finally:
        for fd in markers:os.close(fd)


def test_output_successor_preserved_and_never_reported_complete(private):
    original=m.os.fsync;replaced=[]
    def sync(fd):
        original(fd)
        leaf=private/'out/Notices/Project-NOTICE.txt'
        if not replaced and stat.S_ISDIR(os.fstat(fd).st_mode) and leaf.exists():
            leaf.rename(leaf.with_suffix('.owned-original'));leaf.write_bytes(b'private successor');replaced.append(True)
    with patch.object(m.os,'fsync',sync),pytest.raises(m.OutputUncertain):m.prepare(private/'out')
    assert replaced and (private/'out/Notices/Project-NOTICE.txt').read_bytes()==b'private successor'
    assert (private/'out/Notices/Project-NOTICE.owned-original').read_bytes()==(m.ROOT/'NOTICE').read_bytes()


def test_canonical_apple_icon_names_allow_at_and_tilde_without_opening(private,inert):
    path=zip_fixture(private/'fixture.ipa',inert)
    with zipfile.ZipFile(path,'a') as z:
        z.writestr('Payload/Fixture.app/AppIcon60x60@2x.png',b'inert icon')
        z.writestr('Payload/Fixture.app/AppIcon76x76@2x~ipad.png',b'inert icon')
    report=m.check_ipa(path);assert report['received_files_verified']==46
    for name in ('/absolute@2x','../outside~ipad','safe/../outside','a\\b','a//b','a/./b'):
        with pytest.raises(m.Unavailable):m.safe(name)


def test_prepare_output_verification_precharged_before_read(private,monkeypatch):
    notices={f'Notices/f{i:02}':b'fixed public text' for i in range(17)}
    def inert(root,b):return notices,b'license',{}
    monkeypatch.setattr(m,'_project',inert)
    observed=[];original=m.evidence.verify_written
    def verify(fd,raw):observed.append(len(raw));return original(fd,raw)
    with patch.object(m.evidence,'verify_written',verify):report=m.prepare(private/'normal')
    assert len(observed)==17 and report['resources']['logical_operations']==17
    assert report['resources']['logical_read_bytes']==sum(observed)==289
    def full(root,b):
        b.logical=m.MAX_LOGICAL-len(next(iter(notices.values())))+1
        return notices,b'license',{}
    monkeypatch.setattr(m,'_project',full)
    with patch.object(m.evidence,'verify_written') as reader,pytest.raises(m.OutputUncertain):m.prepare(private/'refused')
    reader.assert_not_called()


@pytest.mark.parametrize('when',['earlier_app_during_share','last_share_hash'])
def test_received_membership_late_insert_refused(private,inert,when):
    app,share=private/'App',private/'Share';directory_fixture(app,inert);directory_fixture(share,inert)
    original=m._hash;calls=[]
    def hashing(*args,**kwargs):
        result=original(*args,**kwargs);calls.append(True)
        if len(calls)==(24 if when=='earlier_app_during_share' else 46):
            ((app if when=='earlier_app_during_share' else share)/'Notices/unapproved').write_bytes(b'extra')
        return result
    with patch.object(m,'_hash',hashing),pytest.raises(m.Unavailable):m.check_directories(app,share)
    assert len(calls)>=24


def test_same_physical_target_cannot_fill_both_roles(private,inert):
    app,share=private/'App',private/'Share';directory_fixture(app,inert);directory_fixture(share,inert)
    # Portable inert identity collision; the original actual App/aPP Mac-FS
    # counter and its corrected replay are retained in the author evidence.
    with patch.object(m,'_target_identity',return_value=(1,2)),pytest.raises(m.Unavailable):m.check_directories(app,share)
