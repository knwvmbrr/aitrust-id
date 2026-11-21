# Independent JPEG metadata observations

Before implementation: add a separate standard-library reader for explicitly
selected local JPEG files. Do not import, modify or depend on the PNG reader.
The outcome is dimensions/component count and fixed APP/COM inventory labels,
with private values omitted. Nothing is uploaded, decoded into pixels or tagged.

The supported subset is one 8-bit baseline Huffman frame, one scan containing all
1 or 3 components, local quantization/Huffman tables, and bounded marker/entropy
framing. Check lengths, header/table shapes, selected table references, escaped
FF bytes, restart-marker ordering and final EOI. Do not decode Huffman symbols,
DCT coefficients, pixels, color, orientation or restart MCU counts. This is not a
universal JPEG validator: entropy coding can be invalid despite valid framing.
Other precision/coding/component/multiscan/abbreviated or DNL-deferred-height
profiles are Unsupported.
Extra data after the first EOI is refused separately, without calling another
possible container corrupt. Metadata label prefixes are untrusted and opaque.

Bounds: 10 MiB selected file, 4 million header pixels, 4096 markers, 64 table
definitions, 128 metadata sections and 256 KiB aggregate metadata. No metadata
inflation, TIFF/XML parsing, thumbnail decoding or dynamic source lookup. One
fresh owned worker has 4 seconds wall, 2 seconds CPU, 8192 bytes stdout and a
256 MiB Linux address-space limit. Kill/reap only an unreaped owned process group.

Traverse the explicit file path with retained no-follow directory descriptors,
read one regular descriptor in bounded chunks, and pass that same descriptor to
the worker. Check path/descriptor identities again and bind the closed result to
captured encoded bytes and exact SOF header. Default text has no filename, raw
value or file hash. Explicit JSON exposes a linkable exact-file digest. This does
not scrub the original file, verify any credential/watermark or infer AI origin.

Owned files: new JPEG module/CLI/tests, this plan, guide/result, source-bound runs
and attributed change. Existing PNG/API/site/scopes/runtime dependencies stay
unchanged. Focus synthetic valid baseline files, unsupported variants, framing
truncation/tables/limits, closed result/input identity, privacy, no-follow/drift,
owned worker failures and actual no-site-packages CLI/recovery. Distinct review
precedes development-branch publication; no full tag closure is earned.

Primary format source: ITU-T T.81 / ISO/IEC 10918-1, Annexes B and C,
https://www.w3.org/Graphics/JPEG/itu-t81.pdf . Marker framing is distinct from
entropy decoding and application-specific metadata interpretation.
