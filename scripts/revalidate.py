"""Execute versioned checks, or reject an existing receipt when sources change."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.revalidation import CAPABILITIES,assess,execute,fingerprint
from protocol.reports import write_report
from protocol.evidence import read_evidence

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capability',choices=sorted(CAPABILITIES));p.add_argument('--receipt',type=Path);p.add_argument('--fingerprint',action='store_true');p.add_argument('--output');a=p.parse_args()
    try:
        if a.fingerprint:result=fingerprint(a.capability);result['pass']=True
        elif a.receipt:
            result=assess(read_evidence(a.receipt),a.capability)
        else:result=execute(a.capability)
    except (ValueError,KeyError,TypeError,OSError,RecursionError):result={'pass':False,'revalidation_required':True,'reason':'revalidation_contract_failed'}
    if a.output:write_report(a.output,result)
    print(json.dumps(result));raise SystemExit(0 if result.get('pass') is True else 1)
