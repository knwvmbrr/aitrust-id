#!/usr/bin/env python3
"""Execute invented private revision practice and refusal controls; no tag gate."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
SOURCES=("tools/session_revisions.py","scripts/review-session-revision.py","scripts/prepare-session-revision-demo.py","scripts/prepare-session-selections.py","scripts/verify-session-revisions.py","protocol/corpus.py","protocol/normalization.py","protocol/unicode15-data.json","tools/blind_review_io.py","protocol/reports.py","tests/test_session_revisions.py")
def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
def verify():
    if sys.flags.optimize:raise ValueError("Run verification with checks enabled.")
    before=hashes();controls=[];work=Path(tempfile.mkdtemp(prefix="aitrust-context-practice-"));work.chmod(0o700)
    def run(name,args,exit_status):
        result=subprocess.run([sys.executable,"-I","-B",*args],cwd=ROOT,capture_output=True,timeout=30)
        assert result.returncode==exit_status and b"PRIVATE_CANARY" not in result.stdout+result.stderr
        if exit_status==2:assert not result.stdout
        controls.append({"case":name,"exit_status":result.returncode,"pass":True,"stdout_sha256":hashlib.sha256(result.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(result.stderr).hexdigest()})
        return json.loads(result.stdout) if result.stdout else None
    try:
        practice=work/"practice";generator=[str(ROOT/"scripts/prepare-session-revision-demo.py"),"--output",str(practice)]
        run("invented_private_practice_created",generator,0)
        sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in practice.iterdir()}
        cli=[str(ROOT/"scripts/review-session-revision.py")]
        for name,file in [("previous","previous.txt"),("current","current.txt"),("context","context.json"),("selections","selections.json")]:cli += ["--"+name,str(practice/file)]
        summary=run("literal_arithmetic_absence_is_not_outside_knowledge",cli,0)
        assert summary["new_literals_not_located_in_captured_context"]==1 and not summary["outside_knowledge_established"]
        assert not summary["semantic_derivation_assessed"] and not summary["tag_asserted"]
        assert "sha256" not in json.dumps(summary) and "invented-context" not in json.dumps(summary)
        details=work/"details";run("new_private_details_created",cli+["--details",str(details)],0)
        detail=json.loads((details/"revision-context.json").read_text())
        assert not detail["ai_authorship_established"] and not detail["human_authorship_established"]
        spans=work/"spans.json";spans.write_bytes(b'[[14,15]]');spans.chmod(0o600)
        prepared=work/"prepared"
        bind=[str(ROOT/"scripts/prepare-session-selections.py"),"--previous",str(practice/"previous.txt"),"--current",str(practice/"current.txt"),"--context",str(practice/"context.json"),"--spans",str(spans),"--output",str(prepared)]
        run("selected_spans_bound_without_manual_hashing",bind,0)
        assert (prepared/"selections.json").read_bytes()==(practice/"selections.json").read_bytes()
        run("existing_prepared_selection_refused",bind,2)
        spans.write_bytes(b'[[true,15]]')
        invalid=list(bind);invalid[-1]=str(work/"invalid-preparation")
        run("invalid_preparation_span_refused",invalid,2)
        assert not (work/"invalid-preparation").exists()
        run("unknown_preparation_argument_not_echoed",[str(ROOT/"scripts/prepare-session-selections.py"),"--unknown","PRIVATE_CANARY"],2)
        run("existing_details_refused",cli+["--details",str(details)],2)
        run("existing_practice_refused",generator,2)
        current=practice/"current.txt";original=current.read_bytes();current.chmod(0o644)
        run("public_input_permissions_refused",cli,2);current.chmod(0o600)
        linked=practice/"linked.txt";os.link(current,linked)
        run("hard_linked_private_input_refused",cli,2);linked.unlink()
        current.unlink();current.symlink_to(practice/"previous.txt")
        run("private_input_symlink_refused",cli,2);current.unlink();current.write_bytes(original);current.chmod(0o600)
        selection=practice/"selections.json";raw=selection.read_bytes();data=json.loads(raw);data["current_sha256"]="0"*64;selection.write_text(json.dumps(data))
        run("stale_selection_hash_refused",cli,2);selection.write_bytes(raw)
        data=json.loads(raw);data["private_example"]="PRIVATE_CANARY";selection.write_text(json.dumps(data))
        run("unknown_private_field_refused_without_echo",cli,2);selection.write_bytes(raw)
        current.write_bytes(b"\xff")
        run("invalid_utf8_private_input_refused",cli,2);current.write_bytes(original)
        run("unknown_private_argument_not_echoed",[str(ROOT/"scripts/review-session-revision.py"),"--unknown","PRIVATE_CANARY"],2)
        assert sources=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in practice.iterdir()}
        assert all(p.stat().st_mode&0o077==0 for p in practice.iterdir())
        controls.append({"case":"owned_private_inputs_unchanged","pass":True})
    finally:shutil.rmtree(work)
    assert not work.exists()
    stable=before==hashes()
    return {"captured_at":datetime.now(timezone.utc).isoformat(),"pass":stable,"sources":before,"source_unchanged_during_execution":stable,"controls":controls,"owned_private_work_removed":True,"semantic_derivation_assessed":False,"outside_knowledge_established":False,"tag_asserted":False,"actual_participant_data":False,"requirements_closed":0}
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    proof=verify();write_report(args.output,proof);print(json.dumps({"pass":proof["pass"],"actual_control_groups":len(proof["controls"]),"owned_private_work_removed":proof["owned_private_work_removed"]}));raise SystemExit(0 if proof["pass"] else 1)
