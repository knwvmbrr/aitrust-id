# Check the notices that travel with the tools

AI Trust ID keeps third-party notices with the resources it distributes. This
check helps you spot missing or changed files. It does not approve a license or
certify a tag.

1. Download the repository and open a terminal in its folder.
2. Run `python3 scripts/verify-asset-notices.py`.
3. Look for `"pass": true`. That means the selected files match the recorded
   review. If the check refuses, keep the original files and report the failure.

No account, upload, installed packages or model download is needed for this
source check. It reads the repository's selected public resources only. It does
not inspect your documents or save your text.

The check covers five self-hosted Nunito Sans font files, their OFL notice and
CSS, five frozen Unicode normalization files, the exact Unicode notice included
in the device/native resources, three runtime notices and the pinned optional
model card. It records four model artifact references without claiming to have
read or cleared the model weights.

After the normal site dependency installation and build, developers can also
run `python3 scripts/verify-asset-notices.py --prepared-runtime`. The five
prepared Pyodide files must match both the installed pinned package and the
recorded upstream archive members. Changing both local copies cannot satisfy
the retained upstream identities. This compares bytes; it does not execute the
runtime or validate a phone app.

For a stronger check, pass `--runtime-archive /path/to/the-pinned-pyodide.tgz`.
The verifier checks the exact npm integrity and recorded archive digest, then
reproduces five selected member identities without extracting or executing
anything. It does not download an archive. Obtain it only from the exact
`resolved` URL in the site's lock; archive processing remains bounded.

`--output runs/your-new-check.json` saves a public engineering receipt to a new
filename. Existing committed run destinations cannot be overwritten. Do not
put private paths or data in public reports.

`python3 scripts/verify-asset-notices.py --require-clearance` exits **1** even
when consistency passes. Full transitive/native/platform coverage, source-offer
obligations, model permissions and qualified review remain open. A hash is not
permission. The project license does not replace an upstream notice.

[Selected inventory](../sbom/assets/notices.json) ·
[Broader dependency notices](dependency-notices.md) ·
[Unicode's published notice and terms](https://www.unicode.org/copyright.html) ·
[Retained Unicode notice](../eval/vectors/unicode/LICENSE.txt)
