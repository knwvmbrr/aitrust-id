#!/usr/bin/env python3
"""Root-only bounded observations of the ACTUAL API service sandbox.
No input, credential, home or database contents are read or reported.
"""
import argparse
import ctypes
from datetime import datetime,timezone
import errno
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

UNIT='aitrustid-ai-tools.service'

def bpf_count(group,kind):
    # Linux UAPI BPF_PROG_QUERY (linux/bpf.h), cgroup ingress0/egress1.
    class Query(ctypes.Structure):
        _fields_=[('target_fd',ctypes.c_uint32),('attach_type',ctypes.c_uint32),('query_flags',ctypes.c_uint32),('attach_flags',ctypes.c_uint32),('prog_ids',ctypes.c_uint64),('prog_cnt',ctypes.c_uint32)]
    ids=(ctypes.c_uint32*16)();fd=os.open(group,os.O_RDONLY|os.O_DIRECTORY)
    try:
        q=Query(fd,kind,0,0,ctypes.addressof(ids),16);libc=ctypes.CDLL(None,use_errno=True)
        if libc.syscall(321,16,ctypes.byref(q),ctypes.sizeof(q))!=0:raise OSError(ctypes.get_errno(),'BPF query unavailable')
        if not 1<=q.prog_cnt<=16:raise ValueError('BPF attachment unavailable')
        return int(q.prog_cnt)
    finally:owned=fd;fd=None;os.close(owned)

def denial_mode(error):
    if isinstance(error,TimeoutError):return 'bounded_timeout'
    if isinstance(error,OSError)and error.errno in (errno.EPERM,errno.EACCES):return 'permission_denied'
    return None

def owned_target_ready(public_ip):
    try:
        s=socket.create_connection((public_ip,22),timeout=2)
        try:return True
        finally:s.close()
    except OSError:return False

def valid_functional(result,before,after):
    fields={'root_home_blocked','operator_home_blocked','source_write_blocked','loopback_connects','nonloopback_connect_blocked'}
    return type(result)is dict and set(result)==fields|{'nonloopback_denial_mode'} and before is True and after is True and all(result[n]is True for n in fields)and result['nonloopback_denial_mode']in ('permission_denied','bounded_timeout')

