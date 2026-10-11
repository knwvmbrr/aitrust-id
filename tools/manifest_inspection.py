"""Optional bounded attached-manifest inspection; never an origin or truth tag."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import struct
import subprocess
import sys
import tempfile
import zlib

from protocol.corpus import CorpusError, read_regular

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'attached-c2pa-inspection/1.0.1'
MAX_ASSET_BYTES = 10 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
DEADLINE_SECONDS = 12
SETTINGS = {'version': 1, 'verify': {'verify_after_reading': True,
    'verify_trust': True, 'verify_timestamp_trust': True,
    'remote_manifest_fetch': False, 'ocsp_fetch': False},
    'core': {'allowed_network_hosts': [], 'decode_identity_assertions': False}}
PIN_FILE = ROOT / 'eval/dependencies/c2pa-inspection.json'


def png_container(raw):
    """Conservative structural limits before entering a native parser."""
    if len(raw) > MAX_ASSET_BYTES or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise CorpusError('Only bounded PNG containers are supported.')
    offset, chunks, image_data = 8, 0, False
    while offset + 12 <= len(raw):
        size = struct.unpack('>I', raw[offset:offset+4])[0]
        kind = raw[offset+4:offset+8]
        end = offset + 12 + size
        if end > len(raw) or not re.fullmatch(b'[A-Za-z]{4}', kind) or chunks >= 4096:
            raise CorpusError('PNG chunk boundaries are unsupported.')
        data = raw[offset+8:end-4]
        if zlib.crc32(kind+data) != struct.unpack('>I', raw[end-4:end])[0]:
            raise CorpusError('PNG chunk integrity failed.')
        if chunks == 0:
            if kind != b'IHDR' or size != 13:
                raise CorpusError('PNG header is unsupported.')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if not width or not height or width * height > 16_000_000 or depth not in depths.get(color, ()) or compression or filtering or interlace not in (0, 1):
                raise CorpusError('PNG dimensions or encoding are unsupported.')
        elif kind == b'IHDR':
            raise CorpusError('Repeated PNG header.')
        if kind == b'IDAT':
            image_data = True
        if kind == b'IEND':
            if size or end != len(raw) or not image_data:
                raise CorpusError('PNG end boundary is unsupported.')
            return
        chunks += 1
        offset = end
    raise CorpusError('PNG container is incomplete.')


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError('Duplicate report field.')
        result[key] = value
    return result


def decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(CorpusError('Non-finite report value.')))
    except (ValueError, UnicodeError, RecursionError):
        raise CorpusError('Invalid bounded SDK report.') from None


def checked_sdk():
    """Check wrapper/native bytes before importing the optional native SDK."""
    pins = decode(read_regular(PIN_FILE, 20000))
    if (not isinstance(pins, dict) or pins.get('schema_version') != 1 or
            pins.get('package') != 'c2pa-python' or pins.get('package_version') != '0.38.0' or
            pins.get('sdk_version') != '0.91.0' or not isinstance(pins.get('profiles'), dict)):
        raise CorpusError('Unsupported SDK pin contract.')
    profile = platform.system().lower() + '-' + platform.machine().lower()
    if profile not in pins['profiles']:
        raise CorpusError('SDK platform is unsupported.')
    expected_native = {'darwin-arm64': 'c2pa/libs/libc2pa_c.dylib',
        'linux-x86_64': 'c2pa/libs/libc2pa_c.so'}.get(profile)
    selected = pins['profiles'][profile]
    required = {'c2pa/__init__.py', 'c2pa/build.py', 'c2pa/c2pa.py', 'c2pa/lib.py', expected_native}
    if (not expected_native or not isinstance(selected, dict) or selected.get('native') != expected_native or
            not isinstance(selected.get('sources'), dict) or set(selected['sources']) != required or
            any(not isinstance(h, str) or not re.fullmatch('[a-f0-9]{64}', h) for h in selected['sources'].values())):
        raise CorpusError('Unsupported SDK source inventory.')
    try:
        distribution = importlib.metadata.distribution('c2pa-python')
    except importlib.metadata.PackageNotFoundError:
        raise CorpusError('Optional pinned SDK is not installed.') from None
    if distribution.version != pins['package_version']:
        raise CorpusError('SDK version differs from the reviewed pin.')
    package = distribution.locate_file('c2pa')
    if package.is_symlink() or any(p.is_symlink() for p in package.parents):
        raise CorpusError('SDK symlink is unsupported.')
    for relative, expected in selected['sources'].items():
        path = distribution.locate_file(relative)
        if not path.resolve().is_relative_to(package.resolve()):
            raise CorpusError('SDK source escapes its distribution.')
        raw = read_regular(path, 40 * 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise CorpusError('SDK source differs from its reviewed pin.')
    return str(distribution.locate_file(pins['profiles'][profile]['native'])), pins


def load_verified_sdk():
    """Import the checked package by absolute path, never by checkout lookup."""
    if any(name == 'c2pa' or name.startswith('c2pa.') for name in sys.modules):
        raise CorpusError('A preloaded SDK is unsupported.')
    native, pins = checked_sdk()
    package = Path(native).parent.parent
    initializer = package / '__init__.py'
    # The CLI adds ROOT to load our protocol. Do not offer that directory, a
    # descendant or the worker's current directory to SDK/transitive imports.
    cwd = Path.cwd().resolve()
    trusted_site = package.parent.resolve()
    sys.path[:] = [entry for entry in sys.path if entry and
        (Path(entry).resolve() == trusted_site or
         (not Path(entry).resolve().is_relative_to(ROOT.resolve()) and
          Path(entry).resolve() != cwd))]
    spec = importlib.util.spec_from_file_location('c2pa', initializer,
        submodule_search_locations=[str(package)])
    if spec is None or spec.loader is None:
        raise CorpusError('The checked SDK cannot be loaded.')
    module = importlib.util.module_from_spec(spec)
    sys.modules['c2pa'] = module
    os.environ['C2PA_LIBRARY_NAME'] = native
    try:
        spec.loader.exec_module(module)
    except BaseException:
        for name in list(sys.modules):
            if name == 'c2pa' or name.startswith('c2pa.'):
                del sys.modules[name]
        raise
    return module, pins


def status_groups(value):
    if not isinstance(value, dict) or set(value) - {'success', 'informational', 'failure'}:
        raise CorpusError('Unsupported validation group.')
    result = {}
    for group in ('success', 'informational', 'failure'):
        rows = value.get(group, [])
        if not isinstance(rows, list) or len(rows) > 2048:
            raise CorpusError('Unsupported validation rows.')
        codes = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('code'), str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', row['code']):
                raise CorpusError('Unsupported validation code.')
            codes.append(row['code'])
        result[group] = codes
    return result


def summarize(report, subject):
    if not isinstance(report, dict):
        raise CorpusError('Unsupported SDK report.')
    active, manifests, validation = report.get('active_manifest'), report.get('manifests'), report.get('validation_results')
    if not isinstance(active, str) or not isinstance(manifests, dict) or active not in manifests or not isinstance(validation, dict) or 'activeManifest' not in validation:
        raise CorpusError('Full active-manifest validation results are required.')
    if len(manifests) > 32 or not isinstance(manifests[active], dict):
        raise CorpusError('Manifest inventory is unsupported.')
    assertions = manifests[active].get('assertions', [])
    if not isinstance(assertions, list) or len(assertions) > 2048:
        raise CorpusError('Assertion inventory is unsupported.')
    groups = status_groups(validation['activeManifest'])
    ingredients = validation.get('ingredientDeltas', [])
    if not isinstance(ingredients, list) or len(ingredients) > 32:
        raise CorpusError('Ingredient inventory is unsupported.')
    ingredient_groups = []
    for item in ingredients:
        if not isinstance(item, dict) or 'validationDeltas' not in item:
            raise CorpusError('Ingredient validation is unsupported.')
        ingredient_groups.append(status_groups(item['validationDeltas']))
    def observation(positive, negative):
        # A failure wins even if a malformed provider includes both outcomes.
        if negative in groups['failure']:
            return 'mismatched'
        if positive in groups['success']:
            return 'matched'
        return 'unknown'
    return {'state': 'OBSERVED', 'method': METHOD,
        'asset_sha256': hashlib.sha256(subject).hexdigest(), 'asset_bytes': len(subject),
        'attached_manifest_count': len(manifests), 'active_assertion_count': len(assertions),
        'active_validation': groups,
        'ingredient_validation': ingredient_groups,
        'asset_binding': observation('assertion.dataHash.match', 'assertion.dataHash.mismatch'),
        'claim_signature': observation('claimSignature.validated', 'claimSignature.mismatch'),
        'signer_trust': 'untrusted' if 'signingCredential.untrusted' in groups['failure'] else
            'reported_trusted' if 'signingCredential.trusted' in groups['success'] else 'unknown',
        'revocation': 'reported_revoked' if 'signingCredential.ocsp.revoked' in groups['failure'] else 'unknown_skipped',
        'tags': [], 'content_truth_established': False,
        'author_identity_established': False, 'independent_accuracy_evidence': False,
        'sharing_warning': 'The asset hash can link a private file. Raw embedded metadata is omitted.'}


def worker():
    """Own child only: fixed stdin bytes, fixed per-reader settings, bounded output."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_REPORT_BYTES, MAX_REPORT_BYTES))
    if sys.platform == 'linux':
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    raw = sys.stdin.buffer.read(MAX_ASSET_BYTES + 1)
    png_container(raw)
    import io
    c2pa, pins = load_verified_sdk()
    if c2pa.__version__ != pins['package_version'] or c2pa.sdk_version() != pins['sdk_version']:
        raise CorpusError('Loaded SDK version differs from the reviewed pin.')
    try:
        with c2pa.Context.from_dict(SETTINGS) as context:
            with c2pa.Reader('image/png', io.BytesIO(raw), context=context) as reader:
                report = reader.json().encode('utf-8')
        if len(report) > MAX_REPORT_BYTES:
            raise CorpusError('SDK report exceeds the byte limit.')
        # Verify full result shape before forwarding private raw bytes to parent.
        summarize(decode(report), raw)
        output = {'kind': 'attached', 'report': decode(report)}
    except c2pa.C2paError.ManifestNotFound:
        output = {'kind': 'not_found'}
    encoded = json.dumps(output, ensure_ascii=True, allow_nan=False).encode()
    if len(encoded) > MAX_REPORT_BYTES:
        raise CorpusError('SDK report exceeds the byte limit.')
    sys.stdout.buffer.write(encoded)


