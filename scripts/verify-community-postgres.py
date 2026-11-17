#!/usr/bin/env python3
"""Actual ephemeral PostgreSQL community controls; no HTTP or real participants."""
import base64
import concurrent.futures
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools import community_core as core
from tools.community_postgres import Postgres, BIN, MAX_STATE, encode_state
from tools.backup_retention import require_namespace

SOURCES = ('tools/community_core.py', 'tools/community_store.py', 'tools/community_postgres.py',
    'scripts/community-workbench.py', 'scripts/community-postgres-sandbox.py', 'scripts/verify-community-postgres.py',
    'deploy/community/synthetic-development.sql', 'tools/blind_review_io.py', 'scripts/worker_process.py',
    'scripts/verify-metadata-store.py', 'tools/backup_retention.py', 'deploy/backup/restore.py', 'protocol/reports.py',
    'tests/test_community_core.py', 'tests/test_community_store.py', 'tests/test_community_cli.py', 'tests/test_community_postgres.py',
    '.github/workflows/community-workbench.yml')


def inventory(): return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def verify(namespace):
    require_namespace(namespace); before = inventory(); os.umask(0o077)
    work = Path(tempfile.mkdtemp(prefix='aitrust-metadata-', dir='/tmp')); work.chmod(0o700)
    (work/'socket').mkdir(mode=0o700)
    control = [str(BIN/'pg_ctl'), '-D', str(work/'data')]
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
    started = False; stopped = True; cleaned = False; cases = []; stage = 'init'; failed = None
    capacity = None
    def run(args, input=None, timeout=20):
        require_namespace(namespace)
        r = subprocess.run(list(map(str,args)), input=input, capture_output=True, timeout=timeout, env=env)
        core.require(r.returncode == 0); return r.stdout
    def req(op, data, rid=None):
        return {'format': core.REQUEST, 'synthetic_only': True, 'request_id': rid or str(uuid.uuid4()), 'operation': op, 'data': data}
    def case(name): cases.append({'case': name, 'pass': True})
    def denied(fn):
        try: fn()
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError): return
        raise AssertionError('Expected fixed refusal')
    def cli(actor, op, data=None, rid=None):
        args = [sys.executable, ROOT/'scripts/community-workbench.py', op, '--sandbox-dir', work]
        raw = None
        if actor:
            args += ['--actor', actor]
            if op == 'apply': raw = core.encode(data)
        return json.loads(run(args, raw))
    try:
        core.require(all((BIN/name).is_file() for name in ('initdb','pg_ctl','psql')))
        run([BIN/'initdb','-D',work/'data','--auth-local=peer','--auth-host=reject','--no-locale','--encoding=UTF8'])
        with (work/'data/postgresql.conf').open('a') as f:
            f.write("\nlisten_addresses=''\nport=55443\nunix_socket_directories='"+str(work/'socket')+"'\ncluster_name='aitrust-metadata-synthetic'\nshared_buffers='16MB'\nmax_connections=12\nlog_statement='none'\nlog_min_error_statement='panic'\nlog_error_verbosity='terse'\n")
        started = True; stopped = False; stage = 'start'
        run(control+['-l',work/'server.log','-w','start'])
        stage = 'install'; pg = Postgres(work); pg.install(synthetic_only=True)
        denied(lambda: pg.install(synthetic_only=True)); case('actual_private_socket_cluster_and_single_install')
        role_rows = json.loads(pg.sql("SELECT json_agg(json_build_object('name',rolname,'login',rolcanlogin,'superuser',rolsuper,'bypass',rolbypassrls)) FROM pg_roles WHERE rolname LIKE 'ait_community_%';"))
        core.require(len(role_rows)==3 and all(not r['login'] and not r['superuser'] and not r['bypass'] for r in role_rows)); case('three_nonlogin_nonprivileged_development_roles')
        stage = 'roles'
        for role, query in [('ait_community_public','SELECT payload FROM community_dev.document;'),
                            ('ait_community_public',"SELECT community_dev.compare_swap_synthetic('','');"),
                            ('ait_community_runtime','DELETE FROM community_dev.document;'),
                            ('ait_community_runtime',"UPDATE community_dev.document SET payload='{}';")]:
            denied(lambda r=role,q=query: pg.sql(q,r))
        denied(lambda:pg.sql("UPDATE community_dev.document SET payload=jsonb_build_object('format','community-workbench/v1','synthetic_only',true,'revision',0);"))
        case('public_cannot_read_private_state_runtime_cannot_directly_mutate_missing_shape_refused')
        stage = 'two_user_review'
        a = cli('user-one','apply',req('submit',{'body':'REMOVED_COMMUNITY_CANARY','consent_public':True}))
        b = cli('user-two','apply',req('submit',{'body':'QUEUED_COMMUNITY_CANARY','consent_public':True}))
        core.require(pg.view('public')['items']==[])
        denied(lambda: cli('user-two','apply',req('approve',{'post_id':a['id'],'version':1})))
        a = cli('mod-one','apply',req('approve',{'post_id':a['id'],'version':1}))
        core.require(pg.view('public')==pg.read().public()); case('actual_cli_two_user_review_and_sql_public_projection_parity')
        stage = 'adversarial_replacement'
        def raw_state():
            return core.parse(pg.sql('SELECT payload::text FROM community_dev.document WHERE singleton=1;', 'ait_community_runtime').encode(),262144)
        def raw_cas(old,new):
            left,right=[base64.b64encode(core.encode(x)).decode() for x in (old,new)]
            return pg.sql("SELECT community_dev.compare_swap_synthetic('"+left+"','"+right+"');",'ait_community_runtime')
        saved=raw_state()
        for change in (lambda v:v.update(format='not-community'),lambda v:v.update(synthetic_only=False),
                       lambda v:v.update(revision=1.5),lambda v:v.update(clock=None),
                       lambda v:v.update(posts=[]),lambda v:v.update(extra='PRIVATE_COMMUNITY_CANARY')):
            invalid=copy.deepcopy(saved);invalid['revision']+=1;change(invalid)
            denied(lambda v=invalid:raw_cas(saved,v))
            core.require(raw_state()==saved)
        case('adversarial_runtime_replacement_wrong_format_types_revision_and_unknown_fields_refused')
        # The trusted runtime can submit synthetic state, not authenticate participants.
        # Public SQL must still mask queued/retracted bodies and nonallowlisted fields.
        corrupt=copy.deepcopy(saved);corrupt['revision']+=1
        selected=corrupt['posts'][b['id']];selected.update(was_public=True,public_reason='PRIVATE_COMMUNITY_CANARY',
            reply_to='PRIVATE_COMMUNITY_CANARY',replacement='PRIVATE_COMMUNITY_CANARY',updated_at='PRIVATE_COMMUNITY_CANARY',version='PRIVATE_COMMUNITY_CANARY')
        corrupt['reports'][str(uuid.uuid4())]={'body':'PRIVATE_COMMUNITY_CANARY'}
        core.require(raw_cas(saved,corrupt)=='t')
        projected=pg.sql('SELECT community_public_dev.snapshot_synthetic();','ait_community_public')
        core.require('QUEUED_COMMUNITY_CANARY' not in projected and 'PRIVATE_COMMUNITY_CANARY' not in projected)
        again=copy.deepcopy(corrupt);again['revision']+=1;again['posts'][b['id']].update(state='retracted',body='RETRACTED_PRIVATE_CANARY')
        core.require(raw_cas(corrupt,again)=='t')
        core.require('RETRACTED_PRIVATE_CANARY' not in pg.sql('SELECT community_public_dev.snapshot_synthetic();','ait_community_public'))
        final_corrupt=copy.deepcopy(again);final_corrupt['revision']+=1
        final_corrupt['posts'][b['id']].update(state='published',body={'private':'UNAPPROVED_PRIVATE_CANARY'},approved_by='user-one')
        core.require(raw_cas(again,final_corrupt)=='t')
        core.require('UNAPPROVED_PRIVATE_CANARY' not in pg.sql('SELECT community_public_dev.snapshot_synthetic();','ait_community_public'))
        restored=copy.deepcopy(saved);restored['revision']=final_corrupt['revision']+1
        core.require(raw_cas(final_corrupt,restored)=='t');core.validate(pg.read().state)
        case('corrupted_was_public_flags_and_private_fields_do_not_expose_queued_retracted_or_unapproved_bodies')
        stage = 'private_reports'
        marker_target=str(uuid.uuid4()); report=cli('user-two','apply',req('report',{'target_id':marker_target,'category':'security','consent_private_metadata':True}))
        denied(lambda: cli('user-two','apply',req('report',{'target_id':marker_target,'category':'security','consent_private_metadata':True,'body':'PRIVATE_COMMUNITY_CANARY'})))
        for value in (pg.view('public'),pg.view('replay')):
            raw=core.encode(value);core.require(not any(x.encode() in raw for x in (marker_target,report['id'],'QUEUED_COMMUNITY_CANARY','PRIVATE_COMMUNITY_CANARY')))
        core.require(pg.view('private',actor='user-one')['reports']=={})
        case('private_report_marker_and_queued_body_absent_from_public_views')
        stage = 'concurrency'
        shared=req('submit',{'body':'Concurrent invented example','consent_public':True})
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda _:Postgres(work).apply('user-one',shared,1000000000000),range(4)))
        core.require(all(v==values[0] for v in values) and len(pg.read().state['posts'])==3)
        bad=dict(shared);bad['data']={'body':'CONFLICT_PRIVATE_CANARY','consent_public':True}
        denied(lambda:pg.apply('user-one',bad,1000000000000));case('actual_concurrent_idempotency_and_conflicting_retry_refusal')
        # Use trusted monotonically advancing test time after the concurrency fence.
        now=1000000000060
        def apply(actor,operation,data): return pg.apply(actor,req(operation,data),now)
        stage = 'retraction_appeal'
        a=apply('mod-one','suspend',{'post_id':a['id'],'version':a['version'],'reason':'conduct'})
        core.require('REMOVED_COMMUNITY_CANARY' not in core.encode(pg.read().state).decode())
        core.require('REMOVED_COMMUNITY_CANARY' not in core.encode(pg.view('replay')).decode())
        appeal=apply('user-one','appeal',{'post_id':a['id'],'version':a['version']})
        denied(lambda:apply('mod-one','resolve_appeal',{'appeal_id':appeal['id'],'decision':'reconsider'}))
        apply('mod-two','resolve_appeal',{'appeal_id':appeal['id'],'decision':'reconsider'})
        core.require(pg.view('public')['items'][0]['body'] is None);case('actual_retraction_scrubbing_and_independent_appeal_no_republication')
        stage = 'correction'
        p=apply('user-one','submit',{'body':'OLD_CORRECTION_CANARY','consent_public':True});p=apply('mod-one','approve',{'post_id':p['id'],'version':1})
        corrected=apply('user-one','supersede',{'post_id':p['id'],'version':p['version'],'body':'Corrected invented explanation','consent_public':True})
        apply('mod-two','approve',{'post_id':corrected['id'],'version':1})
        raw=core.encode(pg.read().state);core.require(b'OLD_CORRECTION_CANARY' not in raw)
        core.require(pg.view('public')==pg.read().public());case('actual_reviewed_correction_and_safe_supersession')
        stage = 'stale_cas'
        first=pg.read();old=core.encode(first.state)
        first.apply('user-two',req('submit',{'body':'CAS one','consent_public':True}),now)
        second=pg.read();second.apply('user-two',req('submit',{'body':'CAS two','consent_public':True}),now)
        def cas(new):
            left,right=[base64.b64encode(x).decode() for x in (old,core.encode(new.state))]
            return pg.sql("SELECT community_dev.compare_swap_synthetic('"+left+"','"+right+"');",'ait_community_runtime')
        core.require(cas(first)=='t' and cas(second)=='f');case('stale_snapshot_cannot_overwrite_committed_state')
        stage = 'byte_capacity'
        denied(lambda: pg.view('public', after=-1)); denied(lambda: pg.view('public', limit=21))
        short = apply('user-one', 'submit', {'body': 'x', 'consent_public': True})
        short = apply('mod-one', 'approve', {'post_id': short['id'], 'version': short['version']})
        refused = False
        for _ in range(128):
            now += 60  # Test storage saturation independently of the actor throttle.
            addition = req('submit', {'body': '🌳' * 500, 'consent_public': True})
            try:
                pg.apply('user-two', addition, now)
            except core.Refused:
                refused = True
                break
        core.require(refused)
        def document_bytes():
            return int(pg.sql('SELECT octet_length(payload::text) FROM community_dev.document;', 'ait_community_runtime'))
        before_bytes = document_bytes()
        candidate = pg.read()
        candidate.apply('user-two', addition, now)  # The core's count/rate limits still allow this.
        candidate_raw = base64.b64encode(encode_state(candidate.state)).decode('ascii')
        attempted_bytes = int(pg.sql("SELECT octet_length(convert_from(decode('"+candidate_raw+"','base64'),'UTF8')::jsonb::text);", 'ait_community_runtime'))
        removable = sum(row['state'] in ('queued', 'published') for row in candidate.state['posts'].values())
        core.require(attempted_bytes <= MAX_STATE and attempted_bytes + 1024 * (removable + 1) > MAX_STATE)
        core.require(addition['request_id'] not in pg.read().state['posts'])
        apply('admin-one', 'pause', {'paused': True})
        paused_bytes = document_bytes()
        apply('mod-one', 'retract', {'post_id': short['id'], 'version': short['version'], 'reason': 'privacy'})
        removed_bytes = document_bytes()
        tombstone = next(row for row in pg.view('public')['items'] if row['id'] == short['id'])
        core.require(tombstone['state'] == 'retracted' and tombstone['body'] is None and removed_bytes > paused_bytes)
        denied(lambda: apply('user-two', 'submit', {'body': 'Unavailable', 'consent_public': True}))
        core.require(pg.view('public')['cache_control'] == 'no-store')
        capacity = {'byte_limit': MAX_STATE, 'document_bytes_at_refusal': before_bytes,
            'rejected_candidate_bytes': attempted_bytes, 'rejected_candidate_reserved_bytes': 1024 * (removable + 1),
            'document_bytes_after_pause': paused_bytes, 'document_bytes_after_retraction': removed_bytes,
            'post_count_at_refusal': len(candidate.state['posts']) - 1}
        case('actual_byte_reserve_refuses_ordinary_writes_but_keeps_pause_and_growing_retraction_available')
        stage = 'source_fence';core.require(inventory()==before)
    except Exception:
        failed=stage
    finally:
        if started:
            try:
                subprocess.run(control+['-m','fast','-w','stop'],capture_output=True,timeout=20,env=env)
                stopped=subprocess.run(control+['status'],capture_output=True,timeout=5,env=env).returncode==3
            except Exception: stopped=False
        if stopped:
            try: shutil.rmtree(work);cleaned=True
            except OSError: cleaned=False
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':failed is None and stopped and cleaned,
        'format':'synthetic-community-postgresql-evidence/v1','sources':before,'source_unchanged':inventory()==before,
        'controls':cases,'capacity':capacity,'failure_stage':failed,'postgresql_major':18,'actual_postgresql':True,
        'non_root':os.geteuid()!=0,'network_namespace_isolated':True,'socket_only_cluster':True,
        'cluster_shutdown_verified':stopped,'private_cluster_removed':cleaned,'synthetic_only':True,
        'public_service_enabled':False,'real_user_data_collected':False,'new_endpoints':0,
        'production_changed':False,'independent_accuracy_evidence':False,'full_requirements_closed':0}
