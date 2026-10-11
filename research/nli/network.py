"""Linux worker-only network syscall denial using the system libseccomp."""
import ctypes,errno,platform
from pathlib import Path
from .pairs import PairError,require
DENIED=('socket','socketpair','connect','bind','listen','accept','accept4','sendto','sendmsg','sendmmsg','recvfrom','recvmsg','recvmmsg','getsockopt','setsockopt','getsockname','getpeername','shutdown','io_uring_setup','io_uring_enter','io_uring_register')

def install_linux_network_filter():
    require(platform.system()=='Linux' and platform.machine() in ('x86_64','aarch64'))
    # The loader uses the system soname with the worker's environment cleared.
    lib=ctypes.CDLL('libseccomp.so.2',use_errno=True)
    signatures={'seccomp_init':([ctypes.c_uint32],ctypes.c_void_p),'seccomp_attr_set':([ctypes.c_void_p,ctypes.c_int,ctypes.c_uint32],ctypes.c_int),'seccomp_syscall_resolve_name':([ctypes.c_char_p],ctypes.c_int),'seccomp_rule_add':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint],ctypes.c_int),'seccomp_load':([ctypes.c_void_p],ctypes.c_int),'seccomp_release':([ctypes.c_void_p],None),'seccomp_arch_native':([],ctypes.c_uint32)}
    for name,(args,result) in signatures.items():
        function=getattr(lib,name);function.argtypes=args;function.restype=result
    require(lib.seccomp_arch_native()=={'x86_64':0xc000003e,'aarch64':0xc00000b7}[platform.machine()])
    ctx=lib.seccomp_init(0x7fff0000);require(bool(ctx))
    try:
        require(lib.seccomp_attr_set(ctx,3,1)==0) # NO_NEW_PRIVS
        require(lib.seccomp_attr_set(ctx,4,1)==0) # synchronize existing threads
        for name in DENIED:
            number=lib.seccomp_syscall_resolve_name(name.encode('ascii'));require(number>=0)
            require(lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,number,0)==0)
        require(lib.seccomp_load(ctx)==0)
    finally:lib.seccomp_release(ctx)
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    require(fields.get('NoNewPrivs','').strip()=='1' and fields.get('Seccomp','').strip()=='2')
    return {'profile':'linux-worker-network-denial/1.0.0','mechanism':'system_libseccomp','native_architecture':platform.machine(),'no_new_privileges':True,'denied_syscalls':list(DENIED),'io_uring_denied':True,'existing_threads_synchronized':True}
