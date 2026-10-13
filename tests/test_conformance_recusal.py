"""Invented signed ballots exercise a rule; never real governance or certification."""
import base64
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tools.conformance_recusal import DOMAIN,assess,canonical,load_pinned
ROOT=Path(__file__).resolve().parents[1]


def encode(raw):return base64.urlsafe_b64encode(raw).decode().rstrip('=')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def stamp(value):return value.isoformat()


def fixtures():
    now=datetime.now(timezone.utc);key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes_raw()
    member={'member_id':'fixture-maintainer','key_id':sha(public),'public_key':encode(public),'role':'maintainer',
            'assignment':'accepted','disclosure':'complete','commercial_interests':[]}
    roster={'profile':'conformance-role-register/v1','valid_from':stamp(now-timedelta(hours=1)),
            'expires_at':stamp(now+timedelta(hours=1)),'members':[member]}
    decision={'profile':'conformance-decision-scope/v1','decision_id':'fixture-decision',
              'created_at':stamp(now-timedelta(minutes=10)),'affected_implementations':['fixture-project']}
    def sign(choice='approve',overrides=None):
        ballot={'profile':'conformance-ballot/v1','vote_id':str(uuid.uuid4()),'roster_sha256':sha(canonical(roster)),
                'decision_sha256':sha(canonical(decision)),'key_id':sha(public),'choice':choice,
                'issued_at':stamp(now-timedelta(minutes=1))}
        ballot.update(overrides or {});ballot['signature']=encode(key.sign(DOMAIN+canonical(ballot)));return ballot
    return now,key,roster,decision,sign


@pytest.mark.parametrize('choice,outcome,eligible',[('approve','eligible_vote',1),('reject','eligible_vote',1),
    ('abstain','recorded_abstention',0),('recuse','recorded_recusal',0)])
def test_authenticated_rule_outcomes_do_not_grant_certification(choice,outcome,eligible):
    now,key,r,d,sign=fixtures();result=assess(r,d,[sign(choice)],sha(canonical(r)),sha(canonical(d)),now)
    assert result['pass'] and result['eligible_votes']==eligible and result['ballots'][0]['outcome']==outcome
    for field in ['certification_granted','RFC_adoption_granted','governance_operation_verified',
                  'real_world_disclosure_truth_verified','independent_people_verified']:assert result[field] is False


@pytest.mark.parametrize('choice',['approve','reject','abstain'])
def test_declared_affected_interest_requires_recusal_even_for_abstention(choice):
    now,key,r,d,sign=fixtures();r['members'][0]['commercial_interests']=['fixture-project']
    result=assess(r,d,[sign(choice)],sha(canonical(r)),sha(canonical(d)),now)
    assert not result['pass'] and result['eligible_votes']==0 and result['ballots'][0]['outcome']=='recusal_required'


def test_unrelated_interest_does_not_block_vote_on_other_implementation():
    now,key,r,d,sign=fixtures();r['members'][0]['commercial_interests']=['unrelated-project']
    assert assess(r,d,[sign()],sha(canonical(r)),sha(canonical(d)),now)['eligible_votes']==1


@pytest.mark.parametrize('kind,outcome',[('unfilled','role_not_eligible'),('observer','role_not_eligible'),('withheld','disclosure_required')])
def test_role_and_disclosure_refusals(kind,outcome):
    now,key,r,d,sign=fixtures();m=r['members'][0]
    if kind=='unfilled':m['assignment']='unfilled'
    elif kind=='observer':m['role']='observer'
    else:m['disclosure']='withheld'
    result=assess(r,d,[sign()],sha(canonical(r)),sha(canonical(d)),now)
    assert not result['pass'] and result['ballots'][0]['outcome']==outcome


def test_explicit_recusal_is_recorded_without_forcing_disclosure():
    now,key,r,d,sign=fixtures();r['members'][0]['disclosure']='withheld'
    result=assess(r,d,[sign('recuse')],sha(canonical(r)),sha(canonical(d)),now)
    assert result['pass'] and result['recorded_recusals']==1 and result['eligible_votes']==0


@pytest.mark.parametrize('kind',['signature','choice','decision','roster','unknown_key','vote_id','future_vote',
    'old_vote','expired','future_register','duplicate_vote','duplicate_member_ballot','duplicate_roster',
    'extra_member','extra_decision','extra_ballot','empty_affected','duplicate_affected','empty_ballots',
    'too_many_ballots','bad_public_key','bad_key_id','public_key_padding','wrong_domain'])
