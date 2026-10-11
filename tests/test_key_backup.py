"""Run offline custody controls without claiming actual nontechnical-user acceptance."""
from pathlib import Path
import subprocess
import os
import pty
import select
import shutil
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]


def test_offline_key_backup_controls():
    result = subprocess.run(['node', '--test', '--test-reporter=tap', 'tests/key-backup.cjs'],
                            cwd=ROOT, capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert b'# fail 0' in result.stdout


def interact(arguments, entries):
    """Drive a real pseudo-terminal with disposable synthetic passwords only."""
    master, slave = pty.openpty()
    before = termios.tcgetattr(slave)
    child = subprocess.Popen([shutil.which('node'), 'scripts/key-backup.cjs', *arguments],
                             cwd=ROOT, stdin=slave, stdout=slave, stderr=slave,
                             close_fds=True)
    transcript = bytearray()
    try:
        cursor = 0
        for prompt, reply in entries:
            deadline = time.monotonic() + 8
            while prompt not in transcript[cursor:]:
                if time.monotonic() >= deadline:
                    raise AssertionError('Hidden input prompt unavailable')
                if select.select([master], [], [], 0.1)[0]:
                    transcript.extend(os.read(master, 16384))
            cursor = len(transcript)
            os.write(master, reply)
        child.wait(timeout=8)
        while select.select([master], [], [], 0.1)[0]:
            transcript.extend(os.read(master, 16384))
        assert termios.tcgetattr(slave) == before, 'Terminal mode was not restored'
        return child.returncode, bytes(transcript)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        os.close(master)
        os.close(slave)


def test_actual_terminal_hidden_password_roundtrip_and_cancellation():
    with tempfile.TemporaryDirectory(prefix='aitrust-custody-pty-') as raw:
        folder = Path(raw).resolve()
        private, public, backup, restored = [folder / name for name in
                                            ('private.pem', 'public.pem', 'backup.json', 'restored.pem')]
        generated = subprocess.run(['node', 'scripts/receipt.cjs', 'keygen', 'Ed25519',
                                    str(private), str(public)], cwd=ROOT, capture_output=True)
        assert generated.returncode == 0
        password = b'Synthetic terminal recovery password'
        code, transcript = interact(['backup', str(private), str(backup)],
                                    [(b'Choose a strong backup password (hidden): ', password + b'\r'),
                                     (b'Repeat the same password (hidden): ', password + b'\r')])
        assert code == 0 and password not in transcript
        code, transcript = interact(['restore', str(backup), str(public), str(restored)],
                                    [(b'Backup password (hidden): ', password + b'\r')])
        assert code == 0 and password not in transcript
        assert restored.read_bytes() == private.read_bytes()
        cancelled = folder / 'cancelled.json'
        code, transcript = interact(['backup', str(private), str(cancelled)],
                                    [(b'Choose a strong backup password (hidden): ', b'\x03')])
        assert code == 2 and not cancelled.exists()
        mismatch = folder / 'mismatch.json'
        code, transcript = interact(['backup', str(private), str(mismatch)],
                                    [(b'Choose a strong backup password (hidden): ', password + b'\r'),
                                     (b'Repeat the same password (hidden): ', b'Different synthetic password\r')])
        assert code == 2 and password not in transcript and not mismatch.exists()
