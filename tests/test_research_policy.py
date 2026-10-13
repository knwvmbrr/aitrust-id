"""Contract drift cannot activate a collector or silently expand owner approval."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from tools import research_policy as p
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def root(tmp_path):
    for name in [p.POLICY,p.DECISION]:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    return tmp_path

def change(root,fn):
    file=root/p.POLICY;data=json.loads(file.read_text());fn(data);file.write_text(json.dumps(data))

def test_exact_approved_definition_is_disabled_and_account_free(root):
    result=p.assess(root)
    assert result['pass'] and result['definition_complete_not_deployment']
    for field in ['collection_enabled','account_gate_for_checking','real_submissions_accepted','operational_gates_passed','training_authorized','legacy_hash_only_registry_adopted']:assert result[field] is False

@pytest.mark.parametrize('field,value',[('collection_enabled',True),('checking_requires_account',True),('submission_default','on'),
    ('permission','implied_by_check'),('operator','unassigned'),('endpoint','https://external.invalid/upload'),
    ('purpose','indefinite_training'),('examples_allowed',True),('subject_hashes_allowed',True),('spans_allowed',True),
    ('participant_identity_allowed',True),('client_time_allowed',True),('free_text_allowed',True),
    ('model_training_authorized',True),('public_aggregation_authorized',True),('method_versions',['unmeasured']),
    ('fields',p.FIELDS+['text']),('required_before_collection',p.GATES[:-1])])
def test_unapproved_contract_expansion_refused(root,field,value):
    change(root,lambda data:data.update({field:value}))
    with pytest.raises(ValueError):p.assess(root)

@pytest.mark.parametrize('key,value',[('active_days',31),('encrypted_backup_max_days',8),('encrypted_backup_max_days',True),
    ('restore_applies_withdrawal_and_expiry_before_access',False),('deletion_instructions_retained_through_affected_backup_expiry',False),
    ('immediate_backup_erasure_promised',True)])
def test_retention_and_recovery_promises_cannot_drift(root,key,value):
    change(root,lambda data:data['retention'].update({key:value}))
    with pytest.raises(ValueError):p.assess(root)

@pytest.mark.parametrize('kind',['extra','missing','numeric_boolean','receipt_changed','receipt_pin','receipt_path','duplicate','oversize','symlink'])
def test_policy_and_receipt_input_refusals(root,kind):
    file=root/p.POLICY
    if kind=='extra':change(root,lambda d:d.update(text='PRIVATE_CANARY'))
    elif kind=='missing':change(root,lambda d:d.pop('permission'))
    elif kind=='numeric_boolean':change(root,lambda d:d.update(collection_enabled=0))
    elif kind=='receipt_changed':file=root/p.DECISION;file.write_bytes(file.read_bytes()+b' ')
    elif kind=='receipt_pin':change(root,lambda d:d['owner_decision'].update(sha256='0'*64))
    elif kind=='receipt_path':change(root,lambda d:d['owner_decision'].update(path='../../private.txt'))
    elif kind=='duplicate':file.write_bytes(b'{"profile":"a","profile":"b"}')
    elif kind=='oversize':file.write_bytes(b' '*16385)
    elif kind=='symlink':target=file.with_name('target');file.rename(target);file.symlink_to(target)
    with pytest.raises(ValueError):p.assess(root)


def test_real_repository_and_cli_preserve_disabled_policy():
    before=(ROOT/p.POLICY).read_bytes();receipt=(ROOT/p.DECISION).read_bytes()
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify-research-policy.py')],capture_output=True,text=True,timeout=15)
    assert result.returncode==0 and not result.stderr and json.loads(result.stdout)['collection_enabled'] is False
    assert (ROOT/p.POLICY).read_bytes()==before and (ROOT/p.DECISION).read_bytes()==receipt
