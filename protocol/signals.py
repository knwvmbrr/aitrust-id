"""Versioned method lookup with explicit inactive and unvalidated boundaries."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def registry(root=ROOT):
    data=json.loads((root/'spec/signal-registry.json').read_text())
    if data.get('schema_version')!=1 or data.get('spec_version')!='0.1.0' or data.get('entries_are_not_release_acceptance') is not True:
        raise ValueError('Unsupported signal catalogue')
    ids=[s['id'] for s in data['signals']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'(?:sig\.[a-z_]+|presidio\.entity)\.v[1-9][0-9]*',i) for i in ids):
        raise ValueError('Missing version or duplicate signal')
    documented=set(re.findall(r'(?:sig\.[a-z_]+|presidio\.entity)\.v[1-9][0-9]*',(root/'spec/signals.md').read_text()))
    documented.update(('sig.remote_command_substitution.v1','sig.remote_process_substitution.v1'))
    if set(ids)!=documented:raise ValueError('Catalogue differs from preserved methods')
    source=(root/'services/evaluator/app.py').read_text()
    active=set(re.findall(r"'((?:sig\.[a-z_]+)\.v[0-9]+)'",source))
    if {s['id'] for s in data['signals'] if s['status']=='active_development'}!=active:
        raise ValueError('Runtime methods differ from active catalogue')
    for s in data['signals']:
        if s['status'] not in ('active_development','procedural','historical_development','proposed') or s['independent_validation'] is not False or s['accepted_conformance_registration'] is not False:
            raise ValueError('Unsupported validation or catalogue state')
        if not s['description'] or not s['feeds']:raise ValueError('Missing method definition')
        required=s['status'] in ('active_development','procedural')
        if bool(s['source_files'])!=required:raise ValueError('Inactive method source binding')
        for name in s['source_files']:
            if name.startswith('/') or '..' in Path(name).parts or not (root/name).is_file() or (root/name).is_symlink():
                raise ValueError('Invalid implementation source')
        if 'historical_source' in s:
            name=s['historical_source']
            if s['status']!='historical_development' or not re.fullmatch(r'eval/methods/context-v[0-9]+\.py',name):
                raise ValueError('Invalid archived method binding')
            file=root/name
            if file.is_symlink() or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=s['historical_source_sha256']:
                raise ValueError('Historical implementation changed')
        if 'reference_implementation' in s:
            reference=s['reference_implementation']
            if s['status']!='proposed' or reference.get('kind') not in ('offline_observation_only','literal_observation_only') or reference.get('tag_mapping_validated') is not False or not reference.get('source_files'):
                raise ValueError('Observation is not an accepted tag mapping')
            for name in [*reference['source_files'],reference['contract']]:
                if name.startswith('/') or '..' in Path(name).parts or (root/name).is_symlink() or not (root/name).is_file():raise ValueError('Missing observation implementation')
    return data

def lookup(signal_id,root=ROOT):
    data=registry(root)
    row=next((s for s in data['signals'] if s['id']==signal_id),None)
    if row is None:return {'status':'unsupported','reason':'unknown_signal_id'}
    reference=row.get('reference_implementation',{})
    return {**row,'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in row['source_files']},
            'reference_implementation_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in reference.get('source_files',[])},
            'signal_id_alone_reproduces_assertion':False,'independent_accuracy_evidence':False}
