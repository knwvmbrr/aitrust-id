"""Read-only JPEG credential/action inspection; no tag or origin inference."""
from contextlib import ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import struct
import sys
from tools.jpeg_provenance_io import Source, Refused, need
from tools.jpeg_provenance_process import run, MAX_REQUEST, MAX_REPORT
from tools import jpeg_provenance_actions as actions
from tools import jpeg_provenance_sdk as loader

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE = 10*1024*1024
SOURCES = ('tools/jpeg_provenance.py', 'tools/jpeg_provenance_io.py',
    'tools/jpeg_provenance_process.py', 'tools/jpeg_provenance_sdk.py',
    'tools/jpeg_provenance_actions.py', 'scripts/inspect-jpeg-provenance.py',
    loader.JPEG, loader.PIN, 'eval/c2pa-inspection.lock', 'LICENSE', 'NOTICE')


def encoded(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('ascii')


def public_certificates(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 65536, 'trust_input_unsupported')
    blocks = re.findall(rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----', raw)
    need(1 <= len(blocks) <= 4 and re.sub(rb'\s+', b'', b''.join(blocks)) == re.sub(rb'\s+', b'', raw), 'trust_input_unsupported')
    return raw.decode('ascii')


def make_request(raw, roots):
    header = encoded({'profile': actions.PROFILE, 'asset_bytes': len(raw),
                      'asset_sha256': hashlib.sha256(raw).hexdigest(), 'trust_bytes': len(roots),
                      'trust_sha256': hashlib.sha256(roots).hexdigest()})
    need(len(header) <= 4096)
    return struct.pack('>I', len(header))+header+roots+raw


def read_request():
    raw = sys.stdin.buffer.read(MAX_REQUEST+1)
    need(4 < len(raw) <= MAX_REQUEST, 'input_limit')
    size = struct.unpack('>I', raw[:4])[0]
    need(0 < size <= 4096 and 4+size <= len(raw), 'invalid_request')
    header = loader.decode(raw[4:4+size])
    need(type(header) is dict and set(header) == {'profile', 'asset_bytes', 'asset_sha256', 'trust_bytes', 'trust_sha256'}
         and header['profile'] == actions.PROFILE and type(header['asset_bytes']) is int
         and 0 < header['asset_bytes'] <= MAX_IMAGE and type(header['trust_bytes']) is int
         and 0 <= header['trust_bytes'] <= 65536
         and len(raw) == 4+size+header['trust_bytes']+header['asset_bytes'], 'invalid_request')
    roots, image = raw[4+size:4+size+header['trust_bytes']], raw[4+size+header['trust_bytes']:]
    need(hashlib.sha256(image).hexdigest() == header['asset_sha256']
         and hashlib.sha256(roots).hexdigest() == header['trust_sha256'], 'invalid_request')
    return image, roots


def worker():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_REPORT, MAX_REPORT))
    if sys.platform == 'linux':
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    image, roots = read_request()
    loader.preflight(image)
    # Reader settings are scoped to this invocation; no process-global test root.
    settings = {**loader.SETTINGS, 'verify': dict(loader.SETTINGS['verify']), 'core': dict(loader.SETTINGS['core'])}
    with ExitStack() as stack:
        c2pa, profile, pins = loader.sdk(stack)
        if roots:
            pem = public_certificates(roots)
            from cryptography import x509
            certs = x509.load_pem_x509_certificates(roots)
            need(1 <= len(certs) <= 4 and all(c.extensions.get_extension_for_class(x509.BasicConstraints).value.ca for c in certs), 'trust_input_unsupported')
            settings['trust'] = {'trust_anchors': pem}
        try:
            with c2pa.Context.from_dict(settings) as context:
                with c2pa.Reader('image/jpeg', io.BytesIO(image), context=context) as reader:
                    text = reader.json()
                    need(type(text) is str and len(text) <= MAX_REPORT, 'report_limit')
                    raw_report = text.encode('utf-8'); need(len(raw_report) <= MAX_REPORT, 'report_limit')
                    report = loader.decode(raw_report)
            actions.project(report)
            value = {'kind': 'attached', 'report': report, 'sdk_profile': profile, 'sdk_sources': pins}
        except c2pa.C2paError.ManifestNotFound:
            value = {'kind': 'not_found', 'sdk_profile': profile, 'sdk_sources': pins}
    raw = encoded(value); need(len(raw) <= MAX_REPORT, 'report_limit')
    sys.stdout.buffer.write(raw)


