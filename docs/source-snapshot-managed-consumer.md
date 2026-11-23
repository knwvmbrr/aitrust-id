# Managed whole-source verification with a finite PS exercise

Architecture recorded before implementation: 2026-11-23T18:16:00.619353+00:00

Isolated branch codex/managed-source-consumer, protected base6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd. Implements only tools/source_snapshot_managed.py, scripts/verify-managed-source.py, tests/test_source_snapshot_managed.py, this guide and own evidence/attribution. ROOT separately owns release policy, archive/Git adapter, V2 artifact IO, producer workflow and publication. No image branch/runtime, shared policy or selected evidence changes.

## Trust and execution order

The caller separately selects the source archive, packet, SPDX, Sigstore bundle, trust-root file, trusted local Git checkout and exact commit. None is an execution command. Require a non-Git owner-private0700 output parent and absent final summary, then capture the public evidence into one exclusive held nofollow0700 private stage. Stream the archive through Capture.artifact into a0600 staged file (64,000,000B bound); never pass it through the16MB read API. Capture packet/SPDX/bundle at16MB each, roots at5MB; all caller and staged descriptors/ancestors stay held.

Call the REAL artifacts.authorize_release for literal source-snapshot with the captured copies and separately selected trusted Git/commit. No verifier, runner, callback or allow flag exists in the production consumer API. Require exact AUTHORIZED/sourcecommit/artifactdigest/policy-admitted/attestation-verified result before any archive source member is materialized or executed. The foundational adapter must establish whole canonical archive↔trusted Git bytes and current source-copy rights. Source6d currently refuses that route; ROOT integration supplies the reviewed adapter/V2 and actual protected signing later. Unit authorization substitutions are engineering controls, never real signature proof.

After authorization, read exactly the current nine PS source-package files plus root NOTICE from the trusted checkout and the installed consumer checkout; require equality. Stream the captured canonical single-gzip/USTAR archive under existing64MBcompressed/256MBsource/16,384file/32MBmember/5MBmetadata limits and a60-second extraction deadline. Reject PAX/links/duplicates/trailing/unsupported framing. Retain only those ten fixed members, each≤2MB and aggregate≤6MB, and match every retained byte to its trusted local cohort and metadata hash. Never extract all files, import archive modules into the parent, or use a received pathname as a command. Preserve source notices.

Materialize the fixed cohort at predetermined single-component names under held nofollow0700 directories; files0600/no overwrite. No recursive stage deletion on success or failure: private archive/evidence/cohort remain for inspection. No package or dependency installation, live service, endpoint, SDK or model.

Use only fixed synthetic positive, negative and invalid-UTF8 probes. The owned bounded supervisor starts a fixed Python environment-reset/exec shim; it execs (same PID, no descendant supervisor) sys.executable -I -S -B at the exact check-ps.py --worker path. Current --worker is pure canonical projection, with no nested PS supervisor. A trusted installed canonical worker supplies full positive/negative reference records; candidate and reference share one10-second per-probe deadline/16KiB output cap. Require exact closed record parity, correct subject/method/flags and invalid-input nonzero/no stdout. No inspected curl command is executed, no arbitrary text/path/model/config is accepted as probe input.

Before final summary, recheck source/evidence/parents/retained stage, rehash archive, and rerun current packet/policy/source verification through the real artifact API. No second signature invocation is necessary while held captured evidence is unchanged. Publish one private0600 no-overwrite bounded summary through Capture.save, then recheck through context close. Any post-publication uncertainty must explicitly disclose that final summary/private bytes may remain; never silently retry or delete a successor.

## Risks and limits

The trusted local checkout and installed consumer code are operator trust roots; arbitrary source archives do not select either. The default route may refuse until ROOT integration; there is no fallback authorization. Captured fixed source and immediate pre/post checks detect supported substitutions; no universal hostile same-UID, parent SIGKILL, host-crash or secure-memory-erasure guarantee. The PS workers contain no networking in this selected reviewed cohort; this is not a general-purpose OS sandbox. Per-probe process groups are killed/reaped on deadline/fault. Failed/private stages are intentionally retained.

Authenticated source copying and these three synthetic PS exercises do not establish detector accuracy, a safe code verdict, native/model/platform rights, all14 route obligations or full F-057/X-02 closure. Unrelated tag routes and packages are not consulted. Actual protected-main signing/whole-current-source consumer evidence remains a ROOT integration task.

## Planned focused acceptance

