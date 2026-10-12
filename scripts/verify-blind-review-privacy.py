"""Execute synthetic offline packet CLI safety; never supplies human ratings."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
FILES = ['scripts/prepare-ps-review.py','tools/blind_review_io.py','protocol/evidence.py',
         'services/evaluator/app.py','eval/gates.yaml','docs/independent-review.md',
         'tools/review_execution.py','protocol/normalization.py','protocol/unicode15-data.json',
         'services/evaluator/requirements.lock','eval/harness.py']


def verify():
    sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
    cases=[]
    with tempfile.TemporaryDirectory(prefix='aitrust-blind-private-') as temporary:
        private=Path(temporary);private.chmod(0o700)
        marker='SyntheticPrivateReviewCanary-20261011'
        rows=[{'id':'one','text':' ='+marker,'category':'display','source':'authored synthetic'},
              {'id':'two','text':marker+' never execute examples','category':'control','source':'authored synthetic'}]
        source=private/'source.jsonl';source.write_text(''.join(json.dumps(r)+'\n' for r in rows));source.chmod(0o600)
        packet=private/'packet'
        def call(name,args,success,check=None):
            result=subprocess.run([sys.executable,str(ROOT/'scripts/prepare-ps-review.py'),*map(str,args)],capture_output=True,timeout=15)
            raw=result.stdout+result.stderr
            if len(raw)>1_000_000 or marker.encode() in raw or str(private).encode() in raw:
                raise ValueError('Private review diagnostic leaked or exceeded its bound')
            if (result.returncode==0)!=success:
                raise ValueError('Synthetic packet CLI result did not match its control')
            value=json.loads(result.stdout) if success else None
            if check:check(value)
            cases.append({'name':name,'exit_status':result.returncode,'pass':True,'output_sha256':hashlib.sha256(raw).hexdigest(),'private_canary_and_path_absent':True})
        call('unknown_command_private_path_refused',[str(private/marker)],False)
        call('extra_private_argument_refused',['compare',packet,'--unexpected-private-path',str(private/marker)],False)
        call('freeze',['freeze',source,packet],True,lambda r:all(r[k] is False for k in ['independence_verified','sampling_accepted','predictions_run','release_assessed']) or (_ for _ in ()).throw(ValueError('Unaccepted flags')))
        assert packet.stat().st_mode&0o777==0o700 and all(f.stat().st_mode&0o777==0o600 for f in packet.iterdir())
        before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in packet.iterdir()}
        call('existing_packet_refused',['freeze',source,packet],False)
        assert before=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in packet.iterdir()}
        call('incomplete_csv_refused',['compare',packet],False)
        call('incomplete_phone_refused',['compare',packet,'--format','json'],False)
        for slot in (1,2):
            file=packet/f'reviewer-{slot}.json';form=json.loads(file.read_text())
            for row in form['items']:row.update(label='positive' if slot==1 else 'ambiguous',reason='Synthetic CLI control only')
            file.write_text(json.dumps(form))
            file=packet/f'reviewer-{slot}.csv'
            with file.open(newline='') as handle:ratings=list(csv.DictReader(handle))
            assert any(row['text'].startswith("' =") for row in ratings)
            for row in ratings:row.update(label='positive' if slot==1 else 'ambiguous',reason='Synthetic CLI control only')
            with file.open('w',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=['id','text','category','source','label','reason']);writer.writeheader();writer.writerows(ratings)
        def disagreements(value):
            assert value['disagreement_ids']==['one','two'] and value['ambiguous_ids']==['one','two']
            assert all(value[k] is False for k in ['independence_verified','predictions_run','release_assessed'])
        call('csv_disagreements_preserved',['compare',packet],True,disagreements)
        call('phone_disagreements_preserved',['compare',packet,'--format','json'],True,disagreements)
        call('bound_phone_comparison',['compare',packet,'--format','json','--require-execution-binding'],True,
             lambda r:r['execution_binding_verified'] is True or (_ for _ in ()).throw(ValueError('Missing execution binding')))
        file=packet/'manifest.json';bound=file.read_bytes();legacy=json.loads(bound)
        legacy['format']='ai-trust-id-blind-ps-review/v1';legacy.pop('execution_context_sha256')
        legacy['method_sha256']=hashlib.sha256((ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
        bound_forms={slot:(packet/f'reviewer-{slot}.json').read_bytes() for slot in (1,2)}
        for slot in (1,2):
            form=json.loads(bound_forms[slot]);form['method_sha256']=legacy['method_sha256']
            (packet/f'reviewer-{slot}.json').write_text(json.dumps(form))
        file.write_text(json.dumps(legacy))
        call('legacy_labels_only',['compare',packet,'--format','json'],True,
             lambda r:r['execution_binding_verified'] is False or (_ for _ in ()).throw(ValueError('False legacy binding')))
        call('legacy_required_binding_refused',['compare',packet,'--format','json','--require-execution-binding'],False)
        file.write_bytes(bound)
        for slot in (1,2):(packet/f'reviewer-{slot}.json').write_bytes(bound_forms[slot])
        file=packet/'manifest.json';original=file.read_bytes()
        file.write_bytes(original.replace(b'"format":',b'"format":"duplicate", "format":',1));call('duplicate_manifest_refused',['compare',packet,'--format','json'],False);file.write_bytes(original)
        value=json.loads(original);value['independence_verified']=True;file.write_text(json.dumps(value));call('forged_independence_refused',['compare',packet,'--format','json'],False);file.write_bytes(original)
        file=packet/'reviewer-1.json';original=file.read_bytes()
        file.write_bytes(b'\xc0\xaf');call('invalid_utf8_refused',['compare',packet,'--format','json'],False);file.write_bytes(original)
        file.unlink();file.symlink_to(source);call('linked_phone_form_refused',['compare',packet,'--format','json'],False);file.unlink();file.write_bytes(original);file.chmod(0o600)
        other=private/'linked';os.link(file,other);call('multiply_linked_form_refused',['compare',packet,'--format','json'],False);other.unlink()
        file.chmod(0o644);call('public_form_refused',['compare',packet,'--format','json'],False);file.chmod(0o600)
        form=json.loads(original);form['items'][0]['reason']='x'*2001;file.write_text(json.dumps(form));call('long_reason_refused',['compare',packet,'--format','json'],False);file.write_bytes(original)
        large=private/'large.jsonl'
        with large.open('wb') as handle:handle.truncate(10_000_001)
        large.chmod(0o600);call('oversized_source_refused',['freeze',large,private/'oversized-packet'],False);assert not (private/'oversized-packet').exists()
        source.chmod(0o644);call('public_source_refused',['freeze',source,private/'public-packet'],False);source.chmod(0o600);assert not (private/'public-packet').exists()
        public=private/'public-parent';public.mkdir(mode=0o755);public.chmod(0o755)
        call('public_destination_parent_refused',['freeze',source,public/'packet'],False);assert not (public/'packet').exists()
    assert not private.exists()
    assert sources=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'kind':'synthetic_offline_blind_review_cli',
            'platform':platform.system(),'python_version':platform.python_version(),'sources':sources,'source_unchanged':True,
            'cases':cases,'private_temporary_material_removed':True,'synthetic_only':True,'human_ratings':False,
            'independence_verified':False,'sampling_accepted':False,'predictions_run':False,'release_assessed':False,
            'scope':'Actual offline CLI and private file controls with invented ratings; not independent reviewers, representative sampling, phone hardware or tag accuracy.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:
        result=verify()
        if args.output:write_report(args.output,result)
    except (OSError,ValueError,AssertionError,subprocess.SubprocessError):
        print('BLIND_REVIEW_PRIVATE_CONTROL_FAILED',file=sys.stderr);return 1
    print(json.dumps({'pass':True,'controls':len(result['cases']),'platform':result['platform'],'synthetic_only':True,'independence_verified':False}));return 0
if __name__=='__main__':raise SystemExit(main())
