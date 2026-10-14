"""New check commands must bind every consumed contract/source asset."""
from pathlib import Path
from datetime import datetime,timezone
import json
import pytest
from protocol import revalidation as r
ROOT=Path(__file__).resolve().parents[1]
REQUIRED={'protocol':['docs/master-scope.json','docs/scope-progress.json','GOVERNANCE.md',
                       'deploy/research/metadata-pilot-policy.json','runs/2026-10-13-metadata-pilot-owner-decision.json','scripts/setup-local.py','tests/test_local_setup.py',
                       'runs/2026-10-13-clean-setup-owner-decision.json','runs/2026-10-13-one-command-linux-setup.json'],
          'extension':['LICENSE','scripts/build-firefox-extension.py','extension/src/firefox/permissions.js']}


def test_actual_new_component_inputs_are_bound():
    for cap,paths in REQUIRED.items():assert set(paths)<=r.fingerprint(cap)['sources'].keys()


def test_complete_local_stack_build_and_checker_inputs_are_bound():
    import importlib.util
    spec=importlib.util.spec_from_file_location('setup_inputs',ROOT/'scripts/verify-local-setup-evidence.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bound=r.fingerprint('protocol')['sources']
    assert set(module.build_inputs())<=set(bound)
    assert module.RECEIPT in bound


@pytest.mark.parametrize('cap,path',[(c,p) for c,paths in REQUIRED.items() for p in paths])
def test_each_input_change_requires_new_evidence(tmp_path,cap,path):
    for common in r.COMMON:
        f=tmp_path/common;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('# control')
    manifest={'schema_version':1,'kind':'engineering_revalidation','independent_accuracy_evidence':False,
        'capabilities':{c:{'patterns':[path],'commands':[['{python}','scripts/check-control.py']]} for c in r.CAPABILITIES}}
    (tmp_path/'eval/revalidation.json').write_text(json.dumps(manifest))
    f=tmp_path/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'original')
    fp=r.fingerprint(cap,tmp_path)
    receipt={'schema_version':1,'kind':'engineering_revalidation','pass':True,'source_unchanged_during_execution':True,
        'captured_at':datetime.now(timezone.utc).isoformat(),'fingerprint':fp,
        'checks':[{'command':cmd,'exit':0,'stdout_sha256':'0'*64,'stderr_sha256':'0'*64} for cmd in fp['commands']],
        'independent_accuracy_evidence':False,'release_approved':False}
    assert r.assess(receipt,cap,tmp_path)['pass']
    f.write_bytes(b'changed');assert not r.assess(receipt,cap,tmp_path)['pass']
