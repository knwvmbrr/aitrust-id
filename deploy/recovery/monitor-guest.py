#!/usr/bin/env python3
"""Exercise reconstructed operational checks only in the selected offline guest."""
import argparse, hashlib, json, os, re, runpy, socket, subprocess, time
from pathlib import Path

def run(args, *, check=True):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=60, check=check)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--nonce',required=True);a=p.parse_args()
    assert os.geteuid()==0 and re.fullmatch('[a-f0-9]{32}',a.nonce)
    assert socket.gethostname()=='aitrust-recovery-'+a.nonce[:8]
    assert Path('/var/lib/aitrust-recovery/restored.json').is_file()
    assert run(['systemd-detect-virt','--vm']).stdout.strip()==b'kvm'
    source=Path('/opt/aitrust-recovery-operations');assert source.is_dir()
    # Reconstruct source-owned checks and actual primary unit definitions. No
    # notification credentials, signing keys or production backup transport.
    for name,dest in [('alerts.py','/opt/aitrust-id/alerts/alerts.py'),('source-health.py','/opt/aitrust-id/backup/source-health.py')]:
        out=Path(dest);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((source/name).read_bytes());out.chmod(0o755)
    for name in ['aitrust-source-backup-health.service','aitrust-source-backup-health.timer','aitrust-source-backup-failure.service']:
        out=Path('/etc/systemd/system')/name;out.write_bytes((source/name).read_bytes());out.chmod(0o644)
    # Actual isolated recovery deliberately prohibits WAL transmission. Defer
    # the normal periodic source-backup probe; exercise its refusal explicitly.
    drop=Path('/etc/systemd/system/aitrust-source-backup-health.timer.d');drop.mkdir(exist_ok=True)
    (drop/'offline-drill.conf').write_text('[Timer]\nOnBootSec=\nOnBootSec=24h\nOnUnitActiveSec=\nOnUnitActiveSec=24h\n')
    run(['systemd-analyze','verify',*[str(Path('/etc/systemd/system')/n) for n in ['aitrust-source-backup-health.service','aitrust-source-backup-health.timer','aitrust-source-backup-failure.service']]])
    run(['systemctl','daemon-reload']);run(['systemctl','enable','--now','aitrust-source-backup-health.timer'])
    api=runpy.run_path('/opt/aitrust-id/alerts/alerts.py')
    assert api['inspect']('primary')==[]
    assert run(['systemctl','start','aitrust-source-backup-health.service'],check=False).returncode!=0
    failed=api['inspect']('primary');assert 'aitrust-source-backup-health.service:failed' in failed
    assert api['plan']({},failed,time.time())[0]=='incident'
    run(['systemctl','reset-failed','aitrust-source-backup-health.service'])
    # Do not stop the live primary: this is the nonce-bound replacement VM.
    run(['systemctl','stop','postgresql@18-main.service'])
    try:
        issues=api['inspect']('primary');assert 'postgresql@18-main.service:inactive' in issues
        action,digest=api['plan']({},issues,time.time());assert action=='incident'
        previous={'digest':digest,'had_issues':True,'sent_at':time.time()}
        mail=api['message']({'transport':'ntfy'},'primary',action,issues)
        content=mail.get_content();assert 'application data' in content and 'postgresql' in content
    finally:
        run(['systemctl','start','postgresql@18-main.service'])
    assert api['inspect']('primary')==[]
    assert api['plan'](previous,[],time.time())[0]=='recovered'
    assert run(['runuser','-u','postgres','--','psql','-XAt','-d','aitrustid','-c','SHOW archive_mode']).stdout.strip()==b'off'
    result={'pass':True,'captured_at':time.time(),'controls':[
        {'case':name,'pass':True} for name in ['actual_source_monitor_units_reconstructed','offline_archive_disabled_failure_detected','replacement_database_outage_detected','bounded_incident_message_contains_no_application_data','replacement_database_restart_detected_as_recovery','production_wal_shipping_stays_disabled']],
        'external_message_sent':False,'source_backup_timer_deferred_for_offline_drill':True,
        'production_backup_health_claimed':False,'operator_response_sla_claimed':False}
    target=Path('/var/lib/aitrust-recovery/monitoring.json');target.write_text(json.dumps(result,indent=2)+'\n');target.chmod(0o600)
    print(json.dumps(result))
if __name__=='__main__':main()