No materialization/probe on authorization refusal; ten exact files only; real stdlib positive/negative/invalid-source probes after an explicitly substituted unit authority; archive/frame/cohort tamper refusals; streaming >16MB input capture; source/parent/stage/.git drift; no-overwrite, late publication uncertainty and FD closure; actual CLI help/fixed refusal/no input echo. No actual signature pass is claimed from injected authority.

## Use after ROOT source-route integration

The caller must already possess the separately selected publisher archive, exact packet/SPDX/bundle and trusted verification roots, plus the trusted Git commit checkout. This tool does not download, approve a policy or install dependencies. Prepare a canonical (non-symlink) owner-private0700 output directory outside every Git checkout; the summary path must not exist. Then run:

```sh
python3 -I -S -B scripts/verify-managed-source.py \
  --artifact /private/owned/source.tar.gz \
  --packet /private/owned/packet.json \
  --spdx /private/owned/spdx.json \
  --bundle /private/owned/bundle.json \
  --trusted-root /private/owned/separately-selected-roots.jsonl \
  --trusted-git-root /trusted/exact-checkout \
  --source-commit EXACT_40_LOWERCASE_HEX_COMMIT \
  --output /private/owned/verification/summary.json
```

Exit0 means actual authorization and the finite probes completed. Exit2 is Unavailable; no accepted final summary was published, but hidden `.source-managed-*` private stages may remain beside the output for inspection. Exit3 is publication uncertainty: a summary and private bytes may exist; inspect before retrying. An existing destination is never overwritten. Stages are deliberately retained even on success, including the full captured archive and its source/grant notices. The summary reports only public artifact/evidence/cohort digests and fixed synthetic case states, not private paths or inspected user text. No user-text probe interface exists. It is a point-in-time observation, not protection against later owner modification.

At this protected base the actual source-snapshot route is blocked; normal CLI input cannot bypass that. ROOT separately integrates the trusted-Git/copy adapter, updated rightsV2 and protected producer before any real source-snapshot authorization can succeed. Focused tests substitute only that external authority function inside tests to exercise the genuine finite-source/stdlib subprocess path; they do not create a real attestation or managed permission.

Focused controls (no SDK/model/service/browser):

```sh
python3 -I -S -B -m unittest discover -s tests -p test_source_snapshot_managed.py -v
```

Initial19-case test execution had one author assertion-index error after the real finite probes completed; the production authorizer call was correct. The failure is preserved and only that test index was corrected. An additional actual write-fault descriptor-ownership control covers the new writer; final current execution is recorded separately.

## Pre-code disk-reserve correction amendment

Recorded 2026-11-23T18:27:34.373547+00:00. ROOT/source review found a missing resource preflight: staged writes could begin before the existing managed-consumer reserve was checked. The previous20-case/source proof stays immutable as the prior candidate. Before changing feature code, declare this exact repair: require shutil.disk_usage(output_parent).free at least2*1024**3+128*1024**2, after held private output-parent/no-overwrite validation and BEFORE public-input capture, stage creation or writing. Keep all archive/packet/member/extraction/process caps unchanged. Add one focused group proving threshold-minus-one creates no stage, authorization, probe or summary, and equality reaches authorization. Run that affected group first, then one complete frozen21-case execution. No actual disk exhaustion, package/model/native/SDK/network or infrastructure action.

### Decoder buffer precision amendment

Recorded before repair: 2026-11-23T18:28:18.000745+00:00. Separate review found the64KiB buffer prose exceeded its implementation: a partially consumed buffer could receive another64KiB chunk, giving a bounded~128KiB transient peak. Tighten each decompression request to the unused portion of the original64KiB buffer, without raising any source/expanded/CPU limit or changing framing. Add a real zlib tracked-peak subcontrol to the existing metadata/member-boundary method, retaining21 methods. Preserve the earlier source candidate/proofs; run that affected method before final frozen21-case execution.

### Final reserve amendment before complete current execution

Recorded 2026-11-23T18:28:47.380253+00:00. ROOT and separate review require a stricter current allowance:2GiB+256MiB free BEFORE staging. The consumer may stage64+48+5+6MB and the nested authorizer may add64+16+5+16MB; their~224MB combined named maxima fit within256MiB while preserving2GiB. This supersedes the earlier128MiB proposed allowance; no processing/source/member/output cap increases. Add an exact threshold constant assertion to the same low-capacity method. No final21-case execution has yet been performed, so its proof will bind only this final guard.
