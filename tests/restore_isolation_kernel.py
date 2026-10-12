import importlib.util,json,os,subprocess,sys,uuid,shutil,hashlib
from pathlib import Path
source=Path(__file__).resolve().parents[1]/'deploy/backup/restore.py'
spec=importlib.util.spec_from_file_location('restore_guard',source); tool=importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
if os.geteuid()!=0 or len(sys.argv)!=2 or sys.argv[1] not in ('host','isolated'):
 raise SystemExit('Owned Linux kernel checks require root and an explicit host or isolated mode')
checks={}
def refuses(call):
 try: call()
 except ValueError: return True
 return False
if sys.argv[1]=='host':
 checks['host_namespace_refused']=refuses(tool.require_isolated_network)
 if not checks['host_namespace_refused']:raise SystemExit('Host control unavailable; refusing to invoke any restore command')
 result=subprocess.run([sys.executable,str(source),'--generation','20261012T000000Z-abcdef01','--backup-label','20261012-000000F','--target','aitrust_probe_'+'a'*32+'_before','--schema','recovery_'+'a'*32,'--expected-rows','2'],capture_output=True,text=True,timeout=15)
 checks['actual_cli_refused_before_generation']=result.returncode==1 and 'loopback-only' in result.stderr
else:
 namespace=tool.require_isolated_network(); tool.require_same_network(namespace)
 checks['fresh_loopback_namespace_passed']=True
 base=Path('/run')/('aitrust-restore-guard-check.'+uuid.uuid4().hex)
 base.mkdir(mode=0o700); protected=base/'protected'; protected.mkdir(mode=0o700)
 name='20261012T000000Z-abcdef01'; selected=protected/name; selected.mkdir(mode=0o700)
 try:
  checks['root_private_generation_passed']=tool.protected_generation(name,protected)==selected
  member=selected/'owned-probe';member.write_bytes(b'owned synthetic recovery guard fixture');member.chmod(0o600)
  checks['root_private_member_passed']=tool.protected_generation(name,protected)==selected
  linked_member=selected/'protected-hardlink';os.link(member,linked_member)
  checks['root_private_hardlink_passed']=tool.protected_generation(name,protected)==selected
  member.chmod(0o640);checks['shared_member_refused']=refuses(lambda:tool.protected_generation(name,protected));member.chmod(0o600)
  os.chown(member,65534,65534);checks['service_owned_member_refused']=refuses(lambda:tool.protected_generation(name,protected));os.chown(member,0,0)
  linked_member.unlink();linked_member.symlink_to('owned-probe');checks['linked_member_refused']=refuses(lambda:tool.protected_generation(name,protected));linked_member.unlink()
  fifo=selected/'owned-fifo';os.mkfifo(fifo,0o600);checks['special_member_refused']=refuses(lambda:tool.protected_generation(name,protected));fifo.unlink()
  selected.chmod(0o750); checks['shared_generation_refused']=refuses(lambda:tool.protected_generation(name,protected)); selected.chmod(0o700)
  os.chown(selected,65534,65534); checks['service_owned_generation_refused']=refuses(lambda:tool.protected_generation(name,protected)); os.chown(selected,0,0)
  protected.chmod(0o750); checks['shared_container_refused']=refuses(lambda:tool.protected_generation(name,protected)); protected.chmod(0o700)
  linked='20261012T000000Z-abcdef02'; (protected/linked).symlink_to(name); checks['linked_generation_refused']=refuses(lambda:tool.protected_generation(linked,protected))
  parent=base/'linked-parent'; parent.symlink_to(protected); checks['linked_ancestor_refused']=refuses(lambda:tool.protected_generation(name,parent))
  checks['changed_namespace_identity_refused']=refuses(lambda:tool.require_same_network((namespace[0],namespace[1]+1)))
  subprocess.run(['/usr/sbin/ip','link','add','guard0','type','veth','peer','name','guard1'],check=True,capture_output=True,timeout=10)
  checks['connected_namespace_refused']=refuses(tool.require_isolated_network)
 finally:
  shutil.rmtree(base)
  checks['owned_root_fixture_removed']=not base.exists()
report={'pass':all(checks.values()),'mode':sys.argv[1],'checks':checks,'restore_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_restore_executed':False,'production_configuration_changed':False}
print(json.dumps(report)); raise SystemExit(0 if report['pass'] else 1)
