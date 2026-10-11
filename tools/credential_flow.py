"""Bounded Python static read-to-HTTP flow. Never executes inspected code."""
import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from protocol.corpus import CorpusError
from protocol.normalization import NORMALIZATION_ID, normalize_nfc

METHOD = 'python-credential-flow-observation/1.0.0'
SECRET_KEYS = {'OPENAI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'GITHUB_TOKEN', 'DATABASE_PASSWORD'}
MAX_CHARACTERS = 8000


@dataclass(frozen=True)
class Value:
    sources: tuple = ()
    literal: object = None


@dataclass(frozen=True)
class File:
    path: str
    constructor: str


@dataclass(frozen=True)
class Symbol:
    kind: str


def secret_path(path):
    if not isinstance(path, str) or not path.isascii() or '\x00' in path or '\\' in path:
        raise CorpusError('Unsupported static file path.')
    pieces = path.split('/')
    if '..' in pieces:
        raise CorpusError('Parent-relative credential paths are unsupported.')
    return pieces[-1] == '.env' or len(pieces) >= 2 and (
        pieces[-2] == '.ssh' and pieces[-1] in ('id_rsa', 'id_ed25519') or
        pieces[-2:] == ['.aws', 'credentials'])


def observe(original):
    if not isinstance(original, str) or not original.strip() or len(original) > MAX_CHARACTERS or '\x00' in original:
        raise CorpusError('Supply bounded Python source.')
    try:
        original.encode('utf-8', errors='strict')
        subject = normalize_nfc(original)
        if len(subject) > MAX_CHARACTERS:
            raise ValueError()
        tree = ast.parse(subject)
    except (UnicodeError, SyntaxError, RecursionError, ValueError):
        raise CorpusError('Invalid or unsupported Python source.') from None
    nodes = list(ast.walk(tree))
    if len(nodes) > 2000:
        raise CorpusError('Python syntax exceeds the node limit.')
    lines = subject.splitlines(keepends=True)
    prefixes = [0]
    for line in lines:
        prefixes.append(prefixes[-1] + len(line))
    def span(node):
        # CPython AST columns are UTF-8 bytes, not Unicode codepoints.
        left = len(lines[node.lineno-1].encode('utf-8')[:node.col_offset].decode('utf-8'))
        right = len(lines[node.end_lineno-1].encode('utf-8')[:node.end_col_offset].decode('utf-8'))
        return (prefixes[node.lineno-1]+left, prefixes[node.end_lineno-1]+right)
    names, reads, findings = {}, [], []
    def read(node):
        position = span(node)
        if position not in reads:
            reads.append(position)
        return Value((position,))
    def symbol(node, kind):
        return isinstance(node, ast.Name) and names.get(node.id) == Symbol(kind)
    def expression(node, depth=0):
        if depth > 32:
            raise CorpusError('Expression exceeds the depth limit.')
        def evaluate(child):
            return expression(child, depth+1)
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, float, bool, type(None)):
            return Value(literal=node.value)
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, (ast.List, ast.Tuple, ast.Dict)):
            children = node.elts if not isinstance(node, ast.Dict) else [*node.keys, *node.values]
            if any(child is None for child in children):
                raise CorpusError('Container unpacking is unsupported.')
            values = [evaluate(child) for child in children]
            if any(not isinstance(v, Value) for v in values):
                raise CorpusError('Unsupported container value.')
            return Value(tuple(sorted(set(source for value in values for source in value.sources))))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = evaluate(node.left), evaluate(node.right)
            if not isinstance(a, Value) or not isinstance(b, Value):
                raise CorpusError('Unsupported concatenation.')
            literal = a.literal+b.literal if isinstance(a.literal, str) and isinstance(b.literal, str) else None
            return Value(tuple(sorted(set(a.sources+b.sources))), literal)
        if isinstance(node, ast.Attribute) and symbol(node.value, 'os') and node.attr == 'environ':
            return Symbol('environment')
        if isinstance(node, ast.Subscript) and evaluate(node.value) == Symbol('environment'):
            key = evaluate(node.slice)
            if not isinstance(key, Value) or not isinstance(key.literal, str):
                raise CorpusError('Environment key must be static.')
            return read(node) if key.literal in SECRET_KEYS else Value()
        if not isinstance(node, ast.Call) or any(k.arg is None for k in node.keywords):
            raise CorpusError('Unsupported expression or transformation.')
        target = node.func
        if symbol(target, 'path') or isinstance(target, ast.Name) and target.id == 'open' and target.id not in names:
            if node.keywords or not 1 <= len(node.args) <= 2 or symbol(target, 'path') and len(node.args) != 1:
                raise CorpusError('Unsupported file constructor.')
            path = evaluate(node.args[0])
            if not isinstance(path, Value) or not isinstance(path.literal, str):
                raise CorpusError('File path must be static.')
            secret_path(path.literal)
            if len(node.args) == 2:
                mode = evaluate(node.args[1])
                if not isinstance(mode, Value) or mode.literal not in ('r', 'rb'):
                    raise CorpusError('Only static read modes are supported.')
            return File(path.literal, 'path' if symbol(target, 'path') else 'open')
        if not isinstance(target, ast.Attribute):
            raise CorpusError('Unsupported function call.')
        owner = evaluate(target.value)
        if isinstance(owner, File) and target.attr in ('read', 'read_text', 'read_bytes'):
            allowed = {'path': ('read_text', 'read_bytes'), 'open': ('read',)}
            if target.attr not in allowed[owner.constructor]:
                raise CorpusError('Read method does not match its file constructor.')
            if node.args or node.keywords:
                raise CorpusError('Only argument-free file reads are supported.')
            return read(node) if secret_path(owner.path) else Value()
        if owner == Symbol('requests') and target.attr in ('post', 'put', 'patch', 'get'):
            if len(node.args) != 1:
                raise CorpusError('Network sink requires one static URL.')
            url = evaluate(node.args[0])
            if not isinstance(url, Value) or not isinstance(url.literal, str):
                raise CorpusError('Network sink URL must be static.')
            try:
                parsed = urlsplit(url.literal)
                if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.port == 0 or any(ord(c) < 33 for c in url.literal):
                    raise ValueError()
            except ValueError:
                raise CorpusError('Unsupported HTTP sink URL.') from None
            outgoing = []
            for keyword in node.keywords:
                if keyword.arg not in ('data', 'json', 'files', 'params', 'headers', 'timeout'):
                    raise CorpusError('Unsupported HTTP sink argument.')
                value = evaluate(keyword.value)
                if not isinstance(value, Value):
                    raise CorpusError('Unsupported HTTP sink value.')
                if keyword.arg != 'timeout':
                    outgoing.extend(value.sources)
            if outgoing:
                findings.append({'id': 'sig.credential_exfil.v1', 'source_spans': sorted(set(outgoing)),
                                 'sink_span': span(node), 'meaning': 'supported_static_credential_read_to_http_argument'})
            return Value()
        raise CorpusError('Unsupported call or transformed value.')
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name not in ('requests', 'os'):
                    raise CorpusError('Unsupported import.')
                names[alias.asname or alias.name] = Symbol(alias.name)
        elif isinstance(statement, ast.ImportFrom) and statement.level == 0 and statement.module == 'pathlib':
            for alias in statement.names:
                if alias.name != 'Path':
                    raise CorpusError('Unsupported import.')
                names[alias.asname or alias.name] = Symbol('path')
        elif isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            names[statement.targets[0].id] = expression(statement.value)
        elif isinstance(statement, ast.Expr):
            expression(statement.value)
        elif isinstance(statement, ast.Pass):
            continue
        else:
            raise CorpusError('Only supported straight-line Python statements are evaluated.')
    return {'format': 'credential-flow-observation/v1', 'method': METHOD,
            'method_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'subject_sha256': hashlib.sha256(subject.encode('utf-8')).hexdigest(),
            'subject_characters': len(subject), 'normalization_id': NORMALIZATION_ID,
            'offset_unit': 'NFC_unicode_codepoint', 'state': 'STATIC_FLOW' if findings else 'NO_SUPPORTED_FLOW',
            'recognized_read_spans': reads, 'findings': findings, 'network_used': False,
            'subject_executed': False, 'secret_contents_read': False, 'intent_established': False,
            'live_credential_verified': False, 'use_mention_classified': False,
            'independent_accuracy_evidence': False, 'tags': []}
