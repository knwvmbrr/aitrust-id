# Read a PNG without sharing its stored text

This local reader shows image dimensions and the kinds of metadata sections
stored in a PNG. It does not upload the file. Names, comments, GPS, URLs and
other embedded values stay out of its output. The original image is not changed
or scrubbed: it can still contain identifying information.

From the repository root, on macOS or Linux with Python 3.12 or later:

```sh
python3 -I -S -B scripts/inspect-png-metadata.py --image /absolute/path/to/image.png
```

No account, Docker, image SDK or package installation is required. `-S` disables
site packages; both this command and its worker use only Python's standard
library. Select a local regular file; URLs, symlinks and pipes are refused.
The command exits 0 when the supported observations complete, or 2 when they
cannot complete. An unsupported file or damaged section never becomes an empty
successful result.

The ordinary output includes dimensions, a count of stored text sections and
fixed labels such as “Author-labelled text fields.” A label is untrusted file
content, not proof of an author or editor. EXIF, color-profile and Content
Credential-shaped sections are counted without interpreting or verifying their
contents. No watermark is detected or verified. No metadata does not mean
human-made, AI-made, safe, authentic or true. No tag is issued.

For an explicit machine-readable record:

```sh
python3 -I -S -B scripts/inspect-png-metadata.py --image /absolute/path/to/image.png --format json
```

**JSON includes the exact captured-file SHA256 and byte length.** That hash can
link a private image to other copies. JSON still omits metadata values and the
filename. Default readable output omits the file hash. Redirecting or sharing
output is your choice; there is no automatic export, retention or telemetry.

## What this profile supports

`png-metadata-preflight/1.0.0` supports still, noninterlaced 8-bit grayscale, RGB,
grayscale-with-alpha and RGBA PNG files. Valid palette, 16-bit, Adam7-interlaced,
animated or unknown-critical-chunk variants are Unsupported. That does not mean
they are corrupt, malicious or AI-generated. JPEG and other formats are also
Unsupported.

The reader checks PNG framing, CRCs, critical ordering, one bounded image zlib
stream, exact supported scanline lengths and filter-byte range. It reads the
syntax and bounded decoded length of tEXt/zTXt/iTXt sections and reports fixed
category counts. It does not reconstruct pixels, render an image, apply color
profiles, establish orientation or calculate a canonical pixel identity.
Opaque ancillary sections are not fully validated. This is a selected preflight
profile, not a universal PNG validator or a credential-signature checker.

Limits are 10 MiB encoded bytes, 4 million pixels, 32 MiB expanded image scanlines,
4096chunks, 256 KiB total stored metadata and expanded text, 64 KiB per text value,
and 128 text sections. The isolated worker has a 4 second wall budget and 2 second
CPU limit; failure cleanup kills and reaps only its owned process group. Linux
also applies a 256 MiB address-space limit. The selected descriptor is size-checked
and read in bounded chunks before launching the worker. These controls do not
promise a deadline for arbitrary underlying filesystem I/O.

Errors distinguish Unsupported, damaged PNG structure, unreadable image data,
unreadable stored text, resource limits and an unavailable worker. The closed
worker record is tied to the captured encoded-file hash, byte length and IHDR.
That validates the software boundary; it is not independent verification of
metadata truth or semantic completeness.

The separate `scripts/inspect-manifest.py` tool can inspect an attached PNG
credential using its pinned optional SDK. It has its own contract and is not
called by this reader. This increment does not release FA/PA, implement SynthID
verification or change any full-tag acceptance requirement.

Primary format reference: [W3C PNG3 Recommendation, 24 June 2025](https://www.w3.org/TR/2025/REC-png-3-20250624/),
sections 5, 10, 11.2 and 11.3.3.

Focused synthetic checks:

```sh
python3 -B -m unittest discover -s tests -p test_png_metadata.py -v
```
