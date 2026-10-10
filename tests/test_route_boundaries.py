"""Deliberately changed surfaces must reopen the reviewed personal boundaries."""
import importlib.util
import json
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('route_boundaries', ROOT / 'scripts/verify-route-boundaries.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def manifest():
    return json.loads((ROOT / 'eval/route-boundaries.json').read_text())


def test_actual_current_guard():
    result = guard.verify()
    assert result['pass'] and result['undeclared_intake_fields_refused'] == 11
    assert result['rules'] == list(guard.RULES)
    assert not result['release_approved'] and not result['network_executed']


@pytest.mark.parametrize('field,value', [('rules', []), ('wire_version', '0.2.0'),
                                       ('independent_release_approval', True)])
def test_changed_policy_refused(field, value):
    row = manifest()
    row[field] = value
    with pytest.raises(ValueError, match='Unsupported boundary'):
        guard.evaluate(row)


def test_changed_source_refused():
    row = manifest()
    row['sources']['services/gateway/app.py'] = '0' * 64
    with pytest.raises(ValueError, match='reviewed source'):
        guard.evaluate(row)


def test_unknown_policy_field_refused():
    row = manifest()
    row['authorized_collection'] = True
    with pytest.raises(ValueError, match='Unsupported boundary'):
        guard.evaluate(row)


@pytest.mark.parametrize('date', ['not-a-date', '2026-10-10T00:00:00', '2999-01-01T00:00:00+00:00'])
def test_undated_or_future_review_refused(date):
    row = manifest()
    row['reviewed_at'] = date
    with pytest.raises(ValueError, match='dated boundary review'):
        guard.evaluate(row)


def test_unreviewed_source_refused(monkeypatch):
    row = manifest()
    altered = {**row['sources'], 'services/gateway/collect.py': '0' * 64}
    monkeypatch.setattr(guard, 'inventory', lambda _: altered)
    with pytest.raises(ValueError, match='reviewed source'):
        guard.evaluate(row)


def test_upload_payment_and_promotion_endpoints_refused(monkeypatch):
    original = guard.routes
    for endpoint in ['/reports/upload', '/billing', '/promotion/publish']:
        def changed(root, relative):
            value = original(root, relative)
            return value + [['post', endpoint]] if 'gateway' in relative else value
        monkeypatch.setattr(guard, 'routes', changed)
        with pytest.raises(ValueError, match='endpoint surface'):
            guard.evaluate(manifest())


@pytest.mark.parametrize('field,value', [('permissions', ['storage', 'webRequest']),
                                       ('host_permissions', ['https://collection.invalid/*']),
                                       ('optional_host_permissions', ['<all_urls>'])])
def test_broader_extension_access_refused(field, value, monkeypatch):
    original = guard.read_json
    def altered(file):
        row = original(file)
        if file.name == 'manifest.json':
            row[field] = value
        return row
    monkeypatch.setattr(guard, 'read_json', altered)
    with pytest.raises(ValueError, match='Extension access'):
        guard.evaluate(manifest())


def test_failed_or_stale_execution_refused(monkeypatch):
    monkeypatch.setattr(guard, 'assess', lambda *args: {'pass': False})
    with pytest.raises(ValueError, match='stale browser execution'):
        guard.evaluate(manifest())


def test_missing_browser_evidence_refused():
    row = manifest()
    row['engineering_receipts'] = {}
    with pytest.raises(ValueError, match='Missing selected browser evidence'):
        guard.evaluate(row)


def test_unsafe_receipt_path_refused():
    row = manifest()
    row['engineering_receipts']['extension'] = '../private.json'
    with pytest.raises(ValueError, match='Unsafe receipt path'):
        guard.evaluate(row)


def test_unique_finite_manifest(tmp_path):
    file = tmp_path / 'bad.json'
    for text in ['{"x":1,"x":2}', '{"x":NaN}']:
        file.write_text(text)
        with pytest.raises(ValueError):
            guard.read_json(file)


def test_dynamic_endpoint_requires_review(tmp_path):
    file = tmp_path / 'app.py'
    file.write_text('@app.post(configured_path)\ndef collect(): pass\n')
    with pytest.raises(ValueError, match='Dynamic endpoint'):
        guard.routes(tmp_path, 'app.py')


def test_guard_wired_into_site_deploy():
    package = json.loads((ROOT / 'site/package.json').read_text())
    assert 'verify-route-boundaries.cjs' in package['scripts']['predeploy']


def test_declared_ci_prepares_assets_for_boundary_checks():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    steps = [row.get('run', '') for row in jobs['site']['steps']]
    build = steps.index('npm run build:site')
    check = steps.index('python -m pytest tests/test_route_boundaries.py -q')
    assert check > build
    assert any('--ignore=tests/test_route_boundaries.py' in row.get('run', '')
               for row in jobs['no-egress']['steps'])


def test_changed_device_execution_refused():
    row = manifest()['device_evidence']
    row['source_commit'] = '0' * 40
    with pytest.raises(ValueError, match='evidence unavailable'):
        guard.device_evidence(row)


def test_device_collection_failure_refused(monkeypatch):
    original = guard.read_json
    selected_receipt = ROOT / manifest()['device_evidence']['receipt']
    def altered(file):
        row = original(file)
        if file == selected_receipt:
            row['engines'][0]['no_text_in_requests_or_cache'] = False
        return row
    monkeypatch.setattr(guard, 'read_json', altered)
    with pytest.raises(ValueError, match='Device privacy execution failed'):
        guard.device_evidence(manifest()['device_evidence'])


def test_registry_deferral_is_reviewed_without_approving_future_registry():
    assert 'X-14' in guard.RULES
    assert guard.verify()['registry_0_1_deferred_enforced']


def test_optional_registry_cannot_become_default():
    row = yaml.safe_load((ROOT / 'deploy/docker-compose.yml').read_text())
    assert guard.compose_boundary(row) == ['anonymizer', 'evaluator', 'gateway']
    del row['services']['registry']['profiles']
    with pytest.raises(ValueError, match='collection container'):
        guard.compose_boundary(row)


@pytest.mark.parametrize('field,value', [('ports', ['0.0.0.0:8787:8000']),
                                       ('volumes', ['assertions:/data']),
                                       ('environment', {'COLLECTION_URL': 'https://collection.invalid'})])
def test_central_collection_or_exposure_refused(field, value):
    row = yaml.safe_load((ROOT / 'deploy/docker-compose.yml').read_text())
    row['services']['gateway'][field] = value
    with pytest.raises(ValueError, match='Collection, persistence'):
        guard.compose_boundary(row)


def test_missing_live_service_evidence_refused(monkeypatch):
    original = guard.read_json
    def altered(file):
        row = original(file)
        if file.relative_to(ROOT).as_posix()==manifest()['service_evidence']:
            row['services']['evaluator']['source_sha256'] = '0' * 64
        return row
    monkeypatch.setattr(guard, 'read_json', altered)
    with pytest.raises(ValueError, match='Service source'):
        guard.service_evidence(manifest()['service_evidence'])


def test_replay_proof_requires_current_executed_private_boundary(monkeypatch):
    relative=manifest()['replay_evidence']
    original=guard.read_json
    for field,value in [('actual_pipeline_and_cli_executed',False),('public_intake_connected',True),('private_markers_absent_from_logs',False),('temporary_input_directory_removed',False),('sources',{})]:
        def altered(file):
            row=original(file)
            if file.as_posix().endswith(relative):row[field]=value
            return row
        monkeypatch.setattr(guard,'read_json',altered)
        with pytest.raises(ValueError):guard.replay_evidence(relative)


def test_host_rendered_pixels_are_bound_by_generator_not_host_font(tmp_path):
    public = tmp_path / 'site/public'
    scripts = tmp_path / 'site/scripts'
    public.mkdir(parents=True)
    scripts.mkdir()
    generator = scripts / 'prepare.mjs'
    generator.write_text('versioned share template')
    image = public / 'share-card.png'
    image.write_bytes(b'mac render')
    first = guard.inventory(tmp_path)
    image.write_bytes(b'linux render')
    assert guard.inventory(tmp_path) == first
    generator.write_text('changed share template')
    assert guard.inventory(tmp_path) != first
    (public / 'unexpected.js').write_text('new script')
    assert 'site/public/unexpected.js' in guard.inventory(tmp_path)


def test_host_rendered_asset_cannot_hide_symlink(tmp_path):
    public = tmp_path / 'site/public'
    public.mkdir(parents=True)
    target = tmp_path / 'target'
    target.write_text('outside boundary')
    (public / 'share-card.png').symlink_to(target)
    with pytest.raises(ValueError, match='symlink'):
        guard.inventory(tmp_path)
