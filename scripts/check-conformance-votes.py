#!/usr/bin/env python3
"""Check signed ballots against separately trusted scope and role-register pins."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.corpus import read_regular
from protocol.evidence import unique,reject,finite


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ballots',type=Path)
    p.add_argument('--roster',type=Path,required=True);p.add_argument('--roster-sha256',required=True)
    p.add_argument('--decision',type=Path,required=True);p.add_argument('--decision-sha256',required=True)
    args=p.parse_args()
    from tools.conformance_recusal import assess,load_pinned
    roster=load_pinned(args.roster,args.roster_sha256);decision=load_pinned(args.decision,args.decision_sha256)
    ballot_path=args.ballots.absolute()
    if any(p.is_symlink() for p in [ballot_path,*ballot_path.parents]):raise ValueError('Linked input refused')
    raw=read_regular(ballot_path,524288)
    ballots=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=unique,parse_constant=reject);finite(ballots)
    result=assess(roster,decision,ballots,args.roster_sha256,args.decision_sha256)
    # Recheck the trusted documents rather than trusting a voter-selected replacement.
    load_pinned(args.roster,args.roster_sha256);load_pinned(args.decision,args.decision_sha256)
    if read_regular(ballot_path,524288)!=raw:raise ValueError('Ballots changed during execution')
    print(json.dumps(result,indent=2))
    return 0 if result['pass'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except ImportError:
        print(json.dumps({'profile':'conformance-recusal-check/v1','pass':False,
            'reason':'policy_dependencies_unavailable','policy_check_only':True,
            'certification_granted':False,'RFC_adoption_granted':False}))
        raise SystemExit(2)
    except (ValueError,TypeError,KeyError,OSError,RecursionError):
        print(json.dumps({'profile':'conformance-recusal-check/v1','pass':False,
            'reason':'invalid_or_unavailable_policy_input','policy_check_only':True,
            'certification_granted':False,'RFC_adoption_granted':False}))
        raise SystemExit(2)
