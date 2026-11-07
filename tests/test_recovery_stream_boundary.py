"""A control child must not consume or forward its parent's recovery material."""
import json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('helper',['guest','isolate','restore-guest','apply'])
def test_control_command_cannot_consume_parent_private_stream(helper):
    source=ROOT/'deploy/recovery'/ (helper+'.py')
    code="import runpy,sys,json; m=runpy.run_path(sys.argv[1]); r=m['run']([sys.executable,'-c','import sys; print(len(sys.stdin.buffer.read()))']); print(json.dumps({'child':int(r.stdout),'parent':sys.stdin.buffer.read().decode()}))"
    r=subprocess.run([sys.executable,'-c',code,str(source)],input=b'PRIVATE_RECOVERY_STREAM_CANARY',capture_output=True,timeout=10)
    assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)=={'child':0,'parent':'PRIVATE_RECOVERY_STREAM_CANARY'}
@pytest.mark.parametrize('helper',['isolate','restore-guest','apply'])
def test_explicit_private_transfer_is_the_only_child_input(helper):
    source=ROOT/'deploy/recovery'/(helper+'.py')
    code="import runpy,sys; m=runpy.run_path(sys.argv[1]); r=m['run']([sys.executable,'-c','import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'],raw=b'EXPLICIT_STREAM'); sys.stdout.buffer.write(r.stdout)"
    r=subprocess.run([sys.executable,'-c',code,str(source)],input=b'UNRELATED_PARENT_STREAM',capture_output=True,timeout=10)
    assert r.returncode==0 and r.stdout==b'EXPLICIT_STREAM'

@pytest.mark.parametrize('ready',[True,False])
def test_readiness_never_claims_that_a_recovered_guest_has_no_data(tmp_path,monkeypatch,ready):
    import runpy,types,hashlib
    tools=runpy.run_path(str(ROOT/'deploy/recovery/isolate.py'));world=tools['inspect'].__globals__
    (tmp_path/'isolation.json').write_text(json.dumps({'pid':123,'network_inode':456,'fresh_guest_boot_id_sha256':hashlib.sha256(b'old-boot').hexdigest()}))
    (tmp_path/'recovery-result.json').write_text('{"pass":true}')
    original=world['os'].stat
    def stat(path,*args,**kwargs):
        if str(path)=='/proc/123/ns/net':return types.SimpleNamespace(st_ino=456)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(world['os'],'stat',stat)
    def ssh(*args,**kwargs):
        if not ready:raise OSError('unavailable')
        return types.SimpleNamespace(stdout=json.dumps({'ready':True,'boot_id':'new-boot'}).encode())
    world['ssh']=ssh;result=tools['inspect'](tmp_path)
    assert result['guest_ready'] is ready
    assert result['guest_data_state']=='not_attested_by_readiness'
    assert 'production_data_copied' not in result


def test_missing_image_utilities_refuse_before_any_host_package_change(monkeypatch):
    import runpy
    tools=runpy.run_path(str(ROOT/'deploy/recovery/prepare.py'));world=tools['main'].__globals__
    monkeypatch.setattr(world['os'],'geteuid',lambda:0)
    original=Path.read_text
    monkeypatch.setattr(Path,'read_text',lambda p,*a,**k:'13.7' if str(p)=='/etc/debian_version' else original(p,*a,**k))
    monkeypatch.setattr(Path,'is_file',lambda p:True)
    monkeypatch.setattr(world['shutil'],'which',lambda name:None)
    called=[];world['run']=lambda *a,**k:called.append(a)
    monkeypatch.setattr(sys,'argv',['prepare.py','--execute'])
    with pytest.raises(ValueError):tools['main']()
    assert called==[]


def test_reboot_wait_does_not_accept_ready_pre_reboot_guest():
    import runpy,types,hashlib
    tools=runpy.run_path(str(ROOT/'deploy/recovery/finish.py'));boots=iter(['before','before','after']);seen=[]
    def ssh(*args,**kwargs):
        boot=next(boots);seen.append(boot);return types.SimpleNamespace(stdout=(boot+'\n').encode())
    control={'inspect':lambda _: {'guest_ready':True},'ssh':ssh}
    assert tools['wait_reboot'](None,control,{'sha256':hashlib.sha256(b'before').hexdigest()},pause=0)=='after'
    assert seen==['before','before','after']


def test_reboot_wait_recovers_from_transient_ssh_failure():
    import runpy,types,hashlib
    tools=runpy.run_path(str(ROOT/'deploy/recovery/finish.py'));seen=[]
    def ssh(*args,**kwargs):
        seen.append(1)
        if len(seen)==1:raise subprocess.CalledProcessError(255,['ssh'])
        return types.SimpleNamespace(stdout=b'after\n')
    assert tools['wait_reboot'](None,{'inspect':lambda _: {'guest_ready':True},'ssh':ssh},{'sha256':hashlib.sha256(b'before').hexdigest()},pause=0)=='after'
    assert len(seen)==2


def test_reboot_wait_times_out_if_ready_guest_never_reboots():
    import runpy,types,hashlib
    tools=runpy.run_path(str(ROOT/'deploy/recovery/finish.py'))
    with pytest.raises(ValueError):tools['wait_reboot'](None,{'inspect':lambda _: {'guest_ready':True},'ssh':lambda *a,**k:types.SimpleNamespace(stdout=b'before\n')},{'sha256':hashlib.sha256(b'before').hexdigest()},timeout=.01,pause=.001)


def test_reboot_wait_refuses_invalid_record_before_accessing_guest():
    import runpy
    tools=runpy.run_path(str(ROOT/'deploy/recovery/finish.py'))
    with pytest.raises(ValueError):tools['wait_reboot'](None,{}, {'sha256':'not-a-hash'})
