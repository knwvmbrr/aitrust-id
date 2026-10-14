#!/usr/bin/env python3
"""Run selected development tag checks independently; no automatic collection."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT))
MAX_CHARS=200000
MAX_BYTES=800000
DEFAULT_ENV=Path.home()/'.config/aitrust-id/runtime.env'

def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate result field')
        value[key]=item
    return value

def read_input(stream):
    raw=stream.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Input too large')
    text=raw.decode('utf-8')
    if not text.strip() or len(text)>MAX_CHARS:raise ValueError('Input outside range')
    return text

def load_checker(name):
    spec=importlib.util.spec_from_file_location('selected_'+name,ROOT/'scripts'/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
CODES=('PS','PII_REDACTED')


def run_tag(code,text,env_file):
    try:
        if code=='PS':
            argv=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json']
            deadline=12
        else:
            argv=[sys.executable,'-B',str(ROOT/'scripts/aitrust.py'),'privacy','--env-file',str(env_file),'--json']
            deadline=30
        child=subprocess.run(argv,input=text.encode('utf-8'),capture_output=True,timeout=deadline,check=False)
        if child.returncode or len(child.stdout)>2_000_000:raise ValueError('Selected checker unavailable')
        row=json.loads(child.stdout,object_pairs_hook=unique,
            parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Invalid result number')))
        if code=='PS':
            row=load_checker('check-ps.py').validate(row,text);state=row['state']
        else:
            row=load_checker('aitrust.py').validate_result(row,privacy=True);state='FINDING' if row['tags'] else 'NO_FINDING'
        return {'code':code,'state':state,'record':row}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,ImportError,subprocess.SubprocessError):
        # Child exceptions, credentials, stderr and response text are never copied.
        return {'code':code,'state':'UNAVAILABLE','reason':'No valid check completed.'}


def check_tags(text,codes,env_file,on_complete=None):
    if (not codes or len(set(codes))!=len(codes) or any(code not in CODES for code in codes)
            or not isinstance(text,str) or not text.strip() or len(text)>MAX_CHARS):
        raise ValueError('Unsupported request')
    rows={}
    with ThreadPoolExecutor(max_workers=len(codes)) as pool:
        pending={pool.submit(run_tag,code,text,env_file):code for code in codes}
        for future in as_completed(pending):
            try:row=future.result()
            except Exception:row={'code':pending[future],'state':'UNAVAILABLE','reason':'No valid check completed.'}
            rows[row['code']]=row
            if on_complete:on_complete(row)
    checks=[rows[code] for code in codes]
    unavailable=sum(row['state']=='UNAVAILABLE' for row in checks)
    return {'format':'ai-trust-id-independent-checks/v1',
            'state':'UNAVAILABLE' if unavailable==len(checks) else 'PARTIAL' if unavailable else 'COMPLETE',
            'checks':checks,'text_included':False,'independently_validated':False}


def brief(row):
    code=row['code'];state=row['state']
    if state=='UNAVAILABLE':return code+': unavailable. No valid check completed; your other checks are separate.'
    if code=='PS':
        return 'PS: supported download-and-run pattern found. Review the command first.' if state=='FINDING' else 'PS: no supported command pattern found. This is not a safety clearance.'
    return 'PII_REDACTED: possible personal details were masked during this check. Your draft is unchanged.' if state=='FINDING' else 'PII_REDACTED: no supported detections were masked. Private details may still be present.'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',nargs='?',default='-',help='UTF-8 response/draft file, or - for stdin')
    parser.add_argument('--tag',action='append',choices=CODES,required=True,help='Explicitly select each check; repeat for another tag')
    parser.add_argument('--env-file',type=Path,default=DEFAULT_ENV,help='Used only for the selected privacy route')
    parser.add_argument('--json',action='store_true',help='Explicit full record export; hashes/offsets may link to input')
    parser.add_argument('--fail-on-finding',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.file=='-':text=read_input(sys.stdin.buffer)
        else:
            with open(args.file,'rb') as stream:text=read_input(stream)
        result=check_tags(text,args.tag,args.env_file,None if args.json else lambda row:print(brief(row),flush=True))
        if args.json:print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
        else:print('Development checks only. PS performs no redaction; nothing is submitted to a training database.')
        if result['state']=='UNAVAILABLE':return 1
        if result['state']=='PARTIAL':return 3
        return 2 if args.fail_on_finding and any(row['state']=='FINDING' for row in result['checks']) else 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        print('UNAVAILABLE: invalid input or selected checks; no result issued.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
