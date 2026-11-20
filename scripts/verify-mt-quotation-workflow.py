#!/usr/bin/env python3
"""Actual authored CLI controls for the selected quotation workflow, not accuracy."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from protocol.normalization import normalize_nfc
from tools import mt_workflow as workflow
from tools import authority_quotation

NAMES=('tools/mt_workflow.py','tools/mt_quotation_component.py','scripts/mt-evidence-worker.py',
 'scripts/check-mt-evidence.py','scripts/verify-mt-quotation-workflow.py','scripts/worker_process.py',
 'tools/authority_quotation.py','scripts/authority-quotation.py','tools/language_observations.py',
 'tools/choice_framing.py','tools/blind_review_io.py','protocol/normalization.py',
 'protocol/unicode15-data.json','protocol/corpus.py','tests/test_mt_quotation_workflow.py',
 'tests/test_mt_workflow.py','tests/test_authority_quotation.py','docs/mt-quotation-workflow.md',
 'docs/mt-evidence-workflow.md','docs/authority-quotation.md')
TEXT='The training example says "Experts agree".'

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Quotation workflow controls refused; use --help.\n')


def main():
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    inventory=lambda:{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in NAMES}
    before=inventory();checks=[]
    command=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-mt-evidence.py'),'--language','en']
    def case(name,argv,text,exit_code,contains=()):
        result=subprocess.run(argv,input=text,capture_output=True,timeout=15)
        assert result.returncode==exit_code,name
        assert all(s.encode() in result.stdout for s in contains),name
        assert b'SYNTHETIC_PRIVATE_CANARY' not in result.stdout+result.stderr,name
        checks.append({'id':name,'observed_exit_status':result.returncode,'pass':True})
        return result
    with tempfile.TemporaryDirectory(prefix='mt-quotation-controls-') as folder:
        private=Path(folder);os.chmod(private,0o700)
        # Reconstruct only the exact prerequisite files of the committed old CLI.
        # This demonstrates the new explicit option was absent without modifying
        # current code or invoking another checkout/installed package.
        base=private/'old-cli';base.mkdir()
        prerequisites=('tools/mt_workflow.py','scripts/mt-evidence-worker.py','scripts/check-mt-evidence.py',
            'scripts/worker_process.py','protocol/normalization.py','protocol/unicode15-data.json',
            'tools/language_observations.py','protocol/corpus.py','tools/blind_review_io.py')
        for name in prerequisites:
            file=base/name;file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(subprocess.check_output(['git','show','eb7873ddc861bfadf921d50d338ab2d2607e0d8b:'+name],cwd=ROOT))
        baseline=subprocess.run([sys.executable,'-I','-S','-B',str(base/'scripts/check-mt-evidence.py'),
            '--language','en','--check','authority-quotation'],input=TEXT.encode(),capture_output=True,timeout=15)
        assert baseline.returncode==2 and b'Framing check refused' in baseline.stderr
        checks.append({'id':'committed_baseline_option_unavailable','observed_exit_status':2,'pass':True})
        selected=command+['--check','authority-quotation']
        case('selected_quote_retained',selected,TEXT.encode(),0,('1 quoted phrase(s); 0 outside phrase(s) without',))
        case('legacy_authority_preserved',command+['--check','authority'],TEXT.encode(),0,('Authority: An authority phrase',))
        case('quoted_marker_not_borrowed',selected,b'Experts agree; the example is "https://example.invalid".',0,
             ('0 quoted phrase(s); 1 outside phrase(s) without',))
        case('outside_marker_retained_unverified',selected,b'Experts agree; see [1].',0,
             ('1 outside phrase(s) with a marker','sources are not verified'))
        case('unsupported_quote_partial_not_global',command+['--check','authority-quotation','--check','urgency'],
             'Buy now. “Experts agree”'.encode(),3,('Authority quotation: unavailable','Urgency: A supported'))
        case('unsupported_quote_not_zero',selected,'“Experts agree”'.encode(),2,('Authority quotation: unavailable',))
        case('no_supported_phrase_is_not_a_verdict',selected,b'A plain unrelated paragraph.',0,('0 quoted phrase(s); 0 outside phrase(s)',))
        case('invalid_utf8_refused',selected,b'\xffSYNTHETIC_PRIVATE_CANARY',2)
        case('duplicate_selection_refused',selected+['--check','authority-quotation'],TEXT.encode(),2)
        dense='Buy now. '+'; '.join('Experts agree' for _ in range(128))+' '+(' [1]'*100)
        case('full_record_budget_refused_not_clipped',selected,dense.encode(),2,('Authority quotation: unavailable',))
        output=private/'evidence';text='Cafe\u0301: '+TEXT+' SYNTHETIC_PRIVATE_CANARY'
        case('explicit_private_full_record',selected+['--details',str(output)],text.encode(),0,('1 quoted phrase(s)',))
        artifact=output/'framing-evidence.json';raw=artifact.read_bytes();record=json.loads(raw);row=record['checks'][0]
        assert record['format']==workflow.CONTEXT_PROFILE and row['original']==authority_quotation.observe(text,'en')[1]
        assert row['raw_subject_sha256']==hashlib.sha256(text.encode()).hexdigest()
        assert row['subject_sha256']==hashlib.sha256(normalize_nfc(text).encode()).hexdigest()
        assert row['sources']==workflow.identity(workflow.QUOTATION)
        assert artifact.stat().st_mode&0o777==0o600 and output.stat().st_mode&0o777==0o700
        assert b'SYNTHETIC_PRIVATE_CANARY' not in raw and record['tag_asserted'] is False
        case('private_no_overwrite',selected+['--details',str(output)],b'Experts agree.',2)
        assert artifact.read_bytes()==raw
        packet=private/'choice'
        case('prepare_existing_synthetic_choice_context',[sys.executable,'-I','-S','-B',str(ROOT/'scripts/prepare-choice-demo.py'),'--output',str(packet)],b'',0)
        case('all_four_explicit_checks_complete',command+['--check','urgency','--check','authority','--check','choice','--check','authority-quotation','--choice-packet',str(packet)],b'Either agree or oppose.',0,('Choice: Your selected wording','Authority quotation: 0 quoted'))
    assert inventory()==before
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'format':'mt-quotation-workflow-controls/v1',
        'pass':True,'source_sha256':before,'source_unchanged_during_execution':True,'actual_cli_controls':checks,
        'python':platform.python_version(),'platform':platform.system(),'authored_synthetic_only':True,
        'baseline_commit':'eb7873ddc861bfadf921d50d338ab2d2607e0d8b','canonical_method_unchanged':'ascii-quoted-authority-observations/1.0.0',
        'complete_canonical_private_record_checked':True,'raw_and_frozen_NFC_bound':True,'private_no_overwrite_checked':True,
        'MT_tag_asserted':False,'intent_or_semantic_endorsement_established':False,'independent_accuracy_evidence':False,
        'independent_corroboration':False,'human_agreement_measured':False,'OS_network_sandbox_exercised':False,
        'scope_percentages_changed':False}
    write_report(args.output,report)
    print(json.dumps({'pass':True,'actual_cli_controls':len(checks),'MT_tag_asserted':False}))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,AssertionError,RuntimeError,subprocess.SubprocessError):
        print('Quotation workflow controls failed; no success report was written.',file=sys.stderr)
        raise SystemExit(1)
