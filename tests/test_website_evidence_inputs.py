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
