#!/usr/bin/env python3
"""Internal NF pipe worker; canonical observations, bounded resources, no network."""
import errno
import json
from pathlib import Path
import platform
import resource
import sys

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT))
from tools import nf_source_evidence as nf


def linux_network_filter():
    """Adapt existing research/nli/network.py mechanism; no NLI import/dependency."""
    import ctypes
    nf.require(platform.machine() in ('x86_64', 'aarch64'))
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    signatures = {'seccomp_init': ([ctypes.c_uint32], ctypes.c_void_p),
        'seccomp_attr_set': ([ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32], ctypes.c_int),
        'seccomp_syscall_resolve_name': ([ctypes.c_char_p], ctypes.c_int),
        'seccomp_rule_add': ([ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint], ctypes.c_int),
        'seccomp_load': ([ctypes.c_void_p], ctypes.c_int), 'seccomp_release': ([ctypes.c_void_p], None),
        'seccomp_arch_native': ([], ctypes.c_uint32)}
    for name, (args, result) in signatures.items():
        function = getattr(lib, name); function.argtypes = args; function.restype = result
    nf.require(lib.seccomp_arch_native() == {'x86_64': 0xc000003e, 'aarch64': 0xc00000b7}[platform.machine()])
    context = lib.seccomp_init(0x7fff0000)
    nf.require(bool(context))
    try:
        nf.require(lib.seccomp_attr_set(context, 3, 1) == 0 and lib.seccomp_attr_set(context, 4, 1) == 0)
        denied = ('socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
                  'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
                  'getsockopt', 'setsockopt', 'getsockname', 'getpeername', 'shutdown',
                  'io_uring_setup', 'io_uring_enter', 'io_uring_register')
        for name in denied:
            number = lib.seccomp_syscall_resolve_name(name.encode('ascii'))
            nf.require(number >= 0 and lib.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0) == 0)
        nf.require(lib.seccomp_load(context) == 0)
    finally:
        lib.seccomp_release(context)
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    nf.require(fields.get('NoNewPrivs', '').strip() == '1' and fields.get('Seccomp', '').strip() == '2')


def sandbox():
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if platform.system() == 'Linux':
        resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
        linux_network_filter()
        control = 'linux_seccomp_deny_network'
    else:
        nf.require(platform.system() == 'Darwin')
        control = 'macos_sandbox_deny_network'
    # Probe only synthetic loopback endpoints before receiving example bytes.
    import socket
    for family, address in ((socket.AF_INET, ('127.0.0.1', 9)), (socket.AF_INET6, ('::1', 9))):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.settimeout(1)
                probe.connect(address)
        except PermissionError as failure:
            nf.require(failure.errno == errno.EPERM)
        else:
            nf.require(False)
    return control


def main():
    try:
        control = sandbox()
        raw = sys.stdin.buffer.read(nf.MAX_RESULT_BYTES + 1)
        request = nf.parse(raw, nf.MAX_RESULT_BYTES)
        nf.require(type(request) is dict and set(request) == {'component', 'pairs', 'source_sha256'})
        kind, pairs = request['component'], request['pairs']
        nf.require(type(kind) is str and kind in nf.CHECKS and type(pairs) is list and 1 <= len(pairs) <= nf.MAX_PAIRS)
        for pair in pairs:
            nf.require(type(pair) is dict and set(pair) == {'claim', 'passage'})
            for value in pair.values():
                nf.require(type(value) is str and value.strip() and '\0' not in value
                           and len(value) <= nf.MAX_PASSAGE_CHARACTERS and nf.normalize_nfc(value) == value)
        with nf.io.Capture() as capture:
            sources = nf.source_identity(capture, (*nf.COMMON, *nf.OPTIONAL[kind]))
            nf.require(request['source_sha256'] == sources)
            rows = nf.evaluate(kind, pairs)
            capture.check()
        result = {'component': kind, 'method': nf.METHODS[kind], 'request_sha256': nf.sha(raw),
                  'source_sha256': sources, 'network_control': control, 'ipv4_ipv6_denied': True, 'rows': rows}
        output = nf.io.encoded(result)
        nf.require(len(output) <= nf.MAX_RESULT_BYTES)
        sys.stdout.buffer.write(output + b'\n')
        return 0
    except Exception:
        print('{"state":"UNAVAILABLE"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
