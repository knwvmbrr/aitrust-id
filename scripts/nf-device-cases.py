#!/usr/bin/env python3
"""Authored canonical comparison cases, not independent accuracy examples."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.nf_device import inspect_nf_device

CASES=[
 ('ties_even',' '.join(['x']*63+['a'+str(i) for i in range(127)]),' '.join(['x']*127+['a'+str(i) for i in range(124)]+['b'+str(i) for i in range(131)]),'cosine'),
 ('literal_same','Water is safe.','Water is safe.','literal'),
 ('negation_exact','Water is safe.','Water is not safe.','literal'),
 ('negation_overlap','Water is safe.','Water is not safe.','cosine'),
 ('canonical_unicode','e\u0301😀','pré é😀 fin','literal'),
 ('emoji','🙂','🙂🙂','literal'),('case','a','A','literal'),
 ('many','a','a '*20,'literal'),('none','a','nothing here','literal'),
 ('lines','red green\nblue','red green\nblue','cosine'),
 ('punctuation','red, green!','red green','cosine'),
 ('unsupported_source_line','Water is safe.','é\nWater is safe.','cosine'),
 ('unicode_overlap','é','é','cosine'),('no_supported_line','a','é','cosine'),
 ('no_tokens','---','abc','cosine'),('over_token','a '*513,'a','cosine'),
 ('too_many_claims','a\n'*33,'a','cosine'),
 ('line_breaks','a\r\nb\rc\vd\fe\x1cf\x1dg\x1eh\x85i\u2028j\u2029k','a\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk','cosine'),
 ('trim','\tred \r\n blue\n','red\nblue\n','cosine'),
 ('same_line_ties','red green','red green\nred green\nred green','cosine'),
 ('empty_claim','','a','literal'),('empty_source','a','','literal'),
 ('bad_claim','a\0','a','literal'),('bad_source','a','a\0','literal'),
 ('limit_claim','x'*2000,'x'*2000,'literal'),
 ('limit_passage','x','x'*2000,'literal'),
 ('over_claim','x'*2001,'x','literal'),('over_passage','x','x'*2001,'literal'),
 ('oversize_normalized','\u0344'*1001,'a','literal'),
 ('private_marker','PRIVATE_NF_CANARY','PRIVATE_NF_CANARY','literal'),
 ('literal_whitespace',' \na','x \na x','literal'),
 ('word_frequency','a a b','a b b','cosine'),('overlap_none','red','blue','cosine')]

if __name__=='__main__':
    rows=[]
    for ident,a,b,c in CASES:
        try:expected=json.loads(inspect_nf_device(a,b,c))
        except (ValueError,UnicodeError):expected=None
        rows.append({'id':ident,'claim':a,'passage':b,'check':c,'expected':expected})
    print(json.dumps(rows,ensure_ascii=True,separators=(',',':')))
