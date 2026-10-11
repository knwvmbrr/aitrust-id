"""Contract/privacy/fault controls without installing the optional native SDK."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import pytest
from protocol.corpus import CorpusError
from tools import manifest_inspection as m

FIXTURES = Path(__file__).parent / 'fixtures/c2pa-inspection-2026'


def report():
    return {'active_manifest': 'test', 'manifests': {'test': {'title': 'PRIVATE_CANARY'}},
        'validation_results': {'activeManifest': {'success': [{'code': 'claimSignature.validated'},
            {'code': 'assertion.dataHash.match'}], 'informational': [{'code': 'signingCredential.ocsp.skipped'}],
            'failure': [{'code': 'signingCredential.untrusted'}]}}}


def test_summary_keeps_separate_axes_and_omits_metadata():
    d = m.summarize(report(), b'private image')
    assert d['asset_binding'] == d['claim_signature'] == 'matched'
    assert d['signer_trust'] == 'untrusted' and d['revocation'] == 'unknown_skipped'
    assert d['tags'] == [] and not d['content_truth_established'] and not d['author_identity_established']
    assert 'PRIVATE_CANARY' not in json.dumps(d)
    assert d['asset_sha256'] == hashlib.sha256(b'private image').hexdigest()


def test_binding_failure_does_not_erase_intact_signature():
    r = report(); r['validation_results']['activeManifest']['failure'].append({'code': 'assertion.dataHash.mismatch'})
    d = m.summarize(r, b'changed')
    assert d['asset_binding'] == 'mismatched' and d['claim_signature'] == 'matched'


def test_missing_positive_does_not_mean_pass():
    r = report(); r['validation_results']['activeManifest']['success'] = []
    d = m.summarize(r, b'a')
    assert d['asset_binding'] == d['claim_signature'] == 'unknown'


def test_explicit_revocation_failure_is_retained():
    r=report();r['validation_results']['activeManifest']['failure'].append({'code':'signingCredential.ocsp.revoked'})
    d=m.summarize(r,b'a')
    assert d['revocation']=='reported_revoked' and d['asset_binding']=='matched'


def test_positive_ocsp_row_does_not_silently_clear_unknown_revocation():
    r=report();r['validation_results']['activeManifest']['success'].append({'code':'signingCredential.ocsp.good'})
    d=m.summarize(r,b'a')
    assert d['revocation']=='unknown_skipped' and 'signingCredential.ocsp.good' in d['active_validation']['success']


@pytest.mark.parametrize('mutation', [
    lambda r: r.pop('validation_results'),
    lambda r: r['validation_results'].pop('activeManifest'),
    lambda r: r.update(active_manifest='missing'),
    lambda r: r.update(manifests=[]),
    lambda r: r['manifests']['test'].update(assertions={}),
    lambda r: r['validation_results'].update(activeManifest=[]),
    lambda r: r['validation_results']['activeManifest'].update(failure='bad'),
    lambda r: r['validation_results']['activeManifest'].update(success=[{'code': '<script>'}]),
    lambda r: r['validation_results']['activeManifest'].update(informational=[{}]),
    lambda r: r['validation_results'].update(ingredientDeltas={}),
    lambda r: r['validation_results'].update(ingredientDeltas=[{}]),
    lambda r: r['validation_results'].update(ingredientDeltas=[{'validationDeltas': {'failure': [None]}}]),
    lambda r: r['validation_results']['activeManifest'].update(unknown=[]),
])
def test_incomplete_or_unexpected_status_is_refused(mutation):
    r = report(); mutation(r)
    with pytest.raises(CorpusError): m.summarize(r, b'a')


def test_positive_ingredient_stays_in_its_scope():
    r = report(); r['validation_results']['activeManifest']['success'] = []
    r['validation_results']['ingredientDeltas'] = [{'ingredientAssertionURI': 'PRIVATE_CANARY',
        'validationDeltas': {'success': [{'code': 'assertion.dataHash.match'}]}}]
    d = m.summarize(r, b'a')
    assert d['asset_binding'] == 'unknown'
    assert d['ingredient_validation'][0]['success'] == ['assertion.dataHash.match']
    assert 'PRIVATE_CANARY' not in json.dumps(d)


@pytest.mark.parametrize('raw', [b'{}{}', b'{"a":1,"a":2}', b'{"x":NaN}', b'\xff', b'['])
def test_invalid_json_refused(raw):
    with pytest.raises(CorpusError): m.decode(raw)


def test_fixture_bytes_are_pinned_and_structurally_bounded():
    pins = json.loads((FIXTURES/'manifest.json').read_text())
    for name, expected in pins['files'].items():
        raw = (FIXTURES/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        m.png_container(raw)
    assert pins['fixture_only'] and pins['license'] == 'Apache-2.0'


@pytest.mark.parametrize('raw', [b'jpg', b'\x89PNG\r\n\x1a\n',
    (FIXTURES/'unsigned.png').read_bytes()[:-1], (FIXTURES/'unsigned.png').read_bytes()+b'junk',
    (FIXTURES/'unsigned.png').read_bytes()[:20]+b'corrupt'+(FIXTURES/'unsigned.png').read_bytes()[27:],
    b'\x89PNG\r\n\x1a\n'+b'\xff'*100])
def test_bad_container_is_unavailable_before_sdk(raw):
    with pytest.raises(CorpusError): m.png_container(raw)


def chunk(kind, data):
    return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))


@pytest.mark.parametrize('width,height,depth,color,interlace', [(0,1,8,2,0),(1,0,8,2,0),
    (100000,100000,8,2,0),(1,1,1,2,0),(1,1,8,5,0),(1,1,8,2,2)])
def test_dimension_and_encoding_bombs_refused(width,height,depth,color,interlace):
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,depth,color,0,0,interlace))+chunk(b'IDAT',b'x')+chunk(b'IEND',b'')
    with pytest.raises(CorpusError): m.png_container(raw)


def test_private_export_and_no_replacement(tmp_path):
    parent=tmp_path.resolve();parent.chmod(0o700);out=parent/'private.json'
    m.save_private(report(),out)
    assert out.stat().st_mode&0o777==0o600 and 'PRIVATE_CANARY' in out.read_text()
    with pytest.raises(CorpusError): m.save_private({},out)
    assert 'PRIVATE_CANARY' in out.read_text()


def test_public_export_directory_refused(tmp_path):
    parent=tmp_path.resolve();parent.chmod(0o755)
    with pytest.raises(CorpusError): m.save_private(report(),parent/'out.json')


def test_checkout_and_symlink_exports_refused(tmp_path):
    with pytest.raises(CorpusError): m.save_private(report(),m.ROOT/'private-do-not-create.json')
    parent=tmp_path.resolve();parent.chmod(0o700);link=parent/'link';link.symlink_to(parent, target_is_directory=True)
    with pytest.raises(CorpusError): m.save_private(report(),link/'out.json')


@pytest.mark.parametrize('failure', ['timeout','crash','bad_json','oversized','wrong_kind'])
def test_native_faults_refused_without_echo(tmp_path,monkeypatch,failure):
    monkeypatch.setattr(m,'checked_sdk',lambda:('/verified/native',{}))
    def runner(argv,**kwargs):
        assert argv[1:3]==['-I','-B'] and kwargs['timeout']==12
        assert not any(k in kwargs['env'] for k in ['LD_LIBRARY_PATH','DYLD_LIBRARY_PATH','PYTHONPATH','HOME'])
        assert Path(kwargs['cwd']).stat().st_mode&0o777==0o700
        if failure=='timeout':raise subprocess.TimeoutExpired(argv,12,stderr='PRIVATE_CANARY')
        if failure=='crash':return subprocess.CompletedProcess(argv,-11)
        kwargs['stdout'].write({'bad_json':b'PRIVATE_CANARY','oversized':b' '*(m.MAX_REPORT_BYTES+1),
            'wrong_kind':b'{"kind":"invented","report":{}}'}[failure])
        return subprocess.CompletedProcess(argv,0)
    with pytest.raises(CorpusError) as error:m.inspect(FIXTURES/'unsigned.png',runner=runner)
    assert 'PRIVATE_CANARY' not in str(error.value)


def test_not_found_never_means_safe(monkeypatch):
    monkeypatch.setattr(m,'checked_sdk',lambda:('/verified/native',{}))
    def runner(argv,**kwargs):
        kwargs['stdout'].write(b'{"kind":"not_found"}');return subprocess.CompletedProcess(argv,0)
    result,raw=m.inspect(FIXTURES/'unsigned.png',runner=runner)
    assert raw is None and result['state']=='NOT_FOUND' and result['tags']==[]
    assert not result['content_truth_established'] and 'does not establish origin or safety' in result['sharing_warning']


def test_settings_keep_verification_enabled_and_external_fetch_disabled():
    assert m.SETTINGS['verify']=={'verify_after_reading':True,'verify_trust':True,
        'verify_timestamp_trust':True,'remote_manifest_fetch':False,'ocsp_fetch':False}
    assert m.SETTINGS['core']['allowed_network_hosts']==[]
    assert m.SETTINGS['core']['decode_identity_assertions'] is False


@pytest.fixture
def fake_sdk(tmp_path,monkeypatch):
    import types
    package=tmp_path.resolve()/'site'/'c2pa';package.mkdir(parents=True)
    sources={}
    names=['c2pa/__init__.py','c2pa/build.py','c2pa/c2pa.py','c2pa/lib.py','c2pa/libs/libc2pa_c.so']
    for name in names:
        path=package.parent/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'reviewed fixture bytes')
        sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    distribution=types.SimpleNamespace(version='0.38.0',locate_file=lambda p:package.parent/p)
    pins={'schema_version':1,'package':'c2pa-python','package_version':'0.38.0','sdk_version':'0.91.0',
        'profiles':{'linux-x86_64':{'native':'c2pa/libs/libc2pa_c.so','sources':sources}}}
    file=tmp_path.resolve()/'pins.json';file.write_text(json.dumps(pins))
    monkeypatch.setattr(m,'PIN_FILE',file);monkeypatch.setattr(m.platform,'system',lambda:'Linux')
    monkeypatch.setattr(m.platform,'machine',lambda:'x86_64');monkeypatch.setattr(m.importlib.metadata,'distribution',lambda _:distribution)
    return package,file,pins,distribution


def test_sdk_checked_without_importing_native(fake_sdk):
    package,_,_,_=fake_sdk;native,pins=m.checked_sdk()
    assert native==str(package/'libs/libc2pa_c.so') and pins['sdk_version']=='0.91.0'


@pytest.mark.parametrize('filename',['__init__.py','build.py','c2pa.py','lib.py','libs/libc2pa_c.so'])
def test_altered_sdk_source_is_refused_before_import(fake_sdk,filename):
    package,_,_,_=fake_sdk;(package/filename).write_bytes(b'ALTERED_PRIVATE_CANARY')
    with pytest.raises(CorpusError) as error:m.checked_sdk()
    assert 'ALTERED_PRIVATE_CANARY' not in str(error.value)


def test_missing_or_symlink_native_refused(fake_sdk):
    package,_,_,_=fake_sdk;native=package/'libs/libc2pa_c.so';native.unlink()
    with pytest.raises(CorpusError):m.checked_sdk()
    native.symlink_to(package/'c2pa.py')
    with pytest.raises(CorpusError):m.checked_sdk()


def test_unreviewed_sdk_version_refused(fake_sdk):
    *_,distribution=fake_sdk;distribution.version='0.39.0'
    with pytest.raises(CorpusError):m.checked_sdk()


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(schema_version=2),lambda p:p.update(package_version='0.39.0'),
    lambda p:p.update(sdk_version='1.0.0'),lambda p:p.update(profiles=[]),
    lambda p:p['profiles']['linux-x86_64'].update(native='/tmp/evil.so'),
    lambda p:p['profiles']['linux-x86_64']['sources'].pop('c2pa/c2pa.py'),
    lambda p:p['profiles']['linux-x86_64']['sources'].update({'c2pa/lib.py':'unreviewed'}),
])
def test_unreviewed_pin_contract_refused(fake_sdk,mutation):
    _,file,pins,_=fake_sdk;mutation(pins);file.write_text(json.dumps(pins))
    with pytest.raises(CorpusError):m.checked_sdk()
