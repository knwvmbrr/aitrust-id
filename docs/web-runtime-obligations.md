# Selected browser runtime obligations

This engineering tool constructs and verifies the notices and source offers for the exact five-file Pyodide 314.0.7 browser runtime. It checks retained source facts independently of received indexes. It does not authorize a release, approve the whole website or clear F-057/X-02.

From a clean checkout, run:

```sh
python3 -I -S -B scripts/verify-web-runtime-obligations.py
```

The JSON result distinguishes retained fact verification from received-file verification. `received_files_verified: 0` means no received runtime artifact was checked. A missing or changed input returns exit 2 and a fixed Unavailable diagnostic.

To prepare companions, choose a new destination beneath an existing owner-private 0700 directory outside Git:

```sh
python3 -I -S -B scripts/verify-web-runtime-obligations.py --prepare /absolute/private/new-companions
```

This writes fourteen 0600 companion files. It neither fetches nor executes the runtime. Existing destinations are refused; an interrupted preparation can leave private files, which must be inspected before retrying. Failed private directories are retained instead of recursively deleted. No protection against a hostile concurrent same-user filesystem writer is claimed.

A received directory must contain exactly these selected directories and files:

| Directory | Required files |
| --- | --- |
| `runtime` | `pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json` |
| `runtime-js-sources` | `PYODIDE-JS-SOURCES.zip`, `NOTICES.txt`, `index.json` |
| `runtime-zlib-sources` | `ZLIB-SOURCES.zip`, `NOTICES.txt`, `index.json` |
| `device-licenses` | `pyodide-MPL-2.0.txt`, `python-license.txt`, `source.txt`, `unicode-license.txt`, `python-stdlib-notices.txt` |
| `runtime-obligations` | `HIWIRE-SOURCES.zip`, `NOTICES.txt`, `obligations.json` |

The runtime bytes must be the pinned publisher files, not a newly rebuilt or substituted interpreter. After placing those five files in `runtime`, check the complete selection:

```sh
python3 -I -S -B scripts/verify-web-runtime-obligations.py --artifact-dir /absolute/private/received-selection
```

Success reports nineteen received files. Every companion is compared with trusted source-derived expected bytes. An altered index cannot approve altered payloads or promote a permission flag. Extra, missing, changed, linked, stale or unknown selected members refuse. Files elsewhere in a larger website distribution are outside this verifier and still require a complete website consumer.

The existing eleven companion files retain their exact bytes and formats. The new Hiwire offer contains the exact preferred source/header/build files at 6a1e67280a15d929ebeceee54a6358c9c8d5f697, two upstream patches, full MPL-2.0 text, publisher obtain information and the parent build/patch context. The complete unmodified Pyodide source archive remains in the existing JS offer, including its nine applied CPython patches. No source is fetched when checking or preparing these files.

Additional notices preserve actual CPython Expat/mpdecimal/HACL terms, conditional mimalloc attribution, libffi MIT copyright holders, the XZ public-domain library distinction, Zstd's selected BSD alternative and adapted xxhash copyright, plus the exact Emscripten/musl/LLVM/MiniLZ4/filesystem terms. Source-header and recipe evidence remain distinct from observed runtime versions and binary object membership. HACL's exact project Apache license and per-file MIT/AND declarations are carried together; its exact upstream NOTICE request returned404. Full LLVM embedding exceptions and musl's limited header/crt waiver are not presented as blanket waivers.

The 614-member stdlib inventory is reused only through the unchanged pinned ZIP hash and immutable member table; this tool does not pretend to perform a new compiler reproduction or runtime execution. The exact React remove-scroll-bar 2.3.8 publisher source facts are retained separately as a project-wide unversioned MIT correspondence inference. They do not make React part of this five-file runtime, relabel the associated 2.3.7 Git context or approve all website packages.

There is one 60-second operation budget: 128 byte-returning reads, 64 MB logical reads, 16 MB retained cache, 8 MB generated outputs and 128 held descriptors. The 123,314,272-byte reservation describes logical payload buffers, not measured RSS. Legacy producer and archive limits remain unchanged. Optional receipt publication uses `--output /absolute/private/new-receipt.json`; it refuses Git ancestry and existing output names. No SDK, model, native code, network, credential or signing operation is required.
