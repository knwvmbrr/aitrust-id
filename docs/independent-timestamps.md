# Give a file an independent timestamp

This optional development tool asks FreeTSA to sign a timestamp for your file's
SHA-256 digest. Your file stays on your device. You can timestamp a signed receipt
or another artifact, then verify the saved response offline. No account, fee or
AI Trust ID server is involved. Existing checkers work without it.

**Share deliberately:** the provider sees your IP, digest and request nonce.
Predictable files can be recognized from their hashes. This is an explicit choice;
the tool never automatically sends a response, prompt or editing history.

## Use it

Requires Linux or macOS, Python 3.12 or newer and **OpenSSL 3**, all open source. Use a trusted
distribution. No Docker or Python package installation is needed for this tool.

1. Obtain `cacert.pem` and `tsa.crt` separately from
   [FreeTSA's certificate page](https://www.freetsa.org/index_en.php). Check its
   published hashes. The current profile pins CA SHA-256
   `2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438`
   and TSA SHA-256
   `8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467`.
   A co-delivered certificate is not automatically trusted. Rotation refuses
   until the profile is deliberately reviewed and updated.
2. Choose your file and a new output directory. The `--send-digest` switch is
   your explicit permission to contact the independent provider:

```sh
python3 scripts/timestamp-artifact.py request YOUR_FILE \
  --ca-file cacert.pem --tsa-file tsa.crt \
  --output-dir NEW_TIMESTAMP_DIRECTORY --send-digest
```

3. Keep the original file, `request.tsq`, `response.tsr`, and separately trusted
   certificates. Verify without contacting us or the authority:

```sh
python3 scripts/timestamp-artifact.py verify YOUR_FILE \
  --query NEW_TIMESTAMP_DIRECTORY/request.tsq \
  --response NEW_TIMESTAMP_DIRECTORY/response.tsr \
  --ca-file cacert.pem --tsa-file tsa.crt
```

Replace the capitalized paths with your own. The output directory must be new;
the tool refuses overwrites and symlink inputs. Saved evidence has owner-only
permissions. The original file is not copied into the evidence directory.
Store it separately; losing it prevents verification of its binding.

## Understand the result

| Result | Meaning |
|---|---|
| Artifact and nonce matched | The signed response matches this exact file and request. |
| Authority time | The UTC time FreeTSA signed, under the separately pinned authority. |
| Revocation unchecked | Fresh certificate-status evidence was not obtained. |
| Authorship unestablished | A timestamp does not establish who created the file or whether it is true. |
| Certified validity / tag issuance false | This component issues no PA, FA, IV or other tag. |

The JSON record contains hashes, byte count, authority time and these limits; no
original words. Invalid input, altered bytes, wrong nonce, untrusted certificates,
unavailable provider or OpenSSL failure exits **2** with no accepted timestamp.
Success exits **0** for the bounded checks above. Verification currently uses
certificate validity at the verifier's current time; it is not long-term archival
validation after certificate expiry or revocation.

The provider's CRL interval does not justify claiming a fresh status check. This
tool therefore never returns `VALID` or a safety clearance. Trust in the authority's
clock and root remains explicit. It measures neither authorship, forgery resistance
nor tag accuracy. To verify a signed receipt too, first run the receipt signature
check described in [offline-receipts.md](offline-receipts.md); timestamp binding
does not replace that signature check.

## Evidence and scope

The public fixture contains a **real independently issued token for synthetic
public text**, its exact request and provider certificates. It is not a real user
example or independent tag validation dataset. Tests verify the actual token and
reject changed artifacts, requests, responses and trust inputs. Mocked transport
tests cover consent and local output behavior only.

Run `python3 -m pytest tests/test_independent_timestamp.py -q` in the project's
verification environment. Real provider issuance and offline Linux checks are
recorded separately in [actual issuance](../runs/2026-10-10-independent-timestamp-issuance.json), [network-isolated Linux verification](../runs/2026-10-10-independent-timestamp-offline-linux.json), and [signed composition receipt → real timestamp](../runs/2026-10-10-composition-receipt-timestamp.json). The first local verification failure is preserved
with its cause: OpenSSL's `ts` command does not accept the CMS trust-disabling
switches. The corrected verifier explicitly selects its CA file, directory and
store; CMS pins the signer using `-nointern`.

This implements a development timestamp component for F-124. RFC-0002 remains a
proposal. Revocation/freshness, usable key recovery, group receipts and validated
authorship tags have their own unfinished jobs. No AI Trust ID authority is operated.
See [architecture and risks](independent-timestamp-plan.md) and
[RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html).
