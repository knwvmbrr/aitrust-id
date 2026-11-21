#!/usr/bin/env python3
"""One bounded canonical literal-policy job; never evaluates subject programs."""
import json
from pathlib import Path
import resource
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import private_policy
from protocol.evidence import unique,finite


def main():
    try:
        if len(sys.argv)!=1:raise ValueError()
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_CPU,(2,2))
        resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
        resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
        if sys.platform.startswith('linux'):
            resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
        raw=sys.stdin.buffer.read(524289)
        if not 0<len(raw)<=524288:raise ValueError()
        value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique)
        finite(value)
        if type(value) is not dict or set(value)!={'format','subject','policy','context'} or value['format']!='local-organization-policy-job/v1':raise ValueError()
        if type(value['subject']) is not str or type(value['policy']) is not str or type(value['context']) is not dict:raise ValueError()
        result=private_policy.observe(value['subject'],value['policy'].encode('utf-8'),value['context'],reviewed=True)
        raw=json.dumps(result,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        if len(raw)>262144:raise ValueError()
        sys.stdout.buffer.write(raw+b'\n')
        return 0
    except BaseException:
        sys.stdout.write('{"state":"UNAVAILABLE","code":"organization_policy_worker_unavailable"}\n')
        return 2


if __name__=='__main__':raise SystemExit(main())
