"""Current/next release exclusion; permits reserved subjects and external evidence inspection."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'version': 'image-provenance-boundary/1.0.0', 'scope_id': 'X-07',
    'current_release': '0.1.0', 'current_image_provenance_issuance': False,
    'next_release_image_provenance_issuance': False,
    'project_issues_replacement_c2pa_credentials': False,
    'external_c2pa_evidence_inspection_permitted': True,
    'nontext_subject_preparation_permitted': True, 'accepted_exception': None,
}
def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out: raise ValueError('Duplicate boundary field')
        out[key] = value
    return out

def inspect(policy):
    if not isinstance(policy, dict) or set(policy) != set(EXPECTED):
        raise ValueError('Unknown or missing boundary field')
    for key, value in EXPECTED.items():
        if type(policy[key]) is not type(value) or policy[key] != value:
            raise ValueError('Image provenance boundary changed: ' + key)
    return True

def verify(root=ROOT):
    policy = json.loads((root/'spec/image-provenance-boundary.json').read_text(), object_pairs_hook=unique)
    inspect(policy)
    tree = ast.parse((root/'services/gateway/app.py').read_text())
    allowlists = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION_TAGS' for t in node.targets):
            if not isinstance(node.value, ast.Call) or not isinstance(node.value.func, ast.Name) or node.value.func.id != 'frozenset' or len(node.value.args) != 1:
                raise ValueError('Review changed assertion allowlist structure')
            allowlists.append(ast.literal_eval(node.value.args[0]))
    if allowlists != [{'PS', 'PII_REDACTED'}]:
        raise ValueError('Review newly asserted tag against the image-provenance boundary')
    return {'pass': True, 'scope_id': 'X-07', 'current_release_image_issuance': False,
            'next_release_image_issuance': False, 'replacement_c2pa_credentials': False,
            'external_evidence_inspection_permitted': True, 'runtime_modality_proof': 'tests/test_consent_conformance.py',
            'future_exception_requires_recorded_product_decision': True}

if __name__ == '__main__':
    print(json.dumps(verify()))
