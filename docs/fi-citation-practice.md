# Try your own declared citation associations

This local practice tool gives you a complete invented example in two Python
commands. It creates the bound subject, attached reference corpus and declared
number associations for the existing canonical citation checker. No manual hashes
or context JSON. No account, network, service, model or package install is needed.
It requires CPython3.10+ on macOS or Linux. This is a computer CLI, not a phone or
browser tool; the source has not been newly verified on Linux by this increment.

## Two commands from the source folder

Download/clone the open-source project and open a terminal at its root. Choose a
new packet name in an **existing private0700 directory outside the checkout**.
Use its canonical absolute path; ancestor symlinks are refused. For example,
replace `/your/private/citation-demo` below with your actual private location.
If you need a disposable parent, `mktemp -d` creates one; resolve OS aliases such
as macOS `/var` to `/private/var` before using the path.

```sh
python3 scripts/prepare-citation-demo.py --output /your/private/citation-demo
python3 scripts/citation-resolution.py check --subject /your/private/citation-demo/subject.txt --corpus /your/private/citation-demo/corpus.json --sidecar /your/private/citation-demo/citations.json
```

Preparation saves exactly three files, all0600, in a new0700 packet directory.
It reads **none of your own messages or references**. The invented declaration
associates `[1]` with the attached `menu` document; `[2]` has no declaration;
`[1,2]` is outside the supported grammar. The second command completes with:

- `resolved-in-attached-corpus: 1`: a supported number has the declared document
  with those attached bytes. This does not prove the citation is correct.
- `unresolved-in-attached-corpus: 1`: no declaration for that supported number.
  This does not mean a source is absent elsewhere or that a claim is fabricated.
- `unsupported: 1`: the list syntax falls outside this finite marker profile.

`COMPLETE` means the inspection ran, not that the subject or references are true.
No confidence, contradiction, source-support, authenticity, freshness, FI/NF tag
or safety verdict is produced. Nothing is automatically uploaded, logged to a
server, enrolled in research or used for training.

## Inspect the exact bindings deliberately

The short console output omits words, document IDs, private paths, fingerprints
and evidence positions. The explicitly saved sidecar JSON binds the raw and
frozen Unicode15 NFC subject, corpus bytes/manifest, declared document raw/NFC
hashes, current parser/CLI/normalizer source identities and exact method profile.
The subject and corpus files contain invented text because you chose to save the
practice packet. Existing files/directories are never overwritten.

To save a separate text-free detailed report, choose a new filename:

```sh
python3 scripts/citation-resolution.py check --subject /your/private/citation-demo/subject.txt --corpus /your/private/citation-demo/corpus.json --sidecar /your/private/citation-demo/citations.json --private-report /your/private/citation-details.json
```

That report includes marker spans, numbers, declarations and hashes. These can
reveal or link information even without full words; inspect before sharing.
For your own bounded UTF-8 subject and supplied references, follow the existing
[canonical guide](fi-citation-sidecar.md). Prepare a new declaration sidecar for
changed raw subject bytes, references, mappings or method sources. The practice
command only creates its fixed invented example; it never infers your mapping.

## Refusal, cleanup and removal

Invalid arguments, unsafe files/directories, stale sources or an existing output
return exit2 with fixed `UNAVAILABLE`. No input/path is echoed. Failure attempts
to remove only files and the directory created by that invocation. If cleanup or
a later close cannot be confirmed, the response instead includes
`reason: output_commit_uncertain` and `output_may_exist: true`: inspect your exact
selected private directory before retrying. Do not assume rollback, success or
filesystem durability after that error, and do not automatically overwrite or
remove what remains. An existing packet is preserved on a repeated invocation.
Abrupt termination/power loss can leave private partial files without a result.

Delete the three files and their packet directory when you no longer want this
practice example; separately downloaded reports remain yours to remove. This is
logical file removal, not forensic memory/disk erasure. No daemon is installed.
The OS owner and selected source remain trusted. Another checker does not import
or depend on this optional preparer; its failure does not change canonical tags.

This is an approachable execution path for the existing resolution-evidence
component. Full T-FI independent contradiction/missing-evidence labels and error
rates, accepted tag mapping and required human operation remain open.
