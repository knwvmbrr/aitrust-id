"""Reference design workflow, not accreditation, human identity or tag validation."""
import copy
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import certification_programme as c


@pytest.fixture
def setup():
    policy = c.parse((ROOT/c.POLICY).read_bytes())
    evidence = c.parse((ROOT/c.delivery().EVIDENCE).read_bytes())
    now = datetime.now(timezone.utc).isoformat()
    app = c.practice(policy, evidence, now)
    return policy, now, app


def action(policy, app, kind, when, disposition=None, **extra):
    role = {'assess':'assessor','decide':'decision_reviewer','appeal_decide':'appeal_reviewer',
            'suspend':'decision_reviewer'}.get(kind,'applicant')
    data = {'reason':'Invented exercise; no actual authority.'}
    if disposition:
        data.update(disposition=disposition,checked_requirements=[r['id']for r in policy['requirements']])
    data.update(extra)
    return {'kind':kind,'actor':app['roles'][role],'at':when,'data':data}


def test_complete_review_appeal_remand_correction_withdrawal_is_replayed(setup):
    p,now,a=setup;events=[]
    def add(kind,disposition=None,**extra):
        events.append(action(p,a,kind,now,disposition,**extra))
        return c.replay(a,events,p,now)[1]
    assert add('assess','recommend')=='ASSESSOR_RECOMMENDED'
    assert add('decide','complete')=='REFERENCE_REVIEW_COMPLETE'
    assert add('appeal')=='APPEAL_PENDING'
    assert add('appeal_decide','remand')=='CHANGES_REQUIRED'
    corrected=copy.deepcopy(a);corrected['documents'][0]['text']='Corrected invented scope, same source.'
    assert add('correct',application=corrected)=='CHANGES_REQUIRED'
    assert add('assess','recommend')=='ASSESSOR_RECOMMENDED'
    assert add('decide','complete')=='REFERENCE_REVIEW_COMPLETE'
    assert add('withdraw')=='WITHDRAWN'
    with pytest.raises(c.Refusal):add('assess','recommend')
    record=c.record(a,events[:-1],now,{},p,None)
    assert all(v is False for v in record['claims'].values())


@pytest.mark.parametrize('kind',['renew','suspend','correct'])
def test_every_change_requires_fresh_assessment(setup,kind):
    p,now,a=setup
    events=[action(p,a,'assess',now,'recommend'),action(p,a,'decide',now,'complete')]
    extra={'valid_until':(c.stamp(now)+timedelta(days=60)).isoformat()}if kind=='renew'else{'application':copy.deepcopy(a)}if kind=='correct'else{}
    events.append(action(p,a,kind,now,**extra))
    state=c.replay(a,events,p,now)[1];assert state in('SUSPENDED','CHANGES_REQUIRED')
    with pytest.raises(c.Refusal):c.replay(a,[*events,action(p,a,'decide',now,'complete')],p,now)


@pytest.mark.parametrize('scope',['tag-accuracy','organization-service'])
def test_interface_checks_never_satisfy_other_scopes(setup,scope):
    p,now,a=setup;a['scope']=scope
    assert c.gaps(a,p,c.stamp(now))
    with pytest.raises(c.Refusal):c.replay(a,[action(p,a,'assess',now,'recommend')],p,now)


def test_missing_requirement_or_28th_result_cannot_recommend(setup):
    p,now,a=setup;a['requirements']['competence']=[]
    with pytest.raises(c.Refusal):c.replay(a,[action(p,a,'assess',now,'recommend')],p,now)
    a['requirements']['competence']=['competence'];a['interface_evidence']['reference']['checks'].pop()
    with pytest.raises(ValueError):c.application(a,p)


@pytest.mark.parametrize('kind',['duplicate_roles','unfilled','conflict','unknown_conflict','same_actor','review_order','unchecked'])
def test_roles_recusal_and_complete_acknowledgment(setup,kind):
    p,now,a=setup;e=action(p,a,'assess',now,'recommend')
    if kind=='duplicate_roles':a['roles']['decision_reviewer']=a['roles']['assessor']
    elif kind=='unfilled':a['roles']['appeal_reviewer']=None
    elif kind=='conflict':a['conflicts']['assessor']=True
    elif kind=='unknown_conflict':a['conflicts']['assessor']=None
    elif kind=='same_actor':e['actor']=a['roles']['applicant']
    elif kind=='review_order':e=action(p,a,'decide',now,'complete')
    else:e['data']['checked_requirements'].pop()
    with pytest.raises(c.Refusal):c.replay(a,[e],p,now)


