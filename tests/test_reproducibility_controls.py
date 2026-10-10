"""Negative contract tests; hypothetical review inputs are never public reviews."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest
from protocol import decisions,revalidation,signals
from protocol.accessibility_release import assess_reviews,TASKS
from protocol.evidence import read_evidence

def stamp():return datetime.now(timezone.utc).isoformat()

@pytest.fixture
def tree(tmp_path):
    for name in revalidation.COMMON:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('control')
    (tmp_path/'scripts/check-control.py').write_text('print("synthetic control")')
    (tmp_path/'sources').mkdir();(tmp_path/'sources/method.py').write_text('first version')
    data={'schema_version':1,'kind':'engineering_revalidation','independent_accuracy_evidence':False,
          'capabilities':{c:{'patterns':['sources/*.py'],'commands':[['{python}','scripts/check-control.py']]} for c in revalidation.CAPABILITIES}}
    (tmp_path/'eval/revalidation.json').write_text(json.dumps(data))
    return tmp_path

def fake(command,**kwargs):return SimpleNamespace(returncode=0,stdout=b'synthetic',stderr=b'')

def receipt(root,cap='PS'):
    return revalidation.execute(cap,root,runner=fake)

def test_receipt_source_and_commands_are_bound(tree):
    r=receipt(tree);assert revalidation.assess(r,'PS',tree)['pass']
    r['checks'][0]['command']=['{python}','scripts/other.py']
    assert not revalidation.assess(r,'PS',tree)['pass']

@pytest.mark.parametrize('mutation',['content','added','removed','symlink','manifest','common'])
def test_changes_trigger_revalidation(tree,mutation):
    r=receipt(tree)
    p=tree/'sources/method.py'
    if mutation=='content':p.write_text('second version')
    elif mutation=='added':(tree/'sources/extra.py').write_text('new')
    elif mutation=='removed':p.unlink()
    elif mutation=='symlink':p.unlink();p.symlink_to(tree/'scripts/check-control.py')
    elif mutation=='common':(tree/'protocol/revalidation.py').write_text('changed runner')
    elif mutation=='manifest':
        d=json.loads((tree/'eval/revalidation.json').read_text());d['capabilities']['PS']['commands'].append(['{python}','scripts/check-control.py']);(tree/'eval/revalidation.json').write_text(json.dumps(d))
    result=revalidation.assess(r,'PS',tree)
    assert not result['pass'] and result['revalidation_required']

@pytest.mark.parametrize('field,value',[('pass',False),('pass',1),('release_approved',True),('independent_accuracy_evidence',True),('source_unchanged_during_execution',False),('captured_at','2026-10-01'),('captured_at','9999-01-01T00:00:00+00:00')])
def test_stale_or_overclaimed_evidence_refused(tree,field,value):
    r=receipt(tree);r[field]=value;assert not revalidation.assess(r,'PS',tree)['pass']

def test_change_during_actual_command_is_not_a_pass(tree):
    def changed(*a,**kw):
        (tree/'sources/method.py').write_text('changed during run');return fake(*a,**kw)
    r=revalidation.execute('PS',tree,runner=changed)
    assert not r['pass'] and not r['source_unchanged_during_execution']

def test_failed_command_does_not_issue_receipt(tree):
    r=revalidation.execute('PS',tree,runner=lambda *a,**kw:SimpleNamespace(returncode=1,stdout=b'',stderr=b'private canary'))
    assert not r['pass'] and 'private canary' not in json.dumps(r)

def hypothetical_reviews(tree):
    receipts={c:receipt(tree,c) for c in ('website','extension')};reviews=[]
    directory=tree/'docs/manual-accessibility';directory.mkdir(parents=True)
    for surface in ('website','extension'):
        for tech in ('NVDA','VoiceOver'):
            account=f'docs/manual-accessibility/{surface}-{tech}.md'
            (tree/account).write_text('Hypothetical unit-test document, never a real accessibility review. '*3)
            reviews.append({'kind':'human_accessibility_review','engineering_fixture':False,'human_performed':True,
               'surface':surface,'technology':tech,'reviewer_public_label':'Hypothetical reviewer',
               'reviewer_publication_consent':True,'environment':'Hypothetical test environment',
               'performed_at':stamp(),'fingerprint':revalidation.fingerprint(surface,tree)['sha256'],
               'tasks':dict.fromkeys(TASKS,'pass'),'unresolved_issues':[],'account':account})
    return reviews,receipts

def test_gate_contract_with_hypothetical_documents_only(tree):
    reviews,receipts=hypothetical_reviews(tree)
    result=assess_reviews(reviews,receipts,tree)
    assert result['pass'] and not result['full_wcag_conformance'] and not result['independent_tag_accuracy']
    assert not assess_reviews([],receipts,tree)['pass']

@pytest.mark.parametrize('mutation',['fixture','machine','consent','stale','duplicate','missing_task','unresolved','missing_account','wrong_directory','missing_receipt','false_pass'])
def test_human_review_gate_refuses_bad_evidence(tree,mutation):
    reviews,receipts=hypothetical_reviews(tree);r=reviews[0]
    if mutation=='fixture':r['engineering_fixture']=True
    elif mutation=='machine':r['human_performed']=False
    elif mutation=='consent':r['reviewer_publication_consent']=False
    elif mutation=='stale':r['fingerprint']='0'*64
    elif mutation=='duplicate':reviews.append(deepcopy(r))
    elif mutation=='missing_task':r['tasks'].pop('navigate')
    elif mutation=='unresolved':r['unresolved_issues']=['failure']
    elif mutation=='missing_account':(tree/r['account']).unlink()
    elif mutation=='wrong_directory':r['account']='tests/fixture.md'
    elif mutation=='missing_receipt':receipts.pop('website')
    elif mutation=='false_pass':r['tasks']['navigate']='pending'
    assert not assess_reviews(reviews,receipts,tree)['pass']

def test_real_repository_has_no_manufactured_manual_review():
    assert not assess_reviews([],{},revalidation.ROOT)['pass']

@pytest.mark.parametrize('mutation',['duplicate','missing','accepted','owner','reason','date'])
def test_decisions_refuse_missing_and_manufactured_acceptance(mutation):
    data=json.loads((decisions.ROOT/'docs/decisions.json').read_text());decisions.validate(data)
    if mutation=='duplicate':data['decisions'][-1]=deepcopy(data['decisions'][0])
    elif mutation=='missing':data['decisions'].pop()
    elif mutation=='accepted':data['decisions'][0]['status']='accepted'
    elif mutation=='owner':data['decisions'][0]['owner']='AI'
    elif mutation=='reason':data['decisions'][0]['reason']=''
    elif mutation=='date':data['decisions'][0]['recorded_at']='2030-01-01'
    with pytest.raises(ValueError):decisions.validate(data)

def test_dated_prose_is_exact_current_source():assert decisions.verify()['pass']

def test_all_signal_ids_have_explainable_state_and_unknowns_refuse():
    data=signals.registry();assert len(data['signals'])==33
    for row in data['signals']:
        found=signals.lookup(row['id']);assert found['description'] and not found['independent_accuracy_evidence']
    for id in ('sig.unknown.v1','sig.piped_installer','<script>','sig.piped_installer.v999'):
        assert signals.lookup(id)['status']=='unsupported'

def test_active_catalogue_and_runtime_cannot_silently_diverge(tmp_path):
    for name in ['spec/signal-registry.json','spec/signals.md']+[name for s in signals.registry()['signals'] for name in s['source_files']]:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(signals.ROOT/name,target)
    data=json.loads((tmp_path/'spec/signal-registry.json').read_text());data['signals'][0]['independent_validation']=True
    (tmp_path/'spec/signal-registry.json').write_text(json.dumps(data))
    with pytest.raises(ValueError):signals.registry(tmp_path)

@pytest.mark.parametrize('raw',[b'{"pass":false,"pass":true}',b'{"value":NaN}',b'{"value":1e999}',b'{"value":"\\ud800"}',b'[]',b'\xff'])
def test_evidence_import_rejects_ambiguous_or_invalid_json(tmp_path,raw):
    p=tmp_path/'review.json';p.write_bytes(raw)
    with pytest.raises(ValueError):read_evidence(p)

def test_evidence_import_is_bounded_and_refuses_symlink(tmp_path):
    p=tmp_path/'real.json';p.write_text('{"pass":true}')
    assert read_evidence(p)=={'pass':True}
    with pytest.raises(ValueError):read_evidence(p,limit=4)
    link=tmp_path/'link.json';link.symlink_to(p)
    with pytest.raises(ValueError):read_evidence(link)

def test_source_bound_receipt_refuses_symlink_runner(tree):
    r=receipt(tree);p=tree/'scripts/revalidate.py';p.unlink();p.symlink_to(tree/'sources/method.py')
    assert not revalidation.assess(r,'PS',tree)['pass']
