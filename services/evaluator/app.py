"""Bounded command-pattern extraction. Scores are heuristics, not probabilities."""
import hashlib
import re
import shlex
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

app = FastAPI(title='AITrust-ID Evaluator')
app.add_middleware(RequestBodyLimitMiddleware,max_body_size=1_250_000)
PRODUCTION_TAGS = frozenset({'PS'})
CALIBRATION_ID = 'uncalibrated-rules-v5'
MODELS = [{'name':'rules-only','sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'revision':'context-v5'}]
PIPED_INSTALLER = re.compile(r'(?<![\w./-])(?P<fetch>(?:curl|wget)\s+[^\n|;&`]*?)\s*\|\s*(?:sudo\s+)?(?:bash|sh)\b')
# The broad fetch_execute.v1 prototype is withdrawn from runtime; see signals.md.
# Full bounded expressions, output routing, and evaluation layers matter.
# These development methods do not fetch URLs or execute commands.
EXECUTOR = r'(?:(?:/(?:usr/)?bin/)?(?:bash|sh|zsh|dash|ksh))'
INTERPRETER = r'(?:(?:/(?:usr/)?bin/)?(?:python(?:[23])?|node|ruby|perl))'
COMMAND = r'(?P<executor>(?:'+EXECUTOR+r'\s+-(?:c|lc|cl)|'+INTERPRETER+r'\s+-(?:c|e)|eval))'
FETCH = r'(?P<fetch>(?:curl|wget)\s+[^()\n;$&|`]+?)'
PREFIX = r'(?<![\w./-])(?:sudo\s+)?'
COMMAND_SUBSTITUTION = re.compile(
    PREFIX+COMMAND+r'\s+(?P<quote>["\x27]?)\$\(\s*'+FETCH+r'\)(?P=quote)')
PROCESS_SUBSTITUTION = re.compile(
    PREFIX+r'(?:'+EXECUTOR+'|'+INTERPRETER+r'|source|\.)\s+<\(\s*'+FETCH+r'\)')
BACKTICK_SUBSTITUTION = re.compile(
    PREFIX+COMMAND+r'\s+(?P<quote>["\x27]?)`\s*'+FETCH+r'`(?P=quote)')


def fetches_stdout(fetch):
    """Tokenize only; never run a shell, fetch a URL, or evaluate a payload."""
    if re.search(r'(?:^|\s)(?:1)?>', fetch):
        return False
    try:
        args = shlex.split(fetch)
    except ValueError:
        return False
    if not args:
        return False
    curl = args[0] == 'curl'
    if args[0] not in ('curl', 'wget'):
        return False  # Shell command names and option letters are case-sensitive.
    stdout = curl
    # Consume option arguments instead of interpreting their letters as options.
    # This is bounded routing recognition, not a general curl/wget or shell parser.
    long_values = ({'--output', '--header', '--user-agent', '--user', '--proxy-user',
                    '--proxy', '--request', '--data', '--data-raw', '--data-binary',
                    '--form', '--referer', '--cookie', '--cookie-jar', '--max-time',
                    '--connect-timeout', '--range', '--url', '--write-out', '--dump-header'}
                   if curl else {'--output-document', '--header', '--user-agent',
                                 '--user', '--password', '--timeout', '--tries',
                                 '--directory-prefix', '--output-file'})
    short_values = 'AbcCdDeEFHmoruUw xXzT'.replace(' ', '') if curl else 'OUoPTt'
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == '--':
            break
        if arg.split('=', 1)[0] in ('--help', '--version') or (curl and arg.split('=', 1)[0] in ('--head', '--config', '--next')):
            return False
        if curl and arg in ('--remote-name', '--remote-name-all'):
            return False
        if arg.startswith('--'):
            key, equal, value = arg.partition('=')
            if key in long_values:
                if not equal:
                    i += 1
                    if i >= len(args):
                        return False
                    value = args[i]
                if key == ('--output' if curl else '--output-document'):
                    stdout = value == '-'
                    if not stdout:
                        return False
        elif arg.startswith('-') and arg != '-':
            flags = arg[1:]
            for pos, flag in enumerate(flags):
                if curl and flag in 'OIK':
                    return False
                if flag in short_values:
                    value = flags[pos + 1:]
                    if not value:
                        i += 1
                        if i >= len(args):
                            return False
                        value = args[i]
                    if flag == ('o' if curl else 'O'):
                        stdout = value == '-'
                        if not stdout:
                            return False
                    break
        i += 1
    return stdout


def display_quote(prefix):
    """Recognize an open literal echo/printf quote, never a later command."""
    command = re.match(r'^\s*(?:echo|printf)\b', prefix)
    if not command:
        return None
    quote = None
    escaped = False
    for pos, char in enumerate(prefix[command.end():], command.end()):
        if escaped:
            escaped = False
            continue
        if char == '\\' and quote != "'":
            escaped = True
        elif char == quote:
            quote = None
        elif char in ('"', "'") and quote is None:
            quote = char
        elif quote is None and char in ';&|':
            return None
        elif quote != "'" and (char == '`' or prefix[pos:pos+2] == '$('):
            return None
    return quote


def substitution_mentioned(text, match):
    prefix = text[text.rfind('\n', 0, match.start()) + 1:match.start()]
    if prefix.lstrip().startswith(('#', '//')) or WARNING.search(prefix):
        return True
    # Only literal display recognized here. Echo with active double-quoted
    # substitution can execute nested commands and must not be suppressed broadly.
    return display_quote(prefix) == "'"


def pipe_mentioned(text, match):
    if substitution_mentioned(text, match):
        return True
    prefix = text[text.rfind('\n', 0, match.start()) + 1:match.start()]
    # A plain double-quoted display is literal; active substitutions are not.
    return ('$' not in prefix + match.group() and '`' not in prefix + match.group()
            and display_quote(prefix) == '"')


def shell_evaluation_layer(match):
    quote = match.groupdict().get('quote')
    if quote != "'":
        return True
    executor = match.group('executor').split()[0].rsplit('/', 1)[-1].lower()
    return executor in ('bash', 'sh', 'zsh', 'dash', 'ksh', 'eval')

OBFUSCATED = re.compile(r'\b(?:eval|exec)\s*\(\s*(?:base64\.b64decode|atob|bytes\.fromhex)\s*\(', re.I)
# Narrow warning syntax scoped to the immediately preceding phrase. Not a broad
# character-window or fenced-code suppression rule.
WARNING = re.compile(r'(?:never\s+(?:run|execute|use)|do\s+not\s+(?:run|execute|use)|don\x27t\s+(?:run|execute|use)|avoid\s+(?:running|executing|using))\s*(?:[`"\x27]\s*)?$', re.I)

class Doc(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(max_length=200_000)

def mentioned(text, start):
    line_start = text.rfind('\n', 0, start) + 1
    prefix = text[line_start:start]
    if prefix.lstrip().startswith(('#', '//')):
        return True
    return bool(WARNING.search(prefix))

@app.get('/healthz')
def healthz():
    return {'ok':True}

@app.post('/signals')
def signals(doc: Doc):
    signals = []
    for pattern, name, score in [(PIPED_INSTALLER,'sig.piped_installer.v3',.97),(OBFUSCATED,'sig.obfuscated_payload.v2',.88)]:
        for match in pattern.finditer(doc.text):
            if (not mentioned(doc.text,match.start())
                    and (pattern is not PIPED_INSTALLER or
                         (not pipe_mentioned(doc.text, match) and fetches_stdout(match.group('fetch'))))):
                signals.append({'id':name,'score':score,'spans':[[match.start(),match.end()]]})
    for pattern, name in [(COMMAND_SUBSTITUTION, 'sig.remote_command_substitution.v3'),
                          (PROCESS_SUBSTITUTION, 'sig.remote_process_substitution.v3'),
                          (BACKTICK_SUBSTITUTION, 'sig.remote_backtick_substitution.v2')]:
        for match in pattern.finditer(doc.text):
            if (not substitution_mentioned(doc.text, match)
                    and (pattern is PROCESS_SUBSTITUTION or shell_evaluation_layer(match))
                    and fetches_stdout(match.group('fetch'))):
                signals.append({'id': name, 'score': .97,
                                'spans': [[match.start(), match.end()]]})
    candidates = [{'code':'PS','confidence':max(s['score'] for s in signals),'signals':signals}] if signals else []
    return {'candidates':candidates,'models':MODELS,'calibration_id':CALIBRATION_ID}
