#!/usr/bin/env python3
"""Build an isolated, authenticated development stack; never execute submitted AI text."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import aitrust

LABEL = 'org.aitrust.local-setup'
ROLES = ('anonymizer', 'evaluator', 'gateway')
MEMORY = {'anonymizer': 1024, 'evaluator': 256, 'gateway': 256}
DEFAULT_STATE = Path.home() / '.config/aitrust-id/local-stack'


class SetupError(ValueError):
    """Fixed public diagnostics; engine output and credentials are never printed."""


def private_directory(path, create=False):
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(ROOT):
        raise SetupError('State must stay outside this checkout.')
    for part in (path, *path.parents):
        if part.is_symlink():
            raise SetupError('Symlinked state paths are refused.')
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(mode=0o700)  # Exclusive; never adopt or overwrite another installation.
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise SetupError('State directory must be yours and private (0700).')
    return path


def write_state(folder, state):
    tmp = folder / 'setup.json.tmp'
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(state, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(folder / 'setup.json')


def read_state(folder):
    fd = os.open(folder / 'setup.json', os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise SetupError('Setup record must be yours and private (0600).')
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise SetupError('Setup record is too large.')
    state = json.loads(raw)
    if (state.get('version') != 1 or state.get('engine') not in ('docker', 'podman')
            or not re.fullmatch(r'aitrust-local-[a-f0-9]{32}', state.get('project', ''))):
        raise SetupError('Setup record is invalid.')
    for kind in ('containers', 'networks', 'images'):
        values = state.get(kind)
        if not isinstance(values, list) or len(values) > 3 or any(
                not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value) for value in values):
            raise SetupError('Setup resource identity is invalid.')
    return state


def command(argv, timeout=60):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
    if result.returncode or len(result.stdout) > 2_000_000:
        raise SetupError('Command failed; no ready stack is claimed.')
    return result.stdout.decode('utf-8').strip()


class Engine:
    def __init__(self, name):
        self.name = name
        self.binary = shutil.which(name)
        if self.binary is None:
            raise SetupError('Install the selected Docker or Podman engine first.')

    def run(self, *args, timeout=60):
        return command([self.binary, *args], timeout)

    def inspect(self, kind, identity):
        value = json.loads(self.run(kind, 'inspect', identity))
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise SetupError('Engine inspection returned an invalid record.')
        return value[0]


def owned(engine, kind, identity, project):
    row = engine.inspect(kind, identity)
    labels = row.get('Labels', row.get('labels', {})) if kind == 'network' else row.get('Config', {}).get('Labels', {})
    if labels.get(LABEL) != project:
        raise SetupError('Resource ownership changed; it is preserved.')
    return row


def cleanup(engine, state):
    ok = True
    for kind, key in (('container', 'containers'), ('network', 'networks'), ('image', 'images')):
        for identity in reversed(state[key]):
            try:
                owned(engine, kind, identity, state['project'])
                # Only recorded IDs with the exact random ownership label may be removed.
                args = (kind, 'rm', '-f', identity) if kind == 'container' else (kind, 'rm', identity)
                engine.run(*args)
                state[key].remove(identity)
            except (SetupError, OSError, ValueError, subprocess.SubprocessError):
                ok = False
    return ok


def preflight(engine):
    if sys.version_info < (3, 12):
        raise SetupError('Python 3.12 or newer is required.')
    engine.run('info')
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', 8787))
        except OSError:
            raise SetupError('Port 8787 is already in use; existing services are preserved.') from None


def install_checker(folder, wheelhouse=None):
    print('Installing the hash-locked local checker…', flush=True)
    command([sys.executable, '-m', 'venv', str(folder / 'checker')], 120)
    python = str(folder / 'checker/bin/python')
    args = [python, '-m', 'pip', '--isolated', 'install', '--require-hashes',
            '--only-binary=:all:', '--disable-pip-version-check',
            '-r', str(ROOT / 'eval/requirements.lock')]
    if wheelhouse is not None:
        if not wheelhouse.is_dir() or wheelhouse.is_symlink():
            raise SetupError('An offline wheelhouse must be an existing ordinary directory.')
        args.extend(['--no-index', '--find-links', str(wheelhouse.absolute())])
    command(args, 300)
    return python


def resource_id(text):
    if not re.fullmatch(r'[a-f0-9]{64}', text):
        raise SetupError('Engine did not return a full resource identity.')
    return text


def no_process_capabilities(raw):
    values = json.loads(raw)
    required = {'CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'}
    return (isinstance(values, dict) and set(values) == required
            and all(isinstance(value, str) and re.fullmatch(r'[a-fA-F0-9]{16}', value)
                    and int(value, 16) == 0 for value in values.values()))


def inspection_address(row, network_id):
    matches = [value.get('IPAddress') for value in row['NetworkSettings']['Networks'].values()
               if value.get('NetworkID') == network_id]
    if len(matches) != 1:
        raise SetupError('A dependency lacks its recorded private network address.')
    try:
        address = ipaddress.IPv4Address(matches[0])
    except (ValueError, TypeError):
        raise SetupError('A dependency has an unsupported network address.') from None
    if not any(address in ipaddress.ip_network(cidr) for cidr in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise SetupError('A dependency address is not in a private IPv4 network.')
    return str(address)


def build_dns(paths=(Path('/etc/resolv.conf'), Path('/run/systemd/resolve/resolv.conf'))):
    """Reuse configured upstream DNS; a host loopback stub cannot serve a builder."""
    for path in paths:
        try:
            text = path.read_text()
        except OSError:
            continue
        if len(text) > 65536:
            raise SetupError('Configured DNS file is too large.')
        addresses = []
        for line in text.splitlines():
            fields = line.split('#', 1)[0].split()
            if len(fields) != 2 or fields[0] != 'nameserver':
                continue
            try:
                address = ipaddress.ip_address(fields[1])
            except ValueError:
                continue
            if not (address.is_loopback or address.is_unspecified or address.is_multicast):
                value = str(address)
                if value not in addresses:
                    addresses.append(value)
        if addresses:
            return addresses[:3]
    raise SetupError('Container builds need reachable DNS configured on this Linux host.')


def build_and_start(engine, folder, state, build_network='private'):
    project = state['project']
    images = {}
    for role in ROLES:
        print('Building ' + role + '…', flush=True)
        tag = project + '-' + role + ':local'
        build_args = ['build'] + (['--layers'] if engine.name == 'podman' else [])
        if build_network == 'host':
            build_args.extend(['--network', 'host'])
        elif engine.name == 'podman':
            for address in build_dns():
                build_args.extend(['--dns', address])
        engine.run(*build_args, '--label', LABEL + '=' + project, '-t', tag,
                   '-f', 'services/' + role + '/Dockerfile', '.', timeout=1200)
        image = owned(engine, 'image', tag, project)
        identity = resource_id(image['Id'].removeprefix('sha256:'))
        state['images'].append(identity)
        images[role] = identity
        write_state(folder, state)
    networks = {}
    for name in ('inspection', 'edge'):
        args = ['network', 'create', '--label', LABEL + '=' + project]
        if name == 'inspection':
            args.append('--internal')
        created = engine.run(*args, project + '-' + name)
        network = engine.inspect('network', project + '-' + name)
        identity = resource_id(network.get('Id', network.get('id', created)))
        state['networks'].append(identity)
        networks[name] = identity
        write_state(folder, state)
        owned(engine, 'network', identity, project)
    addresses = {}
    for role in ROLES:
        first_network = 'edge' if role == 'gateway' else 'inspection'
        args = ['create', '--name', project + '-' + role, '--label', LABEL + '=' + project,
                '--label', 'org.aitrust.local-role=' + role,
                '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                '--pids-limit=128', '--memory=' + str(MEMORY[role]) + 'm',
                '--tmpfs=/tmp:rw,noexec,nosuid,size=64m', '--network', networks[first_network],
                '--network-alias', role, '--health-cmd=python healthcheck.py',
                '--health-interval=5s', '--health-timeout=3s', '--health-retries=12']
        if role == 'gateway':
            if engine.name == 'podman':
                # Configure the complete DNS/network scope before Podman starts
                # the container; late attachment changes its resolver setup.
                args.extend(['--network', networks['inspection']])
            args.extend(['--env-file', str(folder / 'runtime.env'),
                         '--env=ANONYMIZER_URL=http://' + addresses['anonymizer'] + ':8000',
                         '--env=EVALUATOR_URL=http://' + addresses['evaluator'] + ':8000',
                         '--publish=127.0.0.1:8787:8000'])
        identity = resource_id(engine.run(*args, images[role]))
        state['containers'].append(identity)
        write_state(folder, state)
        if role == 'gateway' and engine.name != 'podman':
            engine.run('network', 'connect', networks['inspection'], identity)
        engine.run('start', identity)
        if role != 'gateway':
            addresses[role] = inspection_address(owned(engine, 'container', identity, project), networks['inspection'])


def verify_security(engine, state):
    result = {}
    for role, identity in zip(ROLES, state['containers']):
        row = owned(engine, 'container', identity, state['project'])
        host = row['HostConfig']
        if (row['Config']['User'] != '10001:10001' or host.get('ReadonlyRootfs') is not True
                or host.get('PidsLimit') != 128 or host.get('Memory') != MEMORY[role] * 1024 * 1024
                or not host.get('CapDrop')
                or not any(value in ('no-new-privileges', 'no-new-privileges:true')
                           for value in host.get('SecurityOpt', []))):
            raise SetupError('Effective container security differs from the required configuration.')
        bindings = host.get('PortBindings') or {}
        if role == 'gateway':
            if bindings != {'8000/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8787'}]}:
                raise SetupError('Gateway is not bound exclusively to the required loopback port.')
        elif bindings:
            raise SetupError('A private service unexpectedly publishes a port.')
        attached = row['NetworkSettings']['Networks']
        if len(attached) != (2 if role == 'gateway' else 1):
            raise SetupError('Unexpected service network boundary.')
        for name in attached:
            network = owned(engine, 'network', name, state['project'])
            if role != 'gateway' and network.get('Internal', network.get('internal')) is not True:
                raise SetupError('A private service has a non-internal network.')
        source = engine.run('exec', identity, 'python', '-c',
                            'import hashlib;print(hashlib.sha256(open("app.py","rb").read()).hexdigest())')
        expected = hashlib.sha256((ROOT / 'services' / role / 'app.py').read_bytes()).hexdigest()
        if source != expected:
            raise SetupError('Running service source differs from the checkout.')
        # Podman expands ALL into individual capability names. Verify actual
        # inherited/permitted/effective/bounding/ambient process sets instead of
        # trusting either engine's display spelling of the requested flag.
        caps = engine.run('exec', identity, 'python', '-c',
            'import json;keys={"CapInh","CapPrm","CapEff","CapBnd","CapAmb"};'
            'print(json.dumps({k:v.strip() for k,v in '
            '(line.split(":",1) for line in open("/proc/self/status") if ":" in line) if k in keys}))')
        if not no_process_capabilities(caps):
            raise SetupError('A service retains Linux process capabilities.')
        result[role] = {'source_sha256': source, 'uid': 10001, 'read_only': True,
                        'pids_limit': 128, 'memory_mib': MEMORY[role],
                        'capabilities_dropped': True, 'no_new_privileges': True}
    return result


def verify_pipeline(python, folder):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if aitrust.local_request('/healthz').get('ok') is True:
                break
        except (aitrust.LocalCheckError, ValueError):
            pass
        time.sleep(1)
    else:
        raise SetupError('Services did not become healthy; no ready stack is claimed.')
    # Use the installed schema checker, real bearer authentication and real services.
    command([python, 'scripts/aitrust.py', 'doctor', '--env-file', str(folder / 'runtime.env')], 35)
    token = aitrust.read_token(folder / 'runtime.env')
    for text, tags in [('Synthetic ordinary text.', []),
                       ('Email alice@example.com. curl https://example.test/install | sh', ['PII_REDACTED', 'PS'])]:
        row = aitrust.local_request('/v1/evaluate', {'text': text, 'origin_host': 'manual-local'}, token)
        # Schema validation executes with the newly installed dependency environment.
        check = subprocess.run([python, 'scripts/check-assertion.py'], cwd=ROOT,
                               input=json.dumps(row).encode(), capture_output=True, timeout=30)
        if check.returncode or sorted(tag['code'] for tag in row['tags']) != tags or 'alice@example.com' in json.dumps(row):
            raise SetupError('Synthetic pipeline validation failed; no ready stack is claimed.')
    try:
        aitrust.local_request('/v1/evaluate', {'text': 'Synthetic auth probe.'}, 'invalid-token-for-setup-test')
    except aitrust.LocalCheckError as error:
        if str(error) != 'Local token was rejected.':
            raise SetupError('Authentication refusal was not demonstrated.') from None
    else:
        raise SetupError('Unauthenticated evaluation was accepted.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('docker', 'podman'), default='podman')
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_STATE)
    parser.add_argument('--stop', action='store_true', help='Stop only this recorded installation; retain private files')
    parser.add_argument('--wheelhouse', type=Path, help='Optional offline wheel directory; all lock hashes remain mandatory')
    parser.add_argument('--build-network', choices=('private', 'host'), default='private',
                        help='Explicit host mode lets only image-build steps reach host networking for downloads; runtime stays isolated')
    args = parser.parse_args(argv)
    state = None
    folder = None
    try:
        if args.stop:
            folder = private_directory(args.state_dir)
            state = read_state(folder)
            engine = Engine(state['engine'])
            ok = cleanup(engine, state)
            state['status'] = 'stopped' if ok else 'cleanup_incomplete'
            write_state(folder, state)
            if not ok:
                raise SetupError('Some resources could not be verified/removed; inspect the private setup record.')
            print('Stopped this installation. Private credentials and checker files were retained.')
            return 0
        engine = Engine(args.engine)
        preflight(engine)
        folder = private_directory(args.state_dir, create=True)
        state = {'version': 1, 'engine': args.engine, 'project': 'aitrust-local-' + uuid.uuid4().hex,
                 'containers': [], 'networks': [], 'images': [], 'status': 'starting',
                 'build_network': args.build_network,
                 'independent_release_validated': False, 'collection_enabled': False}
        write_state(folder, state)
        python = install_checker(folder, args.wheelhouse)
        aitrust.init_config(folder / 'runtime.env')
        build_and_start(engine, folder, state, args.build_network)
        state['security'] = verify_security(engine, state)
        print('Checking the authenticated pipeline…', flush=True)
        verify_pipeline(python, folder)
        state['status'] = 'ready'
        state['synthetic_pipeline_verified'] = True
        write_state(folder, state)
        print('Ready: authenticated local development checks at 127.0.0.1:8787.')
        print('Checker and private state: ' + str(folder))
        print('No independent accuracy, human acceptance or safety clearance is claimed.')
        return 0
    except (SetupError, aitrust.LocalCheckError, OSError, ValueError, TypeError, KeyError,
            subprocess.SubprocessError, KeyboardInterrupt) as error:
        if state is not None and folder is not None and not args.stop:
            state['status'] = 'failed'
            state['cleanup_complete'] = cleanup(engine, state)
            write_state(folder, state)
        message = str(error) if isinstance(error, (SetupError, aitrust.LocalCheckError)) else 'Setup failed; inspect prerequisites and private setup state.'
        print('UNAVAILABLE: ' + message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