def inspect(path, runner=subprocess.run):
    raw = read_regular(path, MAX_ASSET_BYTES)
    png_container(raw)
    # Check without importing the SDK in the parent; no subject supplied to it.
    native, _ = checked_sdk()
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'C2PA_LIBRARY_NAME': native}
    with tempfile.TemporaryDirectory(prefix='aitrust-c2pa-') as directory:
        os.chmod(directory, 0o700)
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            try:
                completed = runner([sys.executable, '-I', '-B', str(ROOT/'scripts/inspect-manifest.py'), '--worker'],
                    input=raw, cwd=directory, env=environment, stdout=output, stderr=errors,
                    timeout=DEADLINE_SECONDS, check=False)
            except (OSError, subprocess.TimeoutExpired):
                raise CorpusError('Native inspection was unavailable or timed out.') from None
            if completed.returncode:
                raise CorpusError('Native inspection failed; no valid evaluation was obtained.')
            output.seek(0)
            value = decode(output.read(MAX_REPORT_BYTES+1))
            if output.tell() > MAX_REPORT_BYTES:
                raise CorpusError('Native output exceeds the byte limit.')
    if not isinstance(value, dict) or set(value) not in ({'kind'}, {'kind', 'report'}):
        raise CorpusError('Unsupported native envelope.')
    if value['kind'] == 'not_found' and set(value) == {'kind'}:
        return {'state': 'NOT_FOUND', 'method': METHOD, 'asset_sha256': hashlib.sha256(raw).hexdigest(),
            'asset_bytes': len(raw), 'revocation': 'not_applicable', 'tags': [],
            'content_truth_established': False, 'author_identity_established': False,
            'sharing_warning': 'No attached manifest was found; this does not establish origin or safety. The hash can link a private file.'}, None
    if value['kind'] != 'attached' or 'report' not in value:
        raise CorpusError('Unsupported native envelope.')
    return summarize(value['report'], raw), value['report']


def save_private(report, output):
    """Explicit new full-report file only; preserve owner-private path boundary."""
    output = Path(output).expanduser().absolute()
    if output.resolve().is_relative_to(ROOT) or any(p.is_symlink() for p in (output.parent, *output.parent.parents)):
        raise CorpusError('Keep private reports outside the source checkout.')
    info = output.parent.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise CorpusError('Use an existing owner-private 0700 directory.')
    raw = json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2).encode()
    if len(raw) > MAX_REPORT_BYTES:
        raise CorpusError('Private report exceeds the byte limit.')
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise CorpusError('Choose a new private output file.') from None
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
