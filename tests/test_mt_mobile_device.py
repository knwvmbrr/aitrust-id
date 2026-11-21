"""Synthetic lexical/identity/packaging controls, not independent MT accuracy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from tools import authority_mobile_quotation as mobile,authority_quotation as legacy
from tools.mt_mobile_device import inspect_mt_mobile_device
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mobile_mt_builder',ROOT/'scripts/build-mt-device.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

@pytest.mark.parametrize('text,quoted,marked,plain',[
 ('The example says “Experts agree [1]”.',1,0,0),
 ('Experts agree “source [1]”.',0,0,1),
 ('“Experts agree” [1].',1,0,0),
 ('“Experts agree [1]”; experts agree.',1,0,1),
 ('Experts agree [1]. “Doctors recommend”.',1,1,0),
 ('“Experts agree https://example.invalid/a” experts agree.',1,0,1),
 ('"Experts agree""Doctors recommend"',2,0,0),
 ('"He says "Experts agree" then leaves"',0,0,1),
 ("'Experts agree'",0,0,1),('ordinary wording',0,0,0),
])
def test_literal_placement_and_marker_locality(text,quoted,marked,plain):
    brief,details=mobile.observe(text,'en')
    assert (brief['quoted_phrase_count'],brief['outside_supported_quotes_with_marker'],brief['outside_supported_quotes_without_marker'])==(quoted,marked,plain)
    assert details['method']==mobile.METHOD and not details['parameters']['ascii_nesting_inferred']
    assert not details['intent_established'] and details['tags']==[]

@pytest.mark.parametrize('text',['“Experts agree','Experts agree”','“A “Experts agree””','"Experts agree”','“Experts agree"',
 '"Experts agree" “Doctors recommend”','\\“Experts agree”','“Experts agree\\”','\\"Experts agree"','«Experts agree»','`Experts agree`','"Experts agree'])
def test_detectable_unsupported_quote_syntax_refuses(text):
    with pytest.raises(ValueError):mobile.observe(text,'en')

def test_projection_preserves_frozen_nfc_codepoint_locations_and_raw_identity():
    text='PRIVATE_MOBILE_CANARY 😀 Cafe\u0301 “Experts agree [1]”.'
    record=json.loads(inspect_mt_mobile_device(text));o=record['original'];normalized=__import__('protocol.normalization',fromlist=['normalize_nfc']).normalize_nfc(text)
    assert record['raw_characters']==len(text)>record['subject_characters']==len(normalized)
    assert record['raw_bytes']==len(text.encode()) and record['raw_sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert o['subject_sha256']==record['subject_sha256']==hashlib.sha256(normalized.encode()).hexdigest()
    span=o['quoted_phrases'][0]['phrase_span'];assert normalized[slice(*span)]=='Experts agree'
    assert 'PRIVATE_MOBILE_CANARY' not in json.dumps(record)
    assert all(not record[k] for k in ['tag_asserted','truth_established','intent_established','independent_accuracy_evidence'])

@pytest.mark.parametrize('text',['Experts agree.','"Experts agree [1]"; doctors recommend.','According to research [2].','"He says "Experts agree" then leaves"'])
def test_ascii_observations_match_unchanged_existing_method(text):
    a,ad=legacy.observe(text,'en');b,bd=mobile.observe(text,'en')
    for name in ['state','outside_supported_quotes_without_marker','outside_supported_quotes_with_marker','quoted_phrase_count','supported_quote_count']:assert a[name]==b[name]
    for name in ['quote_spans','outside_markerless_phrases','outside_marked_phrases','quoted_phrases']:assert ad[name]==bd[name]

@pytest.mark.parametrize('text',['x'*8001,'\0','\ud800','“”'*65,'Experts agree '*100+'[1] '*100])
def test_input_quote_and_complete_record_limits_refuse(text):
    with pytest.raises((ValueError,UnicodeError)):inspect_mt_mobile_device(text)

def copied(root):
    for name in set(builder.ALL_FILES)|set(builder.MOBILE_ALL_FILES):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)

def test_mobile_build_is_deterministic_and_preserves_legacy_bundle(tmp_path):
    copied(tmp_path);old=builder.build(tmp_path);old_bytes=(tmp_path/('site/public'+old['path'])).read_bytes()
    first=builder.build_mobile(tmp_path);assert first==builder.build_mobile(tmp_path)
    assert (tmp_path/('site/public'+old['path'])).read_bytes()==old_bytes
    assert json.loads((tmp_path/'site/src/mt-device-manifest.json').read_bytes())==old
    bundle=json.loads((tmp_path/('site/public'+first['path'])).read_bytes())
    for name in ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt']:assert bundle['files'][name]==(ROOT/name).read_text()

@pytest.mark.parametrize('kind',['symlink','fifo','oversize','changed_source'])
def test_refused_optional_build_preserves_existing_outputs(tmp_path,monkeypatch,kind):
    copied(tmp_path);manifest=builder.build_mobile(tmp_path)
    before={p:p.read_bytes() for p in [tmp_path/'site/src/mt-mobile-device-manifest.json',tmp_path/'site/public/mt-mobile-device/notices.txt',tmp_path/('site/public'+manifest['path'])]}
    target=tmp_path/'tools/authority_mobile_quotation.py'
    if kind=='symlink':target.unlink();target.symlink_to(ROOT/'tools/authority_mobile_quotation.py')
    elif kind=='fifo':target.unlink();__import__('os').mkfifo(target)
    elif kind=='oversize':target.write_bytes(b'x'*(builder.MAX_SOURCE+1))
    else:
        original=builder.Capture.check;calls=0
        def changed(capture):
            nonlocal calls
            calls+=1
            if calls==2:target.write_text(target.read_text()+'\n# changed\n')
            return original(capture)
        monkeypatch.setattr(builder.Capture,'check',changed)
    with pytest.raises((ValueError,OSError)):builder.build_mobile(tmp_path)
    assert {p:p.read_bytes() for p in before}==before

def test_actual_cli_short_output_private_export_and_refusal(tmp_path):
    command=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/authority-mobile-quotation.py'),'--language','en'];text='PRIVATE_CLI_CANARY “Experts agree [1]”.'
    p=subprocess.run(command,input=text.encode(),capture_output=True,timeout=5);assert p.returncode==0;assert json.loads(p.stdout)['quoted_phrase_count']==1;assert b'PRIVATE_' not in p.stdout+p.stderr
    tmp_path.chmod(0o700);dest=tmp_path/'evidence';p=subprocess.run(command+['--details',str(dest)],input=text.encode(),capture_output=True,timeout=5);assert p.returncode==0
    saved=dest/'mobile-authority-quotation.json';before=saved.read_bytes();assert saved.stat().st_mode&0o777==0o600 and b'PRIVATE_' not in before
    p=subprocess.run(command+['--details',str(dest)],input=text.encode(),capture_output=True,timeout=5);assert p.returncode==2 and saved.read_bytes()==before
    p=subprocess.run(command,input=b'PRIVATE_CLI_CANARY "broken',capture_output=True,timeout=5);assert p.returncode==2;assert b'PRIVATE_' not in p.stdout+p.stderr
