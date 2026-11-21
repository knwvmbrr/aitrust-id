#!/usr/bin/env python3
"""Offline source/description consistency checks; no SDK, service or network."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'integrations/ai-tools/remote-openapi.json'
SOURCES = ('tools/remote_tag_server.py', 'tools/tag_api.py', 'deploy/ai-tools/render.py')
LIMIT = 256_000
SERVER_DESCRIPTION = ('Engineering preview; public reachability and host account '
                      'installation are verified separately. See the connection '
                      'page for current status. No availability or host approval '
                      'is asserted by this manifest.')


class ContractError(ValueError):
    pass


def require(value):
    if not value:
        raise ContractError('OpenAPI contract refused.')


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def load(raw):
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT)
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False))


def read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        chunks = bytearray()
        while len(chunks) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        after = os.fstat(fd)
        identity = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(len(chunks) == before.st_size
                and all(getattr(before, n) == getattr(after, n) for n in identity))
        return bytes(chunks)
    finally:
        owned, fd = fd, None
        os.close(owned)


def assigned(tree, name):
    return next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def resolve(node, values):
    """Interpret only the literal CHECK_SCHEMA expression; never execute source."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [resolve(n, values) for n in node.elts]
    if isinstance(node, ast.Dict):
        return {resolve(k, values): resolve(v, values)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        require(node.value.id == 'tag_api' and node.attr in values)
        return values[node.attr]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'list' and len(node.args) == 1 and not node.keywords):
        return list(resolve(node.args[0], values))
    raise ContractError('OpenAPI contract refused.')


def verify(document=None, root=ROOT):
    d = load(read(root / MANIFEST, LIMIT)) if document is None else document
    require(type(d) is dict and d.get('openapi') == '3.1.1')
    require(set(d) == {'openapi', 'info', 'servers', 'security', 'paths',
                       'components', 'externalDocs', 'x-aitrust-source-sha256',
                       'x-aitrust-transport-limits', 'x-aitrust-mcp-excluded'})
    require(set(d['components']) == {'schemas'})
    require(d.get('security') == [] and 'securitySchemes' not in d['components'])
    require(d.get('servers') and len(d['servers']) == 1
            and d['servers'][0]['url'] == 'https://vps-18ef1326.vps.ovh.us')
    require(d['servers'][0]['description'] == SERVER_DESCRIPTION)
    require(d.get('x-aitrust-mcp-excluded') is True)
    require(set(d['paths']) == {'/v1/check', '/v1/tags', '/healthz'})
    source = {n: read(root / n, 1_000_000) for n in SOURCES}
    require(all(0 < len(b) <= 1_000_000 for b in source.values()))
    require(d.get('x-aitrust-source-sha256') == {
        n: hashlib.sha256(b).hexdigest() for n, b in source.items()})
    remote = ast.parse(source[SOURCES[0]])
    tag = ast.parse(source[SOURCES[1]])
    proxy = ast.parse(source[SOURCES[2]])
    require(d['servers'][0]['url'] == 'https://' + ast.literal_eval(assigned(proxy, 'HOST')))
    values = {n: ast.literal_eval(assigned(tag, n))
              for n in ('MAX_CHARS', 'MAX_BYTES', 'CODES')}
    values['CODES'] = list(values['CODES'])
    schemas = d['components']['schemas']
    require(schemas['CheckRequest'] == resolve(assigned(remote, 'CHECK_SCHEMA'), values))
    require(d['x-aitrust-transport-limits'] == {
        'wire_bytes': ast.literal_eval(assigned(remote, 'WIRE_LIMIT')),
        'text_utf8_bytes': values['MAX_BYTES'],
        'request_seconds': ast.literal_eval(assigned(remote, 'REQUEST_SECONDS')),
        'ps_seconds': ast.literal_eval(assigned(remote, 'PS_SECONDS')),
        'json_depth': 20})
    # Actual code must still expose precisely this route set plus separate MCP.
    tuples = [n for n in ast.walk(remote) if isinstance(n, ast.Tuple)]
    require(any(all(isinstance(x, ast.Constant) for x in n.elts)
                and set(ast.literal_eval(n)) == set(d['paths']) | {'/mcp'}
                for n in tuples))
    code_errors = {str(n.args[0].value) for n in ast.walk(remote)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == 'answer' and n.args
                   and isinstance(n.args[0], ast.Constant)}
    ids = set()
    for path, method, schema in [('/v1/check', 'post', 'CheckResult'),
                                 ('/v1/tags', 'get', 'TagCatalog'),
                                 ('/healthz', 'get', 'Health')]:
        require(set(d['paths'][path]) == {method})
        op = d['paths'][path][method]
        require(set(op) == {'operationId', 'summary', 'description', 'responses'}
                | ({'requestBody'} if method == 'post' else set()))
        require(type(op.get('operationId')) is str and op['operationId'] not in ids)
        ids.add(op['operationId'])
        require('parameters' not in op and 'security' not in op and 'servers' not in op)
        require(set(op['responses']) == {'200', '421', '502'} | code_errors)
        require(op['responses']['200']['content']['application/json']['schema']
                == {'$ref': '#/components/schemas/' + schema})
        if method == 'get':
            require('requestBody' not in op)
    body = d['paths']['/v1/check']['post']['requestBody']
    require(body['required'] is True and set(body['content']) == {'application/json'}
            and body['content']['application/json']['schema'] == {
                '$ref': '#/components/schemas/CheckRequest'})
    # Keep the public non-content projection closed, with explicit false claims.
    output = schemas['CheckResult']
    result_function = next(n for n in tag.body if isinstance(n, ast.FunctionDef)
                           and n.name == 'result')
    returned = next(n.value for n in ast.walk(result_function) if isinstance(n, ast.Return))
    require(set(output['properties']) == {ast.literal_eval(k) for k in returned.keys})
    require(set(output['required']) == set(output['properties'])
            and output['additionalProperties'] is False)
    for key in ('independently_validated', 'safety_clearance', 'text_included',
                'subject_identity_included', 'research_submitted'):
        require(output['properties'][key] == {'const': False})
    require(output['properties']['format'] == {'const': 'ai-trust-id-tool-result/v1'})
    require(set(output['properties']['state']['enum']) == {'COMPLETE', 'PARTIAL', 'UNAVAILABLE'})
    require(schemas['Health']['properties']['PII_available'] == {'const': False})
    # References are local, resolved and finite: an import must not fetch a schema.
    nodes = [d]
    while nodes:
        value = nodes.pop()
        if isinstance(value, dict):
            if '$ref' in value:
                name = value['$ref']
                require(type(name) is str and name.startswith('#/components/schemas/')
                        and name.split('/')[-1] in schemas)
            nodes.extend(value.values())
        elif isinstance(value, list):
            nodes.extend(value)
    return {'pass': True, 'profile': 'ordinary-json-openapi-source/v1',
            'operations': 3, 'SDK_imported': False, 'network_used': False,
            'public_activation_verified': False, 'AI_host_approval_verified': False,
            'source_sha256': d['x-aitrust-source-sha256']}


if __name__ == '__main__':
    try:
        # Fixed entry point; do not echo arbitrary arguments or local diagnostics.
        import sys
        require(len(sys.argv) == 1)
        print(json.dumps(verify(), sort_keys=True))
    except Exception:
        print('{"pass":false,"reason":"openapi_contract_refused"}')
        raise SystemExit(1)
