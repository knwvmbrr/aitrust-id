"""Optional RFC 3161 component: independent signed time, never authorship or VALID."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

PROFILE = 'independent-timestamp/freetsa-2026/1.0.0'
ENDPOINT = 'https://freetsa.org/tsr'
PINS = {'ca': '2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438',
        'tsa': '8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467'}
MAX_ARTIFACT = 32 * 1024 * 1024
MAX_EVIDENCE = 65536


def read(file, limit=MAX_EVIDENCE):
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        import stat
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_size > limit:
            raise ValueError('Unsupported file or size')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('File grew beyond its bound')
        return raw
    finally:
        os.close(fd)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def command(argv, runner=subprocess.run):
    r = runner(['openssl', *argv], capture_output=True, timeout=30, check=False,
               env={**os.environ, 'LC_ALL': 'C', 'OPENSSL_CONF': os.devnull})
    if r.returncode or len(r.stdout) > 262144 or len(r.stderr) > 262144:
        raise ValueError('Timestamp cryptography or prerequisite refused')
    return r.stdout


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Timestamp redirect refused')


def send(query):
    # A fixed documented provider, verified HTTPS, no credentials or proxy auth.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(ENDPOINT, data=query, method='POST',
                                headers={'Content-Type': 'application/timestamp-query',
                                         'Accept': 'application/timestamp-reply'})
    with opener.open(req, timeout=30) as response:
        if response.status != 200 or response.headers.get_content_type() != 'application/timestamp-reply':
            raise ValueError('Unsupported timestamp response')
        raw = response.read(MAX_EVIDENCE + 1)
    if not raw or len(raw) > MAX_EVIDENCE:
        raise ValueError('Timestamp response size refused')
    return raw


def authority(ca, tsa):
    raw_ca, raw_tsa = read(ca), read(tsa)
    if digest(raw_ca) != PINS['ca'] or digest(raw_tsa) != PINS['tsa']:
        raise ValueError('Separately trusted certificate pin mismatch')
    return raw_ca, raw_tsa


def verify_bytes(artifact, query, response, ca, tsa, runner=subprocess.run):
    if len(artifact) > MAX_ARTIFACT or not query or not response or max(len(query), len(response)) > MAX_EVIDENCE:
        raise ValueError('Timestamp input size refused')
    raw_ca, raw_tsa = authority(ca, tsa)
    # Snapshot all input bytes: OpenSSL sees these copies, never a mutable original.
    with tempfile.TemporaryDirectory(prefix='aitrust-ts-') as directory:
        root = Path(directory)
        for name, raw in [('query.tsq', query), ('response.tsr', response),
                          ('ca.pem', raw_ca), ('tsa.pem', raw_tsa)]:
            (root / name).write_bytes(raw)
        q, r, c, t, token = [str(root / name) for name in
                             ['query.tsq', 'response.tsr', 'ca.pem', 'tsa.pem', 'token.der']]
        query_text = command(['ts', '-query', '-in', q, '-text'], runner).decode('ascii')
        nonce = re.search(r'^Nonce: 0x([0-9A-Fa-f]+)$', query_text, re.M)
        if not nonce or int(nonce[1], 16) == 0 or 'Hash Algorithm: sha256' not in query_text:
            raise ValueError('SHA-256 request with nonce required')
        # ts does not support cms's -no-CApath/-no-CAstore switches. Explicitly
        # select all three trust sources; the directory has no hashed CA entries.
        common = ['ts', '-verify', '-in', r, '-CAfile', c, '-untrusted', t,
                  '-CApath', str(root), '-CAstore', c, '-check_ss_sig']
        command([*common, '-queryfile', q], runner)
        command([*common, '-digest', digest(artifact)], runner)
        command(['ts', '-reply', '-in', r, '-token_out', '-out', token], runner)
        command(['cms', '-verify', '-binary', '-inform', 'DER', '-in', token,
                 '-nointern', '-certfile', t, '-CAfile', c, '-no-CApath', '-no-CAstore',
                 '-purpose', 'timestampsign', '-check_ss_sig', '-out', os.devnull], runner)
        info = command(['ts', '-reply', '-in', r, '-text'], runner).decode('ascii')
        match = re.search(r'^Time stamp: (.+ GMT)$', info, re.M)
        if not match:
            raise ValueError('Signed authority time missing')
        stamp = match[1]
        fmt = '%b %d %H:%M:%S.%f %Y GMT' if '.' in stamp else '%b %d %H:%M:%S %Y GMT'
        moment = datetime.strptime(stamp, fmt).replace(tzinfo=timezone.utc)
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'profile': PROFILE, 'artifact_sha256': digest(artifact), 'artifact_bytes': len(artifact),
            'request_sha256': digest(query), 'response_sha256': digest(response),
            'authority_time': moment.isoformat(), 'authority': 'FreeTSA',
            'record_integrity': 'verified_under_separately_pinned_authority',
            'artifact_binding': 'matched', 'nonce_binding': 'matched',
            'authority_clock': 'authority_attested; not independently measured by AI Trust ID',
            'revocation': 'unchecked', 'authorship': 'unestablished',
            'certified_valid': False, 'tag_issuance': False,
            'independent_tag_accuracy_evidence': False, 'trust_sha256': dict(PINS)}


def verify(artifact, query, response, ca, tsa, runner=subprocess.run):
    return verify_bytes(read(artifact, MAX_ARTIFACT), read(query), read(response), ca, tsa, runner)


def issue(artifact, destination, ca, tsa, consent=False, transport=send, runner=subprocess.run):
    if consent is not True:
        raise ValueError('Explicit digest-sharing permission required')
    authority(ca, tsa)  # Refuse untrusted inputs before any provider contact.
    raw = read(artifact, MAX_ARTIFACT)
    destination = Path(destination).absolute()
    if destination.parent.resolve() != destination.parent or destination.exists():
        raise ValueError('New destination with a non-symlink parent required')
    query = command(['ts', '-query', '-digest', digest(raw), '-sha256', '-cert'], runner)
    # OpenSSL generates the request nonce; do not send an unbounded helper result.
    if not query or len(query) > MAX_EVIDENCE:
        raise ValueError('Timestamp request size refused')
    response = transport(query)
    result = verify_bytes(raw, query, response, ca, tsa, runner)
    destination.mkdir(mode=0o700)
    created = []
    try:
        import json
        for name, content in [('request.tsq', query), ('response.tsr', response),
                              ('verification.json', (json.dumps(result, indent=2) + '\n').encode())]:
            file = destination / name
            fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            created.append(file)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
    except BaseException:
        for file in created:
            file.unlink(missing_ok=True)
        destination.rmdir()
        raise
    return result
