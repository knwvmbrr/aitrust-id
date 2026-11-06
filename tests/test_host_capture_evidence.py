"""A committed pass cannot outlive its executed source or gain human acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('host_evidence',ROOT/'scripts/verify-host-capture-evidence.py')
evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)
class HostEvidence(unittest.TestCase):
 def row(self):return json.loads((ROOT/'runs/2026-11-06-host-capture-linux.json').read_bytes())
 def test_current_actual_os_evidence(self):self.assertTrue(evidence.verify(self.row(),'linux'))
 def test_missing_stale_or_weakened_evidence_refused(self):
  variants=[]
  for field in ('non_root','source_unchanged','actual_foreground_pty','isolated_network_namespace'):
   row=self.row();row[field]=False;variants.append(row)
  for field in ('independent_accuracy_evidence','human_acceptance_complete','company_collection_enabled'):
   row=self.row();row[field]=True;variants.append(row)
  row=self.row();row['sources']['tools/host_capture.py']='0'*64;variants.append(row)
  row=self.row();row['cases']=row['cases'][:-1];variants.append(row)
  row=self.row();row['captured_at']='2999-01-01T00:00:00+00:00';variants.append(row)
  row=self.row();row['test_count']=True;variants.append(row)
  row=self.row();row['skipped']=1;variants.append(row)
  for row in variants:
   with self.subTest(row=row),self.assertRaises(ValueError):evidence.verify(row,'linux')
if __name__=='__main__':unittest.main()
