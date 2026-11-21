"""Actual selected notice delivery, hostile source/files and publication failures."""
import copy
import hashlib
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tools import web_distribution as web

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def selected_root(tmp_path):
    root = tmp_path / 'source'; root.mkdir()
    manifest = json.loads((ROOT/'sbom/notices/manifest.json').read_bytes())
    names = set(web.SOURCES)
    for row in manifest['npm']:
        if row['lock'] == 'site/package-lock.json':
            names.update(n['notice'] for n in row['notices'])
    for name in names:
        dest = root/name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
    (root/'site/public').mkdir(parents=True)
    return root


def files(root):
    return {name:(root/web.DESTINATION/name).read_bytes() for name in web.OUTPUTS}


def build_fixture(root):
    prepared = root/web.DESTINATION
    shutil.copytree(prepared, root/'site/dist/web-licenses')
    (root/'site/dist/reference').mkdir()
    (root/'site/dist/reference/code-license.txt').write_bytes((root/'LICENSE').read_bytes())


def update_lock(root, mutate):
    path = root/'site/package-lock.json'; lock = json.loads(path.read_bytes()); mutate(lock)
    raw = json.dumps(lock).encode(); path.write_bytes(raw)
    p = root/'sbom/notices/manifest.json'; manifest = json.loads(p.read_bytes())
    manifest['sources']['site/package-lock.json'] = hashlib.sha256(raw).hexdigest()
    p.write_text(json.dumps(manifest))


def test_34_archive_notice_records_and_one_distinct_supplement_are_carried(selected_root):
    root = selected_root
    first = web.prepare(root); assert first['packages'] == 35 and not first['release_approved']
    assert first['archive_notice_packages'] == 34 and first['supplemental_project_notice_packages'] == 1
    assert first['exact_release_notice_gap_packages'] == ['react-remove-scroll-bar@2.3.8']
    before = files(root); assert web.prepare(root)['action'] == 'already_current'
    assert files(root) == before
    index = json.loads(before['packages.json']); bundle = before['THIRD-PARTY-NOTICES.txt']
    for row in index['packages']:
        for notice in row['notices']:
            start, end = notice['bundle_byte_span']
            actual = bundle[start:end]
            assert actual == (root/notice['notice']).read_bytes()
            assert hashlib.sha256(actual).hexdigest() == notice['sha256']
    assert b'NOT AN EXACT-RELEASE NOTICE MATCH' in bundle and b'correspondence remains UNVERIFIED' in bundle
    assert b'Copyright (c) Meta Platforms, Inc. and affiliates.' in bundle
    assert b'The above copyright notice and this permission notice shall be included in all' in bundle
    assert (root/'NOTICE').read_bytes() in bundle
    sbom = json.loads(before['web-runtime.spdx.json'])
    assert len(sbom['packages']) == 35
    assert all(p['licenseConcluded'] == 'NOASSERTION' and p['filesAnalyzed'] is False for p in sbom['packages'])
    build_fixture(root)
    assert web.check_built(root)['action'] == 'built_artifact_notice_bytes_verified'


@pytest.mark.parametrize('which', web.OUTPUTS + ('project-license',))
def test_actual_built_notice_or_attribution_loss_refuses(selected_root, which):
    root = selected_root; web.prepare(root); build_fixture(root)
    p = (root/'site/dist/reference/code-license.txt' if which == 'project-license'
         else root/'site/dist/web-licenses'/which)
    p.write_bytes(b'notice replaced')
    with pytest.raises((web.NoticeError, OSError)):
        web.check_built(root)


@pytest.mark.parametrize('fault', ('missing', 'changed', 'hardlink', 'symlink'))
def test_source_notice_fault_preserves_prior_prepared_output(selected_root, fault):
    root = selected_root; web.prepare(root); before = files(root)
    manifest = json.loads((root/'sbom/notices/manifest.json').read_bytes())
    react = next(r for r in manifest['npm'] if r['lock']=='site/package-lock.json' and r['package_path']=='node_modules/react')
    p = root/react['notices'][0]['notice']
    if fault == 'missing':p.unlink()
    elif fault == 'changed':p.write_bytes(b'different license')
    elif fault == 'hardlink':os.link(p, root/'extra-copy')
    else:
        p.rename(root/'other-notice');p.symlink_to(root/'other-notice')
    with pytest.raises((web.NoticeError, OSError, ValueError)):
        web.prepare(root)
    assert files(root) == before


@pytest.mark.parametrize('fault', ('unknown', 'version', 'production-type'))
def test_unreviewed_or_changed_production_lock_refuses(selected_root, fault):
    root = selected_root; web.prepare(root); before = files(root)
    def mutate(lock):
        if fault == 'unknown':lock['packages']['node_modules/unknown-package'] = {'version':'1.0.0','license':'MIT'}
        elif fault == 'version':lock['packages']['node_modules/react']['version'] = '99.0.0'
        else:lock['packages']['node_modules/react']['dev'] = 1
    update_lock(root, mutate)
    with pytest.raises((web.NoticeError, OSError, ValueError)):
        web.prepare(root)
    assert files(root) == before


