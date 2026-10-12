#!/usr/bin/env python3
"""Run synthetic storage controls in a disposable private PostgreSQL 18 cluster."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
BIN=Path('/usr/lib/postgresql/18/bin')


class ControlFailure(ValueError):
    def __init__(self,message,record):
        super().__init__(message);self.record=record


def failure_record(stage,result=None):
    record={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
        'failure_stage':stage,'only_synthetic_records':True,
        'production_database_changed':False,'new_endpoints':0,
        'independent_accuracy_evidence':False,'completed_cases':[],
        'source_snapshot_at_failure':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() if (ROOT/path).is_file() else None
            for path in ('deploy/research/metadata-development.sql','scripts/metadata-store-sandbox.py',
                         'scripts/verify-metadata-store.py','protocol/reports.py','site/src/research-feedback.js',
                         'deploy/research/metadata-invitation-development.sql','scripts/verify-research-invitations.py',
                         'tools/research_admission.py','scripts/research-admission.py','scripts/verify-research-admission.py')}}
    if result is not None:
        record.update(worker_exit_status=result.returncode,
            stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
        try:
            partial=json.loads(result.stdout) if len(result.stdout)<32768 else {}
            completed=partial.get('completed_cases',[])
            if (partial.get('pass') is False and isinstance(completed,list)
                and len(completed)<=64 and all(isinstance(name,str)
                and re.fullmatch(r'[a-z0-9_]{1,100}',name) for name in completed)):
                record['completed_cases']=completed
                diagnostic=partial.get('sql_diagnostic',{})
                index=diagnostic.get('operation_index');code=diagnostic.get('sqlstate')
                if (type(index) is int and 0<=index<=1000 and
                    (code is None or isinstance(code,str) and re.fullmatch(r'[0-9A-Z]{5}',code))):
                    record['sql_diagnostic']={'operation_index':index,'sqlstate':code}
        except (ValueError,TypeError,AttributeError):pass
    return record


def run_control(output, profile='base'):
    if profile not in ('base', 'invitation', 'admission'):
        raise ValueError('Use an explicitly supported synthetic storage profile.')
    if sys.platform!='linux' or os.geteuid()==0:
        raise ValueError('Run as an ordinary Linux user with PostgreSQL 18 installed.')
    for name in ('initdb','pg_ctl','psql','postgres'):
        if not (BIN/name).is_file():raise ValueError('Install PostgreSQL 18 before running synthetic controls.')
    # Only this helper's fresh directory is initialized, started or removed.
    directory=Path(tempfile.mkdtemp(prefix='aitrust-metadata-',dir='/tmp'))
    os.chmod(directory,0o700);(directory/'socket').mkdir(mode=0o700)
    environment={'PATH':os.defpath,'LANG':'C.UTF-8'}
    attempted=False;stopped=True;stage='initialization';problem=None
    def run(arguments,timeout=40,check=True):
        result=subprocess.run(arguments,cwd=directory,capture_output=True,env=environment,timeout=timeout)
        if check and result.returncode:raise ControlFailure('Disposable PostgreSQL operation failed; no production acceptance.',failure_record(stage,result))
        return result
    control=[str(BIN/'pg_ctl'),'-D',str(directory/'data')]
    try:
        run([str(BIN/'initdb'),'-D','data','--auth-local=peer','--auth-host=reject','--no-locale','--encoding=UTF8'])
        configuration=directory/'data/postgresql.conf'
        with configuration.open('a') as stream:
            stream.write("\nlisten_addresses = ''\nport = 55443\nunix_socket_directories = '"+str(directory/'socket')+"'\ncluster_name = 'aitrust-metadata-synthetic'\nshared_buffers = '32MB'\nmax_connections = 10\nlog_statement = 'none'\nlog_min_error_statement = 'panic'\nlog_error_verbosity = 'terse'\n")
        attempted=True;stopped=False;stage='startup'
        run(control+['-l',str(directory/'server.log'),'-w','start'])
        stage='verification'
        worker={'base':'verify-metadata-store.py','invitation':'verify-research-invitations.py',
                'admission':'verify-research-admission.py'}[profile]
        result=subprocess.run([sys.executable,str(ROOT/'scripts'/worker),
            '--sandbox-dir',str(directory)],cwd=ROOT,capture_output=True,
            env=environment,timeout=180)
        if result.returncode:
            raise ControlFailure('Synthetic storage controls failed; bounded failure evidence retained.',failure_record(stage,result))
        return result.stdout
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        problem=error if isinstance(error,ControlFailure) else ControlFailure(
            'Disposable storage control failed; bounded failure evidence retained.',failure_record(stage))
        raise problem
    finally:
        if attempted:
            try:
                run(control+['-m','fast','-w','stop'],check=False)
                stopped=run(control+['status'],check=False).returncode==3
            except (OSError,subprocess.SubprocessError):stopped=False
        if problem is not None:
            problem.record.update(sandbox_shutdown_verified=stopped,private_cluster_removed=False)
        if stopped:
            try:
                shutil.rmtree(directory)
                if problem is not None:problem.record['private_cluster_removed']=True
            except OSError:
                record=problem.record if problem is not None else failure_record('cleanup')
                record.update(sandbox_shutdown_verified=True,private_cluster_removed=False)
                raise ControlFailure('Private synthetic directory cleanup failed.',record) from None
        else:
            # Never unlink an active database or pretend teardown succeeded.
            record=problem.record if problem is not None else failure_record('shutdown')
            record.update(sandbox_shutdown_verified=False,private_cluster_removed=False)
            raise ControlFailure('Shutdown was not confirmed. Private synthetic directory retained: '+str(directory),record)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='output/verification/metadata-store.json')
    parser.add_argument('--profile',choices=['base','invitation','admission'],default='base')
    args=parser.parse_args()
    try:
        record=json.loads(run_control(args.output,args.profile))
        if record.get('pass') is not True:raise ValueError('Synthetic verification did not pass.')
        if any(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected
               for path,expected in record['sources'].items()):
            raise ValueError('Synthetic control sources changed before final evidence publication.')
        record.update(sandbox_shutdown_verified=True,private_cluster_removed=True,
            shutdown_verified_at=datetime.now(timezone.utc).isoformat())
        # Publish evidence only after teardown has succeeded, never while the
        # database is still active or after a cleanup failure.
        write_report(args.output,record,root=ROOT)
        print(json.dumps(record,indent=2))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        if isinstance(error,ControlFailure):
            write_report(args.output,error.record,root=ROOT)
        print(str(error),file=sys.stderr);raise SystemExit(1)
