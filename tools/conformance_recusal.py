"""Offline enforcement of the published project rule, not conformance certification."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from protocol.corpus import read_regular
from protocol.evidence import unique, reject, finite

DOMAIN=b'AITrust-ID/conformance-vote/v1\n'
SHA=re.compile(r'[a-f0-9]{64}\Z')
IDENTIFIER=re.compile(r'[a-z0-9][a-z0-9_.:-]{0,79}\Z')
CHOICES={'approve','reject','abstain','recuse'}


def require(value):
    if not value:raise ValueError('Policy input refused')


def object_fields(value, fields):
    require(type(value) is dict and set(value)==set(fields))


def stamp(value):
    require(type(value) is str and len(value)<=40 and value.endswith(('Z','+00:00')))
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds()==0)
    return parsed


def identifier(value):
    require(type(value) is str and IDENTIFIER.fullmatch(value))
    return value


def digest(value):
    require(type(value) is str and SHA.fullmatch(value))
    return value


def ids(value, minimum=0):
    require(type(value) is list and minimum<=len(value)<=32)
    require(len(set(identifier(item) for item in value))==len(value))
    return set(value)


def decoded(value, length):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]+',value))
    require(len(value)<200)
    raw=base64.urlsafe_b64decode(value+'='*((-len(value))%4))
    require(len(raw)==length and base64.urlsafe_b64encode(raw).decode().rstrip('=')==value)
    return raw


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def load_pinned(path, expected, limit=262144):
    digest(expected);path=Path(path).absolute()
    require(not any(p.is_symlink() for p in [path,*path.parents]))
    raw=read_regular(path,limit)
    require(hashlib.sha256(raw).hexdigest()==expected)
    value=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=unique,parse_constant=reject)
    finite(value)
    return value


def assess(roster, decision, ballots, roster_hash, decision_hash, now=None):
    digest(roster_hash);digest(decision_hash)
    now=now or datetime.now(timezone.utc)
    require(now.tzinfo is not None)
    object_fields(roster,{'profile','valid_from','expires_at','members'})
    require(roster['profile']=='conformance-role-register/v1')
    start,end=stamp(roster['valid_from']),stamp(roster['expires_at'])
    require(start<=now<end and start<end)
    require(type(roster['members']) is list and len(roster['members'])<=128)
    by_key={};member_ids=set()
    for member in roster['members']:
        object_fields(member,{'member_id','key_id','public_key','role','assignment','disclosure','commercial_interests'})
        mid=identifier(member['member_id']);key_id=digest(member['key_id']);key=decoded(member['public_key'],32)
        require(hashlib.sha256(key).hexdigest()==key_id and key_id not in by_key and mid not in member_ids)
        require(member['role'] in {'maintainer','observer'} and member['assignment'] in {'accepted','unfilled'})
        require(member['disclosure'] in {'complete','withheld'})
        ids(member['commercial_interests']);by_key[key_id]=member;member_ids.add(mid)
    object_fields(decision,{'profile','decision_id','created_at','affected_implementations'})
    require(decision['profile']=='conformance-decision-scope/v1');identifier(decision['decision_id'])
    created=stamp(decision['created_at']);require(created<=now)
    affected=ids(decision['affected_implementations'],1)
    require(type(ballots) is list and 1<=len(ballots)<=128)
    outcomes=[];seen_votes=set();seen_members=set()
    for ballot in ballots:
        object_fields(ballot,{'profile','vote_id','roster_sha256','decision_sha256','key_id','choice','issued_at','signature'})
        require(ballot['profile']=='conformance-ballot/v1')
        require(type(ballot['vote_id']) is str and str(uuid.UUID(ballot['vote_id']))==ballot['vote_id'])
        require(ballot['vote_id'] not in seen_votes);seen_votes.add(ballot['vote_id'])
        require(ballot['roster_sha256']==roster_hash and ballot['decision_sha256']==decision_hash)
        key_id=digest(ballot['key_id']);require(key_id in by_key)
        member=by_key[key_id];require(member['member_id'] not in seen_members);seen_members.add(member['member_id'])
        require(ballot['choice'] in CHOICES)
        issued=stamp(ballot['issued_at']);require(max(start,created)<=issued<=now and issued<end)
        payload={key:value for key,value in ballot.items() if key!='signature'}
        try:
            Ed25519PublicKey.from_public_bytes(decoded(member['public_key'],32)).verify(
                decoded(ballot['signature'],64),DOMAIN+canonical(payload))
        except InvalidSignature:
            raise ValueError('Ballot signature refused') from None
        conflict=bool(affected & ids(member['commercial_interests']))
        choice=ballot['choice']
        if member['role']!='maintainer' or member['assignment']!='accepted':result='role_not_eligible'
        elif choice=='recuse':result='recorded_recusal'
        elif member['disclosure']!='complete':result='disclosure_required'
        elif conflict:result='recusal_required'
        elif choice=='abstain':result='recorded_abstention'
        else:result='eligible_vote'
        outcomes.append({'vote_id':ballot['vote_id'],'outcome':result,'eligible_to_count':result=='eligible_vote',
                         'signature_verified':True})
    blocked=any(row['outcome'] in {'role_not_eligible','disclosure_required','recusal_required'} for row in outcomes)
    return {'profile':'conformance-recusal-check/v1','pass':not blocked,
        'roster_sha256':roster_hash,'decision_sha256':decision_hash,
        'eligible_votes':sum(row['eligible_to_count'] for row in outcomes),
        'recorded_recusals':sum(row['outcome']=='recorded_recusal' for row in outcomes),
        'ballots':outcomes,'policy_check_only':True,'certification_granted':False,
        'RFC_adoption_granted':False,'governance_operation_verified':False,
        'real_world_disclosure_truth_verified':False,'independent_people_verified':False}
