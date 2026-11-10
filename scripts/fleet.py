#!/usr/bin/env python3
"""Offline opt-in fleet administration. No daemon, network, capture or paid service."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
try:
    from tools import fleet as f
except ImportError:
    print('FLEET UNAVAILABLE: use the pinned macOS/Linux Python environment. Personal checking remains separate.',file=sys.stderr)
    raise SystemExit(2)

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Fleet operation refused; use --help.\n')

def main(argv=None):
    p=Parser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    g=sub.add_parser('keygen',help='Create an operator-selected private key and a separately shared public key.');g.add_argument('--private',type=Path,required=True);g.add_argument('--public',type=Path,required=True)
    b=sub.add_parser('package',help='Package this trusted source checkout; no download or install hooks.');b.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('enroll',help='Explicit local source/key approval; checking starts paused.');e.add_argument('--root',type=Path,required=True);e.add_argument('--public-key',type=Path,required=True);e.add_argument('--package',type=Path,action='append',required=True);e.add_argument('--cohort',choices=['canary','stable'],required=True);e.add_argument('--consent-local-only',action='store_true')
    g=sub.add_parser('sign-policy',help='Sign an exact policy JSON file with an existing private key.');g.add_argument('--payload',type=Path,required=True);g.add_argument('--key',type=Path,required=True);g.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('apply',help='Apply a signed policy to one explicitly selected enrolled device.');a.add_argument('--root',type=Path,required=True);a.add_argument('--policy',type=Path,required=True)
    a=sub.add_parser('rollout',help='Apply to the explicit roots; unavailable devices cannot affect other cohorts.');a.add_argument('--device-root',type=Path,action='append',required=True);a.add_argument('--policy',type=Path,required=True)
    for op in ['pause','resume','inventory','check','remove']:
        q=sub.add_parser(op);q.add_argument('--root',type=Path,required=True)
        if op=='check':q.add_argument('--json',action='store_true',help='Export metadata including subject hashes/spans; these can link to input.')
        if op=='remove':q.add_argument('--confirm-managed-removal',action='store_true')
    args=p.parse_args(argv)
    try:
        op=args.operation;result=None
        if op=='keygen':
            f.require(args.private.absolute()!=args.public.absolute())
            # Production key creation occurs only when the operator invokes this command.
            key=f.Ed25519PrivateKey.generate();seed=key.private_bytes(f.serialization.Encoding.Raw,f.serialization.PrivateFormat.Raw,f.serialization.NoEncryption())
            f.private_scope(args.private.absolute().parent);f.private_scope(args.public.absolute().parent)
            f.require(not args.private.exists() and not args.private.is_symlink() and not args.public.exists() and not args.public.is_symlink())
            f.publish(args.private,f.encode({'format':'fleet-ed25519-private/v1','seed':base64.b64encode(seed).decode()}));f.publish(args.public,f.encode(f.public_record(key)))
            result={'created':True,'private_key_printed':False,'public_key_fingerprint':f.sha(f.encode(f.public_record(key)))}
        elif op=='package':
            package=f.package();f.publish(args.output,f.encode(package));result={'package':f.sha(f.encode(package)),'method_sha256':package['hashes']['services/evaluator/app.py'],'development_only':True,'source_files':len(package['files'])}
        elif op=='enroll':
            public=f.parse(f.private_read(args.public_key,2048));packages=[f.parse(f.private_read(x)) for x in args.package]
            result=f.Device.enroll(args.root,public,args.cohort,packages,consent=args.consent_local_only)
        elif op=='sign-policy':
            key=f.key_record(f.private_read(args.key,2048),private=True);payload=f.parse(f.private_read(args.payload,65536));envelope=f.sign(payload,key);f.verify_policy(envelope,key.public_key());f.publish(args.output,f.encode(envelope));result={'signed':True,'sequence':payload['sequence'],'cohort':payload['cohort']}
        elif op=='apply':result=f.Device(args.root).apply(f.parse(f.private_read(args.policy,65536)))
        elif op=='rollout':
            f.require(1<=len(args.device_root)<=256 and len(set(map(str,args.device_root)))==len(args.device_root))
            policy=f.parse(f.private_read(args.policy,65536));outcomes=[]
            for i,root in enumerate(args.device_root):
                try:row=f.Device(root).apply(policy);outcomes.append({'index':i,'pass':True,'device':row['device'],'cohort':row['cohort'],'sequence':row['sequence']})
                except Exception:outcomes.append({'index':i,'pass':False,'state':'unavailable_or_not_targeted'})
            result={'format':'fleet-rollout/v1','pass':all(x['pass'] for x in outcomes),'devices':outcomes,'other_cohorts_unchanged':True}
        elif op in ('pause','resume'):result=f.Device(args.root).pause(op=='pause')
        elif op=='inventory':result=f.Device(args.root).inventory()
        elif op=='remove':result=f.Device(args.root).remove(consent=args.confirm_managed_removal)
        else:
            raw=sys.stdin.buffer.read(80001);f.require(len(raw)<=80000);result=f.Device(args.root).check(raw.decode('utf-8','strict'))
            if not args.json:
                print('PS: supported command pattern found.' if result['result']['state']=='FINDING' else 'PS: no supported command pattern found.')
                print('Managed offline development check; not a safety clearance. No text was stored or sent.');return 0
        print(json.dumps(result,allow_nan=False))
        return 1 if op=='rollout' and not result['pass'] else 0
    except KeyboardInterrupt:
        print('Fleet operation cancelled; check inventory before continuing.',file=sys.stderr);return 130
    except Exception:
        print('FLEET UNAVAILABLE: no valid managed operation completed. Personal checking remains separate.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