def inspect(path, *, trust_anchors=None):
    """No executable/URL/remote-resource parameter. Source identities rechecked."""
    with ExitStack() as stack:
        sources = {name: stack.enter_context(Source(ROOT/name, 200000)) for name in SOURCES}
        need(sources[loader.JPEG].sha256 == loader.JPEG_SHA and sources[loader.PIN].sha256 == loader.PIN_SHA, 'source_changed')
        image = stack.enter_context(Source(path, MAX_IMAGE))
        geometry = loader.preflight(image.raw)
        roots = stack.enter_context(Source(trust_anchors, 65536)) if trust_anchors is not None else None
        if roots:
            public_certificates(roots.raw)
        request = make_request(image.raw, roots.raw if roots else b'')
        private = loader.decode(run([sys.executable, '-I', '-B', str(ROOT/'scripts/inspect-jpeg-provenance.py'), '--worker'], request))
        if type(private) is dict and set(private) == {'kind', 'reason'} and private['kind'] == 'unavailable':
            need(type(private['reason']) is str and private['reason'] in actions.REASONS, 'report_unsupported')
            raise Refused(private['reason'])
        need(type(private) is dict and private.get('kind') in ('attached', 'not_found'), 'report_unsupported')
        need(set(private) == ({'kind', 'sdk_profile', 'sdk_sources', 'report'} if private['kind'] == 'attached'
                              else {'kind', 'sdk_profile', 'sdk_sources'}), 'report_unsupported')
        pins = loader.decode(sources[loader.PIN].raw)
        need(type(private['sdk_profile']) is str and private['sdk_profile'] in pins['profiles']
             and private['sdk_sources'] == pins['profiles'][private['sdk_profile']]['sources'], 'sdk_pin_mismatch')
        if private['kind'] == 'attached':
            result = actions.project(private['report'])
        else:
            result = actions.base('NOT_FOUND', 'no_attached_manifest')
            result['revocation'] = 'not_applicable'
        result.update(asset={'encoding': 'image/jpeg', 'sha256': image.sha256, 'bytes': len(image.raw),
                              'identity': 'encoded_file_bytes_not_decoded_pixels', 'header': geometry},
            trust_context={'mode': 'caller_public_anchors' if roots else 'pinned_sdk_default',
                           'anchors_sha256': roots.sha256 if roots else None,
                           'remote_manifest_fetch': False, 'ocsp_fetch': False},
            implementation={name: source.sha256 for name, source in sources.items()},
            sdk={'package': 'c2pa-python', 'version': '0.38.0', 'native_version': '0.91.0',
                 'profile': private['sdk_profile'], 'sources': private['sdk_sources']},
            sharing_warning='The encoded-file and anchor hashes can link copies. Raw metadata is omitted.')
        for source in sources.values():
            source.check()
        image.check()
        if roots:
            roots.check()
        need(len(encoded(result)) <= 32768, 'report_limit')
    # Context/descriptor teardown must complete before any result is released.
    return result


def text_result(value):
    lines = ['AI TRUST ID · JPEG credential details']
    if value['state'] == 'UNAVAILABLE':
        lines += ['Unavailable: this file, encoding, optional SDK or check could not be used.',
                  'Reason: '+value['reason']+'.']
    elif value['state'] == 'NOT_FOUND':
        lines += ['No attached Content Credential was found.']
    else:
        lines += ['Image binding: '+{'matched':'matches the recorded bytes.', 'mismatched':'does not match the recorded bytes.', 'unknown':'Unknown.'}[value['asset_binding']],
                  'Record signature: '+{'matched':'matches.', 'mismatched':'does not match.', 'unknown':'Unknown.'}[value['claim_signature']],
                  'Signer trust: '+{'untrusted':'not trusted by this reader context.', 'sdk_reported_trusted':'reported trusted within this reader context.', 'unknown':'Unknown.'}[value['signer_trust']],
                  'Revocation: '+('reported revoked.' if value['revocation'] == 'reported_revoked' else 'Unknown. Online checks are disabled.')]
        kinds = {x['kind'] for x in value['declarations']}
        if 'generative_creation_declared' in kinds:
            lines += ['Bound recorded declaration: a creation action claims generative AI use.']
        if 'generative_edit_declared' in kinds:
            lines += ['Bound recorded declaration: an editing action claims generative AI use.']
        if not kinds:
            lines += ['No supported, bound action declaration was established.']
        lines += ['Declarations are signed statements, not independently established image origin.',
                  'Complete history and content truth are not verified.']
    lines += ['No metadata, names, paths or file hashes are shown here.',
              'AI origin: Unknown. No FA or PA tag issued.']
    return '\n'.join(lines)
