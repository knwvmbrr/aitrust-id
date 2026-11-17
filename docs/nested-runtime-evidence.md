# Python standard library notices for the bundled runtime

The Pyodide 314.0.7 npm tarball contains a Python 3.14.2 standard library
archive. The inventory replays its exact lock-pinned parent and checks the
archive and runtime metadata against the existing asset observations. It
records all 614 entries, including 559 Python modules, eight auxiliary
files and 47 directories. The archive was read to verify lengths, CRCs and
hashes. No archived source was extracted, imported or executed.

Run the offline consistency check or replay the cached tarball.

```sh
python3 scripts/verify-nested-runtime.py
python3 scripts/verify-nested-runtime.py --runtime-archive /path/to/pinned-pyodide.tgz
```

Only the second command replays the archive bytes. It accepts the exact
current npm lockfile artifact and makes no network requests. For an export,
add `--export-notices` and a new directory in an owner-private parent outside
the checkout. The export preserves existing files.

## What travels with the runtime

The derived [stdlib notice bundle](../sbom/nested-runtime/PYTHON-STDLIB-NOTICES.txt)
contains source and attribution declarations, retained module headers and
their notice texts. It preserves the MagicStack uvloop acknowledgement for
the three explicitly marked asyncio modules and a matching MIT grant and
holder for the four explicitly marked tomllib modules. The tomllib text comes
from the separately retained setuptools-vendored Tomli notice. The matching
grant and holder do not establish package-version equivalence. For macholib,
the bundled README retains the MIT-or-PSF declaration and four module hashes
match files listed under macholib in CPython’s release SPDX record. Its source
archive URL and digest are upstream declarations. The SPDX conclusion remains
`NOASSERTION`.

The web build checks the exact size and SHA-256 of all five staged Pyodide
files before adding the notice to the four existing runtime and Unicode
notices. The licensing page links to the fifth file and the existing
offline worker caches it as a public release asset. Policy version 1.11
downloads retain their original bytes. The actual reference renderer and
offline packager ran against an isolated generated output fixture with the
five real pinned runtime files. The [execution record](../runs/2026-11-17-nested-runtime-obligations.json)
keeps that test separate from a full website build, browser session or
deployment. The native resource packager still needs to consume the same
checked bytes and verify every copy in a fresh archive.

## Remaining F-057 and X-02 acceptance

F-057 requires an SBOM and Sigstore release signing with versioned success and
failure evidence. The protected-main **development source** signing and
download verification already execute. A release claim for a shipped artifact
still needs a reviewed SBOM with artifact/source identities and attestation
of the actual release bytes. The historic Linux inventories and signed
development downloads cover their own recorded artifacts.

X-02 requires a release-configuration, claims and code review that prevents
closed-source or paid personal-pipeline dependencies, or records an explicit
product decision for a conflict. The existing architecture distinguishes
processing dependencies from commercial hosting and owner-chosen platforms.
The new check removes the one known uninspected archive from the npm native
inventory review and enforces its source and notice retention. It leaves the
original package, architecture, source-offer and conflict-policy criteria open.

| Remaining criterion | Evidence already available | Next executable check or outstanding decision |
| --- | --- | --- |
| Runtime OS and Python obligations | Three Linux amd64 image inventories bind to source and preserve upstream notices. | Reconcile exact installed package/version/license terms, including missing declarations and native linkage. Observe additional released runtime architectures from their own image/install-root identities. Do not extrapolate from the amd64 images. |
| Client/build npm and native alternatives | Both locks and all 205 archives have exact inventory/replay evidence. Of 63 packages without a matched notice-name file, Pyodide now has a separate runtime-specific binding. | Bind first-party package notice terms, upstream source and exact platform artifact relationships. Start with 26 esbuild 0.28.1 MIT, 15 rolldown 1.2.13 MIT and five workerd 1.20261006.1 Apache-2.0 platform packages. Resolve the remaining wrappers individually. For the ten Sharp libvips 1.3.4 platform artifacts, map each component/version and LGPL/GPL or other terms to its exact source recipes, notices and applicable distribution obligations. |
| Runtime WASM and source offers | The stdlib ships source and preserves versioned Pyodide/CPython references. The WASM bytes are pinned. | Verify the Pyodide 314.0.7 build recipes, embedded library versions and version-matched source for the exact WASM distribution. Fetch and verify declared source archives where needed. Determine required offer/relinking material for shipped components and check that the actual distribution includes it. A version link alone cannot establish corresponding source. |
| Model, manifest SDK, font and data assets | Nunito Sans OFL and frozen Unicode notice/asset relationships already pass. The pinned optional NLI model card declares Apache-2.0, names its DeBERTa base and training datasets, and is bound to the model revision. NLI and optional manifest SDK have Linux x86_64 and macOS arm64 artifact profiles. | Review the pinned base/model license and notice terms against the distributed model artifacts. Record the distinction between user-downloaded optional assets and bundled bytes. Confirm wheel/SDK bundled-native terms and any data actually redistributed. No need to rerun inference to review these terms or to treat all training datasets as shipped assets. |
| Full conflict-policy enforcement | Existing source-bound checks reject altered inventories; complete clearance is still refused. | Bind reviewed package and route decisions to exact manifests, release configuration and public claims. Execute allowed and refused cases for an unknown, unresolved, prohibited or paid required dependency. If a conflict cannot be removed in engineering, only an explicit authorized product decision can accept the exception. |
| Release SBOM and attestation | Protected-main Sigstore development-source signatures already verify with a separate trust root. | Run artifact-specific inventory, signing and detached verification when the actual release artifact is eligible. Do not substitute the earlier signed source snapshot or count an owner-dependent store gate as passed. |

Neither original criterion specifies qualified legal clearance as a separate
gate. The evidence records technical license and release controls. A
remaining interpretation or product exception requires a decision only when
the applicable terms or boundary cannot be resolved from the scoped evidence.
No global requirement milestone changes with this increment.

[CPython 3.14.2 license and acknowledgements](https://github.com/python/cpython/blob/v3.14.2/Doc/license.rst) ·
[CPython 3.14.2 SPDX inventory](https://github.com/python/cpython/blob/v3.14.2/Misc/sbom.spdx.json) ·
[Pyodide 314.0.7 source and recipes](https://github.com/pyodide/pyodide/tree/314.0.7).
