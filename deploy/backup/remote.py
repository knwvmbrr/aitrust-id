#!/usr/bin/env python3
"""Forced SSH command: only the pgBackRest remote protocol, never a shell."""
import os
import pwd
import shlex
import sys

ALLOWED_COMMANDS = {
    "backup", "check", "info", "archive-push", "archive-get", "stanza-create", "expire"
}
ALLOWED_OPTIONS = {
    'exec-id', 'lock', 'log-level-console', 'log-level-file', 'log-level-stderr',
    'pg1-path', 'pg1-port', 'pg1-socket-path', 'process', 'remote-type', 'stanza',
    'command', 'repo1-path', 'repo', 'repo1-cipher-type', 'repo1-cipher-pass',
    'compress-type', 'compress-level', 'compress-level-network', 'process-max',
    'archive-timeout', 'io-timeout', 'protocol-timeout', 'buffer-size', 'start-fast',
    'type', 'neutral-umask', 'sck-keep-alive', 'priority'
}


def validate(command):
    args = shlex.split(command)
    if len(args) < 4 or args[0] not in {"pgbackrest", "/usr/bin/pgbackrest"}:
        raise ValueError("Only pgBackRest remote protocol is permitted")
    modern = args[-1].split(':')
    if args[-1] != 'remote' and (len(modern) != 2 or modern[1] != 'remote' or modern[0] not in ALLOWED_COMMANDS):
        raise ValueError("Remote operation is not authorized")
    options = args[1:-1]
    if not all(arg.startswith("--") and "\x00" not in arg for arg in options):
        raise ValueError("Unexpected remote protocol argument")
    names = [arg[2:].split('=', 1)[0] for arg in options]
    if any(name not in ALLOWED_OPTIONS for name in names):
        raise ValueError('Remote option is not authorized')
    pairs = [arg[2:].split("=", 1) for arg in options if "=" in arg]
    single = [pair for pair in pairs if pair[0] != 'lock']
    if len({pair[0] for pair in single}) != len(single):
        raise ValueError("Duplicate option is not permitted")
    values = dict(pairs)
    operation = values.get('command') if args[-1] == 'remote' else modern[0]
    if 'command' in values and values['command'] != operation:
        raise ValueError("Conflicting command option")
    if values.get("stanza") != "aitrustid" or operation not in ALLOWED_COMMANDS:
        raise ValueError("Stanza or command is not authorized")
    if values.get("remote-type") not in {"repo", "pg"}:
        raise ValueError("Remote type is not authorized")
    for key, value in {'pg1-path':'/var/lib/postgresql/18/main',
                       'pg1-socket-path':'/var/run/postgresql',
                       'repo1-path':'/var/lib/pgbackrest'}.items():
        if key in values and values[key] != value:
            raise ValueError('Remote path is not authorized')
    if any(arg.startswith(("--config=", "--config-path=", "--config-include-path=")) for arg in options):
        raise ValueError("Client configuration override is not permitted")
    return ["/usr/bin/pgbackrest", *options, args[-1]]


if __name__ == "__main__":
    try:
        argv = validate(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
        account = pwd.getpwuid(os.geteuid()).pw_name
        expected = {'pgbackrest':'repo', 'postgres':'pg'}.get(account)
        if expected is None or '--remote-type=' + expected not in argv:
            raise ValueError('Remote type does not match this service identity')
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(126)
    os.execv(argv[0], argv)
