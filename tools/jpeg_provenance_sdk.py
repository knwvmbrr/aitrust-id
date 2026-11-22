"""JPEG-only optional SDK verification. No import of sibling image tools."""
from contextlib import ExitStack
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
from tools.jpeg_provenance_io import Source, Refused, need

ROOT = Path(__file__).resolve().parents[1]
PIN = 'eval/dependencies/c2pa-inspection.json'
PIN_SHA = '28861a1b7035e42e8c40ffb4d14bf4dabc9b326e7f945a5bafe523c41f15c129'
JPEG = 'integrations/image-metadata-reference/1.0.0/tools/jpeg_metadata.py'
JPEG_SHA = 'c7e8fcb58acd2087a35c886a32b7df1fa390c74c52c023e9b137bdf1dd90872a'
SETTINGS = {'version': 1, 'verify': {'verify_after_reading': True,
    'verify_trust': True, 'verify_timestamp_trust': True,
    'remote_manifest_fetch': False, 'ocsp_fetch': False},
    'core': {'allowed_network_hosts': [], 'decode_identity_assertions': False}}


def decode(raw):
    need(type(raw) in (bytes, str) and len(raw) <= 4*1024*1024, 'report_limit')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, 'report_unsupported'); value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(Refused('report_unsupported')))
        # json's parser depth is not a resource policy; bound it explicitly too.
        pending = [(value, 0)]; count = 0
        while pending:
            item, depth = pending.pop(); count += 1
            need(depth <= 32 and count <= 50000, 'report_limit')
            if type(item) is dict:
                need(len(item) <= 4096, 'report_limit'); pending.extend((x, depth+1) for x in item.values())
            elif type(item) is list:
                need(len(item) <= 4096, 'report_limit'); pending.extend((x, depth+1) for x in item)
            elif type(item) is str:
                need(len(item) <= 262144, 'report_limit')
            elif type(item) is float:
                need(math.isfinite(item), 'report_unsupported')
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Refused('report_unsupported') from None


def preflight(raw):
    with Source(ROOT / JPEG, 100000) as source:
        need(source.sha256 == JPEG_SHA, 'source_changed')
        module = {'__file__': str(ROOT / JPEG), '__name__': 'jpeg_preflight_only'}
        # Exact immutable repository source, never caller-selected code.
        exec(compile(source.raw, str(ROOT / JPEG), 'exec'), module)
        try:
            value = module['inspect_bytes'](raw)
        except module['ImageError'] as error:
            raise Refused(error.reason) from None
        source.check()
        return value['image']


def sdk(stack):
    """Keep checked descriptor identities through reader destruction."""
    pins_source = stack.enter_context(Source(ROOT / PIN, 20000))
    need(pins_source.sha256 == PIN_SHA, 'source_changed')
    pins = decode(pins_source.raw)
    profile = platform.system().lower()+'-'+platform.machine().lower()
    need(profile in ('darwin-arm64', 'linux-x86_64'), 'sdk_platform_unsupported')
    selected = pins['profiles'][profile]
    try:
        distribution = importlib.metadata.distribution('c2pa-python')
    except importlib.metadata.PackageNotFoundError:
        raise Refused('sdk_unavailable') from None
    need(distribution.version == '0.38.0', 'sdk_pin_mismatch')
    need(not any(k == 'c2pa' or k.startswith('c2pa.') for k in sys.modules), 'sdk_preloaded')
    for path, expected in selected['sources'].items():
        source = stack.enter_context(Source(distribution.locate_file(path), 40*1024*1024))
        need(source.sha256 == expected, 'sdk_pin_mismatch')
    native = Path(distribution.locate_file(selected['native'])).absolute()
    package = native.parent.parent
    trusted_site = package.parent.resolve()
    cwd = Path.cwd().resolve()
    sys.path[:] = [entry for entry in sys.path if entry and
        (Path(entry).resolve() == trusted_site or
         (not Path(entry).resolve().is_relative_to(ROOT) and Path(entry).resolve() != cwd))]
    spec = importlib.util.spec_from_file_location('c2pa', package/'__init__.py',
        submodule_search_locations=[str(package)])
    need(spec is not None and spec.loader is not None, 'sdk_unavailable')
    module = importlib.util.module_from_spec(spec)
    sys.modules['c2pa'] = module
    os.environ['C2PA_LIBRARY_NAME'] = str(native)
    spec.loader.exec_module(module)
    need(module.__version__ == '0.38.0' and module.sdk_version() == '0.91.0', 'sdk_pin_mismatch')
    return module, profile, selected['sources']
