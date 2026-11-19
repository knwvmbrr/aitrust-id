# HP literal-detail explorer — architecture and risk boundaries

Build one standalone, opt-in browser component toward F-015/T-HP. Reuse the exact
canonical `literal-quantitative-observations/1.0.1` Python method, including its
existing literal sentence/marker helpers and frozen Unicode15 normalization.
Do not call MT analysis or depend on PS/MT workers, state, availability or results.
Shared immutable helper/runtime artifacts are infrastructure, not tag votes.

The method counts supported ASCII numeric/date-shaped tokens and records whether
an HTTP(S) URL or numbered marker overlaps the same literal sentence unit. It
does not establish truth, source support, valid calendar dates, uncertainty,
semantic specificity or hallucination. No HP or other tag is issued. Identifiers,
percent/hash clipping fences, marker-contained digits and non-ASCII/long-token
skips must remain exactly as the canonical method defines them.

An HP-only Python adapter preserves the entire original record and adds raw
UTF-8 SHA/count/bytes plus frozen-NFC SHA/count and exact source identities. The
browser uses the existing generated frozen normalizer, not host String.normalize.
Closed envelope, original, parameter, source and detail-row schemas validate all
counts, typed flags, span/unit/marker relationships and both input identities
before deeply frozen results can enter explanation or optional private details.
Unknown fields or corrupt records are refused, never filtered into a verdict.

Package unmodified sources, normalizers, LICENSE, NOTICE and Unicode attribution
in a deterministic HP-only hash-addressed source payload. Capture selected source
bytes through no-follow/nonblocking regular-file descriptors, enforce per-file
bounds before reads, hold root/parent/file identities and recheck every input
before replacing output files. Input refusal preserves existing artifacts. Do not
import captured source modules to derive build constants.

Each explicit run owns a fresh HP module Worker and Pyodide instance. The worker
checks the HP source payload and every member hash before creating an ephemeral
in-memory Python filesystem. Loading/evaluation deadlines, output caps and edit,
Clear/cancel/unmount invalidation terminate only that worker. The canonical input
bounds remain 8,000 codepoints / 32,000 bytes, 256 supported details and 48 token
characters. If the full original detail record exceeds its existing 131,072-byte
private-record budget, or the browser envelope exceeds 262,144 bytes, return
Unavailable without clipping or changing the method's classifications.

Use a small lazy HP-only slot with local import/render failure containment. No
runtime download or analysis occurs before the user runs the form. Native labeled
controls, existing brand tokens, calm counts and optional NFC positions support
phone/desktop use. No account, text upload, persistence, telemetry, clipboard
capture or server endpoint is added. Static code/runtime delivery still needs a
connection; no offline installation is promised.

Deliver a separate unpublished fixture and exact Python/browser parity controls.
Exercise malformed/oversized/Unicode input, raw-NFC-equivalent replay, corrupted
source/count/span/raw-field records, missing chunks, worker failure/timeouts,
edit/Clear/cancel/unmount, private detail opt-in, no content requests/storage,
keyboard, 320px/enlarged text and light/dark layout. Shared mounting, build scripts,
site copy/status and global scope/state remain PM-owned. Physical iPhone,
assistive-technology users and independent HP validation remain open.
