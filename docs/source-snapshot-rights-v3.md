# Finite source-copy additions V3

This checker classifies a caller-selected committed source tree against the exact protected `6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd` base and individually reviewed additions. It preserves V1, V2, their tables and their execution history. Source-copy grants do not establish compiled runtime rights, model/data rights, accuracy, legal clearance or release authorization.

The base is mandatory. Optional copied material is accepted only at its exact reviewed Git mode, blob identity, size and raw SHA-256, with every applicable carried grant and author notice present at its exact identity. An unresolved origin refuses whenever its copied material is present. New project-authored paths are individually named and inspected under the existing attribution/declaration rules. An unknown path refuses before the tree is divided into classification phases.

## Check a selected source tree

Run from a checkout containing the frozen checker and its pinned inputs:

```sh
python3 -I -S -B tools/source_release_policy_v3.py --source-commit FULL_COMMIT_ID
```

The selected commit must descend from the exact protected base. The source tree comes from independently selected local Git objects, with replacement objects and lazy fetching disabled. A successful result reports `SOURCE_COPY_PROFILE_SATISFIED`, the full file/byte denominator, source tree identity and exact checker/table identities. `selected_source_protected_release_claimed` is true only for the fixed protected base; a candidate is not described as a protected release.

An unknown, changed or unresolved input reports `UNAVAILABLE` with a fixed diagnostic code and exit status 2. It does not print supplied text, private filesystem paths or raw Git errors. Unavailable must not be interpreted as permission.

## Bind an existing archive to that source

```sh
python3 -I -S -B tools/source_release_policy_v3.py --source-commit FULL_COMMIT_ID --archive /PRIVATE/OWNED/source.tar.gz
```

The source-copy classification runs first. Only after it passes does the captured, SHA-pinned canonical archive binder compare every received source member to the selected Git tree and its actual blob bytes. The checker does not extract or execute received source. A coherent forged manifest and source member still refuse if they disagree with Git.

A successful composed result is `COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND`. Signature verification, release authorization, source-route admission and all broader rights/accuracy claims remain false. The separate managed-release verifier must establish its own trusted repository, protected producer identity, exact artifact/SBOM and current consumer requirements; a received archive cannot approve itself.

## Integration interface and bounds

`tools.source_release_policy_v3` provides `verify(root=ROOT, source_commit=None)` and `verify_archive(raw: bytes, *, source_commit: str)`, plus `PROFILE`, `MAX_FILES`, `MAX_TOTAL`, `MAX_ARCHIVE`, `OID` and `FALSE_CLAIMS`. The first result uses `files` and `source_bytes`; the composed result uses `source_files`, `source_bytes`, `source_tree`, `archive_sha256` and `archive_bytes`.

The checker captures V2 into a private namespace and does not modify V2 globals, the module cache, its policy arrays, the neutral worker or any serializer. The entire classification shares one 30-second deadline, one 2,000,000-byte per-inspected-blob limit and one 64,000,000-byte aggregate inspection budget. Cached, already verified bytes are reused within that same budget. Whole-tree limits remain 16,384 files and 256,000,000 raw source bytes; each file is at most 32,000,000 bytes. The compressed archive is at most 64,000,000 bytes, with the existing separate 5,000,000-byte metadata limit. The composed operation retains its 95-second envelope, at most 60 seconds for binding and a 4 KiB fixed summary.

The additions table is a finite trust input, not a package-name or path-prefix allowlist. Updating it requires review of exact new source facts, required grants and source identities. Its table SHA is pinned in the checker. Existing observations retain their original timestamps and source identities; a later candidate needs its own committed-tree and archive proof.

The current finite table contains135 individually named project paths and93 exact copied rows, including39 publisher metadata files and43 full grant/author texts. Its160-name parser ceiling grants no permission to an unlisted path. The remaining11 copied rows preserve the separately reviewed UFD/CLIP/torchvision code, terms and factual references. The reviewed producer removes the modified HF card whose additional prose had no established grant, keeps the original MIT CLIP card, and supplies a factual URL/revision/hash reference instead. The removed prose is not excluded from a received archive by filtering: any unlisted reappearance refuses.

Three exact generated-metadata transitions retain their original categories and origins. A source selection uses either all three old records with the actual old dependency-policy code, or all three reviewed new producer outputs with the actual new code and exact producer-evidence record. Complete typed JSON differences are limited to the two producer hash leaves and the corresponding derived SPDX namespace. Package lists, grants, notice spans, runtime facts, claims and limitations must remain unchanged. The original producer observations and their execution times remain historical; this checker does not rerun or relabel them.
