"""Owned synthetic source/FS/probe controls. Mock authority is NEVER signature proof."""
import gzip,hashlib,inspect,io,json,os,stat,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import source_snapshot_managed as m
from tools.artifact_evidence_io import Capture,PrivateInputError,encoded

COMMIT='a'*40

def archive(files,commit=COMMIT):
 rows=[{'path':p,'mode':0o644,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in sorted(files.items())]
 meta=encoded({'profile':m.SOURCE_PROFILE,'source_commit':commit,'kind':'development_source_snapshot','tag_release_validated':False,'installed_dependencies_included':False,'files':rows})
 target=io.BytesIO()
 with gzip.GzipFile(fileobj=target,mode='wb',filename='',mtime=0) as compressed:
  with tarfile.open(fileobj=compressed,mode='w',format=tarfile.USTAR_FORMAT) as tar:
   for p,b in [(m.META,meta),*sorted(files.items())]:
    h=tarfile.TarInfo(m.PREFIX+p);h.size=len(b);h.mode=0o644;h.uid=h.gid=h.mtime=0;h.uname=h.gname='';tar.addfile(h,io.BytesIO(b))
 return target.getvalue()

class ManagedSourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve());self.addCleanup(self.temp.cleanup)
  self.dir=Path(self.temp.name);self.dir.chmod(0o700)
  self.files={p:(ROOT/p).read_bytes() for p in m.FILES}
  self.files['unselected-program.py']=b'raise RuntimeError("DO_NOT_EXECUTE_UNSELECTED")\n'
  self.raw=archive(self.files);self.inputs={}
  for key,raw in [('artifact',self.raw),('packet',encoded({'artifact':{'sha256':hashlib.sha256(self.raw).hexdigest(),'bytes':len(self.raw)}})),('spdx',b'{}'),('bundle',b'{}'),('trusted_root',b'{}')]:
   p=self.dir/key;p.write_bytes(raw);p.chmod(0o600);self.inputs[key]=p
  self.output=self.dir/'summary.json'
 def auth(self,record,*args):
  return {'state':'AUTHORIZED','route':'source-snapshot','source_commit':COMMIT,'artifact_sha256':record['artifact']['sha256'],'release_authorized':True,'policy_admitted':True,'attestation_verified':True}
 def verify(self):return m.verify_managed(**self.inputs,output=self.output,source_commit=COMMIT,root=ROOT)
 def mocks(self):return mock.patch.object(m.artifacts,'authorize_release',side_effect=self.auth),mock.patch.object(m.artifacts,'verify_packet',return_value={})
 def stage(self):
  stages=list(self.dir.glob('.source-managed-*'));self.assertEqual(len(stages),1);return stages[0]
 def replace_archive(self,raw):
  self.inputs['artifact'].write_bytes(raw);self.inputs['packet'].write_bytes(encoded({'artifact':{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}}))
 def test_real_authorizer_refusal_precedes_source_or_probe(self):
  with mock.patch.object(m,'_materialize') as build,mock.patch.object(m,'run_worker') as run:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   build.assert_not_called();run.assert_not_called()
  self.assertFalse(self.output.exists());self.assertFalse((self.stage()/'ps-source').exists())
 def test_real_fixed_probes_after_simulated_authority_not_crypto(self):
  a,p=self.mocks();real=m.run_worker;children=[]
  def run(argv,**kw):
   self.assertEqual(argv[:5],[sys.executable,'-I','-S','-B','-c']);self.assertEqual(argv[5],m.PROBE_EXEC)
   self.assertTrue(0<kw['timeout']<=10);self.assertEqual(kw['output_limit'],16384);children.append(argv[-1]);return real(argv,**kw)
  with a as auth,p,mock.patch.object(m,'run_worker',side_effect=run):result=self.verify()
  self.assertEqual(len(children),5);self.assertEqual([c['state'] for c in result['cases']],['FINDING','NO_FINDING','REFUSED'])
  auth.assert_called_once();self.assertEqual(auth.call_args.args[5],'source-snapshot')
  self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600);self.assertEqual(json.loads(self.output.read_text()),result)
  stage=self.stage();self.assertEqual(stat.S_IMODE(stage.stat().st_mode),0o700)
  found={p.relative_to(stage/'ps-source').as_posix() for p in (stage/'ps-source').rglob('*') if p.is_file()};self.assertEqual(found,m.FILES)
  self.assertTrue((stage/'source.tar.gz').exists());self.assertFalse((stage/'ps-source/unselected-program.py').exists())
  self.assertFalse(result['independent_accuracy_evidence']);self.assertFalse(result['complete_fourteen_routes']);self.assertNotIn(str(self.dir),self.output.read_text())
 def test_no_injectable_verifier_or_execution_options(self):
  self.assertEqual(set(inspect.signature(m.verify_managed).parameters),{'artifact','packet','spdx','bundle','trusted_root','output','source_commit','root'})
  self.assertEqual(m.FILES-m.ps_package.FILES,{'NOTICE'});self.assertEqual(len(m.FILES),10)
  import builtins,types
  actual_environment=dict(os.environ)
  for supplied in ({'HOME':'/existing-owner-home','PRIVATE_CANARY':'withheld'},{'PRIVATE_CANARY':'withheld'}):
   launch=mock.Mock();fake_os=types.SimpleNamespace(environ=supplied,defpath=os.defpath,execve=launch)
   fake_sys=types.SimpleNamespace(argv=['probe','fixed-script.py'],executable=sys.executable)
   def fixed_import(name,*args,**kw):
    if name=='os':return fake_os
    if name=='sys':return fake_sys
    raise AssertionError('Unexpected fixed-probe import')
   exec(compile(m.PROBE_EXEC,'<fixed-probe>','exec'),{'__builtins__':dict(vars(builtins),__import__=fixed_import)})
   launched=launch.call_args.args;self.assertEqual(launched[1],[sys.executable,'-I','-S','-B','fixed-script.py','--worker'])
   self.assertEqual(launched[2].get('HOME'),supplied.get('HOME'));self.assertEqual('HOME' in launched[2],'HOME' in supplied)
   self.assertNotIn('PRIVATE_CANARY',launched[2]);self.assertEqual(launched[2]['PATH'],os.defpath)
  self.assertEqual(dict(os.environ),actual_environment)
 def test_authority_flags_route_commit_digest_all_fail_closed(self):
  for field,value in [('state','VERIFIED'),('route','ps-source'),('source_commit','b'*40),('artifact_sha256','b'*64),('release_authorized',1),('policy_admitted',False),('attestation_verified',False)]:
   with self.subTest(field=field):
    def bad(record,*args):return self.auth(record,*args)|{field:value}
    with mock.patch.object(m.artifacts,'authorize_release',side_effect=bad),mock.patch.object(m,'_materialize') as build:
     with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
     build.assert_not_called()
    self.assertFalse(self.output.exists())
 def test_current_expected_source_bytes_required_not_packet_rebinding(self):
  changed=dict(self.files);changed['scripts/check-ps.py']+=b'\n# coherently changed source\n';self.replace_archive(archive(changed))
  a,p=self.mocks()
  with a,p,mock.patch.object(m,'_materialize') as build:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   build.assert_not_called()
 def test_missing_finite_member_refuses_even_simulated_authority(self):
  changed=dict(self.files);del changed['NOTICE'];self.replace_archive(archive(changed));a,p=self.mocks()
  with a,p,mock.patch.object(m,'_probes') as run:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   run.assert_not_called()
 def test_trailing_concatenated_truncated_compression_refused(self):
  for raw in [self.raw+b'X',self.raw+self.raw,self.raw[:-1]]:
   with self.subTest(kind=hashlib.sha256(raw).hexdigest()[:8]):
    self.replace_archive(raw);a,p=self.mocks()
    with a,p,mock.patch.object(m,'_materialize') as build:
     with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
     build.assert_not_called()
 def test_metadata_commit_and_member_caps_before_allocation(self):
  self.replace_archive(archive(self.files,'b'*40));a,p=self.mocks()
  with a,p,mock.patch.object(m,'_materialize') as build:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   build.assert_not_called()
  d={'profile':m.SOURCE_PROFILE,'source_commit':COMMIT,'kind':'development_source_snapshot','tag_release_validated':False,'installed_dependencies_included':False,'files':[{'path':'x','mode':0o644,'bytes':m.MAX_MEMBER+1,'sha256':'a'*64}]}
  with self.assertRaises(PrivateInputError):m._metadata(encoded(d),COMMIT)
  raw=gzip.compress(b'X'*(3*65536),mtime=0);path=self.dir/'buffer-source';path.write_bytes(raw);peaks=[]
  with path.open('rb') as stream:
   reader=m._Inflated(stream.fileno(),{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});decoder=reader.decoder
   class Tracked:
    def decompress(self,block,limit):
     result=decoder.decompress(block,limit);peaks.append(len(reader.buffer)+len(result));return result
    def __getattr__(self,name):return getattr(decoder,name)
   reader.decoder=Tracked();self.assertEqual(reader.take(512),b'X'*512)
   self.assertEqual(reader.take(65536),b'X'*65536);self.assertEqual(reader.take(65536),b'X'*65536)
  self.assertTrue(peaks);self.assertLessEqual(max(peaks),65536)
 def test_archive_larger_than_read_limit_is_streamed_before_denial(self):
  with self.inputs['artifact'].open('wb') as f:f.truncate(16_000_001)
  real_read=Capture.read;real_artifact=Capture.artifact;calls=[]
  def read(c,path,*args,**kw):self.assertNotEqual(Path(path),self.inputs['artifact']);return real_read(c,path,*args,**kw)
  def art(c,path,*args,**kw):calls.append((Path(path),kw.get('copy_to')));return real_artifact(c,path,*args,**kw)
  with mock.patch.object(Capture,'read',read),mock.patch.object(Capture,'artifact',art),mock.patch.object(m.artifacts,'authorize_release') as auth:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   auth.assert_not_called()
  self.assertEqual(calls[0][0],self.inputs['artifact']);self.assertIsNotNone(calls[0][1]);self.assertEqual((self.stage()/'source.tar.gz').stat().st_size,16_000_001)
 def test_existing_output_and_dangling_link_refuse_before_auth(self):
  for link in (False,True):
   if link:self.output.symlink_to(self.dir/'absent')
   else:self.output.write_bytes(b'KEEP')
   with mock.patch.object(m.artifacts,'authorize_release') as auth:
    with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
    auth.assert_not_called()
   if link:self.assertTrue(self.output.is_symlink())
   else:self.assertEqual(self.output.read_bytes(),b'KEEP')
   self.output.unlink()
  self.assertEqual(list(self.dir.glob('.source-managed-*')),[])
 def test_public_input_symlink_and_nonprivate_parent_refuse(self):
  original=self.inputs['bundle'];link=self.dir/'bundle-link';link.symlink_to(original);self.inputs['bundle']=link
  with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  self.inputs['bundle']=original;self.dir.chmod(0o755)
  try:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  finally:self.dir.chmod(0o700)
 def test_late_git_marker_prevents_summary_no_recursive_cleanup(self):
  a,p=self.mocks()
  def late(*args):
   (self.dir/'.git').write_bytes(b'');return [{'id':'inert','status':'PASS'}]
  with a,p,mock.patch.object(m,'_probes',side_effect=late):
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  self.assertFalse(self.output.exists());self.assertTrue((self.stage()/'ps-source').exists())
 def test_stage_successor_after_authority_refuses_without_touching_outside(self):
  outside=self.dir/'outside';outside.mkdir();(outside/'KEEP').write_bytes(b'KEEP')
  def swap(record,*args):
   stage=self.stage();stage.rename(self.dir/'original-stage');stage.symlink_to(outside,target_is_directory=True);return self.auth(record,*args)
  with mock.patch.object(m.artifacts,'authorize_release',side_effect=swap),mock.patch.object(m,'_materialize') as build:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   build.assert_not_called()
  self.assertEqual((outside/'KEEP').read_bytes(),b'KEEP');self.assertTrue((self.dir/'original-stage/source.tar.gz').exists())
 def test_late_source_change_and_policy_failure_prevent_publication(self):
  a,p=self.mocks()
  def mutate(*args):
   (self.stage()/'ps-source/scripts/check-ps.py').write_bytes(b'changed');return []
  with a,p,mock.patch.object(m,'_probes',side_effect=mutate):
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  self.assertFalse(self.output.exists())
 def test_final_packet_policy_failure_retains_stage(self):
  a,_=self.mocks()
  with a,mock.patch.object(m.artifacts,'verify_packet',side_effect=PrivateInputError('refused')),mock.patch.object(m,'_probes',return_value=[]):
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  self.assertFalse(self.output.exists());self.assertTrue(self.stage().exists())
 def test_postpublication_close_error_is_explicit_uncertainty(self):
  a,p=self.mocks();close=Capture.close
  def fail(c):close(c);raise OSError('PRIVATE_CLOSE_CANARY')
  with a,p,mock.patch.object(m,'_probes',return_value=[]),mock.patch.object(Capture,'close',fail):
   with self.assertRaises(m.ManagedSourceUncertain) as error:self.verify()
  self.assertTrue(error.exception.output_may_exist);self.assertTrue(self.output.exists());self.assertNotIn('CANARY',str(error.exception))
 def test_probe_timeout_never_publishes_or_falls_back(self):
  a,p=self.mocks()
  with a,p,mock.patch.object(m,'run_worker',side_effect=subprocess.TimeoutExpired(['fixed'],10)) as run:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   self.assertEqual(run.call_count,1)
  self.assertFalse(self.output.exists())
 def test_invalid_probe_stdout_or_forged_full_record_refused(self):
  a,p=self.mocks();real=m.run_worker
  def forged(argv,**kw):
   result=real(argv,**kw)
   if '.source-managed-' in argv[-1] and kw['input']!=b'\xff':
    d=json.loads(result.stdout);d['redaction_performed']=0;return subprocess.CompletedProcess(argv,0,encoded(d),b'')
   return result
  with a,p,mock.patch.object(m,'run_worker',side_effect=forged):
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
  self.assertFalse(self.output.exists())
 def test_write_fault_releases_every_registered_descriptor_once(self):
  held=[]
  with self.assertRaises(OSError):
   with Capture() as c:
    fd=c.directory(self.dir)
    with mock.patch.object(m.os,'write',side_effect=OSError('fixed write fault')):
     try:m._write(c,fd,'failed-private-file',b'data')
     finally:held=list(c.fds)
  self.assertTrue(held)
  for fd in held:
   with self.assertRaises(OSError):os.fstat(fd)
  self.assertTrue((self.dir/'failed-private-file').exists())
 def test_disk_shortage_refuses_before_stage_capture_or_auth(self):
  self.assertEqual(m.MIN_FREE,2*1024**3+256*1024**2)
  with mock.patch.object(m.shutil,'disk_usage',return_value=type('Usage',(),{'free':m.MIN_FREE-1})()) as disk,mock.patch.object(m.artifacts,'authorize_release') as auth,mock.patch.object(m,'_materialize') as materialize,mock.patch.object(m,'run_worker') as run,mock.patch.object(Capture,'read') as read:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   disk.assert_called_once_with(self.dir);auth.assert_not_called();materialize.assert_not_called();run.assert_not_called();read.assert_not_called()
  self.assertEqual(list(self.dir.glob('.source-managed-*')),[]);self.assertFalse(self.output.exists())
  with mock.patch.object(m.shutil,'disk_usage',return_value=type('Usage',(),{'free':m.MIN_FREE})()),mock.patch.object(m.artifacts,'authorize_release',side_effect=PrivateInputError('fixed refusal')) as auth:
   with self.assertRaises(m.ManagedSourceUnavailable):self.verify()
   auth.assert_called_once()
  self.assertTrue(self.stage().exists());self.assertFalse(self.output.exists())
 def test_actual_cli_help_fixed_refusal_and_no_echo(self):
  script=ROOT/'scripts/verify-managed-source.py'
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script),'--help'],capture_output=True,timeout=10)
  self.assertEqual(result.returncode,0);self.assertIn(b'--source-commit',result.stdout)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(script),'--PRIVATE_ARGUMENT_CANARY'],capture_output=True,timeout=10)
  self.assertEqual(result.returncode,2);self.assertNotIn(b'PRIVATE_ARGUMENT_CANARY',result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
