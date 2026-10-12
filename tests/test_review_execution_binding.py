import copy
import hashlib
import json
from pathlib import Path
import pytest
from test_release_policy import module
from tools.review_execution import SOURCE_FILES, Reader, canonical, execution_context

review = module('scripts/prepare-ps-review.py')


def completed(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path/'source.jsonl'
    source.write_text(json.dumps({'id':'one', 'text':'Invented ordinary answer',
                                 'category':'ordinary', 'source':'synthetic test only'})+'\n')
    source.chmod(0o600)
    packet = tmp_path/'packet'
    manifest = review.freeze(source, packet)
    for slot in (1, 2):
        f = packet/f'reviewer-{slot}.json'
        value = json.loads(f.read_text())
        value['items'][0].update(label='negative', reason='Invented test label')
        f.write_text(json.dumps(value))
    return packet, manifest


def test_actual_selected_context_binds_normalization_runtime_and_installed_code():
    value = execution_context(review.ROOT)
    assert set(value['sources']) == set(SOURCE_FILES)
    assert value['sources']['protocol/unicode15-data.json'] == hashlib.sha256((review.ROOT/'protocol/unicode15-data.json').read_bytes()).hexdigest()
    assert len(value['dependencies']) == 16
    assert all(x['code_files'] > 0 for x in value['dependencies'].values())
    assert len(value['runtime']['executable_sha256']) == 64
    assert not value['remote_attestation'] and not value['independence_verified']
    assert str(review.ROOT).encode() not in canonical(value)


def test_new_recipe_is_private_and_verified_without_predictions(tmp_path):
    packet, manifest = completed(tmp_path)
    assert manifest['format'].endswith('/v2')
    f = packet/'execution-context.json'
    assert f.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(f.read_bytes()).hexdigest() == manifest['execution_context_sha256']
    form=json.loads((packet/'reviewer-1.json').read_text())
    assert form['method_sha256']==manifest['execution_context_sha256']==manifest['method_sha256']
    result = review.compare(packet, 'json', True)
    assert result['execution_binding_verified'] and result['agreement_count'] == 1
    assert not result['predictions_run'] and not result['release_assessed']


@pytest.mark.parametrize('target', ['normalization_code','normalization_data','harness', 'helper', 'categories', 'gate_schema', 'gate_config',
                                   'python','stdlib','dependency_version','dependency_code'])
def test_execution_drift_refuses_labels(tmp_path, monkeypatch, target):
    packet, _ = completed(tmp_path)
    real = review.execution_context
    def changed(root):
        value = copy.deepcopy(real(root))
        sources = {'normalization_code':'protocol/normalization.py',
                   'normalization_data':'protocol/unicode15-data.json',
                   'harness':'eval/harness.py', 'helper':'tools/review_execution.py',
                   'categories':'protocol/categories.py', 'gate_schema':'eval/gates.schema.json',
                   'gate_config':'eval/gates.yaml'}
        if target in sources: value['sources'][sources[target]] = '0'*64
        elif target == 'python': value['runtime']['version'] = '99.0.0'
        elif target == 'stdlib': value['runtime']['standard_library']['shlex.py'] = '0'*64
        elif target == 'dependency_version': value['dependencies']['pydantic']['version'] = '99.0.0'
        else: value['dependencies']['pydantic']['code_sha256'] = '0'*64
        return value
    monkeypatch.setattr(review,'execution_context',changed)
    with pytest.raises(ValueError, match='dependency changed'): review.compare(packet,'json')


@pytest.mark.parametrize('kind', ['missing','changed','duplicate','symlink','public','oversized'])
def test_recipe_member_attacks_refused(tmp_path, kind):
    packet, _ = completed(tmp_path)
    f = packet/'execution-context.json'
    if kind == 'missing': f.unlink()
    elif kind == 'changed': f.write_text('{}')
    elif kind == 'duplicate': f.write_text('{"format":1,"format":2}')
    elif kind == 'symlink':
        f.unlink(); f.symlink_to(packet/'items.jsonl')
    elif kind == 'public': f.chmod(0o644)
    else: f.write_bytes(b' '*(review.MANIFEST_LIMIT+1))
    with pytest.raises((ValueError,OSError)): review.compare(packet,'json')


def test_legacy_labels_remain_readable_but_cannot_supply_binding(tmp_path):
    packet, manifest = completed(tmp_path)
    manifest['format'] = 'ai-trust-id-blind-ps-review/v1'
    del manifest['execution_context_sha256']
    manifest['method_sha256']=hashlib.sha256((review.ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
    for slot in (1,2):
        f=packet/f'reviewer-{slot}.json';value=json.loads(f.read_text());value['method_sha256']=manifest['method_sha256'];f.write_text(json.dumps(value))
    (packet/'manifest.json').write_text(json.dumps(manifest))
    (packet/'execution-context.json').unlink()
    result = review.compare(packet,'json')
    assert not result['execution_binding_verified'] and result['agreement_count']==1
    assert result['execution_scope']=='historical_labels_only'
    with pytest.raises(ValueError, match='Legacy packet'): review.compare(packet,'json',True)


def test_mid_freeze_drift_creates_no_packet(tmp_path,monkeypatch):
    tmp_path.chmod(0o700); source=tmp_path/'source.jsonl'
    source.write_text(json.dumps({'id':'one','text':'synthetic','category':'ordinary','source':'test'})+'\n');source.chmod(0o600)
    real=review.execution_context;calls=0
    def changed(root):
        nonlocal calls
        value=real(root);calls+=1
        if calls>1:value['sources']['protocol/normalization.py']='0'*64
        return value
    monkeypatch.setattr(review,'execution_context',changed)
    with pytest.raises(ValueError,match='changed during freeze'):review.freeze(source,tmp_path/'packet')
    assert not (tmp_path/'packet').exists()


def test_mid_comparison_drift_is_unavailable(tmp_path,monkeypatch):
    packet,_=completed(tmp_path);real=review.execution_context;calls=0
    def changed(root):
        nonlocal calls
        value=real(root);calls+=1
        if calls>1:value['runtime']['version']='99.0.0'
        return value
    monkeypatch.setattr(review,'execution_context',changed)
    with pytest.raises(ValueError,match='changed during comparison'):review.compare(packet,'json')


@pytest.mark.parametrize('kind',['symlink','directory','oversized'])
def test_source_reader_refuses_nonordinary_or_unbounded_files(tmp_path,kind):
    p=tmp_path/'entry'
    if kind=='symlink':p.symlink_to(__file__)
    elif kind=='directory':p.mkdir()
    else:
        with p.open('wb') as f:f.truncate(32_000_001)
    with pytest.raises(ValueError):Reader().hashed(p)


def test_missing_dependency_uses_fixed_unavailable_error(monkeypatch):
    from tools import review_execution
    def missing(_):raise review_execution.metadata.PackageNotFoundError('PrivateHostMarker')
    monkeypatch.setattr(review_execution.metadata,'distribution',missing)
    with pytest.raises(ValueError,match='^Execution dependency is unavailable$'):
        execution_context(review.ROOT)


def test_genuine_pre_v2_packet_preserves_historical_labels(tmp_path):
    import shutil
    origin = review.ROOT/'tests/fixtures/legacy-review-v1'
    identity = json.loads((origin/'origin.json').read_text())
    tmp_path.chmod(0o700)
    packet = tmp_path/'historical'
    packet.mkdir(mode=0o700)
    for name, expected in identity['files'].items():
        raw=(origin/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==expected
        (packet/name).write_bytes(raw);(packet/name).chmod(0o600)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in packet.iterdir()}
    result=review.compare(packet,'json')
    assert result['disagreement_ids']==['historical-one']
    assert result['ambiguous_ids']==['historical-one']
    assert result['execution_scope']=='historical_labels_only'
    assert result['policy_matches_current'] is False
    assert not result['execution_binding_verified'] and not result['release_assessed']
    with pytest.raises(ValueError,match='Legacy packet'):review.compare(packet,'json',True)
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in packet.iterdir()}


@pytest.mark.parametrize('name',['protocol/categories.py','eval/gates.schema.json','eval/gates.yaml'])
def test_actual_direct_input_byte_drift_refuses(tmp_path,monkeypatch,name):
    import shutil
    root=tmp_path/'checkout';root.mkdir()
    for entry in (*SOURCE_FILES,'docs/independent-review.md'):
        target=root/entry;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(review.ROOT/entry,target)
    monkeypatch.setattr(review,'ROOT',root)
    packet,_=completed(tmp_path)
    target=root/name;target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='dependency changed'):review.compare(packet,'json',True)


@pytest.mark.parametrize('distribution,package',[('PyYAML','yaml'),('jsonschema','jsonschema'),
    ('attrs','attr'),('referencing','referencing'),('rpds-py','rpds'),
    ('jsonschema-specifications','jsonschema_specifications')])
def test_actual_harness_package_and_schema_data_drift(tmp_path,monkeypatch,distribution,package):
    from tools import review_execution
    real=review_execution.metadata.distribution
    package_root=tmp_path/'installed'/package;package_root.mkdir(parents=True)
    (package_root/'__init__.py').write_text('# Selected synthetic package identity\n')
    data=package_root/('schema.json' if distribution=='jsonschema-specifications' else 'module.py')
    data.write_text('{}\n' if data.suffix=='.json' else '# Original installed code\n')
    class Installed:
        version=real(distribution).version
        def locate_file(self,entry):
            assert entry==package or distribution=='attrs' and entry=='attrs'
            return package_root
    monkeypatch.setattr(review_execution.metadata,'distribution',lambda name:Installed() if name==distribution else real(name))
    packet,_=completed(tmp_path)
    data.write_bytes(data.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='dependency changed'):review.compare(packet,'json',True)
