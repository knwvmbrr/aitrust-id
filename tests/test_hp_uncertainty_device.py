"""Bounded functional and source-capture controls; no independent accuracy labels."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
from tools import hp_uncertainty_device as device
from tools import language_observations as canonical
from protocol.normalization import normalize_nfc
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hp_uncertainty_builder',ROOT/'scripts/build-hp-uncertainty-device.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def annotation(text):
 n=normalize_nfc(text)
 return {'format':'language-context-annotations/v1','subject_sha256':canonical.digest(n),'uncertainty':[[0,len(n)]],'sources':[]}

def inspect(text,value=None):return json.loads(device.inspect_hp_uncertainty_device(text,json.dumps(annotation(text) if value is None else value)))

class Device(unittest.TestCase):
 def test_original_canonical_record_is_preserved_with_explicit_context(self):
  for text in ['It may work.','This will work.','It is not likely.','May 12','😀 Café. It could work.','Cafe\u0301. “It might work.”']:
   record=inspect(text);self.assertEqual(record['original'],canonical.observe('hedge',text,'en',context=annotation(text)))
   self.assertEqual(record['annotation'],annotation(text));self.assertFalse(record['tag_asserted']);self.assertEqual(record['tags'],[])
 def test_annotation_missing_partial_forged_boolean_extra_or_duplicate_refuses(self):
  text='It may work.'
  values=[None,{},dict(annotation(text),subject_sha256='0'*64),dict(annotation(text),uncertainty=[[0,1]]),dict(annotation(text),uncertainty=[[False,len(text)]]),dict(annotation(text),sources=[[0,1]]),dict(annotation(text),private_input='PRIVATE_CANARY')]
  for value in values:
   with self.assertRaises(ValueError):device.inspect_hp_uncertainty_device(text,json.dumps(value))
  raw=json.dumps(annotation(text));raw=raw[:-1]+',"sources":[]}'
  with self.assertRaises(ValueError):device.inspect_hp_uncertainty_device(text,raw)
 def test_raw_and_frozen_nfc_bindings_remain_distinct(self):
  a,b=inspect('Cafe\u0301. It may work.'),inspect('Café. It may work.')
  self.assertNotEqual(a['raw_sha256'],b['raw_sha256']);self.assertEqual(a['subject_sha256'],b['subject_sha256']);self.assertEqual(a['original'],b['original'])
 def test_calendar_exclusion_and_nonnegation_are_literal(self):
  self.assertEqual(inspect('May 12')['counts'],{'hedge_words':0,'calendar_candidates':1})
  self.assertEqual(inspect('May 123')['counts']['hedge_words'],1)
  self.assertEqual(inspect('not likely')['counts']['hedge_words'],1)
  self.assertFalse(inspect('not likely')['original']['measurements']['negation_interpreted'])
 def test_ambiguous_unicode_boundaries_refuse_instead_of_zero(self):
  for text in ['émay','mayé','mİght','eſtimate','May 12é','「may」']:
   with self.assertRaises(ValueError):inspect(text)
  self.assertEqual(inspect('東京 — It may work.')['counts']['hedge_words'],1)
 def test_blank_nul_surrogate_and_overlimits_refuse_without_clipping(self):
  for text in ['',' ','\x1c\x1f','may\0','\ud800','x'*8001]:
   with self.assertRaises((ValueError,UnicodeError)):inspect(text)
 def test_no_original_words_or_annotation_text_are_exported(self):
  record=inspect('PRIVATE_INPUT_CANARY may work.');raw=json.dumps(record)
  self.assertNotIn('PRIVATE_INPUT_CANARY',raw);self.assertFalse(record['input_persisted']);self.assertFalse(record['subject_text_included'])
 def test_source_bindings_are_exact_and_no_sibling_method_import_required(self):
  record=inspect('may')
  self.assertEqual(record['source_sha256'],{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in device.SOURCES})
  self.assertNotIn('tools/hp_device.py',record['source_sha256']);self.assertNotIn('tools/mt_device.py',record['source_sha256'])

class Packaging(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
  for name in builder.ALL_FILES:
   dst=self.root/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((ROOT/name).read_bytes())
  self.old=self.root/'site/src/hp-uncertainty-manifest.json';self.old.parent.mkdir(parents=True);self.old.write_bytes(b'OLD_OUTPUT')
 def tearDown(self):self.temp.cleanup()
 def unchanged(self):self.assertEqual(self.old.read_bytes(),b'OLD_OUTPUT')
 def test_deterministic_source_and_notice_payloads(self):
  a=builder.build(self.root);b=builder.build(self.root);self.assertEqual(a,b)
  m=a['checks']['hedge'];payload=json.loads((self.root/'site/public'/m['path'].lstrip('/')).read_bytes())
  self.assertEqual(m['sources'],{p:hashlib.sha256(v.encode()).hexdigest() for p,v in payload['files'].items()})
  for name in builder.LICENSE_FILES:self.assertEqual(payload['files'][name],(ROOT/name).read_text())
 def test_source_symlink_refuses_before_any_output_change(self):
  p=self.root/'NOTICE';p.unlink();p.symlink_to(ROOT/'NOTICE')
  with self.assertRaises((ValueError,OSError)):builder.build(self.root)
  self.unchanged()
 def test_parent_symlink_refuses_before_any_output_change(self):
  tools=self.root/'tools';tools.rename(self.root/'original-tools');tools.symlink_to(self.root/'original-tools',target_is_directory=True)
  with self.assertRaises((ValueError,OSError)):builder.build(self.root)
  self.unchanged()
 def test_fifo_refuses_without_blocking_or_changing_outputs(self):
  p=self.root/'NOTICE';p.unlink();os.mkfifo(p)
  with self.assertRaises((ValueError,OSError)):builder.build(self.root)
  self.unchanged()
 def test_oversize_source_refuses_before_output_change(self):
  (self.root/'NOTICE').write_bytes(b'x'*(builder.MAX_SOURCE+1))
  with self.assertRaises(ValueError):builder.build(self.root)
  self.unchanged()
 def test_source_drift_refuses_before_publication(self):
  original=builder.Capture.read;count=0
  def read(capture,name):
   nonlocal count
   raw=original(capture,name);count+=1
   if count==len(builder.ALL_FILES):(self.root/'NOTICE').write_text('changed')
   return raw
  with mock.patch.object(builder.Capture,'read',read):
   with self.assertRaises(ValueError):builder.build(self.root)
  self.unchanged()
 def test_normalizer_drift_refuses_without_overwrite(self):
  (self.root/'protocol/normalization.mjs').write_text('changed')
  with self.assertRaises(ValueError):builder.build(self.root)
  self.unchanged()
 def test_unknown_hedge_lexicon_refuses_without_overwrite(self):
  p=self.root/'tools/language_observations.py';p.write_text(p.read_text().replace('may|might','maybe|might'))
  with self.assertRaises(ValueError):builder.build(self.root)
  self.unchanged()

if __name__=='__main__':unittest.main()
