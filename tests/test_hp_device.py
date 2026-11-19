"""HP literal-method parity and safe source build; never HP accuracy evidence."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from tools import hp_device as hp
from tools import quantitative_observations as canonical
from protocol.normalization import normalize_nfc
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hp_builder',ROOT/'scripts/build-hp-device.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
CASES=['There are 12 items.','There are 12 items [1]. Another has 25.',
 'Rates: 1,250.50 and -12.5%. Date: 2026-99-88.',
 'Only [123] https://example.invalid/123.','ID123 abc-123 123@example.com @123 123@456 192.0.2.1 12,34.',
 'Identifiers: 12#3 2026-10-11#release 12%quota 12%%3 12%34 %12. Total:25.',
 'Cafe\u0301: 12.5%.','é123 表456 78\u0301 90\u00a0',
 '"There are 12 items" is an example.','No numeric detail here.']

@pytest.mark.parametrize('text',CASES)
def test_exact_original_record_and_both_raw_normalized_identities(text):
 record=json.loads(hp.inspect_hp_device(text));assert record['original']==canonical.observe(text,'en')[1]
 raw=text.encode();normalized=normalize_nfc(text)
 assert record['raw_sha256']==hashlib.sha256(raw).hexdigest() and record['raw_characters']==len(text) and record['raw_bytes']==len(raw)
 assert record['subject_sha256']==hashlib.sha256(normalized.encode()).hexdigest() and record['subject_characters']==len(normalized)
 assert text not in json.dumps(record) and record['tags']==[] and record['tag_asserted'] is False

@pytest.mark.parametrize('text',['',' ','\0','\ud800','x'*8001,' '.join('12' for _ in range(257)),None,3])
def test_refusal_not_quiet_result(text):
 with pytest.raises((ValueError,UnicodeError)):hp.inspect_hp_device(text)

def test_complete_record_over_existing_private_budget_is_unavailable_not_clipped():
 text=' '.join('12' for _ in range(100))+' '+(' [1]'*100)
 assert len(canonical.observe(text,'en')[1]['details'])==100
 with pytest.raises(ValueError):hp.inspect_hp_device(text)

def test_no_other_tag_pipeline_is_imported_or_needed():
 script='''import importlib.abc,json,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path=None,target=None):
  if name in ('tools.mt_device','tools.mt_workflow','tools.authority_quotation','tools.choice_framing'):raise ImportError('Blocked unrelated runtime')
sys.meta_path.insert(0,Block())
from tools.hp_device import inspect_hp_device
assert json.loads(inspect_hp_device('There are 12 items.'))['counts']['supported_detail_count']==1
'''
 result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,timeout=5)
 assert result.returncode==0 and not result.stdout and not result.stderr

def tree(tmp_path):
 root=tmp_path/'checkout';root.mkdir()
 for name in builder.ALL_FILES:
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
 builder.build(root);return root

def outputs(root):return {str(p.relative_to(root)):p.read_bytes() for p in (root/'site').rglob('*') if p.is_file()}

def test_builder_exact_deterministic_sources_and_notice_attribution(tmp_path):
 root=tree(tmp_path);a=builder.build(root);b=builder.build(root);assert a==b
 raw=(root/('site/public'+a['path'])).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['bundle_sha256'] and len(raw)==a['bundle_bytes']
 files=json.loads(raw)['files'];assert set(files)==set(builder.ALL_FILES)
 for name,value in files.items():assert value.encode()==(ROOT/name).read_bytes()
 notice=(root/'site/public/hp-device/notices.txt').read_bytes()
 for name in builder.LICENSE_FILES:assert (ROOT/name).read_bytes() in notice

@pytest.mark.parametrize('mode',['symlink','parent_symlink','root_symlink','fifo','oversize','hardlink','normalizer_drift'])
def test_builder_refused_inputs_preserve_outputs_and_never_copy_private_canary(tmp_path,mode):
 root=tree(tmp_path);before=outputs(root);private=tmp_path/'private.txt';private.write_text('SYNTHETIC_PRIVATE_CANARY');source=root/'NOTICE';selected=root
 if mode=='symlink':source.unlink();source.symlink_to(private)
 elif mode=='parent_symlink':
  (root/'protocol').rename(tmp_path/'outside-protocol');(root/'protocol').symlink_to(tmp_path/'outside-protocol',target_is_directory=True)
 elif mode=='root_symlink':selected=tmp_path/'root-link';selected.symlink_to(root,target_is_directory=True)
 elif mode=='fifo':source.unlink();os.mkfifo(source)
 elif mode=='oversize':source.write_bytes(b'x'*200001)
 elif mode=='hardlink':source.unlink();os.link(private,source)
 else:(root/'protocol/normalization.mjs').write_text('Invalid generated source')
 with pytest.raises((ValueError,OSError)):builder.build(selected)
 assert outputs(root)==before and not any(b'SYNTHETIC_PRIVATE_CANARY' in raw for raw in outputs(root).values())

@pytest.mark.parametrize('mode',['file_change','file_replace','parent_replace','root_replace','after_stage'])
def test_all_captured_identities_rechecked_before_any_public_replacement(tmp_path,monkeypatch,mode):
 root=tree(tmp_path);before=outputs(root);original_read=builder.Capture.read;trigger=False
 def mutate():
  if mode in ('file_change','after_stage'):(root/'NOTICE').write_text('SYNTHETIC_PRIVATE_CANARY')
  elif mode=='file_replace':(root/'NOTICE').unlink();(root/'NOTICE').write_text('SYNTHETIC_PRIVATE_CANARY')
  elif mode=='parent_replace':(root/'protocol').rename(tmp_path/'original-protocol');shutil.copytree(tmp_path/'original-protocol',root/'protocol')
  else:root.rename(tmp_path/'moved-root');root.symlink_to(tmp_path/'moved-root',target_is_directory=True)
 if mode=='after_stage':
  original=builder.Capture.check
  def check(self):
   nonlocal trigger
   if not trigger and any((root/'site').rglob('.hp-build-*')):trigger=True;mutate()
   return original(self)
  monkeypatch.setattr(builder.Capture,'check',check)
 else:
  def read(self,name):
   nonlocal trigger
   raw=original_read(self,name)
   if name==builder.ALL_FILES[-1] and not trigger:trigger=True;mutate()
   return raw
  monkeypatch.setattr(builder.Capture,'read',read)
 with pytest.raises((ValueError,OSError)):builder.build(root)
 destination=tmp_path/'moved-root' if mode=='root_replace' else root
 assert trigger and outputs(destination)==before and not list((destination/'site').rglob('.hp-build-*'))

def test_fdopen_failure_closes_owned_descriptor_once_without_output_changes(tmp_path,monkeypatch):
 root=tree(tmp_path);before=outputs(root);opened=[];closed=[];original=os.close
 def fdopen(fd,*args,**kwargs):assert kwargs['closefd'] is False;opened.append(fd);raise OSError('SYNTHETIC_PRIVATE_CANARY')
 def close(fd):closed.append(fd);return original(fd)
 monkeypatch.setattr(os,'fdopen',fdopen);monkeypatch.setattr(os,'close',close)
 with pytest.raises(OSError):builder.build(root)
 assert len(opened)==1 and closed.count(opened[0])==1 and outputs(root)==before
 with pytest.raises(OSError):os.fstat(opened[0])

def test_postpublication_replace_failure_reports_output_uncertainty(tmp_path,monkeypatch):
 root=tree(tmp_path);original=os.replace
 def replace(*args,**kwargs):original(*args,**kwargs);raise OSError('SYNTHETIC_PRIVATE_CANARY')
 monkeypatch.setattr(os,'replace',replace)
 with pytest.raises(builder.OutputCommitUncertain) as caught:builder.build(root)
 assert caught.value.output_may_exist is True and str(caught.value)=='HP build output may exist; inspect before retrying.'
