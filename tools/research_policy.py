"""Check the accepted disabled pilot contract; never enable storage or submit data."""
import hashlib
import json
from pathlib import Path
from protocol.evidence import unique,reject,finite
from protocol.corpus import read_regular

ROOT=Path(__file__).resolve().parents[1]
POLICY='deploy/research/metadata-pilot-policy.json'
DECISION='runs/2026-10-13-metadata-pilot-owner-decision.json'
FIELDS=['schema_version','purpose','tag','method_version','reported_result','failure_category','feedback','sharing']
GATES=['security','withdrawal','active_expiry','encrypted_backup_expiry','replacement_host_recovery',
       'effective_database_grants','proxy_and_provider_review','owner_operation','current_privacy_notice']
EXPECTED={
 'profile':'metadata-pilot-policy/v1','operator':'Michael','endpoint':'https://research.aitrustid.com/v1/feedback',
 'collection_enabled':False,'checking_requires_account':False,'submission_default':'off',
 'permission':'separate_metadata_preview_and_confirm','audience':'private_invited_pilot',
 'purpose':'PS_preview_usability_and_failure_review','tag':'PS','method_versions':['context-v6'],
 'fields':FIELDS,'submission_marker':'consented_metadata_submission','free_text_allowed':False,'examples_allowed':False,
 'subject_hashes_allowed':False,'spans_allowed':False,'participant_identity_allowed':False,'client_time_allowed':False,
 'model_training_authorized':False,'public_aggregation_authorized':False,
 'retention':{'active_days':30,'encrypted_backup_max_days':7,'restore_applies_withdrawal_and_expiry_before_access':True,
              'deletion_instructions_retained_through_affected_backup_expiry':True,'immediate_backup_erasure_promised':False},
 'roles':{'operator':'Michael','migration':'separate','intake':'write_minimum','review':'assigned_read_only','maintenance':'expiry_and_withdrawal'},
 'required_before_collection':GATES}


def same(actual,expected):
    if type(actual) is not type(expected):return False
    if type(expected) is dict:return set(actual)==set(expected) and all(same(actual[k],v) for k,v in expected.items())
    if type(expected) is list:return len(actual)==len(expected) and all(same(a,b) for a,b in zip(actual,expected))
    return actual==expected


def snapshot(path):
    path=Path(path)
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Linked policy input')
    raw=read_regular(path,16384)
    value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=reject);finite(value)
    if type(value) is not dict:raise ValueError('Invalid policy object')
    return value,raw


def assess(root=ROOT):
    root=Path(root).resolve();policy,policy_raw=snapshot(root/POLICY)
    if set(policy)!=set(EXPECTED)|{'owner_decision'}:raise ValueError('Unsupported pilot policy')
    if not same({k:v for k,v in policy.items() if k!='owner_decision'},EXPECTED):raise ValueError('Pilot policy drift')
    pin=policy['owner_decision']
    if type(pin) is not dict or set(pin)!={'path','sha256'} or pin['path']!=DECISION:raise ValueError('Unsupported owner decision pin')
    decision,raw=snapshot(root/DECISION)
    if type(pin['sha256']) is not str or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Owner decision drift')
    if (decision.get('owner')!='Michael' or decision.get('requirement')!='N-011' or decision.get('answer')!='1'
        or decision.get('collection_enabled') is not False or decision.get('taxonomy_changed') is not False
        or decision.get('approval_source')!='Owner reply to request_user_input_async call_d0a915eb4291439ba339b7a961b8adc1, question 0'):
        raise ValueError('Unsupported owner approval')
    # Read twice so a path replacement cannot silently change the policy before output.
    if snapshot(root/POLICY)[1]!=policy_raw or snapshot(root/DECISION)[1]!=raw:raise ValueError('Policy changed during check')
    return {'pass':True,'profile':EXPECTED['profile'],'owner_contract_recorded':True,'policy_sha256':hashlib.sha256(policy_raw).hexdigest(),
            'owner_decision_sha256':pin['sha256'],'collection_enabled':False,'account_gate_for_checking':False,
            'real_submissions_accepted':False,'operational_gates_passed':False,'training_authorized':False,
            'legacy_hash_only_registry_adopted':False,'active_days':30,'backup_max_days':7,
            'definition_complete_not_deployment':True}