def observe(commit,public_ip):
    if os.getuid()!=0:raise ValueError('root_operator_required')
    addr=ipaddress.ip_address(public_ip)
    if not addr.is_global or addr.version!=4:raise ValueError('owned_IP_refused')
    import re
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('release_refused')
    p=subprocess.run(['systemctl','show',UNIT,'-p','MainPID','-p','ControlGroup','-p','DynamicUser','-p','NoNewPrivileges','-p','ProtectHome','-p','ProtectSystem','-p','User','-p','IPAddressAllow','-p','IPAddressDeny','-p','MemoryMax','-p','MemorySwapMax','-p','TasksMax','-p','KillMode','-p','OOMPolicy','-p','CPUQuotaPerSecUSec','-p','StandardOutput','-p','StandardError'],capture_output=True,timeout=10,check=True)
    props=dict(x.split('=',1)for x in p.stdout.decode().splitlines()if'='in x)
    if props.get('ControlGroup')!='/system.slice/'+UNIT or props.get('DynamicUser')!='yes' or props.get('NoNewPrivileges')!='yes' or props.get('ProtectSystem')!='strict' or props.get('ProtectHome')!='yes' or props.get('KillMode')!='control-group' or props.get('OOMPolicy')!='kill' or props.get('StandardOutput')!='null' or props.get('StandardError')!='null':raise ValueError('unit_policy_unavailable')
    pid=int(props['MainPID']);assert pid>1;group=Path('/sys/fs/cgroup')/props['ControlGroup'].lstrip('/')
    controls={n:(group/n).read_text().strip()for n in ['memory.max','memory.swap.max','pids.max','cpu.max','memory.oom.group']}
    quota,period=map(int,controls['cpu.max'].split())
    if controls['memory.max']!='402653184' or controls['memory.swap.max']!='0'or controls['pids.max']!='64'or quota!=period or controls['memory.oom.group']!='1':raise ValueError('resource_limits_unavailable')
    status=dict(x.split(':',1)for x in Path('/proc',str(pid),'status').read_text().splitlines()if':'in x);uid=int(status['Uid'].split()[0]);gid=int(status['Gid'].split()[0])
    if uid==0 or gid==0 or status.get('NoNewPrivs','').strip()!='1' or int(status.get('CapEff','0').strip(),16)!=0:raise ValueError('process_privilege_unavailable')
    attachments={'ingress':bpf_count(group,0),'egress':bpf_count(group,1)}
    outside_before=owned_target_ready(public_ip)
    if not outside_before:raise ValueError('outside_target_control_unavailable')
    readfd,writefd=os.pipe();child=os.fork()
    if child==0:
        os.close(readfd)
        try:
            # Join only this new service's cgroup and mount namespace, then drop
            # privileges; this tests effective IP filters and protected mounts.
            (group/'cgroup.procs').write_text(str(os.getpid()))
            mnt=os.open('/proc/'+str(pid)+'/ns/mnt',os.O_RDONLY)
            try:os.setns(mnt,0)
            finally:os.close(mnt)
            os.setgroups([]);os.setgid(gid);os.setuid(uid)
            result={}
            for name,path in [('root_home','/root'),('operator_home','/home/debian')]:
                try:
                    f=os.open(path,os.O_RDONLY|os.O_DIRECTORY);os.close(f);result[name+'_blocked']=False
                except PermissionError:result[name+'_blocked']=True
            target=Path('/opt/aitrustid-ai-tools/releases')/commit/'source'/'OWNED_PERMISSION_PROBE'
            try:
                f=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(f);target.unlink();result['source_write_blocked']=False
            except OSError as e:result['source_write_blocked']=e.errno in (errno.EACCES,errno.EROFS,errno.EPERM)
            s=socket.create_connection(('127.0.0.1',8790),timeout=2);s.close();result['loopback_connects']=True
            s=socket.socket();s.settimeout(2)
            try:s.connect((public_ip,22));result['nonloopback_connect_blocked']=False;result['nonloopback_denial_mode']=None
            except OSError as e:
                mode=denial_mode(e);result['nonloopback_connect_blocked']=mode is not None;result['nonloopback_denial_mode']=mode
            finally:s.close()
            os.write(writefd,json.dumps(result).encode())
        except Exception:os.write(writefd,b'{"probe_unavailable":true}')
        finally:os.close(writefd);os._exit(0)
    os.close(writefd)
    try:
        import select,time
        if not select.select([readfd],[],[],8)[0]:os.kill(child,9);raise ValueError('probe_timeout')
        raw=os.read(readfd,4097)
    finally:os.close(readfd);os.waitpid(child,0)
    result=json.loads(raw)
    outside_after=owned_target_ready(public_ip)
    if not valid_functional(result,outside_before,outside_after):raise ValueError('functional_isolation_unavailable')
    return {'pass':True,'captured_at':datetime.now(timezone.utc).isoformat(),'profile':'actual-api-service-isolation-1','release_commit':commit,'unit_policy':{k:v for k,v in props.items()if k not in ['MainPID','User']},'effective_cgroup_controls':controls,'actual_BPF_attachment_counts':attachments,'main_process_nonroot_no_capabilities_no_new_privileges':True,'actual_mount_and_cgroup_probe':result,'same_owned_nonloopback_target_connects_outside_cgroup_before_and_after':outside_before and outside_after,'contents_of_homes_or_database_read':False,'limits':['Packet filtering can produce a bounded TCP timeout rather than a syscall permission error; two positive outside-cgroup controls and attached BPF are required.','Functional probe joins the actual service cgroup and mount namespace, then drops to its dynamic UID; it does not claim to duplicate every execution restriction.','No data or credentials are submitted, stored, read or reported; nonloopback test targets only the operator-approved own primary address TCP22.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit',required=True);p.add_argument('--own-public-ip',required=True);a=p.parse_args()
    try:print(json.dumps(observe(a.commit,a.own_public_ip),indent=2))
    except Exception:print('{"pass":false,"reason":"effective_api_isolation_unavailable"}');raise SystemExit(1)
