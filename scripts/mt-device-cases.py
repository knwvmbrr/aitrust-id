#!/usr/bin/env python3
"""Authored exact-method browser parity inputs, never accuracy evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.mt_device import inspect_mt_device

CASES=[('urgency_positive','urgency','Buy now.'),('urgency_overlapping_supported_spans','urgency','Act fast.'),
 ('urgency_legitimate','urgency','Leave now. Call emergency services immediately.'),
 ('urgency_other_unit','urgency','The committee met today. Read the archived minutes.'),
 ('urgency_density_limit','urgency','Buy now. This is an offer. The page has terms.'),
 ('urgency_exact_evidence','urgency','Install the viewer. Buy the pass now. The workshop is today.'),
 ('urgency_nfc','urgency','Read Cafe\u0301 details now. Install the viewer.'),
 ('urgency_quote_not_interpreted','urgency','Act now! This is an example, not advice.'),
 ('urgency_negative','urgency','Read the archive.'),
 ('authority_positive','authority','Experts agree.'),
 ('authority_quoted','authority','The example says "Experts agree".'),
 ('authority_quoted_url','authority','Experts agree; the example is "https://example.invalid".'),
 ('authority_marked','authority','Experts agree; see https://example.invalid.'),
 ('authority_contexts','authority','"Experts agree [1]"; studies show benefits.'),
 ('authority_two_quotes','authority','"Experts agree" and "https://example.invalid".'),
 ('authority_nfc','authority','Cafe\u0301: "Experts agree". Studies show benefits.'),
 ('authority_negative','authority','This is an ordinary example.'),
 ('authority_curly_refusal','authority','“Experts agree”'),
 ('authority_unmatched_refusal','authority','"Experts agree'),
 ('authority_escaped_refusal','authority','"Experts \\"agree"'),
 ('authority_backtick_refusal','authority','`Experts agree`'),
 ('authority_quote_limit','authority','"" '*65),
 ('authority_phrase_limit','authority','Experts agree; '*129),
 ('authority_marker_limit','authority','[1] '*257),
 ('urgency_limit','urgency','x'*8001),
 ('urgency_nul','urgency','PRIVATE_MT_CANARY\0'),
 ('no_input_execution','urgency',"__import__('js').document.body.innerHTML='DO_NOT_EXECUTE_INPUT'\nBuy now.")]

def cases():
 rows=[]
 witnesses=json.loads((ROOT/'runs/2026-10-10-normalization-version-gap.json').read_text())['examples'][:3]
 selected=[*CASES,*[(f'frozen_nfc_witness_{i}', 'urgency',w['input']+' Buy now.') for i,w in enumerate(witnesses)]]
 for identity,kind,text in selected:
  try:expected=json.loads(inspect_mt_device(kind,text))
  except (ValueError,UnicodeError):expected=None
  rows.append({'id':identity,'kind':kind,'text':text,'expected':expected})
 return rows

if __name__=='__main__':print(json.dumps(cases()))