@pytest.mark.parametrize('raw', (b'{"npm":[],"npm":[]}', b'{"bad":"\\ud800"}', b'[]', b'{"value":NaN}'))
def test_malformed_collected_metadata_refuses(selected_root, raw):
    root = selected_root; (root/'sbom/notices/manifest.json').write_bytes(raw)
    with pytest.raises((web.NoticeError, OSError, ValueError, UnicodeError)):
        web.expected(root)


def test_unknown_output_member_is_never_deleted(selected_root):
    root = selected_root; web.prepare(root); before = files(root)
    private = root/web.DESTINATION/'unrelated.txt'; private.write_bytes(b'unrelated owner file')
    with pytest.raises(web.NoticeError):web.prepare(root)
    assert files(root) == before and private.read_bytes() == b'unrelated owner file'


def test_failed_directory_publish_restores_all_previous_bytes(selected_root, monkeypatch):
    root = selected_root; web.prepare(root); before = files(root)
    (root/'NOTICE').write_bytes((root/'NOTICE').read_bytes()+b'\nUpdated project attribution.\n')
    rename = os.rename
    def fail_new(source, dest):
        if Path(source).name.startswith('new-') and Path(dest) == root/web.DESTINATION:
            raise OSError('private failure must not enter public report')
        return rename(source, dest)
    monkeypatch.setattr(os, 'rename', fail_new)
    with pytest.raises(OSError):web.prepare(root)
    assert files(root) == before


def test_source_mutation_after_staging_refuses_without_replacing_old(selected_root, monkeypatch):
    root = selected_root; web.prepare(root); before = files(root)
    (root/'NOTICE').write_bytes(b'new project attribution\n')
    original = web.expected; calls = 0
    def racing(selected):
        nonlocal calls
        calls += 1
        if calls == 2:(root/'NOTICE').write_bytes(b'another project attribution\n')
        return original(selected)
    monkeypatch.setattr(web, 'expected', racing)
    with pytest.raises(web.NoticeError):web.prepare(root)
    assert files(root) == before


def test_expansion_budget_refuses_before_tar_parser(monkeypatch, tmp_path):
    raw, cohort, stamp = web.selected(ROOT)
    row = copy.deepcopy(cohort[0])
    compressed = gzip.compress(b'inert synthetic expanded metadata')
    row['integrity'] = 'sha512-' + web.base64.b64encode(hashlib.sha512(compressed).digest()).decode()
    row['artifact_sha256'] = hashlib.sha256(compressed).hexdigest()
    (tmp_path/(web.digest(row['integrity'].encode())+'.tgz')).write_bytes(compressed)
    monkeypatch.setattr(web, 'selected', lambda root: (raw, [row], stamp))
    monkeypatch.setattr(web, 'MAX_EXPANDED', 1)
    monkeypatch.setattr(web.tarfile, 'open', lambda **kwargs: pytest.fail('tar allocated before expansion refusal'))
    with pytest.raises(web.NoticeError):web.replay_archives(tmp_path, ROOT)


def test_fixed_cli_diagnostics_never_echo_private_arguments():
    for args in (['--private-argument=/private/synthetic-secret'], ['prepare','--archive-dir','/private/synthetic-secret']):
        r = subprocess.run([sys.executable, '-B', 'scripts/web-distribution.py', *args], cwd=ROOT,
                           capture_output=True, timeout=10)
        assert r.returncode == 2 and not r.stderr and b'synthetic-secret' not in r.stdout
        assert json.loads(r.stdout)['reason'] == 'website_notice_check_refused'


def test_real_ps_route_stays_admitted_and_website_not_blindly_admitted():
    from tools.dependency_policy import evaluate
    assert evaluate('ps-source', ROOT)['release_allowed'] is True
    assert evaluate('web-checker', ROOT)['status'] == 'blocked_unknown'


def test_source_mutation_after_publish_rolls_back_prior_directory(selected_root, monkeypatch):
    root = selected_root; web.prepare(root); before = files(root)
    (root/'NOTICE').write_bytes(b'new project attribution\n')
    original = web.expected; calls = 0
    def racing(selected):
        nonlocal calls
        calls += 1
        if calls == 3:(root/'NOTICE').write_bytes(b'changed during publication\n')
        return original(selected)
    monkeypatch.setattr(web, 'expected', racing)
    with pytest.raises(web.NoticeError):web.prepare(root)
    assert files(root) == before


