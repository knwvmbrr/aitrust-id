"""Local text checker. Never executes input, follows redirects, or uses a proxy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DEFAULT_ENV = Path.home() / '.config/aitrust-id/runtime.env'
GATEWAY = 'http://127.0.0.1:8787'
MAX_CHARS = 200_000
MAX_BYTES = MAX_CHARS * 4
EXPLANATIONS = {
    'sig.piped_installer.v4': 'Downloaded output is piped into a shell.',
    'sig.obfuscated_payload.v3': 'A recognized decoded payload is passed to eval/exec.',
    'sig.remote_command_substitution.v4': 'Downloaded output is substituted into an execution command.',
    'sig.remote_process_substitution.v4': 'A supported executor reads downloaded output through process substitution.',
    'sig.remote_backtick_substitution.v3': 'Downloaded output is substituted using backticks into an execution command.',
}


class LocalCheckError(ValueError):
    """Only fixed, safe messages may reach command-line output."""



def private_path(path):
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(ROOT):
        raise LocalCheckError('Keep the credential file outside the repository.')
    return path


def init_config(path):
    path = private_path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise LocalCheckError('Credential directory must be yours, private (0700), and not a symlink.')
    # Exclusive creation prevents accidental replacement of an existing installation.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write('AITRUST_TOKEN=' + secrets.token_urlsafe(32) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return path


def read_token(path):
    path = private_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise LocalCheckError('Credential file must be yours and private (0600).')
        data = stream.read(4097)
    if len(data) > 4096:
        raise LocalCheckError('Credential file is too large.')
    tokens = [line.split('=', 1)[1] for line in data.splitlines() if line.startswith('AITRUST_TOKEN=')]
    if len(tokens) != 1 or not re.fullmatch(r'[A-Za-z0-9_-]{16,256}', tokens[0]) or tokens[0] == 'change-me':
        raise LocalCheckError('Credential file needs one generated AITRUST_TOKEN.')
    return tokens[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocalCheckError('Local gateway redirects are refused.')


def local_request(path, payload=None, token=None):
    headers = {'Accept': 'application/json'}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    data = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(GATEWAY + path, data=data, headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=25) as response:
            if response.status != 200 or response.headers.get_content_type() != 'application/json':
                raise LocalCheckError('Local gateway did not return a successful JSON result.')
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise LocalCheckError('Local gateway result is too large.')
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        messages = {401: 'Local token was rejected.', 422: 'Input is unsupported or invalid.',
                    502: 'A local dependency returned an invalid result.',
                    503: 'Local services are unavailable or busy.', 504: 'Local evaluation timed out.'}
        raise LocalCheckError(messages.get(error.code, 'Local gateway request failed.')) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise LocalCheckError('Local gateway is unavailable. Start the services and run doctor.') from None


def read_input(stream):
    raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise LocalCheckError('Input exceeds the 200,000-character limit.')
    text = raw.decode('utf-8')
    if not text.strip() or len(text) > MAX_CHARS:
        raise LocalCheckError('Provide nonempty UTF-8 text, at most 200,000 characters.')
    return text


def validate_result(result, privacy=False):
    from protocol.assertions import validator as assertion_validator
    schema = json.loads((ROOT / 'spec/assertion.schema.json').read_text())
    validator = assertion_validator(schema)
    if not validator.is_valid(result):
        raise LocalCheckError('Local gateway returned an invalid assertion; no finding is accepted.')
    if 'signature' in result:
        raise LocalCheckError('This unsigned preview cannot verify signed records.')
    if any(tag['code'] not in ('PS', 'PII_REDACTED') for tag in result['tags']):
        raise LocalCheckError('Local gateway returned a tag outside the supported capability set.')
    if privacy:
        return validate_privacy(result)
    expected = hashlib.sha256((ROOT / 'services/evaluator/app.py').read_bytes()).hexdigest()
    if (result['spec_version'] != '0.1.0'
            or result['evaluator']['calibration_id'] != 'uncalibrated-rules-v6'
            or not any(model['name'] == 'rules-only' and model['sha256'] == expected
                       for model in result['evaluator']['models'])):
        raise LocalCheckError('Local evaluator differs from this checkout. Rebuild before checking.')
    for tag in result['tags']:
        for signal in tag['signals']:
            for start, end in signal.get('spans', []):
                if not 0 <= start < end <= result['subject']['char_len']:
                    raise LocalCheckError('Local gateway returned invalid evidence offsets.')
    return result


def validate_privacy(result, root=ROOT):
    """Check the schema-validated identities without extra checker dependencies."""
    import ast
    pipeline=result['evaluator']['preprocessing'];config=pipeline['configuration']
    redactor=config['redactor'];sources=redactor['configuration']['sources']
    current=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
    canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=True,allow_nan=False).encode('ascii')
    checked=lambda identity:identity['sha256']==hashlib.sha256(canonical(
        {key:identity[key] for key in ('version','configuration')})).hexdigest()
    expected={
        'app':'services/anonymizer/app.py',
        'model_loader':'services/anonymizer/model_identity.py',
        'requirements_lock':'services/anonymizer/requirements.lock',
        'identity_contract':'protocol/replay_identity.py',
        'identity_builder':'services/anonymizer/replay_metadata.py',
    }
    gateway_source=(root/'services/gateway/app.py').read_bytes()
    if (result['spec_version']!='0.1.0'
            or result['evaluator']['calibration_id']!='procedural-redaction-v1'
            or result['abstentions']
            or any(tag['code']!='PII_REDACTED' for tag in result['tags'])
            or len(result['tags'])>1
            or pipeline.get('version')!='local-text-pipeline/v1'
            or redactor.get('version')!='presidio-offline-en/v1'
            or not checked(pipeline) or not checked(redactor)
            or config['gateway_source_sha256']!=hashlib.sha256(gateway_source).hexdigest()
            or config['normalization_source_sha256']!=current('protocol/normalization.py')
            or config['normalization_data_sha256']!=current('protocol/unicode15-data.json')
            or any(sources[key]!=current(name) for key,name in expected.items())
            or result['evaluator']['models']!=[
                {'name':'presidio-redaction','sha256':redactor['sha256'],'revision':redactor['version']},
                {'name':'gateway-pipeline','sha256':pipeline['sha256'],'revision':pipeline['version']}]):
        raise LocalCheckError('Privacy method differs from this checkout; no result is accepted.')
    # Read the fixed Literal category contract from those same verified source
    # bytes. No service imports, code execution or FastAPI/Pydantic installation.
    try:
        declaration=next(node for node in ast.parse(gateway_source).body
                         if isinstance(node,ast.ClassDef) and node.name=='Redaction')
        annotation=next(node.annotation for node in declaration.body
                        if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name)
                        and node.target.id=='entities')
        allowed=ast.literal_eval(annotation.slice.slice)
    except (ValueError,AttributeError,StopIteration,SyntaxError):
        raise LocalCheckError('Privacy category contract is unavailable.') from None
    if not isinstance(allowed,tuple) or not all(isinstance(x,str) for x in allowed):
        raise LocalCheckError('Privacy category contract is unavailable.')
    for tag in result['tags']:
        signals=tag['signals']
        if (tag['confidence']!=1. or 'floor' in tag or len(signals)!=1
                or signals[0].get('id')!='presidio.entity.v1'
                or signals[0].get('score')!=1.
                or set(signals[0])!={'id','score','detail'}):
            raise LocalCheckError('Privacy result has unsupported evidence.')
        detail=signals[0]['detail'];entities=detail.get('entities');count=detail.get('count')
        if (set(detail)!={'entities','count'} or not isinstance(entities,list)
                or not 1<=len(entities)<=32
                or any(not isinstance(x,str) or x not in allowed for x in entities)
                or len(set(entities))!=len(entities)
                or type(count) is not int or not len(entities)<=count<=200_000):
            raise LocalCheckError('Privacy result has unsupported metadata.')
    return result


def brief_privacy(result):
    if result['tags']:
        categories=result['tags'][0]['signals'][0]['detail']['entities']
        lines=['Possible personal details found: '+', '.join(x.replace('_',' ').lower() for x in categories)+'.',
               'Review your draft before sharing.']
    else:
        lines=['No supported personal details found.',
               'Review your draft anyway; this is not a privacy clearance.']
    lines+=['This check has not changed your draft or sent it to a chat app.',
            'Detection can miss private details or flag ordinary text.']
    return '\n'.join(lines)


def brief(result):
    ps = [tag for tag in result['tags'] if tag['code'] == 'PS']
    uncertain = any(row['code'] == 'PS' for row in result['abstentions'])
    lines = ['PS · FINDING: supported command-risk pattern.' if ps else
             'PS · UNCERTAIN: no PS finding issued.' if uncertain else
             'PS · NO_FINDING: no supported command-risk pattern found.']
    lines.append('This does not establish a scam or whether the answer is safe or true.')
    if any(tag['code'] == 'PII_REDACTED' for tag in result['tags']):
        lines.append('PII: detected personal information was redacted; other sensitive information may remain.')
    for tag in ps:
        for signal in tag['signals']:
            lines.append(EXPLANATIONS.get(signal['id'], 'Unrecognized evidence identifier; inspect the JSON record.'))
            for start, end in signal.get('spans', []):
                lines.append(f'Redacted-text characters {start}–{end}.')
    lines.extend(['Development method; heuristic scores are not measured probabilities.',
                  'Record: ' + result['assertion_id'], 'Use --json for the structured evidence record.'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='AI Trust ID local development checker; no truth or safety certification.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'doctor', 'check', 'privacy'):
        sub = commands.add_parser(name)
        sub.add_argument('--env-file', type=Path, default=DEFAULT_ENV)
        if name == 'doctor':
            sub.add_argument('--privacy', action='store_true', help='Check only the independent privacy route')
        if name in ('check','privacy'):
            sub.add_argument('file', nargs='?', default='-', help='UTF-8 text file, or - for stdin')
            sub.add_argument('--json', action='store_true', help='Print the schema-validated assertion, without response text')
            sub.add_argument('--fail-on-finding', action='store_true', help='Exit 2 when the requested check finds supported evidence')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            print('Created private local configuration: ' + str(init_config(args.env_file)))
            print('Token not displayed. Existing files are never overwritten.')
            return 0
        token = read_token(args.env_file)
        if args.command == 'doctor':
            privacy=args.privacy
            path='/healthz?check_mode=privacy' if privacy else '/healthz'
            if local_request(path).get('ok') is not True:
                raise LocalCheckError('Local dependencies are not healthy.')
            payload={'text':'Synthetic health check.','origin_host':'manual-local'}
            if privacy:payload['check_mode']='privacy'
            result = validate_result(local_request('/v1/evaluate',payload,token),privacy=privacy)
            print('Authenticated local privacy check ready; valid assertion received. Development checks only.' if privacy else
                  'Authenticated local pipeline ready; valid assertion received. Development checks only.')
            return 0
        if args.file == '-':
            if sys.stdin.isatty():
                print('Paste text, then Ctrl-D to check it locally.', file=sys.stderr)
            text = read_input(sys.stdin.buffer)
        else:
            with open(args.file, 'rb') as stream:
                text = read_input(stream)
        privacy=args.command=='privacy'
        payload={'text':text,'origin_host':'manual-local'}
        if privacy:payload['check_mode']='privacy'
        result = validate_result(local_request('/v1/evaluate',payload,token),privacy=privacy)
        summary=brief_privacy(result) if privacy else brief(result)
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else summary)
        selected='PII_REDACTED' if privacy else 'PS'
        return 2 if args.fail_on_finding and any(tag['code']==selected for tag in result['tags']) else 0
    except ImportError:
        print('UNAVAILABLE: Install hashed eval/requirements.lock in the documented virtual environment.', file=sys.stderr)
    except LocalCheckError as error:
        print('UNAVAILABLE: ' + str(error) + ' No valid check completed.', file=sys.stderr)
    except FileExistsError:
        print('UNAVAILABLE: Configuration already exists; it was preserved.', file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        # No traceback or exception data: inputs and credentials must not reach output.
        print('UNAVAILABLE: Check local configuration, input and service health. No valid check completed.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
