#!/usr/bin/env python3
"""Fixed synthetic full-record cases; no participant or independent labels."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integrations/mt-choice-reference/1.3.0'))
from tools.mt_choice_device import inspect_mt_choice


def cases():
    result=[]
    for name,subject,first,second in [
        ('additive','Not only tea but also coffee.','tea','coffee'),
        ('privacy_prefix','PRIVATE_MT_CHOICE_CANARY Not only tea but also coffee.','tea','coffee'),
        ('either','Either tea or coffee.','tea','coffee'),
        ('only','Only tea or coffee.','tea','coffee'),
        ('neither','Neither tea nor coffee.','tea','coffee'),
        ('between','Between tea and coffee.','tea','coffee'),
        ('quoted_additive','A lesson quotes "not only tea but also coffee".','tea','coffee'),
        ('unicode_NFC','😀 Not only cafe\u0301 but also tea.','café','tea'),
        ('commas_tabs','NOT\tONLY tea, BUT\tALSO coffee.','tea','coffee'),
        ('unsupported','A menu lists tea plus coffee.','tea','coffee'),
        ('negated_legacy','Not only tea or coffee.','tea','coffee'),
    ]:
        request={'subject':subject,'first':first,'second':second,'reference':'Water is also listed.','whole_frame':True}
        wire=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        result.append({'id':name,'request':request,'wire':wire,'expected':json.loads(inspect_mt_choice(wire))})
    return result

if __name__=='__main__':print(json.dumps(cases(),ensure_ascii=True,separators=(',',':')))
