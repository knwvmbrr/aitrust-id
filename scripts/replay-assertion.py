#!/usr/bin/env python3
"""Owner-run current-service replay. Never prints private text, token or paths."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
EXIT={'matched':0,'mismatch':1,'input_mismatch':2,'unavailable':3,'invalid':4}


def read_private(path,limit,credential=False):
    path=Path(path)
    if any(p.is_symlink() for p in path.parents):raise ValueError('Unsupported input')
    try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except OSError:raise ValueError('Unsupported input') from None
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):raise ValueError('Unsupported input')
        if credential and (info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode) not in (0o400,0o600)):
            raise ValueError('Unsupported credential permissions')
        raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Unsupported input size')
    return raw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('assertion_file');p.add_argument('original_text_file')
    p.add_argument('--local-gateway',action='store_true',help='Explicitly allow the existing authenticated 127.0.0.1:8787 service to receive this original text.')
    p.add_argument('--token-file',help='Owner-only regular file, mode 0400/0600, containing only the local token.')
    a=p.parse_args()
    result={'status':'unavailable','reason':'local_service_not_selected','tool_retains_input':False,'independent_accuracy_verified':False}
    try:
        if a.local_gateway and a.token_file:
            from protocol.evidence import unique,reject,finite
            from protocol.replay import replay
            record=json.loads(read_private(a.assertion_file,2_000_000).decode('utf-8'),object_pairs_hook=unique,parse_constant=reject);finite(record)
            if not isinstance(record,dict):raise ValueError('Unsupported assertion')
            text=read_private(a.original_text_file,800_000,credential=True).decode('utf-8',errors='strict')
            token=read_private(a.token_file,257,credential=True).decode('ascii').rstrip('\n')
            result=replay(record,text,token)
    except RuntimeError:
        result={'status':'unavailable','reason':'dependency_configuration_unavailable','tool_retains_input':False,'independent_accuracy_verified':False}
    except ImportError:
        result={'status':'unavailable','reason':'missing_dependencies','tool_retains_input':False,'independent_accuracy_verified':False}
    except (OSError,ValueError,TypeError,RecursionError):
        result={'status':'invalid','reason':'input_or_credential_unavailable','tool_retains_input':False,'independent_accuracy_verified':False}
    print(json.dumps(result,separators=(',',':')))
    return EXIT[result['status']]

if __name__=='__main__':raise SystemExit(main())
