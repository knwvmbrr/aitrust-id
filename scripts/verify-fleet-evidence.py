#!/usr/bin/env python3
"""Require actual current Mac/Linux fleet software evidence for full F-159 closure."""
import argparse,ast,json,runpy,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence
h=runpy.run_path(str(ROOT/'scripts/verify-fleet.py'))['hashes']
def cases():
    tree=ast.parse((ROOT/'tests/test_fleet.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Fleet')
    return sorted(n.name for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
def verify(row,platform):
    def require(ok):
        if not ok:raise ValueError('Fleet execution evidence refused')
    require(row['format']=='fleet-software-engineering/v1' and row['platform']==platform and platform in ('darwin','linux'))
    for key in ['pass','non_root','source_unchanged','actual_cli_processes','synthetic_credentials_and_inputs_only']:require(row[key] is True)
    for key in ['enrolled_real_devices','production_changed','collection_enabled','commercial_service_activated','independent_accuracy_evidence','human_acceptance','physical_phone_tested']:require(row[key] is False)
    if platform=='linux':require(row['isolated_network_namespace'] is True)
    require(row['sources']==h() and row['cases']==cases() and row['test_count']==len(cases()) and row['test_count']>=32)
    require(row['failures']==row['errors']==row['skipped']==0)
    stamp=datetime.fromisoformat(row['captured_at']);require(stamp.tzinfo is not None and stamp<=datetime.now(timezone.utc))
    return {'pass':True,'platform':platform,'cases':row['test_count'],'sources_current':True,'public_tag_release':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--macos',type=Path,default=ROOT/'runs/2026-11-09-fleet-accepted-macos.json');p.add_argument('--linux',type=Path,default=ROOT/'runs/2026-11-09-fleet-accepted-linux.json');a=p.parse_args()
    try:print(json.dumps({'pass':True,'profiles':[verify(read_evidence(a.macos),'darwin'),verify(read_evidence(a.linux),'linux')]}));return 0
    except Exception:print('{"pass":false,"reason":"fleet_execution_missing_or_stale"}');return 1
if __name__=='__main__':raise SystemExit(main())
