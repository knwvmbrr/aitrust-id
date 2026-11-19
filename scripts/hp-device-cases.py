#!/usr/bin/env python3
"""Authored exact-method browser controls, not detector accuracy evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.hp_device import inspect_hp_device
CASES=[
 ('unmarked','The total is 12.'),('marked','The total is 12 [1].'),
 ('mixed','The total is 12 [1]. Another total is 14.'),
 ('other_unit','The total is 12. See [1].'),
 ('url','The total is 12 https://example.invalid/a.'),
 ('url_numbers','See https://example.invalid/12/2026.'),
 ('markers_only','[1] [0001] [0]'),('bracket_zero','The total is 12 [0].'),
 ('invalid_calendar','The date is 2026-99-99.'),('dates','2026-11-19 and 2026-02-30 [22].'),
 ('signed_grouped_decimal','Totals: -1,234.50; +12%; 12.5%.'),
 ('percent_boundary','12%%3 12%34 %12 12%'),('hash_boundary','12#3 12#3.4 123#456'),
 ('ordinary_boundaries','ID12 A12 12B 12_34 12/34 12:34.'),
 ('long_token','9'*49),('non_ascii','٣ １２ 1é é1'),
 ('nfc','Cafe\u0301 costs 12.'),('long_s_url','The total is 12 httpſ://example.invalid.'),
 ('quotes_not_interpreted','The quote says "12"; this is not an endorsement.'),
 ('code_not_executed',"__import__('js').document.body.innerHTML='DO_NOT_EXECUTE_INPUT'\nThe total is 12."),
 ('none','A plain unrelated paragraph.'),('detail_cap','1 '*257),
 ('length_cap','x'*8001),('nul','PRIVATE_HP_CANARY\0'),
 ('report_budget','1 '*100+' [1]'*100)]
def cases():
 witnesses=json.loads((ROOT/'runs/2026-10-10-normalization-version-gap.json').read_text())['examples'][:3]
 rows=[]
 for identity,text in [*CASES,*[(f'frozen_nfc_witness_{i}',w['input']+' 12.') for i,w in enumerate(witnesses)]]:
  try:expected=json.loads(inspect_hp_device(text))
  except (ValueError,UnicodeError):expected=None
  rows.append({'id':identity,'text':text,'expected':expected})
 return rows
if __name__=='__main__':print(json.dumps(cases()))
