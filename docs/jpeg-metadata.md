# Read basic JPEG details privately

**Experimental local CLI.** This companion is separate from the PNG reader and
is not a released image tag or a website checker.

From this source checkout, on macOS or Linux with Python 3.12 or later:

```sh
python3 -I -S -B scripts/inspect-jpeg-metadata.py --image /absolute/path/to/image.jpg
```

No account, Docker, image SDK or package installation is required. The worker
uses only Python's standard library; `-S` disables site packages. Select an
ordinary local file. URLs are never fetched; linked files/directories and pipes
are refused. An observation exits 0; an unsupported or incomplete check exits 2.

You get dimensions from the JPEG header, the component count, and fixed counts
of metadata sections. The reader can notice an Exif, XMP, ICC or JFIF label;
those are untrusted file bytes, not verified metadata. APP11 and other
application/comment sections are opaque. No stored names, GPS, comments, URLs,
filenames or file hash appear in the default output. The original file stays
unchanged and can still contain identifying information. This tool does not
scrub, sanitize, render, rotate or establish the image's color interpretation.

For a deliberately shareable machine-readable record:

```sh
python3 -I -S -B scripts/inspect-jpeg-metadata.py --image /absolute/path/to/image.jpg --format json
```

**JSON includes the captured encoded-file SHA256 and byte length.** A file hash
can identify/link other copies, even when raw metadata is omitted. There is no
automatic export, upload, storage or telemetry. Inspect before sharing output.
A hash of encoded bytes is not a canonical decoded-pixel identity.

## Supported observations and limits

`jpeg-metadata-observation/1.0.0` selects one 8-bit baseline Huffman frame with
1 or 3 components and one scan containing all components. It requires local
8-bit quantization tables and selected baseline DC/AC Huffman tables (destinations
0 or 1). Header sampling factors are bounded to 1–4 with at most 10 blocks per MCU.
Other coding, precision, component, multiscan, abbreviated-table or DNL-deferred-height profiles are
Unsupported. That does not mean malicious, AI-generated or corrupt. Trailing
bytes after the first EOI are separately refused; they may belong to another
container the reader does not interpret.

The checks cover marker/segment bounds, table and scan-header shapes, complete
selected table references, escaped FF bytes, restart-marker sequence and final
EOI. **Entropy codes, MCU restart intervals and pixels are not decoded or
validated.** Damaged entropy can therefore pass framing checks. An OBSERVED
record reports these selected facts; it is not proof of a valid image. Metadata
contents, including thumbnails, ICC data, TIFF/Exif and XMP/XML, remain opaque.
No watermark, Content Credential signature, trust, revocation, authorship,
AI origin or truth is verified. No FA/PA or other tag is issued.

Bounds: 10 MiB input, 4 million header pixels, 4096 markers, 64 table definitions,
128 metadata sections and 256 KiB aggregate metadata. Nothing is inflated or
expanded into pixels. The fresh worker has a 4 second wall budget, 2 second CPU
limit and 8192-byte output cap; Linux adds a 256 MiB address-space limit. The input
is read with retained no-follow descriptors and bounded chunks, then the same
file descriptor feeds the worker. Parent validation binds the exact captured
bytes and replays the small framing record. File identities are rechecked.
These limits do not promise a deadline for arbitrary underlying filesystem I/O.
Default failures contain fixed prose, not selected paths or embedded text.

```sh
python3 -B -m unittest discover -s tests -p test_jpeg_metadata.py -v
```

These are authored synthetic engineering controls, not independent image-origin
accuracy or human/physical-device acceptance. The existing PNG and C2PA tools
retain their separate contracts and dependencies. Full FA/PA/F-155 acceptance
remains open.

Primary format reference: [ITU-T T.81 / ISO/IEC 10918-1, Annexes B and C](https://www.w3.org/Graphics/JPEG/itu-t81.pdf).
