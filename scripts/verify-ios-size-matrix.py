#!/usr/bin/env python3
"""Run separately reviewed representative layout checks on owned Simulators only."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.ios_simulator_matrix import run,Unavailable

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--profiles',nargs='+',choices=['small','regular','plus','max'],required=True);a=p.parse_args()
    try:
        v=run(a.output,a.profiles);print(json.dumps({'pass':v['pass'],'requested_profiles':v['requested_profiles'],'executed_profiles':v['executed_profiles'],'physical_device':False,'human_accessibility':False,'seven_workflow_acceptance':False}));return 0 if v['pass'] else 2
    except (Unavailable,ValueError,OSError,KeyboardInterrupt) as error:
        uncertain=getattr(error,'output_may_exist',False) is True
        print(json.dumps({'pass':False,'state':'OUTPUT_UNCERTAIN' if uncertain else 'UNAVAILABLE','private_output_may_remain':True,'physical_device':False,'human_accessibility':False}));return 3 if uncertain else 2
if __name__=='__main__':raise SystemExit(main())
