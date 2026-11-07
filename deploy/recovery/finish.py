#!/usr/bin/env python3
"""Reboot, verify and remove only the explicitly selected recovery VM."""
import argparse, hashlib, json, os, re, runpy, shutil, subprocess, time
from pathlib import Path
BASE=Path('/var/lib/aitrust-id/recovery-vm');CACHE=Path('/var/lib/aitrust-id/recovery-source')
def check(ok):
    if not ok:raise ValueError('Recovery finalization refused')
def run(args, *, check_status=True, timeout=60):return subprocess.run(list(map(str,args)),stdin=subprocess.DEVNULL,capture_output=True,check=check_status,timeout=timeout)
def load(path,prefix):
    check(path.parent==CACHE and re.fullmatch(prefix+'-[a-f0-9]{64}[.]py',path.name));s=path.lstat();check(s.st_uid==0 and not s.st_mode&0o077 and not path.is_symlink());check(hashlib.sha256(path.read_bytes()).hexdigest()==path.name[len(prefix)+1:-3]);return runpy.run_path(str(path))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['reboot','verify','cleanup']);p.add_argument('--work',required=True,type=Path);p.add_argument('--isolation-tool',required=True,type=Path);p.add_argument('--guest-tool',required=True,type=Path);a=p.parse_args()
    check(os.geteuid()==0);tools=load(a.isolation_tool,'isolate');w=tools['workdir'](a.work);controller=tools['ssh'];row=json.loads((w/'isolation.json').read_text());check(row['only_loopback'] is True)
    if a.action=='reboot':
        check((w/'recovery-result.json').exists() and (w/'monitoring-result.json').exists() and not (w/'reboot-before.json').exists())
        before=json.loads(controller(w,"sudo python3 -c \"import json;from pathlib import Path;print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))\"",isolated=True).stdout)
        (w/'reboot-before.json').write_text(json.dumps({'sha256':hashlib.sha256(before['boot'].encode()).hexdigest()})+'\n');(w/'reboot-before.json').chmod(0o600)
        controller(w,'sudo systemd-run --quiet --on-active=2s /usr/bin/systemctl reboot',isolated=True)
        print(json.dumps({'reboot_requested':True}));return
    if a.action=='verify':
        before=json.loads((w/'reboot-before.json').read_text());deadline=time.monotonic()+60
        while tools['inspect'](w)['guest_ready'] is not True:
            check(time.monotonic()<deadline);time.sleep(2)
        boot=controller(w,'cat /proc/sys/kernel/random/boot_id',isolated=True).stdout.decode().strip();check(hashlib.sha256(boot.encode()).hexdigest()!=before['sha256'])
        proof=json.loads(controller(w,'sudo python3 /etc/aitrust-recovery/restore-guest.py --nonce '+w.name+' --verify-only',isolated=True,timeout=120).stdout);check(proof['pass'] is True)
        host=load(a.guest_tool,'guest');check(host['snapshot']()==json.loads((w/'control.json').read_text())['primary_before'])
        monitor=json.loads((w/'monitoring-result.json').read_text());check(monitor['pass'] is True)
        health=run(['python3','/opt/aitrust-id/backup/source-health.py']);check(json.loads(health.stdout)['passed'] is True)
        result={'pass':True,'captured_at':time.time(),'restored_guest_checks_pass':True,'recovered_guest_rebooted':True,'source_host_identity_configuration_and_services_unchanged':True,'actual_source_archive_health_passes':True,'monitoring_checks_pass':True,'actual_database_inventory_tables':proof['table_count'],'source_repository_contains_application_rows':proof['table_count']>0,'production_collection_enabled':False,'cross_provider_failover':False,'physical_or_human_acceptance':False,'operator_response_sla_claimed':False,'guest_kernel':proof['actual_guest_kernel']}
        (w/'final-verification.json').write_text(json.dumps(result,indent=2)+'\n');(w/'final-verification.json').chmod(0o600);print(json.dumps(result));return
    proof=json.loads((w/'final-verification.json').read_text());check(proof['pass'] is True)
    # Content-hash metadata is public code; all temporary recovery data and
    # throwaway credentials live under this nonce. Never remove source backups.
    base_unit='aitrust-recovery-'+w.name[:16];check(row['unit']==base_unit+'-isolated')
    run(['systemctl','stop',row['unit']],check_status=False)
    check(run(['systemctl','is-active',row['unit']],check_status=False).stdout.strip()!=b'active')
    check(not Path('/proc/'+str(row['pid'])).exists())
    control=json.loads((w/'control.json').read_text());check(load(a.guest_tool,'guest')['snapshot']()==control['primary_before'])
    parent=w.parent;shutil.rmtree(w);check(not w.exists() and parent==BASE)
    result={'pass':True,'captured_at':time.time(),'nonce_guest_removed':True,'private_test_key_and_recovery_material_removed':True,'decrypted_guest_disk_removed':True,'encrypted_staging_copy_removed':True,'source_host_unchanged':True,'original_protected_backup_generations_untouched':True,'physical_erasure_claimed':False}
    print(json.dumps(result))
if __name__=='__main__':main()
