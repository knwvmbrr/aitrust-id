#!/usr/bin/env python3
"""Compare private text with an owner-held corpus; no truth verdict, tag or upload."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
sys.path.insert(0,str(REPO))
from protocol import corpus
from research.nli import references
from research.nli.pairs import PairError, require, validate
from source_snapshot import unique
from tools.blind_review_io import PacketError, create, source
from tools import reference_review_window as review_window
from tools.reference_revision import MAX_POLICY_BYTES

class ReferenceFailure(ValueError):
    def __init__(self,category,action):
        self.category,self.action=category,action
        super().__init__('Reference research unavailable')

class Parser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Reference command refused; use --help for required arguments.\n')

def pair_validator():
    spec=importlib.util.spec_from_file_location('reference_pair_contract',REPO/'scripts/check-nli-pairs.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_observation

def parse_details(raw,request):
    result=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(PairError('Invalid number')))
    require(isinstance(result,dict))
    control=result.pop('network_control',None)
    expected={'Darwin':'macos_sandbox_deny_network','Linux':'linux_worker_seccomp_network_denial'}
    require(platform.system() in expected and control==expected[platform.system()])
    pair_validator()(request,result)
    return result,control

def run_owned(command,**kwargs):
    """The deadline ends the owned session, including the nested model worker."""
    require(platform.system() in ('Darwin','Linux') and hasattr(os,'killpg'))
    timeout=kwargs.pop('timeout')
    kwargs.pop('check');kwargs.pop('capture_output')
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            start_new_session=True,**kwargs) as process:
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.communicate(timeout=5)
            raise subprocess.TimeoutExpired('owned reference worker',timeout) from None
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)

def execute(request,cache,runner=run_owned):
    if cache is None:
        raise ReferenceFailure('model_cache_required','Choose the verified local model cache to evaluate selected passages.')
    cache=Path(cache).expanduser().absolute()
    if not cache.is_dir() or cache.is_symlink():
        raise ReferenceFailure('model_cache_unavailable','Use an existing verified local model cache.')
    with tempfile.TemporaryDirectory(prefix='aitrust-reference-') as temporary:
        base=Path(temporary).resolve();os.chmod(base,0o700)
        create(base/'input',REPO,{'request.json':(json.dumps(request,allow_nan=False)+'\n').encode()})
        command=[sys.executable,str(REPO/'scripts/check-nli-pairs.py'),
            str(base/'input/request.json'),'--model-cache',str(cache),'--details',str(base/'result')]
        env={'PATH':'/usr/bin:/bin','HOME':str(base),'HF_HUB_OFFLINE':'1',
            'TOKENIZERS_PARALLELISM':'false','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',
            'PYTHONDONTWRITEBYTECODE':'1'}
        try:
            run=runner(command,capture_output=True,timeout=55,env=env,check=False,close_fds=True)
        except subprocess.TimeoutExpired:
            raise ReferenceFailure('model_deadline','Retry fewer or shorter passages within the published input limits.') from None
        # Never echo subprocess output, private paths or native exception text.
        if run.returncode!=0:
            raise ReferenceFailure('model_unavailable','Check pinned assets, locked dependencies and the supported network-denied sandbox.')
        require(len(run.stdout)<=10000 and len(run.stderr)<=10000)
        return parse_details(source(base/'result/observations.json',REPO,100000),request)

def check(record,subject,cache=None,threshold=.75,maximum=5,runner=run_owned):
    request=references.prepare(record,subject,threshold,maximum)
    if request is None:
        result=references.observe(record,subject,None,None,threshold,maximum)
        result['network_control']='model_not_invoked'
        return result
    output,control=execute(request,cache,runner)
    _,selected=validate(request);rows=iter(zip(selected,output['pairs']))
    def replay(premise,hypothesis):
        (_,_,_,expected_premise,expected_hypothesis),row=next(rows)
        require((premise,hypothesis)==(expected_premise,expected_hypothesis))
        return row['logits'],row['token_count']
    result=references.observe(record,subject,replay,output['model_identity'],threshold,maximum)
    require(len(result['observations'])==len(output['pairs']))
    result['network_control']=control
    return result

def summary(result,saved):
    return {'profile':result['profile'],'state':result['state'],
        'retrieval_evaluation_obtained':True,'model_evaluation_obtained':result['model_evaluation_obtained'],
        'passages_evaluated':len(result['observations']),
        'result':('A local model compared the selected reference passages. These are research observations, not verified facts.'
            if result['model_evaluation_obtained'] else 'No passage met this lexical selection threshold. This does not show the claim is false.'),
        'network_control':result['network_control'],'detailed_output_saved':saved,
        'reference_freshness':'unestablished','calibrated_probability':False,
        'independent_corroboration':False,'truth_established':False,'tag_asserted':False,'release_approved':False}

def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--subject',type=Path,required=True,help='Private UTF-8 text file, not shell argument text.')
    parser.add_argument('--model-cache',type=Path)
    parser.add_argument('--threshold',type=float,default=.75)
    parser.add_argument('--maximum',type=int,default=5)
    parser.add_argument('--details',type=Path,help='New private output folder; never overwrite.')
    parser.add_argument('--review-windows',type=Path,
        help='Optional private declared-window policy for every attached reference; not freshness evidence.')
    args=parser.parse_args(argv)
    try:
        record=corpus.parse(source(args.corpus,REPO,corpus.MAX_STORE_BYTES))
        subject=source(args.subject,REPO,8000).decode('utf-8','strict')
        policy = review_window.capture(source(args.review_windows, REPO, MAX_POLICY_BYTES)) if args.review_windows else None
        before = review_window.preflight(record, policy, review_window.utc_now()) if policy is not None else None
        result=check(record,subject,args.model_cache,args.threshold,args.maximum)
        after = review_window.preflight(record, policy, review_window.utc_now()) if policy is not None else None
        window_summary = review_window.summary(before, after) if policy is not None else None
        if args.details:
            files={'reference-observations.json':(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()}
            if policy is not None:
                files['reference-window-check.json']=(json.dumps({'before':before,'after':after},indent=2,allow_nan=False)+'\n').encode()
            create(args.details,REPO,files)
        console=summary(result,args.details is not None)
        if policy is not None:console['declared_review_windows']=window_summary
        print(json.dumps(console,ensure_ascii=True,allow_nan=False));return 0
    except review_window.WindowFailure as error:
        print(json.dumps({'state':'UNAVAILABLE','reason':error.category,
            'next_step':'Review every attached source and its declared window; passing dates do not prove freshness or truth.',
            'tag_asserted':False}),file=sys.stderr);return 2
    except ReferenceFailure as error:
        print(json.dumps({'state':'UNAVAILABLE','reason':error.category,'next_step':error.action,'tag_asserted':False}),file=sys.stderr);return 2
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,RecursionError,ImportError,AttributeError,subprocess.SubprocessError,PacketError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'invalid_private_input_or_method_contract',
            'next_step':'Check private file permissions, corpus identity and the published ASCII selection limits.','tag_asserted':False}),file=sys.stderr);return 2

if __name__=='__main__':
    raise SystemExit(main())