@pytest.mark.parametrize('fault', ('changed-text', 'claim-upgrade', 'unknown-fallback'))
def test_supplement_cannot_claim_exact_release_or_cover_unknown_packages(selected_root, fault):
    root = selected_root
    if fault == 'changed-text':
        (root/web.SOURCES[-1]).write_bytes(b'another upstream text')
    elif fault == 'claim-upgrade':
        p = root/web.SOURCES[-2]; meta = json.loads(p.read_bytes())
        meta['claims']['exact_release_license_correspondence_verified'] = True
        p.write_text(json.dumps(meta))
    else:
        p = root/'sbom/notices/manifest.json'; manifest = json.loads(p.read_bytes())
        row = next(r for r in manifest['npm'] if r['lock']=='site/package-lock.json' and r['package_path']=='node_modules/react')
        row['notices'] = [];p.write_text(json.dumps(manifest))
    with pytest.raises(web.NoticeError):web.expected(root)


@pytest.mark.parametrize('field,value', (('integrity',None), ('resolved',7)))
def test_matching_malformed_identity_fields_have_fixed_cli_refusal(selected_root, field, value):
    root = selected_root
    # Matching malformed values must not evade equality checks and reach a
    # string operation whose traceback would expose the selected source path.
    update_lock(root, lambda lock: lock['packages']['node_modules/react'].update({field:value}))
    p = root/'sbom/notices/manifest.json'; manifest = json.loads(p.read_bytes())
    row = next(r for r in manifest['npm'] if r['lock']=='site/package-lock.json' and r['package_path']=='node_modules/react')
    row[field] = value;p.write_text(json.dumps(manifest))
    (root/'tools/dependency_policy.py').write_bytes((ROOT/'tools/dependency_policy.py').read_bytes())
    result = subprocess.run([sys.executable, '-B', 'scripts/web-distribution.py', 'prepare'],
                            cwd=root, capture_output=True, timeout=10)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)['reason'] == 'website_notice_check_refused'


@pytest.mark.parametrize('root_entry', ([], None, {}, {'dependencies':[]}, 'missing'))
def test_root_lock_entry_and_dependencies_have_strict_api_and_cli_refusal(selected_root, root_entry):
    root = selected_root
    def mutate(lock):
        if root_entry == 'missing':lock['packages'].pop('')
        else:lock['packages'][''] = root_entry
    update_lock(root, mutate)
    with pytest.raises(web.NoticeError):web.expected(root)
    result = subprocess.run([sys.executable, '-B', 'scripts/web-distribution.py', 'prepare'],
                            cwd=root, capture_output=True, timeout=10)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)['reason'] == 'website_notice_check_refused'


def test_source_and_notice_budget_refuses_before_reading_notice_contents(monkeypatch):
    calls = []; original = web.read
    def observed(root, name, limit):
        calls.append((name, limit));return original(root, name, limit)
    monkeypatch.setattr(web, 'read', observed)
    monkeypatch.setattr(web, 'MAX_BUNDLE', 1000)
    with pytest.raises(ValueError):web.selected(ROOT)
    assert calls and all(limit <= 1000 for _, limit in calls)
    assert not any(name.startswith('sbom/notices/') and name.endswith('.txt') for name,_ in calls)


def test_duplicate_notice_occurrences_spend_the_combined_budget(monkeypatch):
    raw, cohort, _ = web.selected(ROOT)
    archive = [n for r in cohort for n in r['archive_notices']]
    unique = {n['sha256']:n['bytes'] for n in archive}
    source_bytes = sum(len(raw[name]) for name in web.SOURCES)
    headers = len(web.BUNDLE_PREFIX) + len(raw['NOTICE']) + 1
    for row in cohort:
        headers += len(web.package_header(row))
        if row['supplemental_project_notice']:headers += len(web.SUPPLEMENT_WARNING)
        for notice in row['notices']:
            headers += len(web.notice_header(notice, row['supplemental_project_notice'])) + 1
            if row['supplemental_project_notice']:headers += notice['bytes']
    # A dedup-only check would fit. Every retained occurrence plus its planned
    # bundle copy must instead consume capacity before reading the next copy.
    cap = source_bytes + headers + 2*sum(unique.values()) + 1
    assert cap < source_bytes + headers + 2*sum(n['bytes'] for n in archive)
    calls = []; original = web.read
    def observed(root, name, limit):
        if name.startswith('sbom/notices/') and name.endswith('.txt'):calls.append(name)
        return original(root, name, limit)
    monkeypatch.setattr(web, 'read', observed);monkeypatch.setattr(web, 'MAX_BUNDLE', cap)
    with pytest.raises(web.NoticeError):web.selected(ROOT)
    assert 0 < len(calls) < len(archive) and len(calls) > len(set(calls))


def test_append_guard_checks_before_extending_even_with_selection_injected(monkeypatch):
    selected = web.selected(ROOT)
    class Tracked(bytearray):
        largest = 0
        def extend(self, value):
            super().extend(value);Tracked.largest = max(Tracked.largest, len(self))
    monkeypatch.setattr(web, 'selected', lambda root:selected)
    monkeypatch.setattr(web, 'MAX_BUNDLE', 1000)
    monkeypatch.setattr(web, 'bytearray', Tracked, raising=False)
    with pytest.raises(web.NoticeError):web.expected(ROOT)
    assert Tracked.largest <= 1000
