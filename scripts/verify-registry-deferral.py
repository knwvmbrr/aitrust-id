"""Build/run the actual deferred image in disposable Podman staging, with no real data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
MESSAGE='AI Trust ID registry is deferred from this release. No registry storage or listener was started.\n'

def verify():
    if sys.platform!='linux':
        raise ValueError('Use an isolated Linux staging host; do not launch local Docker.')
    names=['services/registry/Dockerfile','services/registry/deferred.py','scripts/verify-registry-deferral.py']
    sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    tag='localhost/aitrust-staging-registry:'+uuid.uuid4().hex
    containers=[]
    def run(*args, expected=0):
        result=subprocess.run(['podman',*args],capture_output=True,timeout=120)
        if result.returncode!=expected:
            sys.stderr.write(result.stderr.decode(errors='replace'))
            raise ValueError('Registry staging '+args[0]+' returned status '+str(result.returncode)+'.')
        return result.stdout.decode()
    cases=[]
    try:
        version=run('--version').strip()
        run('build','--pull=missing','--network=none','--tag',tag,str(ROOT/'services/registry'))
        with tempfile.TemporaryDirectory(prefix='aitrust-staging-registry-data-') as work:
            data=Path(work);data.chmod(0o755)
            marker=data/'synthetic-record';marker.write_bytes(b'SYNTHETIC_PRIVATE_RECORD');marker.chmod(0o644)
            before={p.name:p.read_bytes() for p in data.iterdir()}
            for case,extra in [('default',[]),('unaccepted_future_version',['--env','AITRUST_REGISTRY_VERSION=1.0.0'])]:
                name='aitrust-staging-registry-'+uuid.uuid4().hex;containers.append(name)
                result=run('run','--name',name,'--network=none','--read-only','--cap-drop=ALL',
                    '--security-opt=no-new-privileges','--pids-limit=16','--memory=32m',
                    '--mount','type=bind,src='+str(data)+',dst=/tmp,ro=true',*extra,tag,expected=64)
                if result!=MESSAGE or before!={p.name:p.read_bytes() for p in data.iterdir()}:
                    raise ValueError('Deferred registry touched data or disclosed unexpected output.')
                info=json.loads(run('inspect',name))[0];host=info['HostConfig']
                if (info['Config']['User']!='10001:10001' or host['ReadonlyRootfs'] is not True
                    or host['NetworkMode']!='none' or host.get('PortBindings')
                    or info['State']['ExitCode']!=64 or info['State']['Running']):
                    raise ValueError('Deferred registry execution boundary differs.')
                if host['Memory']!=32*1024*1024 or host['PidsLimit']!=16:
                    raise ValueError('Deferred registry resource boundary differs.')
                if not any(x.split(':')[0]=='no-new-privileges' for x in host['SecurityOpt']):
                    raise ValueError('Deferred registry permits new privileges.')
                delta=run('diff',name).strip().splitlines()
                if any(line!='C /etc' for line in delta):
                    raise ValueError('Deferred registry wrote application files.')
                cases.append({'name':case,'exit_code':64,'fixed_output':True,
                    'data_unchanged':True,'synthetic_mount_target':'/tmp','user':'10001:10001','read_only':True,
                    'network':'none','no_published_ports':True,'not_running':True,
                    'memory_limit_bytes':host['Memory'],'pid_limit':host['PidsLimit'],
                    'runtime_file_deltas':delta})
        probe_name='aitrust-staging-registry-'+uuid.uuid4().hex;containers.append(probe_name)
        probe='import json,os; d=dict(r.split(":",1) for r in open("/proc/self/status") if ":" in r); print(json.dumps({"uid":os.getuid(),"caps":{k:int(d[k].strip(),16) for k in ("CapEff","CapPrm","CapBnd")},"no_new_privileges":int(d["NoNewPrivs"].strip())}))'
        identity=json.loads(run('run','--name',probe_name,'--network=none','--read-only',
            '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=16',
            '--memory=32m',tag,'python','-c',probe))
        if identity['uid']!=10001 or any(identity['caps'].values()) or identity['no_new_privileges']!=1:
            raise ValueError('Actual registry sandbox identity differs.')
        if sources!={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}:
            raise ValueError('Registry sources changed during verification.')
        record = {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
            'engine':version,'sources':sources,'cases':cases,'runtime_identity':identity,'synthetic_data_only':True,
            'registry_activated':False,'independent_accuracy_evidence':False,
            'scope':'Actual pinned refusal image in disposable Linux Podman staging. No listener or application data writes; not future registry or research pipeline acceptance.'}
    finally:
        cleanup_ok=True
        for name in containers:
            removed=subprocess.run(['podman','rm','--force',name],capture_output=True,timeout=30)
            absent=subprocess.run(['podman','container','exists',name],capture_output=True,timeout=30)
            cleanup_ok=cleanup_ok and removed.returncode==0 and absent.returncode==1
        removed=subprocess.run(['podman','rmi',tag],capture_output=True,timeout=30)
        absent=subprocess.run(['podman','image','exists',tag],capture_output=True,timeout=30)
        cleanup_ok=cleanup_ok and absent.returncode==1
        if not cleanup_ok:
            raise ValueError('Registry staging cleanup did not verify.')
    record['cleanup']={'owned_containers_removed':len(containers),'owned_image_absent':True,'verified':True}
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',default='output/verification/registry-deferral.json');a=p.parse_args()
    try:record=verify()
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        sys.stderr.write(str(error)+'\n')
        record={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'reason':'registry_deferral_execution_failed','registry_accepted':False}
    write_report(a.report,record);print(json.dumps(record));raise SystemExit(0 if record['pass'] else 1)
