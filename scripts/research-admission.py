#!/usr/bin/env python3
"""Exercise private invented requests in the disposable PostgreSQL sandbox only."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.research_admission import AdmissionError, MAX_BYTES, parse, statement
from tools.blind_review_io import source as private_source

spec=importlib.util.spec_from_file_location('admission_sandbox',ROOT/'scripts/verify-metadata-store.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


class PrivateParser(argparse.ArgumentParser):
    def error(self,_message):
        self.exit(2,'Use the documented synthetic admission command.\n')


def execute(path,raw):
    # Parse and check the owned directory before any process/database call.
    request=parse(raw)
    if sys.platform!='linux' or os.geteuid()==0:
        raise AdmissionError('Synthetic admission refused')
    directory=base.sandbox(path)
    command=['/usr/lib/postgresql/18/bin/psql','-XqAtw','-v','ON_ERROR_STOP=1',
             '-h',str(directory/'socket'),'-p','55443','-d','postgres',
             '-U',pwd.getpwuid(os.geteuid()).pw_name]
    environment={'PATH':os.defpath,'LANG':'C.UTF-8',
        'PGOPTIONS':'-c statement_timeout=5000 -c lock_timeout=2000 -c standard_conforming_strings=on'}
    def sql(query):
        r=subprocess.run(command,input=query.encode('ascii'),capture_output=True,
                         env=environment,timeout=12)
        if r.returncode or len(r.stdout)+len(r.stderr)>65536:
            raise AdmissionError('Synthetic admission refused')
        try:return json.loads(r.stdout)
        except (ValueError,UnicodeError,RecursionError):
            raise AdmissionError('Synthetic admission refused') from None
    observed=sql("SELECT json_build_object('data',current_setting('data_directory'),"
        "'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),"
        "'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),"
        "'tcp',inet_server_addr());")
    if (type(observed) is not dict or observed.get('data')!=str(directory/'data')
            or observed.get('socket')!=str(directory/'socket')
            or observed.get('cluster')!='aitrust-metadata-synthetic'
            or observed.get('listen')!='' or observed.get('tcp') is not None
            or not 180000<=int(observed.get('version',0))<190000):
        raise AdmissionError('Synthetic admission refused')
    # Directory replacement or permissions drift invalidates the attempted use.
    if base.sandbox(path)!=directory:
        raise AdmissionError('Synthetic admission refused')
    value=sql(statement(raw))
    expected={'operation','feedback_id'} if request['operation']=='submit' else {'operation','removed'}
    if type(value) is not dict or set(value)!=expected or value['operation']!=request['operation']:
        raise AdmissionError('Synthetic admission refused')
    if request['operation']=='submit':
        if type(value['feedback_id']) is not str:
            raise AdmissionError('Synthetic admission refused')
        try:identity=uuid.UUID(value['feedback_id'])
        except ValueError:
            raise AdmissionError('Synthetic admission refused') from None
        if str(identity)!=value['feedback_id'] or identity.version!=4:
            raise AdmissionError('Synthetic admission refused')
    elif type(value['removed']) is not bool:
        raise AdmissionError('Synthetic admission refused')
    return {'pass':True,'synthetic_only':True,**value}


def main():
    p=PrivateParser(description=__doc__)
    p.add_argument('--sandbox-dir',type=Path,required=True)
    p.add_argument('--request',type=Path,required=True)
    args=p.parse_args()
    try:
        result=execute(args.sandbox_dir,private_source(args.request,ROOT,MAX_BYTES))
    except (ValueError,OSError,TypeError,KeyError,RecursionError,subprocess.SubprocessError):
        print('SYNTHETIC_ADMISSION_REFUSED',file=sys.stderr);return 1
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
