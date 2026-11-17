"""Actual PostgreSQL adapter, restricted to an existing disposable synthetic cluster."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
from scripts.worker_process import run_worker
from tools import community_core as core

ROOT = Path(__file__).resolve().parents[1]
BIN = Path('/usr/lib/postgresql/18/bin')
MAX_STATE = 262144
ROLES = ('ait_community_runtime', 'ait_community_public')


def encode_state(state):
    # Measure compact UTF-8, so Unicode escapes do not impose a second, larger
    # byte budget than PostgreSQL's own JSONB text measurement.
    return json.dumps(state, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


class Postgres:
    def __init__(self, directory):
        core.require(sys.platform == 'linux' and os.geteuid() != 0)
        spec = importlib.util.spec_from_file_location('community_sandbox_guard', ROOT/'scripts/verify-metadata-store.py')
        guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
        self.directory = guard.sandbox(directory)
        core.require((BIN/'psql').is_file())
        self.argv = ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin', 'LANG=C.UTF-8',
                     'PGOPTIONS=-c statement_timeout=3000 -c lock_timeout=1000 -c standard_conforming_strings=on',
                     str(BIN/'psql'), '-XqAtw', '-v', 'ON_ERROR_STOP=1', '-h', str(self.directory/'socket'),
                     '-p', '55443', '-d', 'postgres']
        observed = json.loads(self.sql("SELECT json_build_object('data',current_setting('data_directory'),"
            "'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),"
            "'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),'tcp',inet_server_addr());"))
        core.require(observed == {'data': str(self.directory/'data'), 'socket': str(self.directory/'socket'),
            'cluster': 'aitrust-metadata-synthetic', 'listen': '', 'version': observed['version'], 'tcp': None}
            and 180000 <= int(observed['version']) < 190000)

    def sql(self, query, role=None):
        core.require(role is None or role in ROLES)
        prefix = ('SET ROLE ' + role + ';\n') if role else ''
        result = run_worker(self.argv, input=(prefix + query).encode(), timeout=6, output_limit=524288)
        core.require(result.returncode == 0)
        return result.stdout.decode('utf-8', 'strict').strip()

    def install(self, *, synthetic_only=False):
        core.require(synthetic_only is True)
        # A fresh synthetic schema only. Existing namespaces/roles refuse atomically.
        schema = (ROOT/'deploy/community/synthetic-development.sql').read_text()
        raw = base64.b64encode(encode_state(core.initial())).decode('ascii')
        insertion = "INSERT INTO community_dev.document VALUES(1,convert_from(decode('" + raw + "','base64'),'UTF8')::jsonb);\nCOMMIT;\n"
        core.require(schema.count('\nCOMMIT;\n') == 1)
        self.sql(schema.replace('\nCOMMIT;\n', '\n' + insertion))
        return {'initialized': True, 'synthetic_only': True, 'public_service_enabled': False, 'research_collection_enabled': False}

    def read(self):
        raw = self.sql('SELECT payload::text FROM community_dev.document WHERE singleton=1;', 'ait_community_runtime').encode()
        core.require(0 < len(raw) <= MAX_STATE)
        return core.Community(core.parse(raw, MAX_STATE))

    def apply(self, actor, request, now):
        for _ in range(6):
            engine = self.read(); old = encode_state(engine.state)
            result = engine.apply(actor, request, now); new = encode_state(engine.state)
            if old == new: return result
            core.require(len(new) <= MAX_STATE)
            # Both values use the fixed base64 alphabet, never SQL interpolation of text.
            a, b = (base64.b64encode(raw).decode('ascii') for raw in (old, new))
            changed = self.sql("SELECT community_dev.compare_swap_synthetic('"+a+"','"+b+"');", 'ait_community_runtime')
            core.require(changed in ('t', 'f'))
            if changed == 't': return result
        raise core.Refused('Community workbench operation unavailable or refused.')

    def view(self, operation, **kwargs):
        core.require(operation in ('public', 'replay', 'private', 'audit'))
        if operation == 'public':
            core.require(set(kwargs) <= {'after', 'limit'})
            after, limit = kwargs.get('after', 0), kwargs.get('limit', 20)
            core.require(type(after) is int and 0 <= after <= 2**53-1 and type(limit) is int and 1 <= limit <= 20)
            value = core.parse(self.sql('SELECT community_public_dev.snapshot_synthetic('+str(after)+','+str(limit)+');', 'ait_community_public').encode(), MAX_STATE)
            core.render(value)
            core.require(set(value) == {'format', 'sequence', 'items', 'next_page', 'cache_control', 'training_consent'} and value['cache_control'] == 'no-store' and value['training_consent'] is False)
            return value
        return getattr(self.read(), operation)(**kwargs)
