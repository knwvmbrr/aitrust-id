#!/usr/bin/env python3
"""Inspect fourteen real graphs and bind an explicit artifact to its SPDX/signature."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).absolute().parents[1]))
from tools import distribution_artifacts as tool
from tools.artifact_evidence_io import Capture,PrivateInputError,OutputCommitUncertain,need

class Parser(argparse.ArgumentParser):
    def error(self,_):raise PrivateInputError('Artifact command unavailable.')


def main():
    p=Parser(description=__doc__,allow_abbrev=False)
    p.add_argument('action',choices=('graph','prepare','inspect','spdx','verify-attestation','authorize-release'))
    p.add_argument('--route',required=True,choices=sorted(tool.ROUTES));p.add_argument('--artifact',type=Path)
    p.add_argument('--commit');p.add_argument('--packet',type=Path);p.add_argument('--sbom',type=Path)
    p.add_argument('--bundle',type=Path);p.add_argument('--trusted-root',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.action=='graph':
        need(not any((a.artifact,a.commit,a.packet,a.sbom,a.bundle,a.trusted_root)))
        result=tool.graph(a.route)
        if a.output:tool.save_packet(result,a.output)
        return {'state':'INSPECTED','route':a.route,'components':len(result['nodes']),'unresolved_scopes':len(result['coverage_gaps']),'release_authorized':False}
    need(a.artifact is not None and a.commit is not None)
    if a.action=='prepare':
        need(a.output is not None and not any((a.packet,a.sbom,a.bundle,a.trusted_root)))
        result=tool.prepare(a.route,a.artifact,a.commit);tool.publish_bound(result,a.artifact,a.route,a.commit,a.output)
        return {'state':'PREPARED','route':a.route,'release_authorized':False}
    need(a.packet is not None)
    with Capture()as c:record=tool.parse(c.read(a.packet,tool.MAX_PACKET,private=False))
    tool.verify_packet(record,a.artifact,a.route,a.commit)
    if a.action in ('inspect','spdx'):
        need(not any((a.sbom,a.bundle,a.trusted_root)))
        if a.action=='spdx':need(a.output is not None);tool.publish_bound(record,a.artifact,a.route,a.commit,a.output,spdx_only=True)
        elif a.output:tool.save_packet({'state':'VERIFIED','route':a.route,'packet_matches':True,'release_authorized':False},a.output)
        return {'state':'VERIFIED','route':a.route,'packet_matches':True,'release_authorized':False}
    need(all((a.sbom,a.bundle,a.trusted_root)))
    operation=tool.verify_attestation if a.action=='verify-attestation'else tool.authorize_release
    result=operation(record,a.artifact,a.sbom,a.bundle,a.trusted_root,a.route,a.commit)
    if a.output:tool.save_packet(result,a.output)
    return {k:result[k]for k in ('state','route','attestation_verified','release_authorized')}

if __name__=='__main__':
    try:print(json.dumps(main(),sort_keys=True))
    except OutputCommitUncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}',file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,KeyError,TypeError,RecursionError,UnicodeError,RuntimeError,ImportError):
        print('{"state":"UNAVAILABLE","reason":"artifact_evidence_refused"}',file=sys.stderr);raise SystemExit(2)