def test_recusal_and_appeal_reviewer_cannot_be_bypassed(setup):
    p,now,a=setup;a['conflicts']['assessor']=True
    ev=[action(p,a,'assess',now,'recuse')];assert c.replay(a,ev,p,now)[1]=='RECUSED'
    ev.append(action(p,a,'appeal',now));bad=action(p,a,'appeal_decide',now,'uphold');bad['actor']=a['roles']['decision_reviewer']
    with pytest.raises(c.Refusal):c.replay(a,[*ev,bad],p,now)


def test_expiry_withholds_complete_review_and_cannot_renew_approval(setup):
    p,now,a=setup;events=[action(p,a,'assess',now,'recommend'),action(p,a,'decide',now,'complete')]
    r=c.record(a,events,now,{},p,None);later=(c.stamp(now)+timedelta(days=31)).isoformat()
    assert c.brief(r,p,later)['state']=='REVIEW_EXPIRED'
    assert c.brief(r,p,later)['checklist_complete']is False
    assert not any(r['claims'].values())


@pytest.mark.parametrize('kind',['source','state','bool_integer','extra','removed_event','source_subject'])
def test_closed_replay_source_and_record_binding(setup,kind):
    p,now,a=setup;r=c.record(a,[action(p,a,'assess',now,'recommend')],now,{'fixed':'a'*64},p,None)
    if kind=='source':r['source_sha256']['fixed']='b'*64
    elif kind=='state':r['state']='REFERENCE_REVIEW_COMPLETE'
    elif kind=='bool_integer':r['claims']['certification_granted']=0
    elif kind=='extra':r['accredited']=True
    elif kind=='removed_event':r['actions']=[]
    else:r['application']['implementation']['source_sha256']['scripts/worker_process.py']='f'*64
    with pytest.raises(ValueError):c.check_record(r,{'fixed':'a'*64},p)


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":0.1}',b'['*50+b'0'+b']'*50,b'"'+b'a'*8193+b'"',b'{}'*(c.MAX_INPUT//2+1)])
def test_malformed_and_resource_inputs_refuse(raw):
    with pytest.raises((ValueError,RecursionError)):c.parse(raw)


def invoke(kind,*args):
    return subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/certification-programme.py'),kind,*map(str,args)],capture_output=True,timeout=10)


def test_actual_cli_practice_start_nooverwrite_and_no_echo(tmp_path):
    parent=tmp_path.resolve();parent.chmod(0o700);app=parent/'application.json';rec=parent/'review.json'
    made=invoke('practice','--output',app);assert made.returncode==0,made.stderr
    started=invoke('start','--application',app,'--output',rec);assert started.returncode==0,started.stdout
    summary=json.loads(started.stdout);assert summary['state']=='APPLICATION_RECORDED'and summary['checklist_complete']is True
    assert app.stat().st_mode&0o777==rec.stat().st_mode&0o777==0o600
    old=rec.read_bytes();refused=invoke('start','--application',app,'--output',rec)
    assert refused.returncode==2 and rec.read_bytes()==old
    for r in(made,started,refused):assert str(parent).encode()not in r.stdout+r.stderr and b'example_applicant'not in r.stdout


@pytest.mark.parametrize('kind',['symlink','git','unsafe_parent','fifo'])
def test_unsafe_private_io_refuses_before_output(tmp_path,kind):
    parent=tmp_path.resolve();parent.chmod(0o700);out=parent/'out.json'
    if kind=='git':(parent/'.git').write_text('gitdir: invented')
    elif kind=='unsafe_parent':parent.chmod(0o755)
    elif kind=='symlink':
        link=parent/'link';link.symlink_to(parent,target_is_directory=True);out=link/'out.json'
    else:os.mkfifo(out)
    r=invoke('practice','--output',out);assert r.returncode==2
    assert kind=='fifo' or not out.exists()


