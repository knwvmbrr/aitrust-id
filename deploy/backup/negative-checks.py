#!/usr/bin/env python3
"""Execute destructive attempts only against synthetic markers/test copies."""
import configparser
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import uuid


def run(args):
    return subprocess.run(args, text=True, errors='replace', capture_output=True, check=False, timeout=120)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    os.umask(0o077)
    checks={}
    base=Path('/var/lib/aitrust-id/protected')
    generation=(base/'current').resolve(strict=True)
    marker=base/('.permission-probe-'+uuid.uuid4().hex)
    marker.write_text('synthetic permission probe\n')
    try:
        checks['repository_account_cannot_read_protected']=run(['runuser','-u','pgbackrest','--','cat',str(marker)]).returncode!=0
        checks['repository_account_cannot_delete_protected']=run(['runuser','-u','pgbackrest','--','rm',str(marker)]).returncode!=0 and marker.exists()
        checks['repository_account_cannot_overwrite_protected']=run(['runuser','-u','pgbackrest','--','touch',str(marker)]).returncode!=0
    finally:
        marker.unlink(missing_ok=True)
    candidates=sorted(generation.glob('backup/aitrustid/*/pg_data/PG_VERSION*'))
    if not candidates:
        raise RuntimeError('Expected restored data file not present')
    rel=candidates[0].relative_to(generation)
    working=Path('/var/lib/pgbackrest')/rel
    checks['protected_file_independent_of_working_inode']=candidates[0].stat().st_ino!=working.stat().st_ino
    test=Path('/var/lib/aitrust-id/backup-checks')/uuid.uuid4().hex
    test.mkdir(parents=True,mode=0o700)
    copy=test/'corrupt-repository'
    copy.mkdir(mode=0o700)
    p=run(['rsync','-rt','--no-links','--no-specials','--no-devices',str(generation)+'/',str(copy)+'/'])
    if p.returncode:
        raise RuntimeError('Unable to create disposable corruption-test copy')
    file=copy/rel
    data=bytearray(file.read_bytes())
    checks['encrypted_file_header']=data[:8]==b'Salted__'
    data[min(32,len(data)-1)]^=1
    file.write_bytes(data)
    verify=run(['pgbackrest','--allow-root','--stanza=aitrustid','--repo1-path='+str(copy),'--output=text','--verbose','verify'])
    module_spec=importlib.util.spec_from_file_location('cycle',Path(__file__).with_name('cycle.py'))
    cycle=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cycle)
    checks['corrupted_copy_rejected']=verify.returncode!=0 or not cycle.verification_valid(verify.stdout)
    config=configparser.ConfigParser(interpolation=None)
    config.read('/etc/pgbackrest/pgbackrest.conf')
    config['global']['repo1-path']=str(generation)
    config['global']['repo1-cipher-pass']='incorrect-key-for-disposable-negative-test-only'
    wrong=test/'wrong-key.conf'
    with wrong.open('w') as stream:
        config.write(stream)
    wrong.chmod(0o600)
    wrong_result=run(['pgbackrest','--allow-root','--config='+str(wrong),'--stanza=aitrustid','--output=json','info'])
    try:
        wrong_info=json.loads(wrong_result.stdout)
        accepted=bool(wrong_info) and wrong_info[0]['status']['code']==0 and bool(wrong_info[0].get('backup'))
    except (ValueError,KeyError,TypeError):
        accepted=False
    checks['wrong_cipher_key_rejected']=wrong_result.returncode!=0 or not accepted
    print(json.dumps({'scope':'synthetic_backup_negative_checks','checks':checks,
                      'corrupt_verify_exit':verify.returncode,'passed':all(checks.values())},indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__=='__main__':
    main()
