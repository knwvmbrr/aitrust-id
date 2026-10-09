#!/usr/bin/env python3
"""Monitor archive failures and storage reserve without reading application data."""
import json
import os
import subprocess
import sys


def main():
    if os.geteuid()!=0:
        raise SystemExit('Run as root')
    query="""SELECT jsonb_build_object(
        'archive_enabled', current_setting('archive_mode')='on',
        'archive_failure_pending', COALESCE(last_failed_time > last_archived_time, last_failed_time IS NOT NULL),
        'wal_bytes', (SELECT sum(size) FROM pg_ls_waldir()),
        'database_healthy', true) FROM pg_stat_archiver"""
    p=subprocess.run(['runuser','-u','postgres','--','psql','--no-psqlrc','-XAt',
                      '--set','ON_ERROR_STOP=1','-d','aitrustid','-c',query],
                     capture_output=True,text=True,timeout=20)
    disk=os.statvfs('/var/lib/postgresql')
    checks={'database_query_works':p.returncode==0,
            'database_free_space_above_20_percent':disk.f_bavail/disk.f_blocks >= 0.20}
    if p.returncode==0:
        state=json.loads(p.stdout)
        checks['archive_enabled']=state['archive_enabled']
        checks['no_pending_archive_failure']=not state['archive_failure_pending']
        limit=min(8*1024**3, disk.f_blocks*disk.f_frsize//10)
        checks['wal_storage_within_reserve']=state['wal_bytes']<=limit
    print(json.dumps({'scope':'source_archive_storage_health','checks':checks,
                      'passed':all(checks.values()),'external_notification_delivery_verified':False},indent=2))
    return int(not all(checks.values()))


if __name__=='__main__':
    sys.exit(main())