def test_late_released_parent_close_is_explicitly_uncertain_and_once(tmp_path,capsys):
    parent=tmp_path.resolve();parent.chmod(0o700);out=parent/'application.json';real=os.close;seen=[];marker=[];identity=parent.stat()
    def close(fd):
        st=os.fstat(fd)
        if (st.st_dev,st.st_ino)==(identity.st_dev,identity.st_ino)and not seen:
            seen.append(fd);real(fd);marker.append(os.open(parent,os.O_RDONLY));raise OSError('PRIVATE_EXCEPTION')
        real(fd)
    try:
        with patch('tools.citation_resolution.os.close',side_effect=close):
            with pytest.raises(c.OutputCommitUncertain):c.execute('practice',{},out)
        assert out.exists()and len(seen)==1 and marker
        os.fstat(marker[0])
    finally:
        for fd in marker:real(fd)


def test_constructor_fault_preserves_nooverwrite_and_closes_raw_descriptor(tmp_path):
    parent=tmp_path.resolve();parent.chmod(0o700);out=parent/'application.json';real=os.fdopen
    def fault(fd,*args,**kwargs):
        if args and args[0]=='wb':raise OSError('PRIVATE_CONSTRUCTOR')
        return real(fd,*args,**kwargs)
    with patch('tools.citation_resolution.os.fdopen',side_effect=fault):
        with pytest.raises(OSError):c.execute('practice',{},out)
    assert not out.exists()and list(parent.iterdir())==[]


def test_suspension_requires_actual_correction_before_assessment(setup):
    p,now,a=setup
    events=[action(p,a,'assess',now,'recommend'),action(p,a,'decide',now,'complete'),action(p,a,'suspend',now)]
    with pytest.raises(c.Refusal):c.replay(a,[*events,action(p,a,'assess',now,'recommend')],p,now)
    events.extend([action(p,a,'correct',now,application=copy.deepcopy(a)),action(p,a,'assess',now,'recommend')])
    assert c.replay(a,events,p,now)[1]=='ASSESSOR_RECOMMENDED'


def test_action_cohort_limit_and_document_cap(setup):
    p,now,a=setup
    e=action(p,a,'renew',now,valid_until=a['valid_until'])
    assert c.replay(a,[e]*32,p,now)[1]=='CHANGES_REQUIRED'
    with pytest.raises(c.Refusal):c.replay(a,[e]*33,p,now)
    a['documents']=[{'id':'doc_'+str(i),'text':'Bounded.'}for i in range(65)]
    with pytest.raises(c.Refusal):c.application(a,p)


def test_current_withdrawn_stored_state_cannot_bypass_revalidation(tmp_path,setup):
    p,now,a=setup;parent=tmp_path.resolve();parent.chmod(0o700)
    with c.Capture()as capture:bound=c.sources(capture)
    old=c.record(a,[action(p,a,'withdraw',now)],now,bound,p,None)
    old['state']='REFERENCE_REVIEW_COMPLETE'
    prior=parent/'old.json';app=parent/'app.json'
    for path,value in((prior,old),(app,a)):
        path.write_bytes(c.encoded(value)+b'\n');path.chmod(0o600)
    with pytest.raises(c.Refusal):c.execute('revalidate',{'record':prior,'application':app},parent/'new.json')
    assert not(parent/'new.json').exists()


def test_unreplayable_older_sources_require_new_application_identity(tmp_path,setup):
    p,now,a=setup;parent=tmp_path.resolve();parent.chmod(0o700)
    with c.Capture()as capture:bound=c.sources(capture)
    old=c.record(a,[],now,bound,p,None);old['source_sha256']['tools/certification_programme.py']='f'*64
    prior=parent/'old.json';app=parent/'app.json'
    for path,value in((prior,old),(app,a)):
        path.write_bytes(c.encoded(value)+b'\n');path.chmod(0o600)
    with pytest.raises(c.Refusal):c.execute('revalidate',{'record':prior,'application':app},parent/'new.json')
    fresh=copy.deepcopy(a);fresh['application_id']='new_reference_application';app.write_bytes(c.encoded(fresh)+b'\n')
    assert c.execute('revalidate',{'record':prior,'application':app},parent/'new.json')['state']=='APPLICATION_RECORDED'
    assert json.loads((parent/'new.json').read_bytes())['actions']==[]
