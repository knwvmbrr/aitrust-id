"""Verify a protected MCP release before installing or publishing its connection.

Uses foundational artifact authorization and the independent MCP runtime installer.
It never changes route permission, obtains trust roots, or accepts caller commands.
"""
import os
from pathlib import Path
import secrets
import shutil
import sys

from tools import distribution_artifacts as artifacts
from tools import mcp_distribution as runtime
from tools.artifact_evidence_io import (
    Capture, PrivateInputError, need, snapshot, verify_written,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'mcp-managed-connection/v1'
PROBE_IDS = (
    'exact_two_read_only_tools', 'implemented_capabilities_only',
    'canonical_full_record_finding_no_echo', 'no_finding_is_not_clearance',
    'missing_optional_privacy_preserves_ps', 'invalid_fields_refused_without_echo',
    'oversized_input_refused_without_echo', 'legacy_full_record_parity',
)


class ManagedReleaseUnavailable(PrivateInputError):
    """No new final connection was published; private intermediate bytes may remain."""
    output_may_exist = False
    private_bytes_may_remain = True

    def __init__(self):
        super().__init__('Managed MCP release unavailable.')


class ManagedReleaseUncertain(ManagedReleaseUnavailable):
    """Final connection publication/cleanup may have completed; inspect before retry."""
    output_may_exist = True


def _write(capture, directory_fd, name, raw):
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory_fd)
    capture.fds.append(fd)
    with os.fdopen(fd, 'wb', closefd=False) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(fd)
    verify_written(fd, raw)
    capture.files.append((directory_fd, name, fd, snapshot(os.fstat(fd))))


def _probe_valid(result, record):
    need(type(result) is dict and result.get('configuration_verified') is True
         and result.get('runtime_target_verified') is True
         and result.get('release_authorized') is False
         and result.get('sha256') == record['artifact']['sha256'])
    proof = result.get('runtime')
    need(type(proof) is dict and proof.get('pass') is True
         and proof.get('profile') == 'mcp-installed-synthetic-runtime-proof/v1'
         and proof.get('sdk_version') == '2.3.0'
         and type(proof.get('cases')) is list
         and len(proof['cases']) == len(PROBE_IDS))
    need(all(type(row) is dict and set(row) == {'id', 'status'}
             and row['id'] == expected and row['status'] == 'PASS'
             for row, expected in zip(proof['cases'], PROBE_IDS)))


def install_managed(artifact, packet, spdx, bundle, trusted_root, output, *,
                    source_commit, python=sys.executable, pip_python, root=ROOT):
    """Publish ordinary host connection JSON only after real managed authorization.

    Inputs are separately selected by the caller. The retained private stage is
    part of the installed workspace, not a public export. Failed stages are kept:
    filesystem replacement makes pathname recursive deletion unsafe. No rollback is promised after final publication.
    """
    stage = None
    final_may_exist = False
    capture = Capture()
    try:
        with capture:
            need(type(source_commit) is str and artifacts.COMMIT.fullmatch(source_commit))
            need(Path(python).is_absolute() and Path(pip_python).is_absolute())
            parent, output_name = capture.parent(output)
            try:
                os.stat(output_name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ManagedReleaseUnavailable()
            need(shutil.disk_usage(Path(output).absolute().parent).free
                 >= 2 * 1024**3 + 128 * 1024**2)
            # Capture before stage creation and never authorize one path then
            # install a differently reopened caller file. All later work uses
            # these exact copies in a held private directory.
            raws = {
                'packet.json': capture.read(packet, artifacts.MAX_PACKET, private=False),
                'spdx.json': capture.read(spdx, artifacts.MAX_PACKET, private=False),
                'bundle.json': capture.read(bundle, artifacts.MAX_PACKET, private=False),
                'roots.jsonl': capture.read(trusted_root, 5_000_000, private=False),
            }
            record = artifacts.parse(raws['packet.json'])
            name = '.mcp-managed-' + secrets.token_hex(16)
            os.mkdir(name, 0o700, dir_fd=parent)
            stage = Path(output).absolute().parent / name
            fd = capture.directory(stage)
            for name, raw in raws.items():
                _write(capture, fd, name, raw)
            # Stream the bounded archive without a second in-memory copy.
            archive_fd = os.open('artifact.zip', os.O_RDWR | os.O_CREAT | os.O_EXCL |
                                 os.O_NOFOLLOW, 0o600, dir_fd=fd)
            capture.fds.append(archive_fd)
            with os.fdopen(archive_fd, 'wb', closefd=False) as stream:
                value = capture.artifact(artifact, runtime.MAX_ARCHIVE, copy_to=stream)
                stream.flush()
                os.fsync(archive_fd)
            capture.files.append((fd, 'artifact.zip', archive_fd, snapshot(os.fstat(archive_fd))))
            need(value == record['artifact'])
            capture.check()
            authorized = artifacts.authorize_release(
                record, stage / 'artifact.zip', stage / 'spdx.json',
                stage / 'bundle.json', stage / 'roots.jsonl', 'mcp-stdio', source_commit, root)
            need(authorized.get('state') == 'AUTHORIZED'
                 and authorized.get('release_authorized') is True
                 and authorized.get('policy_admitted') is True
                 and authorized.get('attestation_verified') is True
                 and authorized.get('artifact_sha256') == value['sha256']
                 and authorized.get('source_commit') == source_commit)
            capture.check()
            connection = stage / 'verified-connection.json'
            runtime.install(stage / 'artifact.zip', connection, python=python,
                            pip_python=pip_python, root=root)
            checked = runtime.verify_install(stage / 'artifact.zip', connection,
                python=python, root=root, execute_probe=True)
            _probe_valid(checked, record)
            configuration = runtime.decode(capture.read(connection, 32_000))
            need(configuration.get('release_authorized') is False)

            def current():
                capture.check()
                artifacts.verify_packet(record, stage / 'artifact.zip', 'mcp-stdio',
                                        source_commit, root)
                # No second signature command: immutable captured evidence was
                # authenticated above. Repeat current installed payload/target
                # checks after the SDK exercise and just before publication.
                again = runtime.verify_install(stage / 'artifact.zip', connection,
                    python=python, root=root, execute_probe=False)
                need(again.get('configuration_verified') is True
                     and again.get('runtime_target_verified') is True)
                # Inode stability alone does not preserve the private export
                # boundary: a .git marker may have appeared during verification.
                capture.parent(output)
                capture.directory(stage)
                capture.check()

            # Standard MCP host JSON remains compatible with the developer
            # checker. Authorization is a separate result, never a changed
            # developer config flag masquerading as an authenticated verdict.
            try:
                capture.save(output, configuration, 32_000, prepublish=current)
            finally:
                final_may_exist = capture.output_may_exist
            return {'profile': PROFILE, 'state': 'INSTALLED',
                    'release_authorized': True, 'attestation_verified': True,
                    'artifact_sha256': value['sha256'], 'source_commit': source_commit,
                    'target': checked['target'], 'sdk_cases': len(PROBE_IDS),
                    'configuration_included_in_stdout': False,
                    'license_clearance': False, 'complete_project_obligations': False}
    except (OSError, ValueError, TypeError, KeyError, ImportError, OverflowError,
            RuntimeError, RecursionError, UnicodeError):
        if final_may_exist or capture.output_may_exist:
            raise ManagedReleaseUncertain() from None
        raise ManagedReleaseUnavailable() from None
