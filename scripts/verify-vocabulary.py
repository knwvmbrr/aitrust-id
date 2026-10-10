"""Ensure current consumer vocabularies agree without promoting proposed tags."""
import argparse,ast,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def constant(path,name):
    tree=ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            value=node.value
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id=='frozenset':value=value.args[0]
            return ast.literal_eval(value)
    raise ValueError('Missing consumer vocabulary')
def verify(root=ROOT):
    v=json.loads((root/'spec/vocabulary.json').read_text());schema=json.loads((root/'spec/assertion.schema.json').read_text())
    codes=v['codes'];proposals=v['proposed_codes']
    if len(codes)!=len(set(codes)) or set(codes)&set(proposals):raise ValueError('Invalid code classification')
    if set(schema['$defs']['code']['enum'])!=set(codes):raise ValueError('Schema vocabulary drift')
    if constant(root/'services/gateway/app.py','KNOWN_CODES')!=set(codes):raise ValueError('Gateway vocabulary drift')
    if constant(root/'services/gateway/app.py','PRODUCTION_TAGS')!=set(v['development_gateway_codes']):raise ValueError('Gateway capability drift')
    if constant(root/'services/evaluator/app.py','PRODUCTION_TAGS')!=set(v['development_evaluator_codes']):raise ValueError('Evaluator capability drift')
    if set(schema['properties']['subject']['properties']['modality']['enum'])!=set(v['modalities']):raise ValueError('Reserved modality drift')
    if v['independently_released_codes'] or v['gateway_modalities']!=['text'] or v['unknown_code_behavior']!='upstream_contract_failure' or v['disabled_known_code_behavior']!='abstention_null_floor':raise ValueError('Unaccepted release or failure behavior')
    taxonomy=(root/'spec/taxonomy.md').read_text()
    if any('| `'+code+'` |' not in taxonomy for code in codes):raise ValueError('Missing public definition')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'adopted_codes':len(codes),'reserved_modalities':len(v['modalities']),'proposed_codes':proposals,'release_codes':[],'independent_accuracy_evidence':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
