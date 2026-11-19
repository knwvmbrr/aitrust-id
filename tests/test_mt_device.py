"""Exact-method browser source bundle and adapter controls; no MT accuracy."""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from tools import mt_device
from tools import language_observations, authority_quotation

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mt_builder',ROOT/'scripts/build-mt-device.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


@pytest.mark.parametrize('kind,text',[
 ('urgency','Buy now.'),('urgency','The committee met today. Read the archived minutes.'),
 ('urgency','Leave now. Call emergency services immediately.'),
 ('urgency','Buy now. This is an offer. The page has terms.'),
 ('urgency','Read Cafe\u0301 details now. Install the viewer.'),
 ('authority','Experts agree.'),('authority','The example says "Experts agree".'),
 ('authority','Experts agree; the example is "https://example.invalid".'),
 ('authority','"Experts agree [1]"; studies show benefits.'),
 ('authority','Experts agree; see https://example.invalid.'),
 ('authority','Cafe\u0301: "Experts agree". Studies show benefits.')])
def test_adapter_preserves_full_original_record_and_identity(kind,text):
    record=json.loads(mt_device.inspect_mt_device(kind,text))
    expected=language_observations.observe('urgency',text,language='en') if kind=='urgency' else authority_quotation.observe(text,'en')[1]
    assert record['original']==json.loads(json.dumps(expected))
    assert record['method']==expected['method']
    assert record['subject_sha256']==expected['subject_sha256']
    assert record['tags']==[] and record['intent_established'] is False and record['independent_accuracy_evidence'] is False
    assert text not in json.dumps(record) and record['subject_text_included'] is False


@pytest.mark.parametrize('kind,text',[('bad','Experts agree.'),('urgency',''),('urgency','a'*8001),
 ('urgency','\x00'),('urgency','\ud800'),('authority','“Experts agree”'),('authority','"Experts agree'),
 ('authority','"" '*65),('authority','Experts agree; '*129)])
def test_original_refusal_and_input_limits(kind,text):
    with pytest.raises((ValueError,UnicodeError)):mt_device.inspect_mt_device(kind,text)


def test_optional_authority_failure_does_not_disable_urgency():
    script='''import importlib.abc,json,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='tools.authority_quotation':raise SyntaxError('inert unavailable authority')
sys.meta_path.insert(0,Block())
from tools.mt_device import inspect_mt_device
assert json.loads(inspect_mt_device('urgency','Buy now.'))['state']=='OBSERVATIONS'
try:inspect_mt_device('authority','Experts agree.')
except SyntaxError:pass
else:raise AssertionError('Authority failure was hidden')
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,timeout=5)
    assert result.returncode==0 and not result.stdout and not result.stderr


def test_exact_source_and_project_notice_bundle_is_deterministic(tmp_path):
    for path in builder.ALL_FILES:
        target=tmp_path/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
    first=builder.build(tmp_path);second=builder.build(tmp_path)
    assert first==second
    bundle=tmp_path/('site/public'+first['path']);raw=bundle.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==first['bundle_sha256'] and len(raw)==first['bundle_bytes']
    value=json.loads(raw)
    assert set(value['files'])==set(builder.ALL_FILES)
    for path,text in value['files'].items():assert text.encode()==(ROOT/path).read_bytes()
    notice=(tmp_path/'site/public/mt-device/notices.txt').read_bytes()
    for path in builder.LICENSE_FILES:assert (ROOT/path).read_bytes() in notice
    assert (ROOT/'NOTICE').read_bytes() in notice


def test_builder_refuses_symlink_and_oversized_source(tmp_path):
    link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError):builder.write(link/'target',b'never written')
    for path in builder.ALL_FILES:
        target=tmp_path/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
    (tmp_path/'tools/mt_device.py').write_bytes(b'x'*200001)
    with pytest.raises(ValueError):builder.build(tmp_path)
