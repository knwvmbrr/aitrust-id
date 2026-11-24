"""Small source/IO controls; deliberately no model, optional SDK, download or pip execution."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import visual_score_qualification as q

class QualificationTests(unittest.TestCase):
 def test_source_map_tracks_external_card_not_copied_body(self):
  paths=q.source_map();new='integrations/visual-score-reference/1.0.0/hf-model-card-reference.json'
  self.assertIn(new,paths)
  self.assertNotIn('integrations/visual-score-reference/1.0.0/hf-model-card.md',paths)
  self.assertEqual(q.SOURCE_PATHS.count(new),1)
  self.assertEqual(paths[new],hashlib.sha256((ROOT/new).read_bytes()).hexdigest())
  self.assertEqual(len(paths),88)
  self.assertTrue({'tools/visual_score_budget.py','scripts/run-visual-score-phase.py','tests/test_visual_score_budget.py','tests/test_visual_score_workflow.py'}<=set(paths))
 def test_complete_retained_lock(self):
  d=q.selection();self.assertEqual(len(d['packages']),39);self.assertEqual(sum(x['wheel']['size'] for x in d['packages']),272974128)
  self.assertEqual(d['role_counts'],{'runtime':8,'runtime_and_reference':4,'qualification_reference_only':27})
 def test_coherent_manifest_rebind_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);path=root/q.DATA;path.parent.mkdir(parents=True);d=json.loads((ROOT/q.DATA).read_text());d['packages'][0]['wheel']['url']='https://example.org/other.whl';path.write_text(json.dumps(d))
   with self.assertRaises(q.QualificationRefused):q.selection(root)
 def test_changed_lock_refused(self):
  original=q.raw_file
  def read(path,cap):
   raw=original(path,cap);return raw+b'\n' if Path(path)==ROOT/q.LOCK else raw
  with mock.patch.object(q,'raw_file',side_effect=read):
   with self.assertRaises(q.QualificationRefused):q.selection()
 def test_changed_sidecar_refused(self):
  original=q.raw_file
  def read(path,cap):
   raw=original(path,cap);return raw+b'\n' if str(path).endswith('torch.metadata') else raw
  with mock.patch.object(q,'raw_file',side_effect=read):
   with self.assertRaises(q.QualificationRefused):q.selection()
 def test_exclusive_write_no_overwrite(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x';q.write_new(p,b'first')
   with self.assertRaises(FileExistsError):q.write_new(p,b'other')
   self.assertEqual(p.read_bytes(),b'first');self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
 def test_raw_file_symlink_fifo_and_size_refuse(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x';p.write_bytes(b'123');s=Path(folder)/'link';s.symlink_to(p);fifo=Path(folder)/'fifo';os.mkfifo(fifo)
   with self.assertRaises(OSError):q.raw_file(s,10)
   with self.assertRaises(q.QualificationRefused):q.raw_file(fifo,10)
   with self.assertRaises(q.QualificationRefused):q.raw_file(p,2)
 def test_redirect_exact_hosts_no_credentials(self):
  redirect=q.Redirect();request=__import__('urllib.request',fromlist=['Request']).Request('https://huggingface.co/x')
  for url in ['http://huggingface.co/x','https://huggingface.co.evil.invalid/x','https://name:secret@huggingface.co/x','https://huggingface.co:444/x']:
   with self.assertRaises(q.QualificationRefused):redirect.redirect_request(request,None,302,'',{},url)
 def test_exact_tokenizer_source_preservation_and_private_lifecycle(self):
  import base64
  raw,d=q.source_companion();self.assertEqual((len(d['packages']),len(d['texts']),len(d['associations'])),(153,93,309))
  self.assertEqual(d['carried_notices'],[]);self.assertTrue(all(v is False for v in d['claims'].values()))
  self.assertEqual(sum(len(base64.b64decode(r['base64']))for r in d['texts']),300341)
  with mock.patch.object(q.json,'loads')as decode,self.assertRaises(q.QualificationRefused):q._source_companion(b'X'+raw[1:])
  decode.assert_not_called()
  mutations=[lambda x:x['target'].update(sha256='0'*64),lambda x:x['source'].update(commit='0'*40),lambda x:x['texts'][0].update(base64='AAAA'),lambda x:x['packages'].__setitem__(1,x['packages'][0]),lambda x:x['associations'][0].update(term_sha256='0'*64),lambda x:x['claims'].update(redistribution_approved=True),lambda x:x.update(carried_notices=[{'invented':True}])]
  for change in mutations:
   changed=json.loads(raw);change(changed);other=q._canonical(changed)+b'\n'
   # Coherent producer-error fixtures, not a runtime caller hash override.
   with self.subTest(change=change),mock.patch.object(q,'COMPANION_SHA',q.sha(other)),mock.patch.object(q,'COMPANION_BYTES',len(other)),self.assertRaises(q.QualificationRefused):q._source_companion(other)
  with tempfile.TemporaryDirectory()as folder:
   parent=Path(folder).resolve();parent.chmod(0o700);path=parent/'inert.whl'
   metadata=b'Metadata-Version: 2.4\nName: tokenizers\nVersion: 0.23.3\n\n'
   with zipfile.ZipFile(path,'w')as archive:archive.writestr('tokenizers-0.23.3.dist-info/METADATA',metadata)
   target={**q.TOKENIZER_TARGET,'bytes':path.stat().st_size,'sha256':q.sha(path.read_bytes()),'metadata_bytes':len(metadata),'metadata_sha256':q.sha(metadata)}
   row={'name':'tokenizers','version':'0.23.3','metadata_sha256':q.sha(metadata),'license_files_declared':[],'wheel':{'filename':target['filename'],'size':target['bytes'],'sha256':target['sha256'],'url':'https://example.invalid/INERT.whl'}}
   # This synthetic ZIP branch control substitutes only test identity and the
   # already separately validated companion provider. Actual pinned-wheel proof
   # is retained separately; this is no wheel, compiled or native admission.
   with mock.patch.object(q,'TOKENIZER_TARGET',target),mock.patch.object(q,'source_companion',return_value=(raw,d)):
    result=q.inspect_wheel(path,row);self.assertEqual(result['notices'],[]);self.assertEqual(result['carried_notices'],[]);self.assertEqual(result['supplemental_source_preservation'],q.companion_summary())
    with mock.patch.object(q,'source_companion',side_effect=q.QualificationRefused),self.assertRaises(q.QualificationRefused):q.inspect_wheel(path,row)
    old=path.read_bytes();path.write_bytes(old[:-1]+bytes([old[-1]^1]))
    with self.assertRaises(q.QualificationRefused):q.inspect_wheel(path,row)
    path.write_bytes(old)
   unknown={**row,'name':'unknown'}
   with self.assertRaises(q.QualificationRefused):q.inspect_wheel(path,unknown)
   stage=parent/'visual-score-notice-control';stage.mkdir(mode=0o700);st=stage.stat();identity=[st.st_dev,st.st_ino]
   from tools import visual_score_runtime as runtime
   with mock.patch.object(runtime,'isolation'),mock.patch.object(q,'call')as child:
    with self.assertRaises(FileNotFoundError):q.install(stage,identity)
    child.assert_not_called()
   q.write_new(stage/q.COMPANION_LEAF,raw);self.assertEqual(stat.S_IMODE((stage/q.COMPANION_LEAF).stat().st_mode),0o600)
   with mock.patch.object(runtime,'isolation'),mock.patch.object(q,'selection',return_value={'packages':[]}),mock.patch.object(q,'call')as child:
    q.install(stage,identity)
    self.assertEqual(child.call_count,2) # INERT empty-package fixture; no pip/venv executes.
   with self.assertRaises(FileExistsError):q.write_new(stage/q.COMPANION_LEAF,raw)
   snap=q.snapshot
   def drift(directory):
    entries=snap(directory);(stage/q.COMPANION_LEAF).write_bytes(b'X'+raw[1:]);return entries
   with mock.patch.object(q,'snapshot',side_effect=drift),self.assertRaises(q.QualificationRefused):q.seal_inventory(stage,identity)
   self.assertTrue(stage.exists());(stage/q.COMPANION_LEAF).write_bytes(raw)
   sealed=q.seal_inventory(stage,identity);self.assertEqual(sealed['source_notice_companion'],q.companion_summary());self.assertIn(q.COMPANION_LEAF,sealed['entries'])
   (stage/q.COMPANION_LEAF).write_bytes(b'X'+raw[1:])
   with mock.patch.object(runtime,'isolation'),mock.patch.object(q,'call')as child:
    with self.assertRaises(q.QualificationRefused):q.install(stage,identity)
    child.assert_not_called()
   with self.assertRaises(q.CleanupUncertain):q.cleanup(stage,identity,sealed['entries'])
   (stage/q.COMPANION_LEAF).write_bytes(raw)
   packages=[{'name':r['name'],'version':r['version'],'notices':[{'member':'INERT-license','sha256':'0'*64,'bytes':1}]}for r in q.selection()['packages']]
   token=next(r for r in packages if r['name']=='tokenizers');token.update(notices=[],carried_notices=[],supplemental_source_preservation=q.companion_summary())
   q.write_new(stage/'notice-observations.json',q._canonical({'format':'visual-score-wheel-notices/v2','packages':packages,'legal_clearance':False}))
   self.assertEqual(q.notice_observations(stage)['packages'],packages)
   (stage/q.COMPANION_LEAF).write_bytes(raw[:-1]+b' ')
   with self.assertRaises(q.QualificationRefused):q.notice_observations(stage)
   (stage/q.COMPANION_LEAF).write_bytes(raw)
   current=q.seal_inventory(stage,identity);q.cleanup(stage,identity,current['entries']);self.assertFalse(stage.exists())
 def test_failed_forward_diagnostics_and_bounded_sdk_probe(self):
  import contextlib,types,subprocess,time
  from tools import visual_score as core,visual_score_assets as assets,visual_score_runtime as runtime,visual_score_process as process
  spec=importlib.util.spec_from_file_location('forward_diagnostic_verifier',ROOT/'scripts/verify-visual-score-qualification.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
  secret='PRIVATE_CANARY /private/input?token=PRIVATE'
  unavailable=core.unavailable('worker_unavailable');last={};original_spawn=v.subprocess.Popen;children=[]
  def spawn(argv,*args,**kwargs):
   code='import sys;sys.stdin.buffer.read();print('+repr(json.dumps(unavailable))+');sys.exit(2)'
   child=original_spawn([sys.executable,'-I','-S','-B','-c',code],*args,**kwargs);children.append(child);return child
  with tempfile.TemporaryDirectory()as folder,mock.patch.dict(os.environ,{'VISUAL_QUAL_TMP':folder}),mock.patch.object(v.subprocess,'Popen',side_effect=spawn):
   result=v.native_cli(Path(folder)/'inert-not-read',Path(folder)/'models-not-read',diagnostic=last,call_id='gradient.png_production')
  self.assertEqual(result,unavailable);self.assertEqual(last,{'call_id':'gradient.png_production','phase':'validated','state':'UNAVAILABLE','reason':'worker_unavailable','exit_status':2,'exception_class':None});self.assertIsNotNone(children[0].returncode)
  self.assertEqual(v.validate_last_call(last),last)
  for change in [lambda d:d.update(call_id=secret),lambda d:d.update(exit_status=True),lambda d:d.update(reason=secret),lambda d:d.update(exception_class=secret)]:
   d=dict(last);change(d)
   with self.assertRaises(q.QualificationRefused):v.validate_last_call(d)
  # No SDK imports: these exact fake modules are used only by this source control.
  isolation={'loopback_only_observed':True,'capability_sets_zero':True,'no_new_privileges':True,'nonroot':True};calls=[]
  torch=types.ModuleType('torch');torch.__version__=runtime.VERSIONS['torch'];torch.set_num_threads=lambda n:calls.append(('threads',n));torch.set_num_interop_threads=lambda n:calls.append(('interop',n));torch.use_deterministic_algorithms=lambda b:calls.append(('deterministic',b))
  safe=types.ModuleType('safetensors');safe.safe_open=object();safetorch=types.ModuleType('safetensors.torch');safetorch.load=object();pil=types.ModuleType('PIL');pil.Image=object();pil.features=object()
  with mock.patch.dict(sys.modules,{'torch':torch,'safetensors':safe,'safetensors.torch':safetorch,'PIL':pil}),mock.patch.object(runtime,'isolation',return_value=isolation),mock.patch.object(v.importlib.metadata,'version',side_effect=lambda n:runtime.VERSIONS[n]):
   observed=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL);self.assertEqual(observed['state'],'SDK_AVAILABLE');self.assertFalse(observed['actual_model_forward_completed']);self.assertEqual(v.validate_sdk_probe(observed),observed);self.assertEqual(calls,[('threads',1),('interop',1),('deterministic',True)])
   with mock.patch.object(torch,'set_num_interop_threads',side_effect=RuntimeError(secret)):
    failed=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
   self.assertEqual((failed['stage'],failed['exception_class'],failed['errno'],failed['os_error_class']),('cpu_interop_threads','RuntimeError',None,'other_or_missing'));self.assertNotIn('PRIVATE',json.dumps(failed));self.assertEqual(failed['state'],'UNAVAILABLE')
   for name,stage in [('set_num_threads','cpu_intraop_threads'),('set_num_interop_threads','cpu_interop_threads'),('use_deterministic_algorithms','cpu_deterministic_algorithms')]:
    with mock.patch.object(torch,name,side_effect=PermissionError(13,secret,secret)):
     denied=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
    self.assertEqual((denied['stage'],denied['exception_class'],denied['errno'],denied['os_error_class']),(stage,'PermissionError',13,'permission_denied'));self.assertEqual(v.validate_sdk_probe(denied),denied);self.assertNotIn('PRIVATE',json.dumps(denied))
   for number,expected,category in [(1,1,'permission_denied'),(13,13,'permission_denied'),(12,12,'resource_exhausted'),(23,23,'resource_exhausted'),(24,24,'resource_exhausted'),(28,28,'resource_exhausted'),(30,30,'read_only_filesystem'),(None,None,'other_or_missing'),(True,None,'other_or_missing'),(987654,None,'other_or_missing')]:
    with mock.patch.object(torch,'set_num_threads',side_effect=OSError(number,secret)):
     denied=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
    self.assertEqual(denied['errno'],expected);self.assertEqual(denied['os_error_class'],category);v.validate_sdk_probe(denied);self.assertNotIn('PRIVATE',json.dumps(denied))
   self.assertEqual((observed['trace_roles'],observed['trace_truncated'],observed['filename_role'],observed['observed_torch_git_version']),([],False,'other_or_missing',None))
   # Already-present module fields only; no lazy SDK version import/getattr.
   version=types.ModuleType('torch.version');torch.version=version
   for claim,expected in [('a1'*20,'a1'*20),('A1'*20,None),('g'*40,None),('a'*41,None),(True,None),(None,None)]:
    version.git_version=claim;self.assertEqual(v._probe_git_version(torch),expected)
   version.git_version='a1'*20
   class TorchModuleSubclass(types.ModuleType):pass
   torch_subclass=TorchModuleSubclass('torch');torch_subclass.version=version
   self.assertEqual(v._probe_git_version(torch_subclass),'a1'*20)
   with mock.patch.object(torch,'use_deterministic_algorithms',side_effect=PermissionError(13,secret,'/held-home/cache')) ,mock.patch.dict(os.environ,{'HOME':'/held-home'}):
    located=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
   self.assertEqual(located['filename_role'],'private_home_descendant');self.assertEqual(located['observed_torch_git_version'],'a1'*20);v.validate_sdk_probe(located)
   for path,expected in [('/held-home','private_home'),('/held-home/cache','private_home_descendant'),('/held-venv','venv_root'),('/held-venv/lib','venv_descendant'),(v.PROBE_MODEL_SENTINEL,'model_sentinel'),('/held-home-neighbor/cache','other_or_missing'),('/held-venv-neighbor','other_or_missing'),('/held-home/../elsewhere','other_or_missing'),('/held-home/./cache','other_or_missing'),('/held-home//cache','other_or_missing'),('//held-home/cache','other_or_missing'),('/held-home/','other_or_missing'),('/held-home/\0cache','other_or_missing'),('/physical-alias/cache','other_or_missing'),('/'+'x'*2048,'other_or_missing'),(None,'other_or_missing'),(object(),'other_or_missing')]:
    self.assertEqual(v._probe_filename_role(path,'/held-home','/held-venv'),expected)
   # Finite inert frame objects exercise the bounded traversal without source,
   # paths, exception formatting or optional SDK imports.
   pairs=list(v.SDK_TRACE_ROLES)+[(secret,secret),('x'*257,'cache_dir'),('torch._inductor.codecache','x'*129)]
   def trace_chain(pairs):
    chain=None
    for module,function in reversed(pairs):chain=types.SimpleNamespace(tb_frame=types.SimpleNamespace(f_globals={'__name__':module},f_code=types.SimpleNamespace(co_name=function)),tb_next=chain)
    return chain
   self.assertEqual(v._probe_trace_roles(trace_chain(pairs)),(['cache_root','cache_lock','header_dir','cpp_dir','other','other','other'],False))
   self.assertEqual(v._probe_trace_roles(trace_chain([pairs[0]]*32)),(['cache_root']*32,False));self.assertEqual(v._probe_trace_roles(trace_chain([pairs[0]]*33)),(['cache_root']*32,True))
   namespace={'__name__':'torch._inductor.runtime.cache_dir_utils','secret':secret}
   exec(compile('def cache_dir(*args):\n raise PermissionError(13, secret, "/held-home/cache")','<inert-closed-frame>','exec'),namespace)
   with mock.patch.object(torch,'use_deterministic_algorithms',namespace['cache_dir']),mock.patch.dict(os.environ,{'HOME':'/held-home'}):
    framed=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
   self.assertEqual(framed['trace_roles'][-1],'cache_root');self.assertEqual(framed['filename_role'],'private_home_descendant');self.assertNotIn('PRIVATE',json.dumps(framed));self.assertNotIn('held-home',json.dumps(framed));v.validate_sdk_probe(framed)
   worst={**framed,'trace_roles':['cache_root']*32,'trace_truncated':True}
   self.assertEqual(v.validate_sdk_probe(worst),worst);self.assertLessEqual(len(json.dumps(worst,sort_keys=True).encode()),2048)
   combined={'primary_exception_class':'QualificationRefused','last_call':last,'sdk_probe':{'diagnostic_only':True,'state':'COMPLETED','reason':None,'timeout_seconds':15.,'probe':worst}}
   self.assertLessEqual(len(json.dumps(combined,sort_keys=True).encode()),4096)
   for change in [lambda d:d.update(trace_roles=['other']*33),lambda d:d.update(trace_roles=[secret]),lambda d:d.update(trace_roles=[{}]),lambda d:d.update(trace_roles=()),lambda d:d.update(trace_truncated=1),lambda d:d.update(trace_truncated=True,trace_roles=[]),lambda d:d.update(filename_role=secret),lambda d:d.update(observed_torch_git_version='A'*40),lambda d:d.update(observed_torch_git_version=True)]:
    invalid=dict(framed);change(invalid)
    with self.assertRaises(q.QualificationRefused):v.validate_sdk_probe(invalid)
   with mock.patch.object(v,'_probe_trace_roles',side_effect=ValueError(secret)),mock.patch.object(torch,'use_deterministic_algorithms',side_effect=PermissionError(13,secret,secret)):
    secondary=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
   self.assertEqual((secondary['stage'],secondary['errno'],secondary['exception_class']),('cpu_deterministic_algorithms',13,'PermissionError'));self.assertEqual(secondary['trace_roles'],[]);self.assertNotIn('PRIVATE',json.dumps(secondary));v.validate_sdk_probe(secondary)
   for change in [lambda d:d.update(errno=True),lambda d:d.update(errno=987654),lambda d:d.update(os_error_class=secret),lambda d:d.update(errno=13,os_error_class='read_only_filesystem')]:
    invalid=dict(denied);change(invalid)
    with self.assertRaises(q.QualificationRefused):v.validate_sdk_probe(invalid)
  with mock.patch.object(runtime,'isolation',side_effect=assets.Refused('network_isolation_unavailable')),mock.patch.object(v.importlib.metadata,'version')as versions:
   refused=v._sdk_probe_infer(v.PROBE_BODY,v.PROBE_MODEL_SENTINEL)
  versions.assert_not_called();self.assertEqual(refused['stage'],'isolation');self.assertIsNone(refused['isolation'])
  now=time.monotonic_ns()
  for stop,expected in [(now+30*10**9,15.),(now+8*10**9,2.),(now+6*10**9,None)]:
   with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':str(stop)}),mock.patch.object(v.time,'monotonic_ns',return_value=now):
    budget=v._probe_budget();self.assertEqual(None if budget is None else budget[2],expected)
  with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':'invalid'}),mock.patch.object(process,'run')as run:
   self.assertEqual(v.sdk_failure_probe(last,RuntimeError())['state'],'SKIPPED');run.assert_not_called()
  with mock.patch.object(process,'run')as run:
   self.assertEqual(v.sdk_failure_probe(last,KeyboardInterrupt())['state'],'SKIPPED');run.assert_not_called()
  probe_source=process.run;home_paths=[];probe_children=[];actual_spawn=process.subprocess.Popen
  def track_spawn(*args,**kwargs):child=actual_spawn(*args,**kwargs);probe_children.append(child);return child
  def inert_probe(argv,wire,timeout):
   self.assertEqual(argv[-1],'--sdk-diagnostic-worker');self.assertLessEqual(timeout,15.);self.assertGreater(timeout,0)
   length=int.from_bytes(wire[:4],'big');header=json.loads(wire[4:4+length]);self.assertEqual(wire[4+length:],v.PROBE_BODY);home=Path(header['cache_dir']);home_paths.append(home);self.assertEqual(stat.S_IMODE(home.stat().st_mode),0o500);self.assertEqual(list(home.iterdir()),[])
   program='import sys;sys.stdin.buffer.read();print('+repr(json.dumps(observed))+')'
   return probe_source([sys.executable,'-I','-S','-B','-c',program],wire,timeout=timeout)
  with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':str(time.monotonic_ns()+40*10**9)}),mock.patch.object(process,'run',side_effect=inert_probe)as run,mock.patch.object(process.subprocess,'Popen',side_effect=track_spawn):
   checked=v.sdk_failure_probe(last,RuntimeError())
  self.assertEqual(checked['state'],'COMPLETED');self.assertEqual(run.call_count,1);self.assertTrue(all(not p.exists()for p in home_paths));self.assertTrue(all(p.returncode is not None for p in probe_children))
  # Real owned short-child timeout/reap; SDK/kernel resource claims are NOT made.
  def timeout_probe(argv,wire,timeout):return probe_source([sys.executable,'-I','-S','-B','-c','import time;time.sleep(.2)'],wire,timeout=.01)
  with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':str(time.monotonic_ns()+40*10**9)}),mock.patch.object(process,'run',side_effect=timeout_probe),mock.patch.object(process.subprocess,'Popen',side_effect=track_spawn):
   timed=v.sdk_failure_probe(last,RuntimeError())
  self.assertEqual(timed['state'],'UNAVAILABLE');self.assertEqual(timed['reason'],'deadline');self.assertTrue(all(p.returncode is not None for p in probe_children))
  original_home=assets.PrivateHome
  class CloseFault:
   def __enter__(self):self.inner=original_home();return self.inner.__enter__()
   def __exit__(self,*args):self.inner.__exit__(*args);raise assets.Refused('cleanup_uncertain')
  with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':str(time.monotonic_ns()+40*10**9)}),mock.patch.object(assets,'PrivateHome',CloseFault),mock.patch.object(process,'run',side_effect=inert_probe):
   uncertain=v.sdk_failure_probe(last,RuntimeError())
  self.assertEqual(uncertain['reason'],'cleanup_uncertain');self.assertTrue(all(not p.exists()for p in home_paths))
  retained=[]
  def nonempty_probe(argv,wire,timeout):
   length=int.from_bytes(wire[:4],'big');home=Path(json.loads(wire[4:4+length])['cache_dir']);retained.append(home)
   # Inert hostile same-owner fixture, not an SDK write or cleanup permission.
   home.chmod(0o700);(home/'sentinel').write_bytes(b'preserve');home.chmod(0o500)
   return json.dumps(observed).encode()
  try:
   with mock.patch.dict(os.environ,{'VISUAL_QUAL_FORWARD_STOP_NS':str(time.monotonic_ns()+40*10**9)}),mock.patch.object(process,'run',side_effect=nonempty_probe):
    nonempty=v.sdk_failure_probe(last,RuntimeError())
   self.assertEqual(nonempty['reason'],'cleanup_uncertain');self.assertEqual((retained[0]/'sentinel').read_bytes(),b'preserve')
  finally:
   for home in retained:home.chmod(0o700);(home/'sentinel').unlink();home.rmdir()
  with tempfile.TemporaryDirectory()as folder:
   stage=Path(folder);(stage/'tmp').mkdir();oldtemp=tempfile.tempdir;probe=mock.Mock();probe.connect.side_effect=OSError(101,'inert')
   def native(*args,diagnostic,call_id,**kwargs):
    value=core.unavailable('model_missing'if call_id=='missing_model'else'runtime_unavailable'if call_id=='no_sdk'else'worker_unavailable');diagnostic.clear();diagnostic.update(call_id=call_id,phase='validated',state='UNAVAILABLE',reason=value['reason'],exit_status=2,exception_class=None);return value
   try:
    with mock.patch.dict(os.environ,{'VISUAL_QUAL_OUTER_NETNS':'net:[inert-outside]'}),mock.patch.object(v.os,'readlink',return_value='net:[inert-inside]'),mock.patch.object(runtime,'isolation',return_value=isolation),mock.patch.object(v.socket,'socket',return_value=probe),mock.patch.object(v,'installed',return_value={}),mock.patch.object(v,'ps'),mock.patch.object(q,'notice_observations',return_value={}),mock.patch.object(v,'native_cli',side_effect=native),mock.patch.object(v,'sdk_failure_probe',side_effect=OSError(secret)):
     report=v.execute(stage,sys.executable)
   finally:tempfile.tempdir=oldtemp
   self.assertFalse(report['pass']);self.assertFalse(report['actual_model_forward_completed']);self.assertEqual(report['reason'],'qualification_failed')
   # Secondary failure must not erase the primary last-call reason.
   self.assertEqual(report['failure_diagnostics']['last_call']['reason'],'worker_unavailable');self.assertNotIn('PRIVATE',json.dumps(report));self.assertLessEqual(len(json.dumps(report['failure_diagnostics']).encode()),4096)
 def wheel(self,path,extra=None,declared=None):
  meta=b'Metadata-Version: 2.4\nName: example\nVersion: 1.0\nLicense-File: LICENSE\n\n'
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('example-1.0.dist-info/METADATA',meta);z.writestr('example-1.0.dist-info/licenses/LICENSE',b'MIT synthetic licence')
   for name,data in extra or []:z.writestr(name,data)
  return {'name':'example','version':'1.0','metadata_sha256':q.sha(meta),'license_files_declared':declared or ['LICENSE']}
 def test_actual_zip_metadata_notice(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x.whl';row=self.wheel(p);out=q.inspect_wheel(p,row);self.assertEqual(out['notices'][0]['sha256'],q.sha(b'MIT synthetic licence'));self.assertTrue(out['notices'][0]['publisher_declared'])
  # Real pinned wheel29 metadata layout, not a copied wheel or real vendored
  # code: primary bytes are the existing licensed retained METADATA; nested
  # bodies/notices below are explicitly inert parser fixtures.
  selected=q.selection()['packages'][28]
  self.assertEqual((selected['name'],selected['version']),('setuptools','84.2.1'))
  self.assertEqual(selected['wheel']['sha256'],'ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2')
  primary_bytes=(ROOT/selected['retained_metadata_path']).read_bytes()
  self.assertEqual(q.sha(primary_bytes),selected['metadata_sha256'])
  primary='setuptools-84.2.1.dist-info/METADATA'
  nested=('setuptools/_vendor/autocommand-2.2.2.dist-info/METADATA', 'setuptools/_vendor/backports.tarfile-1.2.0.dist-info/METADATA', 'setuptools/_vendor/importlib_metadata-8.7.1.dist-info/METADATA', 'setuptools/_vendor/jaraco.text-4.0.0.dist-info/METADATA', 'setuptools/_vendor/jaraco_context-6.1.0.dist-info/METADATA', 'setuptools/_vendor/jaraco_functools-4.4.0.dist-info/METADATA', 'setuptools/_vendor/more_itertools-10.8.0.dist-info/METADATA', 'setuptools/_vendor/packaging-26.3.dist-info/METADATA', 'setuptools/_vendor/platformdirs-4.4.0.dist-info/METADATA', 'setuptools/_vendor/tomli-2.4.0.dist-info/METADATA', 'setuptools/_vendor/wheel-0.46.3.dist-info/METADATA', 'setuptools/_vendor/zipp-3.23.0.dist-info/METADATA')
  self.assertEqual(len(nested),12)
  with tempfile.TemporaryDirectory() as folder:
   def container(name,mode='normal'):
    path=Path(folder)/name
    with zipfile.ZipFile(path,'w')as z:
     if mode!='nested_only':z.writestr(primary,b'changed primary'if mode=='changed_primary'else primary_bytes)
     z.writestr('setuptools-84.2.1.dist-info/licenses/LICENSE',b'INERT primary notice')
     for i,member in enumerate(nested):z.writestr(member,primary_bytes if mode=='changed_primary'and i==0 else b'Name: inert parser fixture\nVersion: 1.0\n')
     z.writestr('setuptools/_vendor/inert/LICENSE',b'INERT vendored notice')
     if mode=='two_primary':z.writestr('other-1.0.dist-info/METADATA',b'Name: inert\nVersion: 1.0\n')
     if mode=='unsafe_vendor':z.writestr('setuptools/_vendor/../escape',b'inert')
    return path
   observed=q.inspect_wheel(container('valid.whl'),selected)
   self.assertEqual({n['member']for n in observed['notices']},{'setuptools-84.2.1.dist-info/licenses/LICENSE','setuptools/_vendor/inert/LICENSE'})
   for mode in ('nested_only','changed_primary','two_primary','unsafe_vendor'):
    with self.assertRaises(q.QualificationRefused):q.inspect_wheel(container(mode+'.whl',mode),selected)
 def test_actual_zip_path_duplicate_notice_missing_refuse(self):
  with tempfile.TemporaryDirectory() as folder:
   for i,(extra,declared) in enumerate([([('../escape',b'x')],None),([('/escape',b'x')],None),([('bad\\escape',b'x')],None),([],['MISSING'])]):
    p=Path(folder)/(str(i)+'.whl');row=self.wheel(p,extra,declared)
    with self.assertRaises(q.QualificationRefused):q.inspect_wheel(p,row)
 def test_actual_zip_symlink_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x.whl';row=self.wheel(p)
   with zipfile.ZipFile(p,'a') as z:
    info=zipfile.ZipInfo('link');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'/outside')
   with self.assertRaises(q.QualificationRefused):q.inspect_wheel(p,row)
 def test_notice_bound_before_read(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x.whl';row=self.wheel(p);original=zipfile.ZipFile.infolist
   def entries(z):
    rows=original(z)
    for entry in rows:
     if entry.filename.endswith('/LICENSE'):entry.file_size=q.MAX_NOTICE+1
    return rows
   with mock.patch.object(zipfile.ZipFile,'infolist',entries):
    with self.assertRaises(q.QualificationRefused):q.inspect_wheel(p,row)
 def staged(self,parent):
  p=Path(parent)/'visual-score-owned';p.mkdir(mode=0o700);(p/'nested').mkdir();(p/'nested/f').write_bytes(b'private');st=p.stat();return p,[st.st_dev,st.st_ino]
 def test_actual_cleanup_exact_tree_not_symlink_target(self):
  with tempfile.TemporaryDirectory() as folder:
   outside=Path(folder)/'keep';outside.write_bytes(b'owner');p,ident=self.staged(folder);(p/'link').symlink_to(outside);inventory=q.snapshot(p);q.cleanup(p,ident,inventory);self.assertFalse(p.exists());self.assertEqual(outside.read_bytes(),b'owner')
 def test_cleanup_replacement_and_unknown_preflight_no_mutation(self):
  with tempfile.TemporaryDirectory() as folder:
   p,ident=self.staged(folder);inventory=q.snapshot(p);(p/'unknown').write_bytes(b'do not delete')
   with self.assertRaises(q.CleanupUncertain):q.cleanup(p,ident,inventory)
   self.assertEqual((p/'nested/f').read_bytes(),b'private');self.assertTrue((p/'unknown').exists())
   (p/'unknown').unlink();(p/'nested/f').rename(p/'nested/old');(p/'nested/f').write_bytes(b'successor')
   with self.assertRaises(q.CleanupUncertain):q.cleanup(p,ident,inventory)
   self.assertEqual((p/'nested/f').read_bytes(),b'successor')
 def test_cleanup_root_successor_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   p,ident=self.staged(folder);inventory=q.snapshot(p);p.rename(Path(folder)/'preserved');p.mkdir(mode=0o700)
   with self.assertRaises(q.QualificationRefused):q.cleanup(p,ident,inventory)
   self.assertTrue(p.exists());self.assertTrue((Path(folder)/'preserved/nested/f').exists())
 def test_owned_call_known_reaped_never_signalled(self):
  child=mock.Mock(returncode=0);child.wait.side_effect=OSError('after reap')
  with mock.patch.object(q.subprocess,'Popen',return_value=child),mock.patch('os.killpg') as kill:
   with self.assertRaises(OSError):q.call(['fixed'])
   kill.assert_not_called()
 def test_actual_total_timer_interrupts_stall(self):
  import time
  start=time.monotonic()
  with self.assertRaises(q.QualificationRefused):
   with q.total_budget(.02):time.sleep(.5)
  self.assertLess(time.monotonic()-start,.3)
 def test_acquisition_rejects_unapproved_url_before_file(self):
  with tempfile.TemporaryDirectory() as folder:
   destination=Path(folder)/'never'
   with self.assertRaises(q.QualificationRefused):q.acquire_file('https://evil.invalid/a',destination,1)
   self.assertFalse(destination.exists())
 def test_noncanonical_zip_alias_refused(self):
  for name in ['root//item','root/./item','../item','/item']:
   with self.assertRaises(q.QualificationRefused):q.safe_member(zipfile.ZipInfo(name))
 def test_finalizer_never_accepts_failed_removal(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   from tools.visual_score import unavailable
   for name,data in [('forward',{'format':'offline-image-score-native-qualification/v1','pass':True}),('clean',{'pass':False}),('removed',unavailable('model_missing')),('ps',{})]: (root/name).write_text(json.dumps(data))
   # Isolate only the trusted PS validator; failed removal must independently refuse.
   with mock.patch('runpy.run_path',return_value={'validate':lambda *_:{'state':'FINDING'}}):
    with self.assertRaises(q.QualificationRefused):q.finalize(root/'forward',root/'clean',root/'removed',root/'ps',root/'output')
   self.assertFalse((root/'output').exists())
 def test_reference_no_unsafe_loader_or_network_entry(self):
  source=(ROOT/'tools/visual_score_reference.py').read_text()
  import ast
  calls=[ast.unparse(n.func) for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call)]
  self.assertFalse(any(x.endswith(('torch.load','jit.load','from_pretrained','urlopen')) for x in calls));self.assertIn('CLIPVisionModelWithProjection',calls)
 def test_workflow_no_secret_signer_or_required_gate(self):
  s=(ROOT/'.github/workflows/visual-score-qualification.yml').read_text()
  self.assertIn('contents: read',s);self.assertIn("github.ref == 'refs/heads/codex/nov23-image-native-qualification'",s);self.assertIn("github.event_name == 'workflow_dispatch'",s);self.assertIn("inputs.expected_commit == github.sha",s)
  for bad in ['id-token:','secrets.','pull_request_target','rm -rf','torch.load','pip install --upgrade']:self.assertNotIn(bad,s)
  self.assertIn('retention-days: 7',s);self.assertIn('--clear-groups --no-new-privs --bounding-set=-all',s);self.assertIn('inventory-sha256',(ROOT/'scripts/run-visual-score-phase.py').read_text())
 def test_production_source_unchanged_from_source_stage(self):
  frozen=json.loads((ROOT/'runs/2026-11-23-offline-image-score-final-source-controls.json').read_text())
  # Author proof structure is deliberately inspected, not inferred as numerical execution.
  values=[]
  def visit(v):
   if isinstance(v,dict):
    for k,x in v.items():
     if k in ('tools/visual_score.py','tools/visual_score_runtime.py','tools/visual_score_assets.py','tools/visual_score_process.py') and isinstance(x,str) and len(x)==64:values.append((k,x))
     visit(x)
   elif isinstance(v,list):
    for x in v:visit(x)
  visit(frozen);self.assertTrue(values)
  peer_raw=(ROOT/'runs/2026-11-23-hf-card-factual-reference-distinct-review.json').read_bytes()
  self.assertEqual(q.sha(peer_raw),'c81742135b10ea00fc75c24e58e44321dce4855a1f0544702464761b45a486c5')
  peer=json.loads(peer_raw)
  for path,digest in values:
   raw=(ROOT/path).read_bytes()
   if path=='tools/visual_score.py':
    # Explicit reviewed environment-only successor; the old source proof is not rewritten.
    self.assertEqual(digest,'8066d31995042d5d142d2c68b08fce5e8f5ad2d90fb1d4a9f7d17673d919fea8')
    self.assertEqual(q.sha(raw),'4ee21a460408d787fa6f6f4e23a56d62fd3a1325f0a025d5c89f3c88f8c5f79c')
    continue
   if path=='tools/visual_score_assets.py':
    # Historical source is retained: undo only the separately reviewed factual pins.
    self.assertEqual(q.sha(raw),peer['source_sha256'][path])
    text=raw.decode('utf-8');line=next(x for x in text.splitlines() if x.startswith('SOURCE_PINS='));original=line
    for current,previous in (("'hf-model-card-reference.json': '7ba894d89271710d574456154041d8dc98e0cb90af0929ce2ea77af782718621'","'hf-model-card.md': 'de4274ec48590ab3aa1c239720ff55e99a37f4165c117ba3ad7af2b7df72687c'"),("'source.json': 'f95f1008433c32216e0153c8ffd3d9cab4327abed047c19f28fd0c99d55253dc'","'source.json': '37ae88d90d3caa1a0d0274455b8e28326ddf77fb8848a80c56f3593ef721614a'")):
     self.assertEqual(original.count(current),1);original=original.replace(current,previous)
    self.assertEqual(text.count(line),1);raw=text.replace(line,original,1).encode('utf-8')
   self.assertEqual(q.sha(raw),digest)


class CleanupOwnershipTests(unittest.TestCase):
 def tree(self,folder):
  parent=Path(folder).resolve();p=parent/'visual-score-owned';p.mkdir(mode=0o700);(p/'nested').mkdir();(p/'nested/f').write_bytes(b'owned private fixture');outside=parent/'outside';outside.mkdir();os.link(p/'nested/f',outside/'f');st=p.stat();return p,[st.st_dev,st.st_ino],outside
 def assert_preserved(self,p,outside,original):
  self.assertEqual((outside/'f').read_bytes(),b'owned private fixture');self.assertEqual((original/'f').read_bytes(),b'owned private fixture');self.assertTrue(p.exists())
 def test_cleanup_exact_original_intermediate_link_after_snapshot(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);inventory=q.snapshot(p);capture=q.snapshot;original=p.parent/'original';swapped=[]
   def substitute(path):
    value=capture(path);(p/'nested').rename(original);(p/'nested').symlink_to(outside,target_is_directory=True);swapped.append(True);return value
   with mock.patch.object(q,'snapshot',side_effect=substitute):
    with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
   self.assertEqual(swapped,[True]);self.assertTrue((p/'nested').is_symlink());self.assert_preserved(p,outside,original)
 def test_cleanup_postcapture_directory_link_or_directory_swap(self):
  for kind in ['symlink','directory']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
    p,identity,outside=self.tree(folder);inventory=q.snapshot(p);ino=(p/'nested').stat().st_ino;names=q._names;original=p.parent/'original';swapped=[]
    def substitute(fd):
     result=names(fd)
     if os.fstat(fd).st_ino==ino and not swapped:
      (p/'nested').rename(original)
      if kind=='symlink':(p/'nested').symlink_to(outside,target_is_directory=True)
      else:(p/'nested').mkdir();os.link(outside/'f',p/'nested/f')
      swapped.append(True)
     return result
    with mock.patch.object(q,'_names',side_effect=substitute):
     with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
    self.assertEqual(swapped,[True]);self.assert_preserved(p,outside,original);self.assertTrue((p/'nested/f').exists())
 def test_cleanup_late_leaf_successor_is_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);inventory=q.snapshot(p);ino=(p/'nested').stat().st_ino;names=q._names;old=p.parent/'original-file';swapped=[]
   def substitute(fd):
    value=names(fd)
    if os.fstat(fd).st_ino==ino and not swapped:
     (p/'nested/f').rename(old);(p/'nested/f').write_bytes(b'successor');swapped.append(True)
    return value
   with mock.patch.object(q,'_names',side_effect=substitute):
    with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
   self.assertEqual(swapped,[True]);self.assertEqual((p/'nested/f').read_bytes(),b'successor');self.assertEqual(old.read_bytes(),b'owned private fixture');self.assertTrue((outside/'f').exists())
 def test_cleanup_root_or_parent_successor_after_snapshot(self):
  for kind in ['root','parent']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
    anchor=Path(folder).resolve()/'anchor';anchor.mkdir();p,identity,outside=self.tree(anchor);inventory=q.snapshot(p);capture=q.snapshot;swapped=[]
    def substitute(path):
     value=capture(path)
     if kind=='root':
      p.rename(anchor/'original-root');p.mkdir(mode=0o700);(p/'keep').write_bytes(b'successor')
     else:
      anchor.rename(anchor.parent/'original-anchor');anchor.mkdir();(anchor/p.name).mkdir(mode=0o700);(anchor/p.name/'keep').write_bytes(b'successor')
     swapped.append(True);return value
    with mock.patch.object(q,'snapshot',side_effect=substitute):
     with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
    self.assertEqual(swapped,[True]);self.assertEqual((p/'keep').read_bytes(),b'successor')
    original=anchor/'original-root' if kind=='root' else anchor.parent/'original-anchor'/p.name
    self.assertTrue((original/'nested/f').exists())
 def test_cleanup_new_unknown_after_snapshot_refuses_before_delete(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);inventory=q.snapshot(p);capture=q.snapshot
   def substitute(path):
    value=capture(path);(p/'unknown').write_bytes(b'not owned by inventory');return value
   with mock.patch.object(q,'snapshot',side_effect=substitute):
    with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
   self.assertTrue((p/'unknown').exists());self.assertTrue((p/'nested/f').exists());self.assertTrue((outside/'f').exists())
 def test_cleanup_mutations_are_single_leaf_fd_relative(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);(p/'nested/deeper').mkdir();(p/'nested/deeper/g').write_bytes(b'g');(p/'link').symlink_to(outside,target_is_directory=True);inventory=q.snapshot(p);unlink=os.unlink;rmdir=os.rmdir;calls=[]
   def checked_unlink(name,*,dir_fd=None):
    self.assertIsNotNone(dir_fd);self.assertNotIn('/',os.fspath(name));calls.append(('unlink',name));return unlink(name,dir_fd=dir_fd)
   def checked_rmdir(name,*,dir_fd=None):
    self.assertIsNotNone(dir_fd);self.assertNotIn('/',os.fspath(name));calls.append(('rmdir',name));return rmdir(name,dir_fd=dir_fd)
   with mock.patch.object(q.os,'unlink',side_effect=checked_unlink),mock.patch.object(q.os,'rmdir',side_effect=checked_rmdir):q.cleanup(p,identity,inventory)
   self.assertFalse(p.exists());self.assertEqual((outside/'f').read_bytes(),b'owned private fixture');self.assertEqual(len(calls),6)
 def test_cleanup_nested_open_fault_closes_all_acquired_descriptors(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);inventory=q.snapshot(p);opened=set();real_open=os.open;real_close=os.close;failed=[]
   def opened_at(name,*args,**kwargs):
    if name=='nested':failed.append(True);raise OSError('inert open fault')
    fd=real_open(name,*args,**kwargs);self.assertNotIn(fd,opened);opened.add(fd);return fd
   def closed(fd):
    self.assertIn(fd,opened);opened.remove(fd);return real_close(fd)
   with mock.patch.object(q.os,'open',side_effect=opened_at),mock.patch.object(q.os,'close',side_effect=closed):
    with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
   self.assertTrue(failed);self.assertEqual(opened,set());self.assertTrue((p/'nested/f').exists());self.assertTrue((outside/'f').exists())
 def test_cleanup_close_after_release_never_retries_reused_number(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);inventory=q.snapshot(p);ino=(p/'nested').stat().st_ino;marker=p.parent/'marker';marker.write_bytes(b'marker');real_open=os.open;real_close=os.close;opened=set();fault=[];marker_fds=[]
   def opened_at(*args,**kwargs):
    fd=real_open(*args,**kwargs);self.assertNotIn(fd,opened);opened.add(fd);return fd
   def closed(fd):
    self.assertIn(fd,opened);info=os.fstat(fd);opened.remove(fd);real_close(fd)
    if info.st_ino==ino and not fault:
     fault.append(fd);marker_fds.append(real_open(marker,os.O_RDONLY));raise OSError('released then failed close')
   try:
    with mock.patch.object(q.os,'open',side_effect=opened_at),mock.patch.object(q.os,'close',side_effect=closed):
     with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,inventory)
    self.assertEqual(opened,set());self.assertEqual(marker_fds,fault);self.assertEqual(os.read(marker_fds[0],6),b'marker');self.assertTrue((p/'nested/f').exists());self.assertTrue((outside/'f').exists())
   finally:
    for fd in marker_fds:real_close(fd)
 def test_cleanup_inventory_escape_and_depth_refuse_without_mutation(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);good=q.snapshot(p)
   for name in ['../outside/f','nested//f','nested/./f','nested/../../outside/f','/'.join(['x']*(q.MAX_TREE_DEPTH+1))]:
    bad=dict(good);bad[name]=good['nested/f']
    with self.assertRaises(q.CleanupUncertain):q.cleanup(p,identity,bad)
   self.assertTrue((p/'nested/f').exists());self.assertTrue((outside/'f').exists())
 def test_cleanup_snapshot_does_not_follow_directory_symlinks(self):
  with tempfile.TemporaryDirectory() as folder:
   p,identity,outside=self.tree(folder);(p/'pointer').symlink_to(outside,target_is_directory=True);inventory=q.snapshot(p)
   self.assertTrue(stat.S_ISLNK(inventory['pointer'][2]));self.assertNotIn('pointer/f',inventory);q.cleanup(p,identity,inventory);self.assertTrue((outside/'f').exists())


 def test_acquisition_diagnostics_are_bounded_private_and_never_mask_failure(self):
  import contextlib,sys,urllib.error
  from types import SimpleNamespace
  from tools import visual_score_assets as assets
  spec=importlib.util.spec_from_file_location('diagnostic_operator',ROOT/'scripts/run-visual-score-phase.py');operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
  private='PRIVATE_FAILURE_CANARY https://private.invalid/path?token=PRIVATE'
  rows=[{'name':'fixed'+str(i),'version':'1','wheel':{'filename':'fixed'+str(i)+'.whl','url':'https://example.invalid/fixed'+str(i),'size':5,'sha256':'0'*64}}for i in range(1,40)]
  for operation in ['capacity','head_fetch','head_layout','wheel','backbone','notice']:
   with self.subTest(operation=operation),tempfile.TemporaryDirectory()as folder:
    root=Path(folder).resolve();root.chmod(0o700);workspace=root/'visual-score-inert';wheel_calls=[]
    def fetch(url,destination,*a,**kw):
     if url==q.HEAD_URL:
      if operation=='head_fetch':raise urllib.error.HTTPError(private,403,private,{},None)
     elif url==q.MODEL_URL:
      if operation=='backbone':raise q.AcquisitionPredicate('sha256_mismatch',200)
     else:
      wheel_calls.append(url)
      if operation=='wheel'and len(wheel_calls)==3:raise TimeoutError(private)
     destination.write_bytes(b'INERT');return {'bytes':5,'sha256':'0'*64}
    def layout(raw):
     if operation=='head_layout':raise assets.Refused('head_format')
     return b'INERT_NOT_MODEL'
    def capacity(path):
     if operation=='capacity':raise q.QualificationRefused(private)
    original_write=q.write_new
    def notice(path,raw):
     if path.name==q.COMPANION_LEAF:return original_write(path,raw)
     if operation=='notice':raise OSError(private)
     raise AssertionError('No inert case may reach successful acquisition')
    with mock.patch.object(q,'selection',return_value={'packages':rows}),mock.patch.object(q,'capacity',side_effect=capacity),mock.patch.object(q,'acquire_file',side_effect=fetch),mock.patch.object(assets,'pinned_head',side_effect=layout),mock.patch.object(q,'inspect_wheel',return_value={'expanded_bytes':1}),mock.patch.object(q,'write_new',side_effect=notice),self.assertRaises(q.AcquisitionFailed)as caught:q.acquire(workspace)
    obs=caught.exception.observation;self.assertEqual(obs['operation'],operation);self.assertNotIn('PRIVATE',json.dumps(obs));self.assertNotIn(str(root),json.dumps(obs));self.assertLess(len(json.dumps(obs).encode()),4096);self.assertEqual(q.validate_acquisition_diagnostic(obs),obs)
    self.assertEqual(obs['role_counts']['head_fetched'],int(operation not in ['capacity','head_fetch']))
    self.assertEqual(obs['role_counts']['head_layout_validated'],int(operation in ['wheel','backbone','notice']))
    self.assertEqual(obs['role_counts']['wheels_completed'],2 if operation=='wheel'else 39 if operation in ['backbone','notice']else 0)
    self.assertEqual(obs['role_counts']['current_wheel_ordinal'],3 if operation=='wheel'else 0)
    self.assertEqual(obs['role_counts']['backbone_verified'],int(operation=='notice'));self.assertEqual(obs['role_counts']['notice_inventory_written'],0)
    if operation=='head_fetch':self.assertEqual((obs['category'],obs['reason_code'],obs['http_status']),('http_error','http_status',403))
    if operation=='head_layout':self.assertEqual((obs['category'],obs['reason_code']),('asset_refused','head_format'))
    if operation=='backbone':self.assertEqual((obs['reason_code'],obs['http_status']),('sha256_mismatch',200))
  obs=q.acquisition_failure(ValueError(private),'capacity')
  for mutate in [lambda d:d.update(url=private),lambda d:d.update(http_status=True),lambda d:d.update(operation=[]),lambda d:d['role_counts'].update(wheels_completed=40)]:
   malformed=json.loads(json.dumps(obs));mutate(malformed)
   with self.assertRaises(q.QualificationRefused):q.validate_acquisition_diagnostic(malformed)
  with tempfile.TemporaryDirectory()as folder:
   destination=Path(folder).resolve()/'inert';response=mock.MagicMock();response.status=200;response.headers={'Content-Length':'4'};response.__enter__.return_value=response
   opener=mock.Mock();opener.open.return_value=response
   with mock.patch.object(q.urllib.request,'build_opener',return_value=opener),self.assertRaises(q.AcquisitionPredicate)as caught:q._acquire_file(q.HEAD_URL,destination,5)
   self.assertEqual((caught.exception.reason,caught.exception.http_status),('declared_size_mismatch',200));response.read.assert_not_called()
  for write_error in [False,True]:
   with self.subTest(write_error=write_error),tempfile.TemporaryDirectory()as folder:
    reports=Path(folder).resolve();reports.chmod(0o700);workspace=reports/'visual-score-inert';failure=q.AcquisitionFailed(q.acquisition_failure(OSError(private),'head_fetch'));real_emit=operator.emit
    def emit(path,value):
     if write_error and path.name=='acquisition-diagnostic-private.json':raise OSError(private)
     return real_emit(path,value)
    with mock.patch.object(operator.b,'boot',return_value='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'):
     record=operator.b.new_record('a'*40)
     with mock.patch.object(q,'capacity_facts',return_value={'pass':True}),mock.patch.object(q,'main',side_effect=failure),mock.patch.object(operator,'emit',side_effect=emit),self.assertRaises(q.AcquisitionFailed)as caught:operator.worker('acquire',workspace,reports,sys.executable,record)
     self.assertIs(caught.exception,failure);operator.failure(reports,'acquire','phase_failed');out=json.loads((reports/'qualification.json').read_bytes());self.assertIs(out['pass'],False);self.assertEqual(out['state'],'UNQUALIFIED');self.assertNotIn('PRIVATE',json.dumps(out));self.assertEqual('acquisition_diagnostic'in out,not write_error)
     before=(reports/'qualification.json').read_bytes();operator.failure(reports,'acquire','phase_failed');self.assertEqual((reports/'qualification.json').read_bytes(),before)

  for complete in [False,True]:
   with self.subTest(entered_without_typed_diagnostic=not complete),tempfile.TemporaryDirectory()as folder:
    reports=Path(folder).resolve();reports.chmod(0o700);primary=OSError(private);real_emit=operator.emit
    def main(argv):
     if not complete:raise primary
     print(json.dumps({'pass':True,'workspace_devino':[1,2]})) # INERT completion only.
    def emit(path,value):
     if path.name=='acquisition-private.json':raise primary
     return real_emit(path,value)
    with mock.patch.object(operator.b,'boot',return_value='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'):
     record=operator.b.new_record('a'*40)
     with mock.patch.object(q,'capacity_facts',return_value={'pass':True}),mock.patch.object(q,'main',side_effect=main),mock.patch.object(operator,'emit',side_effect=emit),self.assertRaises(OSError)as caught:operator.worker('acquire',reports/'visual-score-inert',reports,sys.executable,record)
     self.assertIs(caught.exception,primary)
    file=reports/'acquisition-diagnostic-private.json';self.assertEqual(file.exists(),complete)
    if complete:
     value=json.loads(file.read_text());self.assertEqual(value['operation'],'notice');self.assertEqual(value['role_counts']['wheels_completed'],39);self.assertEqual(value['role_counts']['notice_inventory_written'],1)

if __name__=='__main__':unittest.main()
