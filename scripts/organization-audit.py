#!/usr/bin/env python3
"""Preview, retain and review approved metadata in an organization-owned PostgreSQL store."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.organization_audit import parse,prepare,encoded,validate_metadata,digest
from tools.organization_audit_store import Store,private_file,install,policy,tenant_create,enroll,verify_export,checkpoint,recovery_controls,reconcile,backup
from tools.blind_review_io import create

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Audit command refused; use --help.\n')

def main(argv=None):
    p=Parser(description=__doc__)
    p.add_argument('--service');p.add_argument('--service-file',type=Path);p.add_argument('--pass-file',type=Path)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--input',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    sub.add_parser('install')
    q=sub.add_parser('tenant');q.add_argument('--tenant',required=True);q.add_argument('--record-days',type=int,required=True);q.add_argument('--audit-days',type=int,required=True);q.add_argument('--backup-hours',type=int,required=True)
    q=sub.add_parser('enroll');q.add_argument('--tenant',required=True);q.add_argument('--principal',required=True);q.add_argument('--capability',action='append',required=True)
    sub.add_parser('policy')
    q=sub.add_parser('append');q.add_argument('--input',type=Path,required=True);q.add_argument('--accept-policy',required=True);q.add_argument('--predecessor')
    q=sub.add_parser('review');q.add_argument('--id',required=True);q.add_argument('--decision',choices=['agree','disagree','uncertain'],required=True);q.add_argument('--reason',choices=['supported','missed_pattern','false_alarm','insufficient_context','other'],required=True)
    q=sub.add_parser('remove');q.add_argument('--id',required=True)
    sub.add_parser('expire')
    q=sub.add_parser('export');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('verify');q.add_argument('--input',type=Path,required=True);q.add_argument('--checkpoint',type=Path)
    q=sub.add_parser('recovery-controls');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconcile');q.add_argument('--input',type=Path,required=True);q.add_argument('--expected-sha256',required=True);q.add_argument('--maximum-age-minutes',type=int,required=True)
    q=sub.add_parser('backup');q.add_argument('--config',type=Path,required=True);q.add_argument('--empty-include-directory',type=Path,required=True);q.add_argument('--stanza',required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='prepare':
            v=prepare(private_file(a.input));create(a.output,ROOT,{'metadata.json':encoded(v)+b'\n'})
            result={'prepared':True,'metadata_only':True,'stored':False,'source_record_sha256':v['source_record_sha256']}
        elif a.command=='verify':
            # Audit exports are bounded to 20 MB; credentials and source inputs stay at 2 MB.
            from scripts.source_snapshot import read_file
            v=parse(read_file(a.input,20_000_000),20_000_000)
            result=verify_export(v,parse(private_file(a.checkpoint)) if a.checkpoint else None)
        else:
            if not a.service or not a.service_file:raise ValueError('Missing private database service')
            db=Store(a.service,a.service_file,a.pass_file)
            if a.command=='install':install(db);result={'installed':True,'collection_enabled':False}
            elif a.command=='tenant':result=tenant_create(db,a.tenant,policy(a.record_days,a.audit_days,a.backup_hours))
            elif a.command=='enroll':result=enroll(db,a.tenant,a.principal,a.capability)
            elif a.command=='policy':result=db.call('policy')
            elif a.command=='append':
                v=validate_metadata(parse(private_file(a.input)));result=db.call('append',encoded(v).decode(),a.accept_policy,a.predecessor)
            elif a.command=='review':result=db.call('review',a.id,a.decision,a.reason)
            elif a.command=='remove':result=db.call('remove_record',a.id)
            elif a.command=='expire':result=db.call('expire')
            elif a.command=='export':
                v=db.export();create(a.output,ROOT,{'audit.json':encoded(v)+b'\n','checkpoint.json':encoded(checkpoint(v))+b'\n'})
                result={'exported':True,'records':len(v['records']),'events':len(v['events']),'independent_witness':False}
            elif a.command=='recovery-controls':
                v=recovery_controls(db);create(a.output,ROOT,{'recovery.json':encoded(v)+b'\n'})
                result={'created':True,'sha256':digest(encoded(v)),'keep_latest_pin_outside_database':True}
            elif a.command=='backup':result=backup(db,a.config,a.empty_include_directory,a.stanza)
            elif a.command=='reconcile':result=reconcile(db,parse(private_file(a.input)),a.expected_sha256,a.maximum_age_minutes)
        print(json.dumps(result,allow_nan=False));return 0
    except Exception:
        # Never reflect source examples, credential filenames, SQL, database errors, or record values.
        print('{"state":"UNAVAILABLE","reason":"organization_audit_contract_refused"}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
