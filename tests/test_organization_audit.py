"""Closed audit metadata and offline CLI refusals; no external records or network."""
import copy,json,os,subprocess,sys
from pathlib import Path
import pytest
from test_assertion_replay import assertion
from test_newsroom import device_record
from tools.organization_audit import prepare,encoded,parse,validate_metadata
from tools.organization_audit_store import policy,private_file,checked_schema,verify_export

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('kind',['gateway','device'])
def test_supported_sources_preserve_result_without_copying_answer(assertion,device_record,kind):
    row=assertion if kind=='gateway' else device_record
    value=prepare(encoded(row))
    assert value['subject_sha256']==row['subject']['sha256']
    assert value['text_included'] is False and value['independent_accuracy_verified'] is False
    assert value['method_sha256']==sorted({m['sha256'] for m in row.get('evaluator',row)['models']})
    assert 'origin_host' not in value and 'calibration_id' not in value
    assert b'curl' not in encoded(value)

@pytest.mark.parametrize('mutation',['extra','span','overlap','state','flag','negative','bool','unknown','id','null'])
def test_metadata_refuses_unapproved_or_inconsistent_content(device_record,mutation):
    v=prepare(encoded(device_record))
    if mutation=='extra':v['answer']='PRIVATE_AUDIT_CANARY'
    elif mutation=='span':v['tags'][0]['signals'][0]['spans']=[[0,v['subject_char_len']+1]]
    elif mutation=='overlap':v['abstentions']=[{'code':'PS','reason':'timeout','confidence':None,'floor':None}]
    elif mutation=='state':v['result_state']='NO_FINDING'
    elif mutation=='flag':v['independent_accuracy_verified']=True
    elif mutation=='negative':v['tags'][0]['confidence']=-1
    elif mutation=='bool':v['subject_char_len']=True
    elif mutation=='unknown':v['tags'][0]['code']='SC'
    elif mutation=='id':v['tags'][0]['signals'][0]['id']='PRIVATE_AUDIT_CANARY\n'
    elif mutation=='null':v['subject_sha256']=None
    with pytest.raises(Exception):validate_metadata(v)

@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":"\\ud800"}',b'[]',b'\xff'])
def test_strict_json(raw):
    with pytest.raises(Exception):parse(raw)

@pytest.mark.parametrize('values',[(0,40,24),(30,30,24),(30,31,168),(30,37,0),(True,40,24),(3651,4000,24)])
def test_no_implicit_or_inconsistent_retention(values):
    with pytest.raises(ValueError):policy(*values)

@pytest.mark.parametrize('kind',['symlink','fifo','public','hardlink'])
def test_private_inputs_refuse_unsafe_files(tmp_path,kind):
    path=tmp_path/'private';path.write_bytes(b'{}');path.chmod(0o600)
    if kind=='symlink':target=tmp_path/'link';target.symlink_to(path);path=target
    elif kind=='fifo':path.unlink();os.mkfifo(path,0o600)
    elif kind=='public':path.chmod(0o644)
    elif kind=='hardlink':os.link(path,tmp_path/'other')
    with pytest.raises((ValueError,OSError)):private_file(path)


def test_cli_prepare_is_private_and_existing_output_is_unchanged(tmp_path,device_record):
    source=tmp_path/'source';source.write_bytes(encoded(device_record));source.chmod(0o600);tmp_path.chmod(0o700)
    command=[sys.executable,str(ROOT/'scripts/organization-audit.py'),'prepare','--input',str(source),'--output',str(tmp_path/'packet')]
    first=subprocess.run(command,capture_output=True,timeout=15)
    assert first.returncode==0 and b'curl' not in first.stdout+first.stderr
    out=tmp_path/'packet'/'metadata.json';original=out.read_bytes()
    assert out.stat().st_mode&0o777==0o600
    second=subprocess.run(command,capture_output=True,timeout=15)
    assert second.returncode==2 and out.read_bytes()==original
    assert str(source).encode() not in second.stderr


def test_schema_has_only_server_understood_keywords():
    assert checked_schema()['additionalProperties'] is False


def test_extension_projection_keeps_count_without_entity_names(assertion):
    a=copy.deepcopy(assertion)
    a['tags'].append({'code':'PII_REDACTED','confidence':1,'signals':[{'id':'presidio.entity.v1','score':1,'spans':[]}]})
    source={'format':'ai-trust-id-result-export/v1','exported_at':'2026-10-15T00:00:00Z','result_state':'FINDING',
      'selected_tag':None,'assertion_id':a['assertion_id'],'subject':a['subject'],
      'evaluator':{k:a['evaluator'][k] for k in ('calibration_id','models')},'tags':a['tags'],
      'redaction_summary':[{'count':2,'entities':['EMAIL_ADDRESS']}],'abstentions':[],
      'training_label':None,'review_status':'unreviewed_detector_output','delivery':'local_download_only'}
    value=prepare(encoded(source));assert value['redaction_counts']==[2]
    assert b'EMAIL_ADDRESS' not in encoded(value)
    source['result_state']='NO_FINDING'
    with pytest.raises(ValueError):prepare(encoded(source))


def test_administration_cannot_select_ambiguous_policy_days():
    p=policy(3650,3657,168)
    assert p['record_days']==3650 and p['hashes_are_linkable'] is True


def test_child_output_and_execution_deadlines_are_bounded():
    from tools.organization_audit_store import bounded_command
    env={'PATH':'/usr/bin:/bin'}
    with pytest.raises(ValueError):bounded_command([sys.executable,'-c','print("x"*3000000)'],env)
    with pytest.raises(subprocess.TimeoutExpired):bounded_command([sys.executable,'-c','import time; time.sleep(10)'],env,timeout=.2)
    assert bounded_command([sys.executable,'-c','print("ready")'],env)==b'ready\n'


@pytest.mark.parametrize('mutation',['source','control','enabled','failure','runtime','future'])
def test_linux_receipt_cannot_be_reused_after_source_or_acceptance_changes(mutation):
    import importlib.util
    spec=importlib.util.spec_from_file_location('audit_evidence',ROOT/'scripts/verify-organization-audit-evidence.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    receipt=json.loads((ROOT/gate.EVIDENCE).read_bytes())
    assert gate.verify(receipt)['pass'] is True
    if mutation=='source':receipt['sources']['tools/organization_audit.py']='0'*64
    elif mutation=='control':receipt['controls'].pop()
    elif mutation=='enabled':receipt['production_changes']=True
    elif mutation=='failure':receipt['pass']=False
    elif mutation=='runtime':receipt['postgresql_version']='postgres (PostgreSQL) 17.0'
    elif mutation=='future':receipt['captured_at']='2099-01-01T00:00:00+00:00'
    with pytest.raises(ValueError):gate.verify(receipt)
