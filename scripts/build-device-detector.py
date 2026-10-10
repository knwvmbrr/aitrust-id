"""Build a fail-closed, stdlib-only projection of the exact selected PS method."""
import ast
import hashlib
import os
import tempfile
import io
import tokenize
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = set('PRODUCTION_TAGS CALIBRATION_ID FROZEN_WORD PIPED_TARGET PIPED_INSTALLER EXECUTOR INTERPRETER COMMAND FETCH PREFIX COMMAND_SUBSTITUTION PROCESS_SUBSTITUTION BACKTICK_SUBSTITUTION OBFUSCATED WARNING'.split())
FUNCTIONS = set('fetches_stdout display_quote substitution_mentioned pipe_mentioned shell_evaluation_layer mentioned build_context warning_before pipe_matches signals compile_pattern'.split())


# Normalize syntax differences only at AST-identified tuple targets. Rewriting
# arbitrary lines would also alter triple-quoted strings and detector patterns.
def canonicalize(text):
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def position(line, byte_column):
        prefix = lines[line - 1].encode('utf-8')[:byte_column].decode('utf-8')
        return offsets[line - 1] + len(prefix)
    edits = []
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)) else []
        for target in targets:
            if not isinstance(target, ast.Tuple):
                continue
            start = position(target.lineno, target.col_offset)
            end = position(target.end_lineno, target.end_col_offset)
            segment = text[start:end]
            tokens = [t for t in tokenize.generate_tokens(io.StringIO(segment).readline)
                      if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER)]
            if not tokens or tokens[0].string != '(' or tokens[-1].string != ')':
                continue
            depth = 0
            outer = True
            for index, token in enumerate(tokens):
                if token.type == tokenize.OP and token.string == '(':
                    depth += 1
                elif token.type == tokenize.OP and token.string == ')':
                    depth -= 1
                    if depth == 0 and index != len(tokens) - 1:
                        outer = False
                        break
            if outer:
                edits.append((start, end, segment[1:-1]))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def canonical_bundle(header, body, entry):
    raw_text = header + body + '\n' + entry
    text = canonicalize(raw_text)
    if ast.dump(ast.parse(raw_text)) != ast.dump(ast.parse(text)):
        raise ValueError('Tuple normalization changed bundle AST; refusing to emit')
    if canonicalize(text) != text:
        raise ValueError('Tuple normalization is not idempotent; refusing to emit')
    return text.encode()


def write_if_changed(target, data):
    """Publish a whole file or keep the previous one; no truncate-write window."""
    if target.is_symlink():
        raise ValueError('Build target must not be a symlink: ' + str(target))
    if target.exists() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.build-', delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


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
    header = 'import hashlib, json\nfrom types import SimpleNamespace as Doc\n'
    normalizer = (ROOT/'protocol/normalization.py').read_text()
    tables = (ROOT/'protocol/unicode15-data.json').read_text().strip()
    normalizer = normalizer.replace("from pathlib import Path\n", "").replace("json.loads(Path(__file__).with_name('unicode15-data.json').read_text())", 'json.loads(' + repr(tables) + ')')
    header += normalizer + '\n'
    header += 'MODELS = ' + repr([{'name':identity['name'], 'sha256':method_hash, 'revision':identity['revision']}]) + '\n'
    body = ast.unparse(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])))
    # Pasted input is a function argument, never Python source. No command runs.
    entry = '''
def check_device(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError('Require 1–20000 text characters')
    text = normalize_nfc(text)
    result = signals(Doc(text=text))
    return json.dumps({
        'format': 'ai-trust-id-device-preview/v1',
        'state': 'FINDING' if result['candidates'] else 'NO_FINDING',
        'subject': {'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'codepoint_count': len(text), 'normalization': NORMALIZATION_ID},
        **result, 'redaction_performed': False,
        'independently_validated': False, 'training_label': None,
        'label_status': 'unreviewed_prediction', 'text_included': False
    })
'''
    return canonical_bundle(header, body, entry), method_hash


def main():
    data, method_hash = project((ROOT/'services/evaluator/app.py').read_bytes())
    bundle_hash = hashlib.sha256(data).hexdigest()
    path = ROOT/'site/public/device'
    if path.is_symlink():
        raise ValueError('Public bundle directory must not be a symlink')
    path.mkdir(parents=True, exist_ok=True)
    name = 'method-' + bundle_hash + '.py'
    write_if_changed(path/name, data)
    # Do not publish an obsolete method alongside the manifest's current one.
    # A failed removal blocks the build; no new manifest is issued.
    for old in path.glob('method-*.py'):
        if old.name != name:
            old.unlink()
    manifest = {'method_sha256':method_hash, 'bundle_sha256':bundle_hash,
                'path':'/device/'+name, 'runtime':'314.0.7', 'max_codepoints':20000,
                'normalization_id':'NFC-Unicode-15.0.0/v1',
                'normalization_data_sha256':hashlib.sha256((ROOT/'protocol/unicode15-data.json').read_bytes()).hexdigest()}
    write_if_changed(ROOT/'site/src/device-manifest.json',
                     (json.dumps(manifest, indent=2)+'\n').encode())
    provenance = {**manifest, 'builder_python':sys.version.split()[0],
                  'tuple_normalization':'AST-target-only/v1'}
    write_if_changed(ROOT/'output/device-build.json',
                     (json.dumps(provenance, indent=2)+'\n').encode())
    print(json.dumps(provenance))
    return manifest


if __name__ == '__main__':
    main()
