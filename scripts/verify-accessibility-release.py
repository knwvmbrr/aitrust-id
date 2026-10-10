"""Fail release when current-source automation or real manual reviews are missing."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.accessibility_release import assess_reviews
from protocol.reports import write_report
from protocol.evidence import read_evidence

def read(path):
    if path is None or not path.exists():return {}
    return read_evidence(path)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--website-receipt',type=Path,default=ROOT/'eval/release/website-accessibility.json');p.add_argument('--extension-receipt',type=Path,default=ROOT/'eval/release/extension-accessibility.json');p.add_argument('--reviews',type=Path,default=ROOT/'docs/manual-accessibility/reviews.json');p.add_argument('--output');a=p.parse_args()
    try:
        reviews=read(a.reviews)
        result=assess_reviews(reviews.get('reviews',[]),{'website':read(a.website_receipt),'extension':read(a.extension_receipt)})
    except (ValueError,TypeError,KeyError,OSError,RecursionError):result={'pass':False,'failures':['accessibility_evidence_unavailable_or_invalid']}
    result['captured_at']=datetime.now(timezone.utc).isoformat()
    if a.output:write_report(a.output,result)
    print(json.dumps(result));raise SystemExit(0 if result['pass'] else 1)
