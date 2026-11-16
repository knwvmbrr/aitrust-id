"""The real optional SDK controls must run after every inventoried input change."""
import ast
from fnmatch import fnmatchcase
from pathlib import Path
import pytest
import yaml
ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('event', ['push', 'pull_request'])
@pytest.mark.parametrize('verifier', ['scripts/verify-manifest-inspection.py', 'scripts/verify-manifest-declarations.py'])
def test_real_parser_job_tracks_every_fingerprinted_dependency(event, verifier):
    workflow = yaml.load((ROOT / '.github/workflows/manifest-inspection.yml').read_text(), Loader=yaml.BaseLoader)
    paths = workflow['on'][event]['paths']
    tree = ast.parse((ROOT / verifier).read_text())
    assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'paths' for t in n.targets)]
    inventory = ast.literal_eval(assignments[0].value)
    inventory += ['tests/fixtures/c2pa-inspection-2026/signed.png', '.github/workflows/manifest-inspection.yml', 'tests/test_manifest_workflow.py']
    if verifier.endswith('verify-manifest-declarations.py'):
        inventory += ['tests/fixtures/c2pa-declarations-2026/declared-creation.png']
    assert 'protocol/**' in paths
    assert all(any(fnmatchcase(name, pattern) for pattern in paths) for name in inventory)
