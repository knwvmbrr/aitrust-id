# Read local image details without uploading the image

This experimental on-device preview inspects selected PNG and JPEG container
facts. It does not determine whether an image was made by AI, whether it is
true, who made it, or whether it is a valid/safe image. No tag is issued.
The full FA tag remains Planned: this optional helper supplies container facts,
not its origin claim. The existing C2PA SDK inspector remains a different tool.

## Use it

Open the **FA** modal and **Image details · preview**, choose an ordinary PNG or JPEG using the file
picker, then choose **Inspect image**. Selecting a file alone does not read its
contents or start a worker. Header dimensions and fixed metadata-section counts
appear after a supported check. Private embedded names, comments, GPS, URLs and
other stored values are never printed by this preview.

A section labelled Exif, XMP, ICC or JFIF is untrusted file content. A Content
Credential-shaped PNG section or opaque JPEG APP11 section is not a verified
credential. Missing sections establish neither human nor AI origin.

The default summary omits the file hash and filename. The native file picker can
show your selected filename locally. **Show exact image record** is optional:
its JSON includes the encoded-file SHA256 and byte length. That hash can link the
image to other copies. No automatic export or sharing is provided. An encoded-file
hash is not a canonical decoded-pixel identity.

**Clear image**, changing the file, Cancel or closing/unmounting the preview
invalidates the old result and stops its reader/worker. This releases application
references, not a guarantee of forensic memory erasure. The original image stays
unchanged and can still contain identifying metadata; this is not a scrubber.

## Supported subset and failure states

- At most 10 MiB and 4 million header pixels.
- PNG: still, noninterlaced 8-bit grayscale/RGB/grayscale-alpha/RGBA. Framing,
  CRCs, critical ordering, one bounded zlib stream, scanline lengths and filter
  byte ranges are checked. No pixel reconstruction or color interpretation.
- JPEG: one 8-bit baseline Huffman frame with 1 or 3 components and one scan,
  bounded local table and marker profiles. Entropy codes, MCU intervals and
  pixels are not decoded or validated. Damaged entropy can pass these framing
  observations. Dimensions alone do not establish renderability.

Valid palette/16-bit/interlaced/animated PNG and progressive/multiscan/other JPEG
profiles are **Unsupported**, not malicious, corrupt or AI-generated. Selected
malformed framing, truncated data and limits are reported separately. A runtime,
asset, deadline or invalid-result failure says **Unavailable**, never zero
findings or safe. No failure changes the behavior of independent PS/MT methods.

PNG expansion is capped at 32 MiB, metadata at 256 KiB and individual text at
64 KiB; chunk/marker counts are capped at 4096. Output is capped at 8192 bytes.
Startup/capture is bounded to 45 seconds and a worker evaluation to 6 seconds.
These are engineering bounds, not measured accessibility/accuracy guarantees.

## What reaches the network

Only public UI, method and the existing pinned Python runtime files are fetched.
File bytes, names, metadata and private results do not enter a request, account,
telemetry, research submission or browser storage. Initial use needs those public
files, about 14 MiB for the shared runtime. Local computation does not by itself
guarantee offline availability; this standalone fixture does not install an
additional service worker or expand an offline allowlist.

The two parsers are exact reviewed source from
8e1b1a23a1bef0659bf1ec567ceef647b5cd76a5. The browser uses a fixed, deny-by-default
projection of their pure declarations; OS/file/subprocess supervisors are excluded.
All full sources, declaration digests and applicable project LICENSE/NOTICE are
retained. A source/projection change fails the builder. Request-bound hashes and
closed result checks protect record identity; they are not independent proof of
semantic completeness, image authenticity or truth.

## Reproduce from this source checkout

Use the repository's existing pinned dependencies, Node22+ and Python3.12+.
No image SDK, account, model, Docker or new dependency is required.

```sh
python3 -m pytest tests/test_image_device.py -q
node --test tests/image-metadata-client.mjs
node --test tests/image-fixture-output.mjs
npm run build:site
node scripts/verify-image-metadata-site.cjs
```

`AITRUST_BUILD_PYTHON` and `AITRUST_VERIFY_PYTHON` select the existing trusted
build/reference interpreters. They are operator configuration, never file content.
The normal build reuses the existing runtime cache. The production-route
verifier serves that build only on an owned random loopback fixture with the
reviewed headers. The source also retains a standalone engineering fixture; its
builder refuses an existing output directory instead of clearing it. Browser proof, distinct review and protected integration/publication are
recorded separately; no physical-phone or full FA/PA/F-155 completion is implied.
