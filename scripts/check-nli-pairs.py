"""Owner-private sentence-pair research; summary only, no tag issuance or collection."""
import argparse,json,os,platform,shutil,subprocess,sys,tempfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(REPO))
from research.nli.pairs import PairError,require,validate,analyze
from research.nli.backend import expected_identity
from source_snapshot import read_file,unique
from tools.blind_review_io import source,PacketError,create

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Sentence-pair command refused; use --help for required arguments.\n')

def worker(cache):
    require(os.environ.get('AITRUST_NLI_WORKER_PROFILE')=='bounded-sentence-pair-worker/1')
    require(platform.system() in ('Darwin','Linux'))
    raw=sys.stdin.buffer.read(262145);require(0<len(raw)<=262144)
    request=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(PairError('Invalid number')))
    validate(request)
    if platform.system() in ('Linux','Darwin'):
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(35,35))
        if platform.system()=='Linux':
            resource.setrlimit(resource.RLIMIT_AS,(2_147_483_648,2_147_483_648))
    if platform.system()=='Linux':
        from research.nli.network import install_linux_network_filter
        install_linux_network_filter()
    else:
        # Exercise denial before model loading. The parent launches this worker
        # with the OS deny-network profile; this sends no example bytes.
        import errno,socket
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            try:probe.connect(('127.0.0.1',9))
            except PermissionError as error:require(error.errno==errno.EPERM)
            else:raise PairError('Required network denial unavailable')
    from research.nli.backend import Backend
    backend=Backend(cache,read_file)
    result=analyze(request,backend,backend.identity)
    print(json.dumps(result,allow_nan=False,separators=(',',':')))

def main():
    parser=Parser(description=__doc__);parser.add_argument('input',type=Path,nargs='?');parser.add_argument('--model-cache',type=Path,required=True);parser.add_argument('--details',type=Path);parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    if args.worker:
        require(args.input is None and args.details is None);worker(args.model_cache);return
    require(args.input is not None)
    raw=source(args.input,REPO,262144)
    request=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(PairError('Invalid number')));validate(request)
    cache=args.model_cache.absolute()
    require(cache.is_dir() and not cache.is_symlink())
    command=[sys.executable,str(Path(__file__).resolve()),'--worker','--model-cache',str(cache)]
    if platform.system()=='Darwin':
        require(Path('/usr/bin/sandbox-exec').is_file());command=['/usr/bin/sandbox-exec','-p','(version 1) (allow default) (deny network*)',*command];network='macos_sandbox_deny_network'
    elif platform.system()=='Linux':
        network='linux_worker_seccomp_network_denial'
    else:raise PairError('Local model sandbox unavailable')
    with tempfile.TemporaryDirectory(prefix='aitrust-nli-home-') as temporary:
        env={'PATH':'/usr/bin:/bin','HOME':str(Path(temporary).resolve()),'AITRUST_NLI_WORKER_PROFILE':'bounded-sentence-pair-worker/1','HF_HUB_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
        r=subprocess.run(command,input=raw,capture_output=True,timeout=45,env=env,check=False)
    require(r.returncode==0 and 0<len(r.stdout)<=100000)
    result=json.loads(r.stdout,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(PairError('Invalid number')))
    validate_observation(request,result)
    result['network_control']=network
    if args.details:
        create(args.details,REPO,{'observations.json':(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()})
    print(json.dumps({'profile':result['profile'],'evaluation_obtained':True,'pairs_evaluated':len(result['pairs']),'result':'local model observations; inspect private details before interpreting them','network_control':network,'detailed_output_saved':args.details is not None,'calibrated_probability':False,'tag_asserted':False,'release_approved':False}))

def validate_observation(request,result):
    require(isinstance(result,dict) and isinstance(result.get('pairs'),list))
    require(len(result['pairs'])==len(request['pairs']))
    rows=iter(result['pairs'])
    def replay(first,second):
        row=next(rows)
        return row['logits'],row['token_count']
    rebuilt=analyze(request,replay,expected_identity())
    # Exact JSON types, field set, identity, spans, score normalization and limitations.
    require(json.dumps(result,sort_keys=True,allow_nan=False)==json.dumps(rebuilt,sort_keys=True,allow_nan=False))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,RecursionError,ImportError,AttributeError,subprocess.SubprocessError,PacketError):
        print('Sentence-pair research unavailable; check private input, pinned assets and supported sandbox.',file=sys.stderr);raise SystemExit(2)
