#!/usr/bin/env python3
"""Credential-context static worker; inspected source is data, never executed."""
import errno
from pathlib import Path
import platform
import resource
import sys
ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))
from tools import credential_flow_context as tool

def linux_network_filter():
    """Adapt existing research/nli/network.py mechanism; no NLI import/dependency."""
    import ctypes
    tool.require(platform.machine() in ('x86_64', 'aarch64'))
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    signatures = {'seccomp_init': ([ctypes.c_uint32], ctypes.c_void_p),
        'seccomp_attr_set': ([ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32], ctypes.c_int),
        'seccomp_syscall_resolve_name': ([ctypes.c_char_p], ctypes.c_int),
        'seccomp_rule_add': ([ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint], ctypes.c_int),
        'seccomp_load': ([ctypes.c_void_p], ctypes.c_int), 'seccomp_release': ([ctypes.c_void_p], None),
        'seccomp_arch_native': ([], ctypes.c_uint32)}
    for name, (args, result) in signatures.items():
        function = getattr(lib, name); function.argtypes = args; function.restype = result
    tool.require(lib.seccomp_arch_native() == {'x86_64': 0xc000003e, 'aarch64': 0xc00000b7}[platform.machine()])
    context = lib.seccomp_init(0x7fff0000)
    tool.require(bool(context))
    try:
        tool.require(lib.seccomp_attr_set(context, 3, 1) == 0 and lib.seccomp_attr_set(context, 4, 1) == 0)
        denied = ('socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
                  'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
                  'getsockopt', 'setsockopt', 'getsockname', 'getpeername', 'shutdown',
                  'io_uring_setup', 'io_uring_enter', 'io_uring_register')
        for name in denied:
            number = lib.seccomp_syscall_resolve_name(name.encode('ascii'))
            tool.require(number >= 0 and lib.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0) == 0)
        tool.require(lib.seccomp_load(context) == 0)
    finally:
        lib.seccomp_release(context)
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    tool.require(fields.get('NoNewPrivs', '').strip() == '1' and fields.get('Seccomp', '').strip() == '2')


def sandbox():
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if platform.system() == 'Linux':
        resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
        linux_network_filter()
        control = 'linux_seccomp_deny_network'
    else:
        tool.require(platform.system() == 'Darwin')
        control = 'macos_sandbox_deny_network'
    # Probe only synthetic loopback endpoints before receiving example bytes.
    import socket
    for family, address in ((socket.AF_INET, ('127.0.0.1', 9)), (socket.AF_INET6, ('::1', 9))):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.settimeout(1)
                probe.connect(address)
        except PermissionError as failure:
            tool.require(failure.errno == errno.EPERM)
        else:
            tool.require(False)
    return control


def main():
    try:
        control=sandbox()
        raw=sys.stdin.buffer.read(tool.MAX_REQUEST_BYTES+1)
        request=tool.parse(raw,tool.MAX_REQUEST_BYTES)
        tool.require(type(request) is dict and set(request)=={'code','source_sha256'})
        code=request['code']
        tool.require(type(code) is str and bool(code.strip()) and '\0' not in code
                     and len(code)<=tool.MAX_CODE_CHARACTERS and len(code.encode())<=32000
                     and tool.normalize_nfc(code)==code)
        with tool.io.Capture() as capture:
            sources=tool.identity(capture)
            tool.require(request['source_sha256']==sources)
            from tools import credential_flow
            observation=credential_flow.observe(code)
            capture.check()
        value={'request_sha256':tool.sha(raw),'source_sha256':sources,'network_control':control,
               'ipv4_ipv6_denied':True,'observation':observation}
        output=tool.io.encoded(value)
        tool.require(len(output)<=tool.MAX_RESULT_BYTES)
        sys.stdout.buffer.write(output+b'\n');return 0
    except Exception:
        print('{"state":"UNAVAILABLE"}');return 2


if __name__=='__main__':raise SystemExit(main())
