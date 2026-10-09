"""Build a fail-closed, stdlib-only projection of the unchanged PS method."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = set('PRODUCTION_TAGS CALIBRATION_ID PIPED_INSTALLER EXECUTOR INTERPRETER COMMAND FETCH PREFIX COMMAND_SUBSTITUTION PROCESS_SUBSTITUTION BACKTICK_SUBSTITUTION OBFUSCATED WARNING'.split())
FUNCTIONS = set('fetches_stdout display_quote substitution_mentioned pipe_mentioned shell_evaluation_layer mentioned signals'.split())


def project(raw):
    tree = ast.parse(raw)
    selected = []
    assignments, functions = set(), set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name not in {'hashlib', 're', 'shlex'} or item.asname:
                    raise ValueError('New evaluator import requires projection review')
                if item.name in {'re', 'shlex'}:
                    selected.append(ast.Import(names=[item]))
        elif isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & CONSTANTS:
                if not names <= CONSTANTS:
                    raise ValueError('Unrecognized mixed method assignment')
                assignments |= names
                selected.append(node)
            elif names not in ({'app'}, {'MODELS'}):
                raise ValueError('New evaluator state requires device projection review')
        elif isinstance(node, ast.FunctionDef):
            if node.name in FUNCTIONS:
                functions.add(node.name)
                node.decorator_list = []
                selected.append(node)
            elif node.name != 'healthz':
                raise ValueError('New evaluator function requires device projection review')
        elif isinstance(node, ast.ImportFrom):
            if node.module not in {'pathlib','fastapi','pydantic','starlette.middleware.body_limit'}:
                raise ValueError('New evaluator module requires projection review')
        elif isinstance(node, ast.ClassDef):
            if node.name != 'Doc':
                raise ValueError('New evaluator class requires projection review')
        elif not isinstance(node, ast.Expr):
            raise ValueError('Unrecognized evaluator structure')
    if assignments != CONSTANTS or functions != FUNCTIONS:
        raise ValueError('Required method structure changed')
    method_hash = hashlib.sha256(raw).hexdigest()
    models = next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MODELS' for t in n.targets))
    model = models.value.elts[0]
    metadata = {ast.literal_eval(k):v for k,v in zip(model.keys,model.values)}
    if set(metadata) != {'name','sha256','revision'} or len(models.value.elts) != 1:
        raise ValueError('New model identity structure requires projection review')
    identity = {key:ast.literal_eval(metadata[key]) for key in ('name','revision')}
    identity['sha256'] = method_hash
    header = 'import hashlib, json, unicodedata\nfrom types import SimpleNamespace as Doc\n'
    header += 'MODELS = ' + repr([{'name':identity['name'], 'sha256':method_hash, 'revision':identity['revision']}]) + '\n'
    body = ast.unparse(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])))
    # Pasted input is a function argument, never Python source. No command runs.
    entry = '''
def check_device(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError('Require 1–20000 text characters')
    text = unicodedata.normalize('NFC', text)
    result = signals(Doc(text=text))
    return json.dumps({
        'format': 'ai-trust-id-device-preview/v1',
        'state': 'FINDING' if result['candidates'] else 'NO_FINDING',
        'subject': {'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'codepoint_count': len(text), 'normalization': 'NFC'},
        **result, 'redaction_performed': False,
        'independently_validated': False, 'training_label': None,
        'label_status': 'unreviewed_prediction', 'text_included': False
    })
'''
    return (header + body + '\n' + entry).encode(), method_hash


def main():
    data, method_hash = project((ROOT/'services/evaluator/app.py').read_bytes())
    bundle_hash = hashlib.sha256(data).hexdigest()
    path = ROOT/'site/public/device'
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob('method-*.py'):
        old.unlink()
    name = 'method-' + bundle_hash + '.py'
    (path/name).write_bytes(data)
    manifest = {'method_sha256':method_hash, 'bundle_sha256':bundle_hash,
                'path':'/device/'+name, 'runtime':'314.0.7', 'max_codepoints':20000}
    (ROOT/'site/src/device-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