def test_forgery_replay_and_structural_inputs_refused(kind):
    now,key,r,d,sign=fixtures();ballot=sign();ballots=[ballot]
    if kind=='signature':ballot['signature']=encode(b'0'*64)
    elif kind=='choice':ballot['choice']='reject'
    elif kind=='decision':d['affected_implementations']=['changed-project']
    elif kind=='roster':r['members'][0]['commercial_interests']=['fixture-project']
    elif kind=='unknown_key':ballot=sign(overrides={'key_id':'0'*64});ballots=[ballot]
    elif kind=='vote_id':ballots=[sign(overrides={'vote_id':'PRIVATE_CANARY'})]
    elif kind=='future_vote':ballots=[sign(overrides={'issued_at':stamp(now+timedelta(minutes=1))})]
    elif kind=='old_vote':ballots=[sign(overrides={'issued_at':stamp(now-timedelta(hours=2))})]
    elif kind=='expired':r['expires_at']=stamp(now-timedelta(seconds=1));ballots=[sign()]
    elif kind=='future_register':r['valid_from']=stamp(now+timedelta(seconds=1));ballots=[sign()]
    elif kind=='duplicate_vote':ballots=[ballot,deepcopy(ballot)]
    elif kind=='duplicate_member_ballot':ballots=[ballot,sign('reject')]
    elif kind=='duplicate_roster':r['members']*=2;ballots=[sign()]
    elif kind=='extra_member':r['members'][0]['text']='PRIVATE_CANARY';ballots=[sign()]
    elif kind=='extra_decision':d['text']='PRIVATE_CANARY';ballots=[sign()]
    elif kind=='extra_ballot':ballots=[sign(overrides={'text':'PRIVATE_CANARY'})]
    elif kind=='empty_affected':d['affected_implementations']=[];ballots=[sign()]
    elif kind=='duplicate_affected':d['affected_implementations']*=2;ballots=[sign()]
    elif kind=='empty_ballots':ballots=[]
    elif kind=='too_many_ballots':ballots=[ballot]*129
    elif kind=='bad_public_key':r['members'][0]['public_key']=encode(b'1'*31);ballots=[sign()]
    elif kind=='bad_key_id':r['members'][0]['key_id']='0'*64;ballots=[sign()]
    elif kind=='public_key_padding':r['members'][0]['public_key']+='=';ballots=[sign()]
    elif kind=='wrong_domain':
        payload={k:v for k,v in ballot.items() if k!='signature'};ballot['signature']=encode(key.sign(canonical(payload)))
    with pytest.raises(ValueError):assess(r,d,ballots,sha(canonical(r)),sha(canonical(d)),now)


@pytest.mark.parametrize('kind',['pin','symlink','fifo','oversize','duplicate_json','nonfinite','utf8','deep','surrogate'])
def test_pinned_file_contract(tmp_path,kind):
    file=tmp_path/'record';raw=b'{"a":1}'
    if kind=='duplicate_json':raw=b'{"a":1,"a":2}'
    elif kind=='nonfinite':raw=b'{"a":NaN}'
    elif kind=='utf8':raw=b'\xff'
    elif kind=='deep':raw=b'['*70+b'0'+b']'*70
    elif kind=='surrogate':raw=b'{"a":"\\ud800"}'
    file.write_bytes(raw);pin=sha(raw)
    if kind=='pin':pin='0'*64
    elif kind=='symlink':target=tmp_path/'target';file.rename(target);file.symlink_to(target)
    elif kind=='fifo':file.unlink();os.mkfifo(file)
    elif kind=='oversize':file.write_bytes(b'x'*262145);pin=sha(file.read_bytes())
    with pytest.raises(ValueError):load_pinned(file,pin)


@pytest.mark.parametrize('choice,conflict,exit_code',[('approve',False,0),('approve',True,1),('abstain',True,1),('recuse',True,0)])
def test_actual_cli_outcomes_and_private_inputs_unchanged(tmp_path,choice,conflict,exit_code):
    now,key,r,d,sign=fixtures()
    if conflict:r['members'][0]['commercial_interests']=['fixture-project']
    inputs={'roster':canonical(r),'decision':canonical(d),'ballots':canonical([sign(choice)])}
    for name,raw in inputs.items():(tmp_path/name).write_bytes(raw)
    proc=subprocess.run([sys.executable,str(ROOT/'scripts/check-conformance-votes.py'),str(tmp_path/'ballots'),
        '--roster',str(tmp_path/'roster'),'--roster-sha256',sha(inputs['roster']),
        '--decision',str(tmp_path/'decision'),'--decision-sha256',sha(inputs['decision'])],capture_output=True,text=True,timeout=15)
    assert proc.returncode==exit_code and not proc.stderr and str(tmp_path) not in proc.stdout
    assert json.loads(proc.stdout)['eligible_votes']==(1 if exit_code==0 and choice=='approve' else 0)
    assert all((tmp_path/name).read_bytes()==raw for name,raw in inputs.items())
