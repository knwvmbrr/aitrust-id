"""Published reference inputs must invalidate stale website evidence."""
from datetime import datetime, timezone
import json
import re
from pathlib import Path

import pytest

from protocol.revalidation import COMMON, ROOT, assess, fingerprint


def test_actual_builder_copy_inputs_are_bound_except_append_only_changelog():
    builder=(ROOT/'site/scripts/prepare.mjs').read_text()
    copied=re.findall(r"\['([^']+)'\s*,\s*'[^']+'\]",builder)
    required={name for name in copied if (ROOT/name).is_file() and name!='CHANGELOG.md'}
    assert len(required)>40
    observed=fingerprint('website')['sources']
    assert required <= observed.keys()
    assert 'docs/master-scope.json' in observed
    assert 'docs/scope-progress.json' in observed
    assert 'docs/changelog-policy.md' in observed
    assert 'CHANGELOG.md' not in observed


@pytest.fixture
def small_root(tmp_path):
    manifest=json.loads((ROOT/'eval/revalidation.json').read_text())
    manifest['capabilities']['website']['patterns']=[
        'docs/**/*','SECURITY.md','runs/published-reference.json']
    for name in COMMON:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(manifest) if name=='eval/revalidation.json' else '# fixture\n')
    for name in ['docs/changelog-policy.md','docs/nested/policy.json',
                 'SECURITY.md','runs/published-reference.json']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('original\n')
    return tmp_path


def receipt(root):
    before=fingerprint('website',root)
    return {'schema_version':1,'kind':'engineering_revalidation','pass':True,
            'captured_at':datetime.now(timezone.utc).isoformat(),
            'source_unchanged_during_execution':True,'fingerprint':before,
            'checks':[{'command':command,'exit':0,'stdout_sha256':'0'*64,
                       'stderr_sha256':'0'*64} for command in before['commands']],
            'independent_accuracy_evidence':False,'release_approved':False}


@pytest.mark.parametrize('name',['docs/changelog-policy.md','docs/nested/policy.json',
                               'SECURITY.md','runs/published-reference.json'])
def test_changed_publication_input_refuses_the_previously_passing_receipt(small_root,name):
    old=receipt(small_root)
    assert assess(old,'website',small_root)['pass']
    (small_root/name).write_text('changed\n')
    assert not assess(old,'website',small_root)['pass']


def test_new_public_document_also_invalidates_receipt(small_root):
    old=receipt(small_root)
    assert assess(old,'website',small_root)['pass']
    (small_root/'docs/new-policy.md').write_text('new\n')
    assert not assess(old,'website',small_root)['pass']


def test_append_only_bookkeeping_has_no_receipt_cycle(small_root):
    old=receipt(small_root)
    (small_root/'CHANGELOG.md').write_text('new attributed event\n')
    (small_root/'runs/new-execution.json').write_text('{}\n')
    assert assess(old,'website',small_root)['pass']


def test_clean_checkout_and_generated_manifest_have_same_source_identity(small_root):
    p=small_root/'eval/revalidation.json';manifest=json.loads(p.read_text())
    manifest['capabilities']['website']['patterns'].append('site/src/**/*')
    p.write_text(json.dumps(manifest))
    source=small_root/'site/src/app.jsx';source.parent.mkdir(parents=True);source.write_text('source\n')
    before=fingerprint('website',small_root)
    generated=small_root/'site/src/device-manifest.json';generated.write_text('derived output\n')
    assert fingerprint('website',small_root)==before
    generated.unlink()
    assert fingerprint('website',small_root)==before
    source.write_text('changed source\n')
    assert fingerprint('website',small_root)!=before


def test_derived_manifest_exclusion_keeps_generator_inputs_bound():
    required={'scripts/build-device-detector.py','services/evaluator/app.py',
              'protocol/normalization.py','protocol/unicode15-data.json'}
    observed=fingerprint('website')['sources']
    assert required <= observed.keys()
    assert 'site/src/device-manifest.json' not in observed


def test_route_inventory_is_also_independent_of_the_derived_manifest(tmp_path):
    from test_release_policy import module
    routes=module('scripts/verify-route-boundaries.py')
    source=tmp_path/'site/src/app.jsx';source.parent.mkdir(parents=True);source.write_text('source\n')
    before=routes.inventory(tmp_path)
    generated=source.with_name('device-manifest.json');generated.write_text('derived\n')
    bundle=tmp_path/('site/public/device/method-'+'a'*64+'.py')
    bundle.parent.mkdir(parents=True);bundle.write_text('generated method\n')
    assert routes.inventory(tmp_path)==before
    generated.unlink()
    bundle.unlink()
    assert routes.inventory(tmp_path)==before


@pytest.mark.parametrize("capability",["protocol","website"])
def test_selected_review_recipe_inputs_are_bound_in_consumer_receipts(capability):
    from tools.review_execution import SOURCE_FILES
    assert set(SOURCE_FILES) <= fingerprint(capability)["sources"].keys()


@pytest.mark.parametrize("capability",["protocol","website"])
def test_synthetic_admission_consumers_bind_executable_and_database_contract(capability):
    required={'tools/research_admission.py','scripts/research-admission.py',
        'scripts/verify-research-admission.py','scripts/metadata-store-sandbox.py',
        'scripts/verify-metadata-store.py','scripts/verify-research-invitations.py',
        'deploy/research/metadata-development.sql','deploy/research/metadata-invitation-development.sql',
        'tests/test_research_admission.py','.github/workflows/metadata-storage.yml'}
    assert required <= fingerprint(capability)['sources'].keys()


@pytest.mark.parametrize('capability', ['protocol', 'website'])
def test_reference_revision_consumers_bind_source_and_privacy_contract(capability):
    required = {'tools/reference_revision.py', 'scripts/review-reference-revision.py',
        'scripts/prepare-reference-revision-demo.py', 'scripts/verify-reference-revision.py',
        'tests/test_reference_revision.py', 'tools/blind_review_io.py', 'protocol/corpus.py',
        'protocol/corpus_support.py', 'protocol/normalization.py', 'protocol/unicode15-data.json',
        'docs/reference-revisions.md', '.github/workflows/ci.yml'}
    assert required <= fingerprint(capability)['sources'].keys()
