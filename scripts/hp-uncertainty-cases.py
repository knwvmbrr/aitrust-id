#!/usr/bin/env python3
"""Authored synthetic cases, never independent labels or accuracy estimates."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol.normalization import normalize_nfc
from tools.language_observations import digest
from tools.hp_uncertainty_device import inspect_hp_uncertainty_device
CASES=[('present','It may work.'),('absent','This will work.'),('negation','It is not likely to work.'),
 ('calendar','May 12 is the date.'),('calendar_space','MAY\u202f12 is the date.'),('not_calendar_three_digits','May 123 is written.'),
 ('calendar_punctuation','May 12.5 is written.'),('calendar_word_suffix','May 12th is written.'),('calendar_underscore','May 12_ is written.'),
 ('upper','MIGHT work; perhaps not.'),('all_words','may might could possibly perhaps probably likely unlikely uncertain unclear approximately roughly estimated estimate'),
 ('whole_word','maybe mayhem estimates unlikelyhood'),('curly','“It might work.”'),('unicode_prefix','😀 Café. It could work.'),
 ('canonical_nfc','Cafe\u0301. It might work.'),('calendar_only','May 99'),('line_break','It MAY\n12 work.'),('multiple','may may MAY 1 maybe might'),
 ('quote_no_intent','The example says “It is likely.”'),('ascii_identifier','x_may may_2 2may'),('unicode_elsewhere','東京 — It perhaps works.'),
 ('nonascii_adjacent_left','émay work'),('nonascii_adjacent_right','mayé work'),('special_I','It mİght work.'),('special_long_s','An eſtimate.'),
 ('calendar_unknown_edge','May 12é'),('unknown_quote','「may」'),('blank',' '),('control_blank','\x1c\x1f'),('nul','may\0'),('oversize','x'*8001)]

def cases():
 rows=[]
 for name,text in CASES:
  n=normalize_nfc(text);annotation={'format':'language-context-annotations/v1','subject_sha256':digest(n),'uncertainty':[[0,len(n)]],'sources':[]}
  try:expected=json.loads(inspect_hp_uncertainty_device(text,json.dumps(annotation)))
  except (ValueError,UnicodeError):expected=None
  rows.append({'id':name,'text':text,'expected':expected})
 return rows
if __name__=='__main__':print(json.dumps(cases(),ensure_ascii=True,separators=(',',':')))
