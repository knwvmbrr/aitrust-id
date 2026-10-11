#!/usr/bin/env python3
"""Run synthetic storage controls in a disposable private PostgreSQL 18 cluster."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
BIN=Path('/usr/lib/postgresql/18/bin')


def run_control(output):
    if sys.platform!='linux' or os.geteuid()==0:
        raise ValueError('Run as an ordinary Linux user with PostgreSQL 18 installed.')
    for name in ('initdb','pg_ctl','psql','postgres'):
        if not (BIN/name).is_file():raise ValueError('Install PostgreSQL 18 before running synthetic controls.')
    # Only this helper's fresh directory is initialized, started or removed.
    directory=Path(tempfile.mkdtemp(prefix='aitrust-metadata-',dir='/tmp'))
    os.chmod(directory,0o700);(directory/'socket').mkdir(mode=0o700)
    environment={'PATH':os.defpath,'LANG':'C.UTF-8'}
    attempted=False;stopped=True
    def run(arguments,timeout=40,check=True):
        result=subprocess.run(arguments,cwd=directory,capture_output=True,env=environment,timeout=timeout)
        if check and result.returncode:raise ValueError('Disposable PostgreSQL operation failed; no production acceptance.')
        return result
    control=[str(BIN/'pg_ctl'),'-D',str(directory/'data')]
    try:
        run([str(BIN/'initdb'),'-D','data','--auth-local=peer','--auth-host=reject','--no-locale','--encoding=UTF8'])
        configuration=directory/'data/postgresql.conf'
        with configuration.open('a') as stream:
            stream.write("\nlisten_addresses = ''\nport = 55443\nunix_socket_directories = '"+str(directory/'socket')+"'\ncluster_name = 'aitrust-metadata-synthetic'\nshared_buffers = '32MB'\nmax_connections = 10\nlog_statement = 'none'\nlog_min_error_statement = 'panic'\nlog_error_verbosity = 'terse'\n")
        attempted=True;stopped=False
        run(control+['-l',str(directory/'server.log'),'-w','start'])
        result=subprocess.run([sys.executable,str(ROOT/'scripts/verify-metadata-store.py'),
            '--sandbox-dir',str(directory)],cwd=ROOT,capture_output=True,
            env=environment,timeout=180)
        if result.returncode:
            raise ValueError('Synthetic storage controls failed; no participant data was accepted.')
        return result.stdout
    finally:
        if attempted:
            try:
                run(control+['-m','fast','-w','stop'],check=False)
                stopped=run(control+['status'],check=False).returncode==3
            except (OSError,subprocess.SubprocessError):stopped=False
        if stopped:shutil.rmtree(directory)
        else:
            # Never unlink an active database or pretend teardown succeeded.
            raise ValueError('Shutdown was not confirmed. Private synthetic directory retained: '+str(directory))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='output/verification/metadata-store.json');args=parser.parse_args()
    try:
        record=json.loads(run_control(args.output))
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
        print(str(error),file=sys.stderr);raise SystemExit(1)
