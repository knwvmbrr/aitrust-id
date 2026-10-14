#!/usr/bin/env python3
"""Standalone PS development check. No local service, account or redaction required."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MAX_CHARS=20000
MAX_BYTES=MAX_CHARS*4
MAX_RESULT=2_000_000
DEADLINE=10


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate result field')
        result[key]=value
    return result


def validate(row,text):
    expected={'format','state','subject','candidates','models','calibration_id',
              'redaction_performed','independently_validated','training_label',
              'label_status','text_included'}
    if not isinstance(row,dict) or set(row)!=expected:raise ValueError('Unsupported result')
    if (row['format']!='ai-trust-id-device-preview/v1'
            or row['calibration_id']!='uncalibrated-rules-v6'
            or any(row[key] is not False for key in ('redaction_performed','independently_validated','text_included'))
            or row['training_label'] is not None or row['label_status']!='unreviewed_prediction'):
        raise ValueError('Unsupported claim')
    # This is the same trusted frozen normalizer used by the projected method.
    normalization=runpy.run_path(str(ROOT/'protocol/normalization.py'))
    normalized=normalization['normalize_nfc'](text)
    if row['subject']!={'sha256':hashlib.sha256(normalized.encode()).hexdigest(),
                       'codepoint_count':len(normalized),'normalization':normalization['NORMALIZATION_ID']}:
        raise ValueError('Input identity differs')
    method_hash=hashlib.sha256((ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
    if row['models']!=[{'name':'rules-only','sha256':method_hash,'revision':'context-v6'}]:
        raise ValueError('Method identity differs')
    candidates=row['candidates']
    if not isinstance(candidates,list) or len(candidates)>1:raise ValueError('Unsupported candidates')
    if row['state']!=('FINDING' if candidates else 'NO_FINDING'):raise ValueError('Result state differs')
    for candidate in candidates:
        if (not isinstance(candidate,dict) or set(candidate)!={'code','confidence','signals'}
                or candidate['code']!='PS' or type(candidate['confidence']) not in (float,int)
                or not .7<=candidate['confidence']<=1):raise ValueError('Unsupported candidate')
        signals=candidate['signals']
        if not isinstance(signals,list) or not signals or len(signals)>MAX_CHARS:
            raise ValueError('Unsupported signals')
        allowed={'sig.piped_installer.v4','sig.remote_command_substitution.v4',
                 'sig.remote_process_substitution.v4','sig.remote_backtick_substitution.v3',
                 'sig.obfuscated_payload.v3'}
        for signal in signals:
            if (not isinstance(signal,dict) or set(signal)!={'id','score','spans'}
                    or signal['id'] not in allowed or type(signal['score']) not in (float,int)
                    or not 0<=signal['score']<=1 or not isinstance(signal['spans'],list)
                    or not signal['spans'] or len(signal['spans'])>MAX_CHARS):
                raise ValueError('Unsupported evidence')
            for span in signal['spans']:
                if (not isinstance(span,list) or len(span)!=2 or any(type(v) is not int for v in span)
                        or not 0<=span[0]<span[1]<=len(normalized)):
                    raise ValueError('Unsupported offsets')
    return row


def check(text):
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_CHARS:
        raise ValueError('Input outside supported range')
    # Isolate method imports and exceptions from other tags and the caller.
    # Inspected text is pipe data, never command-line code or an executed file.
    child=subprocess.run([sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--worker'],
        input=text.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        timeout=DEADLINE,check=False)
    if child.returncode or len(child.stdout)>MAX_RESULT:raise ValueError('Worker unavailable')
    row=json.loads(child.stdout,object_pairs_hook=unique,
                   parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Invalid number')))
    return validate(row,text)


def worker():
    raw=sys.stdin.buffer.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Input too large')
    text=raw.decode('utf-8')
    if not text.strip() or len(text)>MAX_CHARS:raise ValueError('Input too large')
    project=runpy.run_path(str(ROOT/'scripts/build-device-detector.py'))['project']
    bundle,_=project((ROOT/'services/evaluator/app.py').read_bytes())
    method={}
    exec(compile(bundle,'<trusted-PS-projection>','exec'),method)
    # The projection itself checks input bounds and performs frozen NFC.
    row=json.loads(method['check_device'](text))
    print(json.dumps(row,allow_nan=False))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',nargs='?',default='-',help='UTF-8 response file, or - for stdin; maximum 20,000 characters')
    parser.add_argument('--json',action='store_true',help='Export metadata including hashes/offsets; may link to your input')
    parser.add_argument('--fail-on-finding',action='store_true',help='Exit 2 on a finding; 1 means unavailable, never no finding')
    args=parser.parse_args(argv)
    try:
        if args.file=='-':raw=sys.stdin.buffer.read(MAX_BYTES+1)
        else:
            with open(args.file,'rb') as stream:raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError('Input too large')
        row=check(raw.decode('utf-8'))
        if args.json:print(json.dumps(row,indent=2,ensure_ascii=False,allow_nan=False))
        else:
            print('PS: this includes a supported download-and-run pattern.' if row['state']=='FINDING' else
                  'PS: no supported command pattern found.')
            print('Checked only on this computer. No redaction was performed.')
            print('Development check; this is not a safety clearance or independently validated release.')
        return 2 if args.fail_on_finding and row['state']=='FINDING' else 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError):
        print('PS UNAVAILABLE: no valid check completed. Other tag checks remain separate.',file=sys.stderr)
        return 1


if __name__=='__main__':
    if sys.argv[1:]==['--worker']:
        try:worker()
        except Exception:raise SystemExit(1)
    else:raise SystemExit(main())
