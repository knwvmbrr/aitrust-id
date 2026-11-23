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
  self.assertEqual(len(paths),87)
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
 def wheel(self,path,extra=None,declared=None):
  meta=b'Metadata-Version: 2.4\nName: example\nVersion: 1.0\nLicense-File: LICENSE\n\n'
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('example-1.0.dist-info/METADATA',meta);z.writestr('example-1.0.dist-info/licenses/LICENSE',b'MIT synthetic licence')
   for name,data in extra or []:z.writestr(name,data)
  return {'name':'example','version':'1.0','metadata_sha256':q.sha(meta),'license_files_declared':declared or ['LICENSE']}
 def test_actual_zip_metadata_notice(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'x.whl';row=self.wheel(p);out=q.inspect_wheel(p,row);self.assertEqual(out['notices'][0]['sha256'],q.sha(b'MIT synthetic licence'));self.assertTrue(out['notices'][0]['publisher_declared'])
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

if __name__=='__main__':unittest.main()
