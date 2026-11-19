# Optional NLI model and runtime notice/source review

This finite cohort reads the existing pinned English cross-encoder model record
and both complete optional runtime locks. It preserves actual wheel notices and
versioned official source references. It does not install packages, run model
code, change services or fetch resources during verification.

```sh
python3 scripts/verify-nli-license-cohort.py
python3 scripts/verify-nli-license-cohort.py --wheel-mac /private/mac-wheels --wheel-linux /private/linux-wheels
python3 scripts/verify-nli-license-cohort.py --require-distribution-ready
```

The first command checks retained source, notice and obligation consistency. The
second additionally hashes and CRC-checks the actual locked ZIPs and reproduces
their notice/source/native inventory without extracting or executing them. Only
that replay substantiates archive bytes. The third exits 1 while distribution
obligations remain unresolved. A successful consistency check is not a grant of
permission. Existing observations cannot be overwritten by collection.

EOCD and actual central-directory entry count/size bounds are checked before
ZipFile allocates its filelist. ZIP64 central directories/EOCD, multidisk and
inconsistent framing are outside this finite wheel profile. Local ZIP64 size
extras are accepted only when both sizes exactly match the bounded classic
central record; this includes redundant extras present in the locked Linux
protobuf wheel. Raw local/central names must agree and be safe before ZipInfo
normalizes them. No tar or sdist parser is used.

The checked manifest is `sbom/reviews/nli/manifest.json`. Its deterministic
`THIRD-PARTY-NOTICES.txt` bundle includes retained original texts, model/base
declarations and source references. Newly discovered original notice texts have
their own digests; existing notice blobs are reused when bytes match. Hashes and
HTTPS observations identify the retained bytes, not an authenticated publisher,
complete licensing clearance or independent model accuracy.

The prior inventory missed ONNX Runtime's root `LICENSE` and
`ThirdPartyNotices.txt` and additional NumPy notice members. The tokenizers and
flatbuffers wheels contain no matched notice file; version-pinned official
source license texts are separately retained and identified as such. They are
not represented as files originally present in those wheels.

For source Python packages the record binds actual source-form presence and
notice-retention actions. Tqdm includes MPL-covered Python source and its
MIT/MPL notice; covered Source Code Form must remain available under MPL with
the prescribed notice. Native runtime components keep distinct unresolved
bundled-library/source obligations. In particular, ml_dtypes retains Eigen MPL
terms, Linux NumPy carries BLAS/Fortran binaries, and ONNX's NOTICE identifies
additional bundled projects. These cannot be cleared from a package's headline
license expression.

ONNX Runtime's actual third-party text contains MPL/source-offer language and an
Intel MKL Simplified Software License. Presence in a broad notice file does not
establish that MKL is linked into the selected CPU wheel. Exact applicability,
bundled code and source/build correspondence remain unresolved. The observed
official tag/release and advertised short-commit source lookups returned 404;
no unpinned `main` source is substituted and an offline check does not repeat or
reinterpret those historical requests.

The pinned fine-tuned model card declares Apache-2.0 and names Microsoft's
DeBERTa base without its exact revision. Hugging Face explicitly supports
repository licensing through card metadata, so this is real publisher licensing
evidence for the pinned repository assets. The observed repository trees contain
no separate license file; that is a packaging fact, not an automatic prohibition.
A pinned current base card declares MIT, and a related Microsoft DeBERTa source
MIT license is retained. Those references do not establish the exact base
revision used in training or turn related-code terms into proof about that
particular pretrained snapshot. The manifest preserves this scope limit rather
than claiming unrestricted rights or rejecting the explicit publisher license.
See [Hugging Face licensing semantics](https://huggingface.co/docs/hub/repositories-licenses).
Training datasets
named in the card are not among the four downloaded assets and are not treated
as data redistributed by this tool. Python and OS are external prerequisites.

Before any distribution-ready claim, review the recorded model/base scope limits
and resolve each native entry's retained blocker, supply applicable source/relinking materials
and integrate the checked notice bundle into the actual distribution. This
cohort does not adopt a new global route policy or close F-057/X-02. It issues
no NF/FI/HP/PS tag, accuracy claim or qualified legal clearance.
