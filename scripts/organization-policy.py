#!/usr/bin/env python3
"""Govern local tenant policy jobs; no hosted service, account or public tag."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Organization policy command unavailable; use --help.\n')


def main(argv=None):
    p=Parser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True,parser_class=Parser)
    key=sub.add_parser('keygen');key.add_argument('--output',type=Path,required=True)
    init=sub.add_parser('init');init.add_argument('--registry',type=Path,required=True);init.add_argument('--authority',type=Path,required=True);init.add_argument('--accept-local-contract',action='store_true')
    for operation in ('enroll','grant','revoke','add-policy','prepare','check','job-enabled','tenant-enabled','inspect','remove-tenant','remove-registry'):
        q=sub.add_parser(operation);q.add_argument('--registry',type=Path,required=True)
        if operation!='remove-registry':q.add_argument('--namespace',required=True)
        if operation in ('enroll','grant','revoke','tenant-enabled','remove-tenant','remove-registry'):q.add_argument('--authority',type=Path,required=True)
        if operation in ('revoke','add-policy','prepare','check','job-enabled','inspect'):q.add_argument('--credential',type=Path,required=True)
        if operation=='enroll':q.add_argument('--offering',choices=('team','enterprise','proprietary'),required=True)
        if operation=='grant':q.add_argument('--roles',nargs='+',required=True);q.add_argument('--seconds',type=int,default=3600);q.add_argument('--output',type=Path,required=True)
        if operation=='add-policy':q.add_argument('--policy',type=Path,required=True)
        if operation in ('prepare','job-enabled'):q.add_argument('--job',required=True)
        if operation=='prepare':q.add_argument('--revision',type=int,required=True);q.add_argument('--output',type=Path,required=True)
        if operation in ('prepare','check'):q.add_argument('--subject',type=Path,required=True)
        if operation=='check':q.add_argument('--selection',type=Path,required=True);q.add_argument('--reviewed-policy',action='store_true');q.add_argument('--output',type=Path)
        if operation in ('job-enabled','tenant-enabled'):q.add_argument('--enabled',choices=('true','false'),required=True)
        if operation=='inspect':q.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    uncertain_class=None
    try:
        from tools.organization_policy_io import OutputCommitUncertain
        uncertain_class=OutputCommitUncertain
        from tools import organization_policy_registry as m
        op=args.operation
        if op=='keygen':result=m.keygen(args.output)
        elif op=='init':result=m.initialize(args.registry,args.authority,args.accept_local_contract)
        elif op=='enroll':result=m.enroll(args.registry,args.namespace,args.offering,args.authority)
        elif op=='grant':result=m.grant(args.registry,args.namespace,args.authority,args.roles,args.seconds,args.output)
        elif op=='revoke':result=m.revoke(args.registry,args.namespace,args.authority,args.credential)
        elif op=='add-policy':result=m.add_policy(args.registry,args.namespace,args.credential,args.policy)
        elif op=='prepare':result=m.prepare(args.registry,args.namespace,args.credential,args.job,args.revision,args.subject,args.output)
        elif op=='check':result=m.check(args.registry,args.namespace,args.credential,args.selection,args.subject,args.reviewed_policy,args.output)
        elif op=='job-enabled':result=m.enable_job(args.registry,args.namespace,args.credential,args.job,args.enabled=='true')
        elif op=='tenant-enabled':result=m.enable_tenant(args.registry,args.namespace,args.authority,args.enabled=='true')
        elif op=='inspect':result=m.inspect_tenant(args.registry,args.namespace,args.credential,args.output)
        elif op=='remove-tenant':result=m.remove_tenant(args.registry,args.namespace,args.authority)
        else:result=m.remove_registry(args.registry,args.authority)
        print(json.dumps(result,sort_keys=True));return 0
    except Exception as error:
        # Import failure is handled without assuming a module binding exists.
        uncertain=uncertain_class is not None and isinstance(error,uncertain_class)
        print(json.dumps({'state':'UNAVAILABLE','code':'output_commit_uncertain' if uncertain else 'organization_policy_unavailable',
            'literal_occurrences':None,'output_may_exist':uncertain,'operation_may_have_applied':uncertain,
            'next_step':'Inspect the registry and requested destination before retrying.' if uncertain else 'Review the local contract, selected private files, current permissions and supported limits.',
            'public_tag_asserted':False}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
