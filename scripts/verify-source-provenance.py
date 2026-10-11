#!/usr/bin/env python3
"""Authenticate a development source download using separately trusted offline evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import tarfile
from source_snapshot import COMMIT, MAX_ARCHIVE, inspect, read_file, unique

REPO = 'knwvmbrr/aitrust-id'
WORKFLOW = REPO + '/.github/workflows/ci.yml'
IDENTITY = 'https://github.com/' + WORKFLOW + '@refs/heads/main'
PREDICATE = 'https://slsa.dev/provenance/v1'


def verify(artifact, bundle, trusted_root, commit, runner=subprocess.run):
    if not COMMIT.fullmatch(commit):
        raise ValueError('Expected exact source commit required from a trusted channel')
    captures = {
        'source.tar.gz': read_file(artifact, MAX_ARCHIVE),
        'bundle.json': read_file(bundle, 5_000_000),
        'trusted-root.jsonl': read_file(trusted_root, 5_000_000),
    }
    raw = captures['source.tar.gz']
    # gh and archive inspection consume the same captured bytes. Original paths
    # are never handed to the external verifier after capture.
    with tempfile.TemporaryDirectory(prefix='aitrust-source-verification-') as temporary:
        stage = Path(temporary).resolve(strict=True)
        stage.chmod(0o700)
        for name, data in captures.items():
            fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o400)
        argv = ['gh', 'attestation', 'verify', str(stage / 'source.tar.gz'),
                '--bundle', str(stage / 'bundle.json'),
                '--custom-trusted-root', str(stage / 'trusted-root.jsonl'),
                '--repo', REPO,
                '--cert-identity', IDENTITY, '--cert-oidc-issuer',
                'https://token.actions.githubusercontent.com',
                '--source-digest', commit, '--source-ref', 'refs/heads/main',
                '--deny-self-hosted-runners', '--predicate-type', PREDICATE,
                '--format', 'json']
        completed = runner(argv, capture_output=True, timeout=120, check=False)
        if (completed.returncode or not isinstance(completed.stdout, bytes)
                or not 0 < len(completed.stdout) <= 5_000_000):
            raise ValueError('Cryptographic provenance or identity verification refused')
        for name, expected in captures.items():
            if read_file(stage / name, len(expected)) != expected:
                raise ValueError('Captured verification input changed')
    verified = json.loads(completed.stdout, object_pairs_hook=unique)
    digest = hashlib.sha256(raw).hexdigest()
    if not isinstance(verified, list) or not verified or len(verified) > 30:
        raise ValueError('Missing verified provenance')
    for result in verified:
        v = result['verificationResult']
        statement = v['statement']
        if (not v.get('verifiedTimestamps') or statement['predicateType'] != PREDICATE
                or not any(s.get('digest') == {'sha256': digest}
                           for s in statement['subject'])):
            raise ValueError('Witnessed source digest missing')
    # No archive content is interpreted until cryptographic verification succeeds.
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'kind': 'authenticated_development_source_snapshot',
            'repository': REPO, 'signer_workflow': WORKFLOW,
            'expected_certificate_identity': IDENTITY, 'offline_inputs': True,
            'captured_inputs_verified': True,
            'bundle_sha256': hashlib.sha256(captures['bundle.json']).hexdigest(),
            'trusted_root_sha256': hashlib.sha256(captures['trusted-root.jsonl']).hexdigest(),
            'independent_tag_accuracy_evidence': False, 'license_cleared': False,
            **inspect(raw, commit)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('artifact', type=Path)
    p.add_argument('--bundle', required=True, type=Path)
    p.add_argument('--trusted-root', required=True, type=Path)
    p.add_argument('--commit', required=True)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    result = verify(a.artifact, a.bundle, a.trusted_root, a.commit)
    if a.output:
        with a.output.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, EOFError, RecursionError,
            tarfile.TarError, subprocess.SubprocessError) as error:
        print('Source verification refused: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
