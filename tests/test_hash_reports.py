"""Real private inbox transactions and CLI failures; invented hash-only feedback."""
import copy,json,os,sqlite3,subprocess,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import hash_reports as h
class HashReports(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='aitrust-hash-test-');self.base=Path(self.tmp.name).resolve();self.base.chmod(0o700);self.root=self.base/'inbox'
        self.call('init','--root',self.root)
        self.row={'format':h.FORMAT,'subject_sha256':'a'*64,'method_sha256':'b'*64,'code':'PS','category':'false_alarm'}
    def tearDown(self):self.tmp.cleanup()
    def call(self,*args,raw=None,refuse=False):
        r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/hash-reports.py'),*map(str,args)],input=raw,capture_output=True,timeout=20)
        if refuse:self.assertNotEqual(r.returncode,0);return r
        self.assertEqual(r.returncode,0,r.stderr.decode());return json.loads(r.stdout)
    def ingest(self,row=None,consent=True,refuse=False):
        args=['ingest','--root',self.root]
        if consent:args+=['--consent-store-hashes']
        return self.call(*args,raw=h.encode(row or self.row),refuse=refuse)
    def personal(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json'],input=b'A personal answer.',capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['state'],'NO_FINDING')
    def test_preview_never_creates_or_changes_an_inbox(self):
        before=(self.root/'reports.sqlite').read_bytes();r=self.call('preview','--json',raw=h.encode(self.row));self.assertFalse(r['stored']);self.assertIsNone(r['training_label']);self.assertEqual(before,(self.root/'reports.sqlite').read_bytes())
    def test_intake_requires_explicit_storage_consent(self):
        self.ingest(consent=False,refuse=True);self.assertEqual(self.call('stats','--root',self.root)['active_records'],0)
    def test_actual_intake_status_and_export_are_unverified_metadata(self):
        r=self.ingest();self.assertFalse(r['verified']);self.assertIsNone(r['training_label']);self.assertFalse(r['duplicate'])
        output=self.base/'export.json';self.call('export','--root',self.root,'--output',output);d=json.loads(output.read_bytes());self.assertEqual(len(d['records']),1);self.assertEqual(d['records'][0]['feedback'],self.row);self.assertFalse(d['training_labels_included']);self.assertEqual(output.stat().st_mode&0o777,0o600)
    def test_duplicate_does_not_refresh_expiry(self):
        first=self.ingest()
        with mock.patch.object(h.time,'time',return_value=first['created_at']+3600):second=h.Inbox(self.root).ingest(self.row,consent=True)
        self.assertEqual(first['ticket'],second['ticket']);self.assertEqual(first['created_at'],second['created_at']);self.assertEqual(first['expires_at'],second['expires_at']);self.assertTrue(second['duplicate']);self.assertEqual(self.call('stats','--root',self.root)['active_records'],1)
    def test_distinct_method_code_and_category_remain_distinct_feedback(self):
        self.ingest()
        for fields in [{'method_sha256':'c'*64},{'code':'PII_REDACTED'},{'category':'unclear'}]:self.ingest({**self.row,**fields})
        self.assertEqual(self.call('stats','--root',self.root)['active_records'],4)
    def test_private_text_notes_credentials_positions_and_training_labels_refused(self):
        sentinel='HASH_PRIVATE_'+uuid.uuid4().hex
        for key in ['text','redacted_text','notes','email','token','positions','training_label','url']:
            r=self.ingest({**self.row,key:sentinel},refuse=True);self.assertNotIn(sentinel.encode(),r.stdout+r.stderr)
        self.assertEqual(self.call('stats','--root',self.root)['active_records'],0);self.assertNotIn(sentinel.encode(),(self.root/'reports.sqlite').read_bytes())
    def test_wrong_hash_code_category_and_types_refused(self):
        for key,value in [('subject_sha256','a'*63),('method_sha256','B'*64),('subject_sha256',False),('code','BT'),('code','FA'),('category','verified_true'),('category',[]),('format','assertion/v1')]:self.ingest({**self.row,key:value},refuse=True)
        self.assertEqual(self.call('stats','--root',self.root)['active_records'],0)
    def test_duplicate_keys_malformed_utf8_nan_and_overlong_payload_refused(self):
        for raw in [b'{"format":"a","format":"b"}',b'{"a":NaN}',b'\xff',b' '*4097]:self.call('ingest','--root',self.root,'--consent-store-hashes',raw=raw,refuse=True)
    def test_expiry_prunes_logically_and_clock_rollback_does_not_restore(self):
        row=self.ingest()
        with mock.patch.object(h.time,'time',return_value=row['expires_at']+1):stats=h.Inbox(self.root).stats();self.assertEqual(stats['expired_removed'],1);self.assertEqual(stats['active_records'],0)
        self.assertEqual(self.call('stats','--root',self.root)['active_records'],0)
    def test_withdrawal_is_local_logical_and_idempotent(self):
        row=self.ingest();r=self.call('withdraw','--root',self.root,'--ticket',row['ticket']);self.assertTrue(r['withdrawn']);self.assertFalse(r['external_copies_removed']);self.assertEqual(self.call('stats','--root',self.root)['active_records'],0)
        self.assertFalse(self.call('withdraw','--root',self.root,'--ticket',row['ticket'])['withdrawn'])
    def test_withdrawal_does_not_change_a_prior_export(self):
        row=self.ingest();out=self.base/'before.json';self.call('export','--root',self.root,'--output',out);before=out.read_bytes();self.call('withdraw','--root',self.root,'--ticket',row['ticket']);self.assertEqual(before,out.read_bytes());self.assertEqual(self.call('stats','--root',self.root)['active_records'],0)
    def test_sql_injection_and_unknown_ticket_never_delete_other_feedback(self):
        self.ingest();self.call('withdraw','--root',self.root,'--ticket',"' OR 1=1 --",refuse=True);self.assertFalse(self.call('withdraw','--root',self.root,'--ticket',str(uuid.uuid4()))['withdrawn']);self.assertEqual(self.call('stats','--root',self.root)['active_records'],1)
    def test_retention_is_bounded_and_initialization_never_overwrites(self):
        for days in ['0','31','-1']:
            root=self.base/('invalid-'+days);self.call('init','--root',root,'--days',days,refuse=True);self.assertFalse(root.exists())
        before=(self.root/'reports.sqlite').read_bytes();self.call('init','--root',self.root,refuse=True);self.assertEqual(before,(self.root/'reports.sqlite').read_bytes())
    def test_reserved_name_and_checkout_are_refused_before_creation(self):
        target=self.base/'.ssh';self.call('init','--root',target,refuse=True);self.assertFalse(target.exists())
        checkout=self.base/'checkout';checkout.mkdir(mode=0o700);(checkout/'.git').write_text('test only');self.call('init','--root',checkout/'inbox',refuse=True);self.assertFalse((checkout/'inbox').exists())
    def test_new_database_build_failure_does_not_publish_partial_inbox(self):
        target=self.base/'broken-init'
        with mock.patch.object(h.sqlite3,'connect',side_effect=OSError('Synthetic failure')):
            with self.assertRaises(Exception):h.Inbox.initialize(target)
        self.assertFalse(target.exists())
    def test_public_permissions_and_symlink_roots_are_refused(self):
        self.root.chmod(0o755);self.call('stats','--root',self.root,refuse=True);self.root.chmod(0o700)
        alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True);self.call('stats','--root',alias,refuse=True)
    def test_linked_database_and_hard_linked_lock_are_refused(self):
        db=self.root/'reports.sqlite';saved=self.base/'saved.sqlite';db.rename(saved);db.symlink_to(saved);self.call('stats','--root',self.root,refuse=True);db.unlink();saved.rename(db)
        os.link(self.root/'access.lock',self.base/'other-lock');self.call('stats','--root',self.root,refuse=True)
    def test_foreign_files_survive_refused_removal(self):
        other=self.root/'my-notes.txt';other.write_text('Preserve this');other.chmod(0o600);self.call('remove','--root',self.root,'--confirm-inbox-removal',refuse=True);self.assertEqual(other.read_text(),'Preserve this')
    def test_unknown_tables_and_triggers_are_refused(self):
        with sqlite3.connect(self.root/'reports.sqlite') as db:db.execute('CREATE TABLE extra(private TEXT)')
        self.call('stats','--root',self.root,refuse=True)
        with sqlite3.connect(self.root/'reports.sqlite') as db:
            db.execute('DROP TABLE extra');db.execute("CREATE TRIGGER sqliteX_hidden AFTER INSERT ON reports BEGIN UPDATE reports SET category='unclear' WHERE ticket=new.ticket; END")
        self.ingest(refuse=True)
        with sqlite3.connect(self.root/'reports.sqlite') as db:self.assertEqual(db.execute('SELECT count(*) FROM reports').fetchone()[0],0)
        self.personal()
    def test_reserved_prefix_lookalike_cannot_hide_an_extra_schema_object(self):
        with sqlite3.connect(self.root/'reports.sqlite') as db:db.execute('CREATE TABLE sqliteX_hidden(private TEXT)')
        self.call('stats','--root',self.root,refuse=True)
    def test_linked_crash_journal_is_refused_before_sqlite_opens(self):
        target=self.base/'foreign';target.write_bytes(b'keep private data');target.chmod(0o600)
        (self.root/'reports.sqlite-journal').symlink_to(target);self.call('stats','--root',self.root,refuse=True);self.assertEqual(target.read_bytes(),b'keep private data')
    def test_modified_schema_is_refused(self):
        with sqlite3.connect(self.root/'reports.sqlite') as db:db.execute('ALTER TABLE reports ADD COLUMN response_text TEXT')
        self.ingest(refuse=True)
    def test_actual_capacity_refuses_new_records_but_preserves_duplicates(self):
        now=int(time.time());identifiers=[str(uuid.uuid4()) for _ in range(10000)]
        with sqlite3.connect(self.root/'reports.sqlite') as db:
            db.executemany('INSERT INTO reports VALUES(?,?,?,?,?,?,?)',[(identifiers[i],f'{i:064x}','b'*64,'PS','false_alarm',now,now+30*86400) for i in range(10000)])
        self.ingest(refuse=True);duplicate=self.ingest({**self.row,'subject_sha256':f'{1:064x}'});self.assertTrue(duplicate['duplicate']);self.assertEqual(self.call('stats','--root',self.root)['active_records'],10000)
        self.call('withdraw','--root',self.root,'--ticket',identifiers[0]);self.ingest();self.assertEqual(self.call('stats','--root',self.root)['active_records'],10000)
    def test_actual_concurrent_duplicate_intake_creates_one_ticket(self):
        args=[sys.executable,'-B',str(ROOT/'scripts/hash-reports.py'),'ingest','--root',str(self.root),'--consent-store-hashes']
        children=[subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(3)];results=[]
        for p in children:p.stdin.write(h.encode(self.row));p.stdin.flush()
        for p in children:p.stdin.close();p.stdin=None
        for p in children:
            out,err=p.communicate(timeout=20);self.assertEqual(p.returncode,0,err.decode());results.append(json.loads(out))
        self.assertEqual(len({r['ticket'] for r in results}),1);self.assertEqual(self.call('stats','--root',self.root)['active_records'],1)
    def test_actual_process_crash_rolls_back_and_releases_lock(self):
        self.ingest();identifier=str(uuid.uuid4());program="from tools import hash_reports as h;import sys,os,time;inbox=h.Inbox(sys.argv[1]);\nwith inbox.transaction() as (db,days):\n now=int(time.time());db.execute('INSERT INTO reports VALUES(?,?,?,?,?,?,?)',(sys.argv[2],'c'*64,'b'*64,'PS','unclear',now,now+days*86400));os._exit(17)"
        r=subprocess.run([sys.executable,'-B','-c',program,str(self.root),identifier],cwd=ROOT,capture_output=True,timeout=10);self.assertEqual(r.returncode,17);self.assertEqual(self.call('stats','--root',self.root)['active_records'],1)
    def test_corrupt_database_is_unavailable_and_personal_checker_works(self):
        (self.root/'reports.sqlite').write_bytes(b'not sqlite');self.call('stats','--root',self.root,refuse=True);self.personal()
    def test_export_never_overwrites_existing_or_follows_links(self):
        self.ingest();out=self.base/'out.json';out.write_text('Keep this');out.chmod(0o600);self.call('export','--root',self.root,'--output',out,refuse=True);self.assertEqual(out.read_text(),'Keep this')
        alias=self.base/'alias.json';alias.symlink_to(out);self.call('export','--root',self.root,'--output',alias,refuse=True);self.assertEqual(out.read_text(),'Keep this')
    def test_removal_requires_confirmation_and_leaves_personal_route(self):
        self.call('remove','--root',self.root,refuse=True);self.assertTrue(self.root.exists());self.call('remove','--root',self.root,'--confirm-inbox-removal');self.assertFalse(self.root.exists());self.personal()
    def test_no_authority_directory_or_network_configuration_is_required(self):
        self.ingest();s=self.call('stats','--root',self.root);self.assertFalse(s['public_registry_enabled']);self.assertFalse(s['automatic_upload']);self.assertFalse(s['company_collection_enabled']);self.assertTrue(s['all_feedback_unverified'])
if __name__=='__main__':unittest.main()
